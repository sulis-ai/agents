"""The Working Set must be wired into the primary agent's change behaviour.

A skill the agent triggers is dead unless the agent is actually told to trigger it.
This pins that the Sulis agent body wires /sulis:working-set into how it works a
change — init at binding, show at the start of every turn (the make-or-break
read-every-turn habit), update/log as decisions land, crystallize at the boundary.
Without this the Working Set ships as a skill nothing calls — the exact
"built but not wired" pattern.
"""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[5]
_SULIS = _ROOT / "plugins" / "sulis" / "agents" / "sulis.md"


def _text() -> str:
    assert _SULIS.is_file(), f"missing {_SULIS}"
    return _SULIS.read_text(encoding="utf-8")


def test_agent_references_the_working_set_skill() -> None:
    t = _text()
    assert "sulis-working-set" in t or "/sulis:working-set" in t, (
        "the Sulis agent must trigger the working-set skill, or it's dead"
    )


def test_agent_wires_the_three_trigger_moments() -> None:
    low = _text().lower()
    assert "working set" in low
    # the make-or-break read-every-turn habit + the lifecycle moments
    assert "every turn" in low, "must wire `show` at the start of every turn"
    assert "init" in low and "crystallize" in low, "must wire init + crystallize"


def test_wiring_lives_in_the_change_context() -> None:
    # it's change-scoped behaviour, so it belongs in the change-context section
    t = _text()
    assert "Maintain the Working Set" in t
    i_ws = t.index("Maintain the Working Set")
    i_change = t.index("## Change context")
    assert i_ws > i_change, "the Working Set wiring belongs under Change context"
