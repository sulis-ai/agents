"""WP-009 — the single-scenario driver (`_drive_scenario.py`).

SC-11 / NFR-R02: an undrivable tool scenario must be **recorded deferred** — a
visible deferred-infrastructure record — never a silent skip. A scenario that is
drivable drives and reports observed; one that is not (no sandbox / credential)
writes a deferred record and exits with a distinct, documented code so the
caller can tell "deferred" apart from "passed" and from "failed".

Placed under ``tests/unit/`` so ``branch-ci.yml`` runs it.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_SCRIPTS_DIR = _HERE.parent.parent
_DRIVER = _SCRIPTS_DIR / "_drive_scenario.py"

if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

# Documented exit codes (mirrored from the driver):
RC_OBSERVED = 0
RC_DEFERRED = 3


def _write(tmp_path: Path, payload: dict) -> Path:
    f = tmp_path / "scenario.json"
    f.write_text(json.dumps(payload), encoding="utf-8")
    return f


def _run(fixture: Path, out: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(_DRIVER), "--scenario", str(fixture), "--out", str(out)],
        capture_output=True,
        text=True,
    )


def test_undrivable_tool_recorded_deferred(tmp_path: Path) -> None:
    """SC-11 — an undrivable tool scenario is recorded deferred, never skipped."""
    fixture = _write(
        tmp_path,
        {
            "id": "SC-14",
            "surface": "tool",
            "drivable": False,
            "deferred_need": "tool-drive-sandbox: dev-tier endpoint + credential",
        },
    )
    out = tmp_path / "deferred.json"
    result = _run(fixture, out)

    # Distinct exit code — NOT 0 (would read as observed/passed), NOT a crash.
    assert result.returncode == RC_DEFERRED, (
        f"an undrivable tool scenario must exit {RC_DEFERRED} (deferred), "
        f"never 0 (would be a fake pass) nor a silent skip; "
        f"rc={result.returncode} stderr={result.stderr}"
    )
    # The deferred need is recorded — visible, never silent (NFR-R02).
    assert out.is_file(), "the driver must write a deferred record"
    record = json.loads(out.read_text(encoding="utf-8"))
    assert record["disposition"] == "deferred"
    assert record["scenario"] == "SC-14"
    assert "tool-drive-sandbox" in record["deferred_need"]


def test_drivable_scenario_observed(tmp_path: Path) -> None:
    """A drivable scenario drives and reports observed (exit 0)."""
    fixture = _write(
        tmp_path,
        {"id": "SC-13", "surface": "tool", "drivable": True},
    )
    out = tmp_path / "result.json"
    result = _run(fixture, out)
    assert result.returncode == RC_OBSERVED, (
        f"a drivable scenario must exit 0 (observed); rc={result.returncode} "
        f"stderr={result.stderr}"
    )
    record = json.loads(out.read_text(encoding="utf-8"))
    assert record["disposition"] == "observed"
    assert record["scenario"] == "SC-13"


def test_undrivable_without_explicit_need_still_recorded(tmp_path: Path) -> None:
    """An undrivable scenario with no stated need still records a deferred entry."""
    fixture = _write(tmp_path, {"id": "SC-15", "surface": "tool", "drivable": False})
    out = tmp_path / "deferred.json"
    result = _run(fixture, out)
    assert result.returncode == RC_DEFERRED
    record = json.loads(out.read_text(encoding="utf-8"))
    assert record["disposition"] == "deferred"
    assert record["deferred_need"]  # a default need is recorded, never blank


def test_unreadable_scenario_is_bad_input(tmp_path: Path) -> None:
    """A missing scenario file is bad input (exit 2)."""
    result = _run(tmp_path / "absent.json", tmp_path / "out.json")
    assert result.returncode == 2


def test_malformed_scenario_is_bad_input(tmp_path: Path) -> None:
    """A non-JSON scenario file is bad input (exit 2)."""
    f = tmp_path / "scenario.json"
    f.write_text("{nope", encoding="utf-8")
    result = _run(f, tmp_path / "out.json")
    assert result.returncode == 2
    assert "not valid JSON" in result.stderr
