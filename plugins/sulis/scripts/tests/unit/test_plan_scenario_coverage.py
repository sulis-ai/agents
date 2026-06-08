"""Journey-rigor #4 — plan-work enforces journey scenario coverage.

Structural assertion over the live plan-work SKILL.md: the scenario-coverage
gate must exist, call the objective checker, and GATE the decompose. Without
it, a change builds *some* of a journey and silently ships the rest as a hole —
the half-built-round-trip class behind four green-but-broken login attempts.
The design stage walks the journey (#85); this is the plan stage that proves
every not-green hop has a WP (check ALL, build some).
"""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[5]
_PLAN = _ROOT / "plugins" / "sulis" / "skills" / "plan-work" / "SKILL.md"


def _text() -> str:
    assert _PLAN.is_file(), f"missing {_PLAN}"
    return _PLAN.read_text(encoding="utf-8")


def test_plan_work_has_the_scenario_coverage_gate() -> None:
    t = _text().lower()
    assert "scenario-coverage gate" in t, (
        "plan-work must have a scenario-coverage gate (check ALL, build some)"
    )
    # the "build some / check all" framing (markdown emphasis sits between words,
    # e.g. "*check all* of it" — match the words, not a contiguous phrase)
    assert "builds " in t and "some" in t and "check" in t and "journey" in t


def test_gate_calls_the_objective_checker() -> None:
    t = _text()
    assert "verify_scenario_coverage" in t, (
        "the gate must call the objective brain checker, not trust a claim"
    )


def test_gate_blocks_on_gaps_and_classifies() -> None:
    t = _text().lower()
    # classification vocabulary + a real gate
    assert "gap" in t and "out-of-scope" in t and "planned" in t
    assert "gate" in t and "not done" in t, (
        "a journey scenario with no WP and no out-of-scope record (a GAP) "
        "must block the decompose"
    )


def test_rubric_lists_p9_journey_coverage() -> None:
    t = _text()
    assert "P9" in t and "scenario coverage" in t.lower(), (
        "the Decompose Validation Rubric must list P9 — Journey scenario coverage"
    )
