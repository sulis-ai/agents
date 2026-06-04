"""Journey-rigor #6 — the human-handoff is wired into the gate flow + named.

Structural pins: the change/ship acceptance-gate section must give a blocked
manual journey a path to green via sulis-attest-scenario (not just a dead-end
block), and the dispatcher must NAME the automated browser driver as a follow-on
(no silent cap) rather than implying browser flows are unsupported.
"""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[5]
_CHANGE = _ROOT / "plugins" / "sulis" / "skills" / "change" / "SKILL.md"
_DISPATCH = _ROOT / "plugins" / "sulis" / "scripts" / "_scenario_dispatch.py"


def test_change_skill_offers_the_human_handoff_for_blocked_journeys() -> None:
    t = _CHANGE.read_text(encoding="utf-8")
    assert "sulis-attest-scenario" in t, (
        "a blocked manual journey must have a path to green via attestation"
    )
    low = t.lower()
    assert "human-attested" in low and "by hand" in low


def test_dispatch_names_the_browser_driver_followon() -> None:
    t = _DISPATCH.read_text(encoding="utf-8").lower()
    # browser flows route via human → manual → attestation today; the automated
    # driver is a NAMED follow-on, not a silent gap
    assert "browser" in t and "follow-on" in t
    assert "sulis-attest-scenario" in t
