"""WP-002 — the drive-journey-walk fixture harness.

`_drive_journey_walk.py` is the methodology driver the design-stage journey-walk
scenarios (SC-06..SC-09, SC-19) drive. It walks a fixture's journey hop-by-hop,
classifies each hop EXISTS / planned-WP / GAP, writes a `## Journey Walk` section
to ``--out``, and exits non-zero when a bare GAP blocks design completion
(fail-closed at the walk level, NFR-S04). The tool surface applies the sharper
binding-EXISTS bar (ADR-003 / FR-09): a hop is EXISTS only when BOTH the handler
AND its ServiceSpec binding are cited; a handler that merely serves is a GAP.

These are unit-level drives against the real driver: a clean UI fixture produces
a walk section and exits 0; the gap fixtures exit 1. Placed under ``tests/unit/``
so ``branch-ci.yml`` (which runs only ``tests/unit/`` on ``feat/wp-*`` pushes)
actually executes the behavioural gate — a test at the ``tests/`` root would
never run on the gating CI (the recurring "CI never runs that dir" failure).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
_SCRIPTS_DIR = _HERE.parent.parent
_DRIVER = _SCRIPTS_DIR / "_drive_journey_walk.py"
_FIXTURES = _SCRIPTS_DIR / "tests" / "fixtures" / "methodology"

if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import _drive_journey_walk as djw  # noqa: E402  (after sys.path insert)


def _run(fixture: str, surface: str, out: Path) -> subprocess.CompletedProcess:
    """Drive the walk on a fixture via the CLI, returning the completed process."""
    return subprocess.run(
        [
            sys.executable,
            str(_DRIVER),
            "--fixture",
            str(_FIXTURES / fixture),
            "--surface",
            surface,
            "--out",
            str(out),
        ],
        capture_output=True,
        text=True,
    )


def test_drive_journey_walk_emits_walk_section(tmp_path: Path) -> None:
    """A clean UI fixture drives a completed walk and writes a Journey Walk section."""
    out = tmp_path / "DESIGN.md"
    result = _run("ui-clean", "ui", out)

    assert result.returncode == 0, f"clean walk must exit 0; stderr={result.stderr}"
    assert out.is_file(), "the driver must write the design doc to --out"
    text = out.read_text(encoding="utf-8")
    assert "## Journey Walk" in text, "the doc must carry a Journey Walk section"
    # Every hop classified with a status column; no hop classified GAP in the
    # clean fixture (the summary line legitimately reads "no bare GAP").
    assert "exists" in text.lower()
    assert "| GAP |" not in text, "a clean walk must have no GAP-status hop"
    assert "no bare GAP" in text


def test_bare_gap_yields_nonzero_exit(tmp_path: Path) -> None:
    """SC-07 — a UI hop with neither a component nor a planned WP blocks design."""
    out = tmp_path / "DESIGN.md"
    result = _run("ui-with-gap", "ui", out)

    assert result.returncode == 1, (
        f"a bare GAP must fail-closed (exit 1); rc={result.returncode} "
        f"stderr={result.stderr}"
    )
    # The walk section is still written so the human can see WHERE the gap is.
    assert out.is_file()
    assert "| GAP |" in out.read_text(encoding="utf-8")


def test_tool_serving_no_binding_is_gap(tmp_path: Path) -> None:
    """SC-09 — a tool handler that serves but has no ServiceSpec binding is a GAP."""
    out = tmp_path / "DESIGN.md"
    result = _run("tool-serving-no-binding", "tool", out)

    assert result.returncode == 1, (
        f"a handler without a binding is a GAP (FR-09 / NFR-S02), must exit 1; "
        f"rc={result.returncode} stderr={result.stderr}"
    )
    text = out.read_text(encoding="utf-8")
    assert "GAP" in text


def test_clean_tool_surface_with_binding_passes(tmp_path: Path) -> None:
    """A tool surface whose operations cite BOTH handler and binding walks clean."""
    out = tmp_path / "DESIGN.md"
    result = _run("sample-tool-surface", "tool", out)

    assert result.returncode == 0, (
        f"a fully-bound tool surface must exit 0; stderr={result.stderr}"
    )
    text = out.read_text(encoding="utf-8")
    assert "## Journey Walk" in text
    assert "exists" in text.lower()


def test_walk_output_is_deterministic(tmp_path: Path) -> None:
    """NFR-04 — an unchanged fixture produces a byte-identical walk section twice."""
    out_a = tmp_path / "a.md"
    out_b = tmp_path / "b.md"
    _run("ui-clean", "ui", out_a)
    _run("ui-clean", "ui", out_b)

    assert out_a.read_text(encoding="utf-8") == out_b.read_text(encoding="utf-8")


# ─── Unit-level classification + loader branches (called directly) ──────────


def test_classify_hop_ui_branches() -> None:
    assert djw.classify_hop({"component": "f.py#x"}, "ui") == (djw.EXISTS, "f.py#x")
    assert djw.classify_hop({"planned_wp": "WP-9"}, "ui") == (djw.PLANNED, "WP-9")
    assert djw.classify_hop({}, "ui") == (djw.GAP, "")


def test_classify_hop_tool_branches() -> None:
    bound = {"handler": "h.py#c", "binding": "s.yaml#op"}
    assert djw.classify_hop(bound, "tool") == (djw.EXISTS, "h.py#c + s.yaml#op")
    # planned WP on the tool surface is planned-WP, not GAP
    assert djw.classify_hop({"planned_wp": "WP-9"}, "tool") == (djw.PLANNED, "WP-9")
    # handler that serves but has no binding is a GAP (FR-09)
    status, detail = djw.classify_hop({"handler": "h.py#c"}, "tool")
    assert status == djw.GAP and "no ServiceSpec binding" in detail
    assert djw.classify_hop({}, "tool") == (djw.GAP, "")


def test_planned_wp_hop_does_not_block(tmp_path: Path) -> None:
    """A planned-WP hop is not a bare GAP — the walk completes (exit 0)."""
    fixture = {
        "journey": "j",
        "scenarios": [
            {
                "id": "SC-X",
                "surface": "ui",
                "hops": [{"name": "h", "planned_wp": "WP-9"}],
            }
        ],
    }
    fpath = tmp_path / "f.json"
    fpath.write_text(json.dumps(fixture), encoding="utf-8")
    out = tmp_path / "o.md"
    rc = djw.main(["--fixture", str(fpath), "--surface", "ui", "--out", str(out)])
    assert rc == 0
    assert "planned-WP" in out.read_text(encoding="utf-8")


def test_no_scenarios_for_surface_is_not_a_gap(tmp_path: Path) -> None:
    """A journey with no scenarios on the requested surface walks clean (exit 0)."""
    fixture = {
        "journey": "j",
        "scenarios": [{"id": "SC-X", "surface": "ui", "hops": []}],
    }
    fpath = tmp_path / "f.json"
    fpath.write_text(json.dumps(fixture), encoding="utf-8")
    out = tmp_path / "o.md"
    rc = djw.main(["--fixture", str(fpath), "--surface", "tool", "--out", str(out)])
    assert rc == 0
    assert "No `tool`-surface scenarios" in out.read_text(encoding="utf-8")


def test_load_fixture_from_directory_and_name(tmp_path: Path) -> None:
    """load_fixture resolves a directory (first JSON) and a bare name (<name>.json)."""
    (tmp_path / "only.json").write_text(json.dumps({"journey": "d"}), encoding="utf-8")
    assert djw.load_fixture(tmp_path)["journey"] == "d"
    assert djw.load_fixture(tmp_path / "only")["journey"] == "d"


def test_load_fixture_empty_directory_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        djw.load_fixture(tmp_path)
