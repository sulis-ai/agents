"""WP-007 (testable-state-done) — design phase authors Scenario entities.

draft-architecture must instruct the design stage to define the change's
`Scenario` entities up front (as living graph entities), so the testable-state
DoD gate has cases to run. Structural assertion over the live SKILL.md.

Stdlib + pytest. Python 3.11-safe.
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[5]
_DRAFT_ARCH = _REPO_ROOT / "plugins" / "sulis" / "skills" / "draft-architecture" / "SKILL.md"


def _text() -> str:
    assert _DRAFT_ARCH.is_file(), f"missing {_DRAFT_ARCH}"
    return _DRAFT_ARCH.read_text(encoding="utf-8")


def test_design_authors_scenarios() -> None:
    text = _text()
    assert "Scenario" in text, "draft-architecture must name the Scenario entity"
    # the three edges that make a Scenario a verification case
    for token in ("verifies", "exercises", "journey"):
        assert token in text, f"Scenario authoring must mention `{token}`"


def test_design_ties_scenarios_to_the_gate() -> None:
    text = _text().lower()
    assert "testable-state" in text or "sulis-verify-acceptance" in text, (
        "design must tie Scenarios to the testable-state DoD gate / runner"
    )


def test_scenarios_are_living_entities_not_change_dir() -> None:
    text = _text()
    # guards the supersession: cases are graph entities, not a change-dir file
    assert "living graph" in text or "graph entit" in text.lower(), (
        "Scenarios must be authored as living graph entities (not a change-dir file)"
    )
