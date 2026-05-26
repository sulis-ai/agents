"""Structure test: the agents/ top level holds only real agents (WP-009).

A verification *report* (`sulis.VERIFICATION_REPORT.md`, no YAML frontmatter)
was sitting directly under `plugins/sulis/agents/`, where WP-002's
`discover()` globs `agents/*.md` non-recursively. That made the report a
**parse failure** in the inventory, which forced WP-007's coverage gate
`passed = False` and blocked R10 (`test_gate_passes_clean_marketplace`). The
report is genuinely misplaced; per ADR-004 (closed-world, silence is never
consent) the fix is to *move the file* into the established `iterations/`
archive — not to weaken the glob or add a gate skip-heuristic.

Per the EP-07 / Fowler refactoring discipline, this test pins the current
state before the move. It FAILS RED against the pre-move tree on two
post-move invariants:

  * `test_every_top_level_agent_md_has_frontmatter` — `sulis.VERIFICATION_REPORT.md`
    has no frontmatter, so the parse yields no `name`;
  * `test_relocated_report_exists` — the archive target path does not yet exist.

Both PASS once the `git mv` relocates the report into
`agents/iterations/sulis/1/VERIFICATION_REPORT.md`. The suite stays green at
HEAD after the move — these two invariants are the auditable characterisation
of "the agents/ top level is parse-clean", independent of WP-007's generic
gate assembly.

Stdlib + pytest only, Python 3.11-safe. Reads the live agent files via the
established `_wpxlib.read_frontmatter` reader so the test exercises the same
parse path the gate uses (mirrors `test_route_status_duplicate.py`).
"""

from __future__ import annotations

from pathlib import Path

from _wpxlib import read_frontmatter

# Resolve the marketplace agents root relative to this test file.
# tests/unit/ -> tests/ -> scripts/ -> sulis/ -> plugins/sulis/
_AGENTS_ROOT = Path(__file__).resolve().parents[3] / "agents"

# The archive target for the relocated iteration-1 report. The sibling
# iterations/sulis/2/VERIFICATION_REPORT.md already exists, so the shape is
# the established convention — not a new mechanism (CP-01).
_RELOCATED_REPORT = (
    _AGENTS_ROOT / "iterations" / "sulis" / "1" / "VERIFICATION_REPORT.md"
)


def _top_level_agent_files() -> list[Path]:
    """The `*.md` directly under agents/, matching discover()'s glob.

    Non-recursive on purpose: discover() globs `agents/*.md`, so the
    iterations/ archive (and any nested report) is correctly excluded.
    """
    return sorted(_AGENTS_ROOT.glob("*.md"))


def test_agents_root_exists():
    """Guard: the agents root resolves to a real directory in the live tree."""
    assert _AGENTS_ROOT.is_dir(), f"missing agents root {_AGENTS_ROOT}"


def test_every_top_level_agent_md_has_frontmatter():
    """Every top-level `agents/*.md` must parse to frontmatter with a `name`.

    Fails RED against the pre-move tree because `sulis.VERIFICATION_REPORT.md`
    (a report, not an agent) has no YAML frontmatter, so `read_frontmatter`
    yields no `name`. Passes once the report is relocated out of the
    `agents/*.md` glob into the iterations/ archive.
    """
    offenders = []
    for md in _top_level_agent_files():
        fm = read_frontmatter(md)
        if not fm.get("name"):
            offenders.append(md.name)
    assert not offenders, (
        "top-level agents/*.md without parseable frontmatter `name`: "
        f"{offenders}. A file under agents/ must be a real agent (with "
        "frontmatter) or it belongs in the iterations/ archive (ADR-004 — "
        "the file is misplaced; move it, do not weaken discover())."
    )


def test_relocated_report_exists():
    """The iteration-1 report lives in the established iterations/ archive.

    Fails RED (the target path does not yet exist); passes after the
    `git mv` relocates the stray report into
    `agents/iterations/sulis/1/VERIFICATION_REPORT.md`.
    """
    assert _RELOCATED_REPORT.is_file(), (
        f"expected relocated report at {_RELOCATED_REPORT} "
        "(git mv from agents/sulis.VERIFICATION_REPORT.md)."
    )
