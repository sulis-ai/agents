"""WP-005 wiring — the change-ship flow runs the acceptance gate.

The testable-state gate must actually fire at ship (alongside the step-4.8
requirements DoD gate), or it's a gate in name only. Structural assertion over
the live change/SKILL.md.

Stdlib + pytest. Python 3.11-safe.
"""

from __future__ import annotations

from pathlib import Path

_SHIP = (
    Path(__file__).resolve().parents[5]
    / "plugins" / "sulis" / "skills" / "change" / "SKILL.md"
)


def _text() -> str:
    assert _SHIP.is_file(), f"missing {_SHIP}"
    return _SHIP.read_text(encoding="utf-8")


def test_ship_runs_the_acceptance_gate() -> None:
    text = _text()
    assert "sulis-verify-acceptance" in text, (
        "change ship must invoke sulis-verify-acceptance (the testable-state gate)"
    )


def test_ship_blocks_on_blocked_verdict() -> None:
    text = _text().lower()
    assert "blocked" in text and "stop" in text, (
        "ship must STOP on a blocked acceptance verdict (not call the change done)"
    )


def test_ship_treats_deferred_as_blocking_by_default() -> None:
    # #83: observed-or-blocked. A deferred (never-driven) outcome no longer
    # passes silently — ship blocks unless --allow-deferred is consciously set.
    text = _text().lower()
    assert "deferred" in text and "allow-deferred" in text, (
        "ship must treat a deferred outcome as blocking by default, with the "
        "conscious --allow-deferred escape documented"
    )
    assert "observed-or-blocked" in text, (
        "ship must state the observed-or-blocked discipline"
    )
