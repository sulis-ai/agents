"""WP-010 — the scenarios report surfaces the surface tag + UC-flow coverage.

`scenarios/SKILL.md` produces a read-only founder-facing report of a change's
verifiable scenarios. This WP extends it to surface, in plain English:

  * each scenario's **surface** (``ui`` | ``tool`` — the WP-007 tag), and
  * the change's **UC-flow-coverage** verdict (``covered`` | ``gaps`` — the
    WP-008 gate, ``_verify_uc_flow_coverage.py``),

rolled up alongside the pre-existing scenario-required (#103) and
journey-coverage (#86) verdicts. BDR-002: three distinct gates, ONE founder-
facing rollup — the rollup must not collapse the gates' distinct logic.

It is a **documentation extend** (``primitive: extend``, ``kind: docs``):
there is no runtime behaviour to drive, so the RED gate is a *doc-lint* that
pins the realized invariants on the live founder-facing ``scenarios/SKILL.md``.
The skill is the artifact; the lint asserts the report description references
the surface dimension and the UC-flow verdict, and stays founder-English (no
``SC-NN`` scenario ids in the founder-facing rollup — FE-06, C-06, the WP
Contract: "uncovered flows shown as plain titles").

Stdlib + pytest only, Python 3.11-safe. Paths resolve relative to this test
file so the suite is location-stable inside any worktree (lesson #60: this
lives in ``tests/unit/`` — the dir branch-ci actually runs).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# tests/unit/ -> tests/ -> scripts/ -> sulis/ -> plugins/ -> repo-root
_REPO_ROOT = Path(__file__).resolve().parents[5]
_SKILL = _REPO_ROOT / "plugins" / "sulis" / "skills" / "scenarios" / "SKILL.md"


def _read(path: Path) -> str:
    if not path.exists():
        pytest.fail(
            f"{path.name} missing at {path}. WP-010 extends this file; the "
            "doc-lint assertions cannot run until it exists."
        )
    return path.read_text(encoding="utf-8")


# ─── The report surfaces the surface tag + the UC-flow-coverage verdict ──────


def test_report_shows_tool_scenarios_and_uc_flow_coverage():
    """The report surfaces each scenario's SURFACE (ui|tool — WP-007) and the
    change's UC-FLOW-COVERAGE verdict (covered|gaps — WP-008), rolled up
    alongside the existing verdicts (BDR-002: three gates, one rollup)."""
    text = _read(_SKILL)
    low = text.lower()

    # 1. The surface dimension (WP-007's ui|tool tag) is surfaced per scenario.
    assert "surface" in low, (
        "The report must surface each scenario's surface dimension (the WP-007 "
        "ui|tool tag). 'surface' does not appear in scenarios/SKILL.md."
    )
    # Both surface values named — the report distinguishes ui from tool
    # scenarios (the founder sees per-surface flow coverage).
    assert re.search(r"\btool\b", low) and re.search(r"\bui\b", low), (
        "The report must name BOTH surface values (ui and tool) so the founder "
        "can see per-surface flow coverage (WP-007 tag, DESIGN §6.5 hop A6)."
    )

    # 2. The UC-flow-coverage verdict (WP-008) is surfaced in the rollup.
    assert re.search(r"uc[\s-]?flow", low) or "flow coverage" in low, (
        "The report must surface the UC-flow-coverage verdict (the WP-008 "
        "gate). No reference to UC-flow coverage in scenarios/SKILL.md."
    )
    # Its two verdicts appear (covered | gaps) — the rollup shows the verdict.
    assert "covered" in low and "gaps" in low, (
        "The report must surface the UC-flow-coverage verdict values "
        "(covered | gaps) so the founder sees whether every UC flow has a "
        "covering scenario (WP-008, FR-12/13)."
    )

    # 3. The gate that produces the verdict is named so the surface is wired to
    #    the real WP-008 source, not re-derived (read-only — Contract invariant).
    assert "_verify_uc_flow_coverage" in text, (
        "The report must read the UC-flow verdict from the WP-008 gate "
        "(_verify_uc_flow_coverage.py) — read-only, the brain/gate is truth. "
        "It must not re-derive the verdict itself (Contract: changes no verdict "
        "logic)."
    )

    # 4. BDR-002: three DISTINCT gates roll up into one result. The rollup must
    #    name all three verdicts without collapsing them.
    assert "#103" in text and "#86" in text, (
        "BDR-002: the rollup unifies three DISTINCT gates — the scenario-"
        "required gate (#103), the journey-coverage check (#86), and the "
        "UC-flow-coverage gate (WP-008). All three must be named in the rollup "
        "so their distinct logic is preserved (not collapsed)."
    )


def test_report_uses_plain_titles_not_ids():
    """The founder-facing rollup carries no SC-NN scenario ids — uncovered
    flows are shown as plain titles (FE-06, C-06, the WP Contract)."""
    text = _read(_SKILL)

    # No bare SC-NN scenario identifier anywhere in the founder-facing skill
    # body (e.g. "SC-13", "SC-01"). The Contract: "no scenario ids in
    # founder-facing prose; uncovered flows shown as plain titles".
    leaked = re.findall(r"\bSC-\d{2,}\b", text)
    assert not leaked, (
        f"Founder-facing scenarios/SKILL.md leaks scenario ids {leaked!r}. "
        "The rollup must surface uncovered flows as PLAIN TITLES, never as "
        "SC-NN ids (FE-06, C-06, the WP Contract)."
    )

    # The skill must explicitly instruct surfacing uncovered flows as plain
    # titles (the positive form of the no-ids invariant) — so the discipline is
    # encoded, not merely incidentally absent.
    low = text.lower()
    assert "plain title" in low or "plain-title" in low, (
        "The skill must instruct that uncovered flows are surfaced as plain "
        "titles (the founder-English rollup form), not scenario ids "
        "(WP Contract: 'uncovered flows shown as plain titles')."
    )
