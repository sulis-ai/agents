"""WP-009 — the UC-flow → scenario coverage assertion (`_assert_flow_scenario_map.py`).

SC-10: every use-case flow (main / alternate / exception) must map to at least
one verifiable scenario, or be recorded out-of-scope. The script reads a
flow-map fixture and exits 0 iff every enumerated flow is covered; non-zero
(naming the uncovered flows) otherwise — fail-closed (NFR-S04): an absent
mapping is a gap, never silently passed.

Placed under ``tests/unit/`` so ``branch-ci.yml`` (which runs only
``tests/unit/`` on ``feat/wp-*`` pushes) actually executes the gate.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_SCRIPTS_DIR = _HERE.parent.parent
_ASSERT = _SCRIPTS_DIR / "_assert_flow_scenario_map.py"

if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


def _run(fixture: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(_ASSERT), str(fixture)],
        capture_output=True,
        text=True,
    )


def _write(tmp_path: Path, payload: dict) -> Path:
    f = tmp_path / "flow-map.json"
    f.write_text(json.dumps(payload), encoding="utf-8")
    return f


def test_every_flow_has_a_scenario(tmp_path: Path) -> None:
    """SC-10 — when each flow has a covering scenario, the gate passes (exit 0)."""
    fixture = _write(
        tmp_path,
        {
            "flows": ["UC-01:main", "UC-01:2a", "UC-01:5a"],
            "scenarios": [
                {"id": "SC-01", "covers": ["UC-01:main"]},
                {"id": "SC-02", "covers": ["UC-01:2a", "UC-01:5a"]},
            ],
        },
    )
    result = _run(fixture)
    assert result.returncode == 0, (
        f"every flow covered must exit 0; rc={result.returncode} "
        f"stderr={result.stderr}"
    )


def test_uncovered_flow_blocks(tmp_path: Path) -> None:
    """SC-10 (negative) — an uncovered exception flow fails the gate (exit 1)."""
    fixture = _write(
        tmp_path,
        {
            "flows": ["UC-01:main", "UC-01:5b"],
            "scenarios": [{"id": "SC-01", "covers": ["UC-01:main"]}],
        },
    )
    result = _run(fixture)
    assert result.returncode == 1, (
        f"an uncovered flow must fail-closed (exit 1, NFR-S04); "
        f"rc={result.returncode} stderr={result.stderr}"
    )
    assert "UC-01:5b" in result.stderr, "the gate must name the uncovered flow"


def test_out_of_scope_flow_is_not_a_gap(tmp_path: Path) -> None:
    """A flow recorded out-of-scope is covered-by-record, not a gap (NR-05)."""
    fixture = _write(
        tmp_path,
        {
            "flows": ["UC-01:main", "UC-01:4a"],
            "scenarios": [{"id": "SC-01", "covers": ["UC-01:main"]}],
            "out_of_scope": ["UC-01:4a"],
        },
    )
    result = _run(fixture)
    assert result.returncode == 0, (
        f"an explicitly out-of-scope flow must not be a gap; "
        f"rc={result.returncode} stderr={result.stderr}"
    )


def test_no_flows_is_clean(tmp_path: Path) -> None:
    """An empty flow inventory walks clean (exit 0) — nothing to cover."""
    fixture = _write(tmp_path, {"flows": [], "scenarios": []})
    assert _run(fixture).returncode == 0


def test_unreadable_fixture_is_bad_input(tmp_path: Path) -> None:
    """A missing fixture is bad input (exit 2)."""
    assert _run(tmp_path / "absent.json").returncode == 2


def test_malformed_json_is_bad_input(tmp_path: Path) -> None:
    """A non-JSON fixture is bad input (exit 2), not a coverage verdict."""
    f = tmp_path / "flow-map.json"
    f.write_text("{not json", encoding="utf-8")
    result = _run(f)
    assert result.returncode == 2
    assert "not valid JSON" in result.stderr
