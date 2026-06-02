"""Structural verification for WP-005 (platform-contract-standard change).

WP-005 extends ``plugins/sulis/skills/plan-work/SKILL.md`` so it emits the
``platform:`` / ``touch-class:`` WP-frontmatter field on any WP that touches a
third-party platform. That field is the detection signal P-PLAT (the rubric's
Phase 10, WP-004) reads to decide whether a WP set needs a Platform Contract
(OAQ-4 / MUC-004).

The skill is prose, so the RED cycle pins the documented emission contract as
structural assertions over the live SKILL.md text.

Per the WP Contract (`Definition of Done > Red`):

  1. ``plan-work/SKILL.md`` documents the ``platform:`` + ``touch-class:``
     frontmatter keys.
  2. It states the write / deploy / read-only value set.
  3. It references the P-PLAT rubric phase (by name) as the consumer.

Stdlib + pytest only, Python 3.11-safe.
"""

from __future__ import annotations

from pathlib import Path

# tests/unit/ -> tests/ -> scripts/ -> sulis/ -> plugins/ -> repo-root
_REPO_ROOT = Path(__file__).resolve().parents[5]
_PLAN_WORK = _REPO_ROOT / "plugins" / "sulis" / "skills" / "plan-work" / "SKILL.md"


def _text() -> str:
    assert _PLAN_WORK.is_file(), f"missing skill file {_PLAN_WORK}"
    return _PLAN_WORK.read_text(encoding="utf-8")


def test_plan_work_emits_platform_field() -> None:
    """plan-work documents the platform:/touch-class: emission (OAQ-4)."""
    text = _text()

    assert "platform:" in text and "touch-class:" in text, (
        "plan-work/SKILL.md must document the `platform:` + `touch-class:` "
        "WP-frontmatter keys (OAQ-4)."
    )

    lowered = text.lower()
    for token in ("write", "deploy", "read-only"):
        assert token in lowered, (
            "plan-work/SKILL.md must state the touch-class value "
            f"'{token}' (write/deploy/read-only)."
        )

    assert "P-PLAT" in text, (
        "plan-work/SKILL.md must reference the P-PLAT rubric phase as the "
        "consumer of the emitted field (authority split; no restating)."
    )


def test_plan_work_default_is_omit_for_no_touch() -> None:
    """The documented default for a WP touching no third party is to omit the
    fields (absence = no gated touch)."""
    text = _text().lower()
    assert "omit" in text, (
        "plan-work/SKILL.md must document that WPs touching no third party "
        "omit the platform:/touch-class: keys (absence = not-applicable)."
    )
