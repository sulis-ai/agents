"""Journey-rigor #3 — the design stage walks the journey before handing off.

Structural assertion over the live draft-architecture (+ audit) SKILL.md: the
journey-walk step must exist, pull the full scenario set, walk hop-by-hop with
an existence check, and GATE the design. Without it, a half-built round-trip
(the consumption half missing) passes design + per-piece review — the failure
behind four green-but-broken login attempts.
"""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[5]
_DRAFT = _ROOT / "plugins" / "sulis" / "skills" / "draft-architecture" / "SKILL.md"
_AUDIT = _ROOT / "plugins" / "sulis" / "skills" / "audit" / "SKILL.md"


def _text(p: Path) -> str:
    assert p.is_file(), f"missing {p}"
    return p.read_text(encoding="utf-8")


def test_draft_architecture_has_the_journey_walk_step() -> None:
    t = _text(_DRAFT).lower()
    assert "walk the journey" in t, "draft-architecture must have a journey-walk step"
    assert "hop" in t and ("outside-in" in t or "work-backwards" in t or "work backwards" in t)


def test_journey_walk_pulls_the_full_scenario_set() -> None:
    t = _text(_DRAFT)
    assert "find_scenarios_for_journey" in t, (
        "the walk must pull the journey's full scenario set (check ALL, build some)"
    )


def test_journey_walk_is_a_gate_with_an_existence_check() -> None:
    t = _text(_DRAFT).lower()
    # existence check (exists / planned / gap) + a real gate before plan-work
    assert "gap" in t and "exists" in t
    assert "gate" in t and "not complete" in t and "plan-work" in t, (
        "the walk must GATE design completion — design 'not complete' (a bare GAP "
        "blocks) before plan-work"
    )


def test_audit_brownfield_also_walks_the_journey() -> None:
    t = _text(_AUDIT).lower()
    assert "walk the journey" in t or "journey walk" in t, (
        "the brownfield audit stage must also walk the journey against existing code"
    )
