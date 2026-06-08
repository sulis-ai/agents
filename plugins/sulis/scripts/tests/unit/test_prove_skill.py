"""Structural pins for the /sulis:prove skill — the "is it real or vibe-coded?" gate.

prove is the consumer-level reality check: find the critical scenarios, drive them
for real, validate the saved output, return observed-or-blocked. These pins stop its
load-bearing disciplines from silently rotting out of the skill.
"""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[5]
_PROVE = _ROOT / "plugins" / "sulis" / "skills" / "prove" / "SKILL.md"


def _text() -> str:
    assert _PROVE.is_file(), f"missing {_PROVE}"
    return _PROVE.read_text(encoding="utf-8")


def test_skill_exists_with_description() -> None:
    t = _text()
    assert t.startswith("---") and "name: prove" in t
    assert "description:" in t


def test_drives_the_real_flow_not_stubs() -> None:
    low = _text().lower()
    assert "for real" in low and ("no stubs" in low or "no mocks" in low)
    assert "consumer" in low  # drive the real interface as a consumer


def test_validates_saved_output_observed_not_assumed() -> None:
    low = _text().lower()
    assert "saved output" in low or "saved record" in low or "saved result" in low
    # the done bar: observed, not "it ran"
    assert "ran without error" in low and "not a pass" in low


def test_finds_critical_scenarios_journeys_and_nfrs() -> None:
    low = _text().lower()
    assert "critical scenario" in low
    assert "find_scenarios_for_journey" in _text()  # the journey set
    assert "nfr" in low or "non-functional" in low   # the production mechanisms


def test_observed_or_blocked_verdict_and_stub_flagging() -> None:
    low = _text().lower()
    assert "observed-or-blocked" in low or ("observed-green" in low and "blocked" in low)
    # flags stubs/fakes
    assert "slots in here" in low or "notimplemented" in low or "stub" in low
