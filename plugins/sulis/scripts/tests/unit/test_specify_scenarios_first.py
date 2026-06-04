"""Journey-rigor #5 — specify authors scenarios FIRST + verifiable.

Structural assertion over the live specify SKILL.md: the Work-Backwards
principle (the journey drives the requirements, not a trailing artifact) and
the verifiability MUST (every journey carries an observable check; the outcome
is observable) must be present. Without them, requirements get written first
and scenarios reverse-engineered to match — the green-but-broken class where the
only thing checked is the requirement, never the round-trip the user walks.
"""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[5]
_SPECIFY = _ROOT / "plugins" / "sulis" / "skills" / "specify" / "SKILL.md"


def _text() -> str:
    assert _SPECIFY.is_file(), f"missing {_SPECIFY}"
    return _SPECIFY.read_text(encoding="utf-8")


def test_specify_has_work_backwards_principle() -> None:
    t = _text().lower()
    assert "work backwards" in t or "work-backwards" in t
    assert "outside-in" in t or "outside in" in t, (
        "specify must establish the Outside-In / Work-Backwards discipline"
    )


def test_journey_is_the_driver_not_a_trailing_artifact() -> None:
    t = _text().lower()
    assert "scenarios first" in t, (
        "the journey must be drafted first and drive the requirements"
    )
    # the journey frames the requirements, not the other way round
    assert "drive" in t and "journey" in t


def test_verifiability_is_a_must() -> None:
    t = _text()
    assert "require_verifiable" in t, (
        "specify must point at the authoring-time verifiability gate"
    )
    low = t.lower()
    assert "observable" in low and "outcome" in low, (
        "every journey must carry an observable check and an observable outcome"
    )


def test_green_but_broken_failure_named() -> None:
    # the prose must name the failure it closes, so the rule isn't cargo-culted
    t = _text().lower()
    assert "green" in t and "broken" in t
