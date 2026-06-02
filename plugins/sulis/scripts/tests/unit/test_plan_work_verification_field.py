"""Structural verification for CH-01KT2B (verification-by-design) WP-005.

The change extends `/sulis:plan-work` so every Work Package it emits
carries a `verification:` frontmatter field in one of three canonical
shapes (per ADR-003: concrete / deferred / trivial carveout). The
field is the machine-readable seam between a WP and the behavioural
test ledger (FR-015), and it is what the slice-end review (extended
in `references/lifecycle.md` per ADR-005) scans to aggregate
deferred infrastructure needs.

This module pins the new prose in place so a future heading or
content drift surfaces as a failing test rather than a silent
methodology regression. Stdlib + pytest only, Python 3.11-safe.
Resolves paths relative to this test file so the suite is location-
stable inside any worktree.

Four assertions:

  1. `/sulis:plan-work` SKILL.md names `verification:` as a required
     frontmatter field on every WP.
  2. The SKILL cites `ADR-003` (the three-shape schema source).
  3. The SKILL cites `VERIFICATION_QUESTIONS.md` (the canonical
     kind → adapter source).
  4. The SKILL Workflow contains a step instructing the agent to set
     the `verification:` field per the adapter table.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# tests/unit/ → tests/ → scripts/ → sulis/ → plugins/sulis/ → plugins/
_PLUGINS_SULIS = Path(__file__).resolve().parents[3]
_PLAN_WORK_SKILL = _PLUGINS_SULIS / "skills" / "plan-work" / "SKILL.md"


@pytest.fixture(scope="module")
def plan_work_text() -> str:
    """The live `/sulis:plan-work` SKILL.md content as a single string."""
    assert _PLAN_WORK_SKILL.is_file(), (
        f"missing plan-work SKILL.md at {_PLAN_WORK_SKILL}"
    )
    return _PLAN_WORK_SKILL.read_text(encoding="utf-8")


def test_skill_names_verification_field_as_required(plan_work_text: str) -> None:
    """The skill names `verification:` as a required WP frontmatter field.

    Without the field being named-and-required, executors emit WPs
    without it (P-VER failure mode 8 surfaces the regression at
    rubric-time, but the prose itself must establish the rule).
    """
    # Match `verification:` in a context that includes "required" or
    # "MUST" within ~200 chars on either side, OR appears within a
    # section explicitly listing required frontmatter fields.
    pattern = re.compile(
        r"verification:\s*\n.{0,400}(?:required|MUST|three shapes|ADR-003)",
        re.IGNORECASE | re.DOTALL,
    )
    assert pattern.search(plan_work_text), (
        "plan-work SKILL.md is missing a verification: field declaration "
        "in a required-field context. Expected the field to appear in "
        "the 'What a Work Package Contains' section with explicit prose "
        "naming it as required (one of the three ADR-003 shapes). "
        "Without this, executors emit WPs lacking the field and the "
        "behavioural test ledger (FR-015) has no machine-readable seam."
    )


def test_skill_cites_adr_003(plan_work_text: str) -> None:
    """The skill cites ADR-003 for the three-shape schema.

    The three shapes (concrete / deferred / trivial) live in
    ADR-003 — the skill MUST cite that ADR rather than re-stating
    the schema inline (NFR-004 single-source-of-truth defence).
    """
    pattern = re.compile(r"ADR-003", re.IGNORECASE)
    assert pattern.search(plan_work_text), (
        "plan-work SKILL.md is missing a citation to ADR-003 "
        "(per-WP verification: frontmatter three-shape schema). "
        "Without the citation, the skill duplicates schema content "
        "inline and drifts from the canonical ADR."
    )


def test_skill_cites_verification_questions_canonical(
    plan_work_text: str,
) -> None:
    """The skill cites `VERIFICATION_QUESTIONS.md` for the adapter table.

    The kind → adapter mapping is canonical in
    `plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md`.
    The skill MUST cite it by name so the kind→adapter resolution is
    discoverable to a reader scanning the Workflow section.
    """
    pattern = re.compile(r"VERIFICATION_QUESTIONS\.md", re.IGNORECASE)
    assert pattern.search(plan_work_text), (
        "plan-work SKILL.md is missing a citation to "
        "VERIFICATION_QUESTIONS.md — the canonical kind → adapter "
        "mapping. The skill MUST cite it so the per-WP verification: "
        "field setter knows where to look up the adapter for the "
        "current change's kind:."
    )


def test_skill_workflow_sets_verification_field(plan_work_text: str) -> None:
    """The Workflow names a step that sets `verification:` per WP.

    Readers scanning the Workflow section need an unambiguous step
    naming the verification-field setter so the methodology behaviour
    is pinned. Buried prose under another heading would not surface.
    """
    # Accept a numbered step or bold lead-in that includes BOTH the
    # "verification" cue AND the "set" / "field" / "adapter" cue
    # within a small window.
    pattern = re.compile(
        r"(?:Step\s+4d|set\s+the\s+`?verification|verification:\s*field\s+per)",
        re.IGNORECASE,
    )
    assert pattern.search(plan_work_text), (
        "plan-work SKILL.md is missing a Workflow step naming the "
        "verification: field setter. Expected wording like "
        "'Step 4d — Set the verification: field per WP' so the "
        "per-WP enforcement is discoverable. Without the step, "
        "the field's three shapes are documented but the setter "
        "behaviour is ambient prose and does not pin executor "
        "behaviour."
    )
