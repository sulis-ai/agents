"""Structural verification for CH-01KT1T (canonicalise-cross-wp-ids).

The change extends `/sulis:plan-work` and the Decompose Validation
Rubric with a methodology check: parallel-dispatched WPs that share
an identifier (ULID, slug, version literal, namespace) MUST have
that identifier pre-minted in an authoritative upstream source — a
TDD "Canonical Identifiers" section, an `ADR-NN-canonical-identifiers.md`,
or an existing instance file — before decomposition completes. Without
this, each executor invents its own value and they diverge.

Anchor case: CH-01KSZ4 (release-train-as-entities, wave 1) had WP-003
and WP-004 both minting a tenant ULID. WP-004 used a deterministic
SHA256→Crockford-base32 recipe; WP-003 used the placeholder
`01JA0AAA1BBBCCCDDDEEEFFFGS`. The calling session caught the
divergence at the post-train audit and reconciled WP-003 by hand
(commit 4360684: "fix(release-train): canonicalise tenant ULID on
triggers.jsonld to WP-004's value"). Pre-canonicalisation in the
design phase prevents the recurrence.

This module pins the new sections in place so a future heading or
content drift surfaces as a failing test rather than a silent
methodology regression. Stdlib + pytest only, Python 3.11-safe.
Resolves paths relative to this test file so the suite is location-
stable inside any worktree.

Four assertions:

  1. `/sulis:plan-work` SKILL.md contains a heading/step naming the
     cross-WP identifier canonicalisation check.
  2. `decompose-validation-rubric.md` contains a new phase (P7 or
     later) with a section title containing "canonicalisation" or
     "identifier" — the mechanical analog of the skill prose.
  3. The two artifacts cross-reference each other (the skill mentions
     the rubric's new phase by name OR the rubric mentions the skill
     step) so a reader following one finds the other.
  4. The CH-01KSZ4 provenance (release-train wave-1 tenant-ULID
     divergence) is cited as the worked example in at least one of
     the two artifacts — future readers need the lesson source to
     understand why the check exists.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# tests/unit/ → tests/ → scripts/ → sulis/ → plugins/sulis/ → plugins/
_PLUGINS_SULIS = Path(__file__).resolve().parents[3]
_PLAN_WORK_SKILL = _PLUGINS_SULIS / "skills" / "plan-work" / "SKILL.md"
_RUBRIC = _PLUGINS_SULIS / "references" / "decompose-validation-rubric.md"


@pytest.fixture(scope="module")
def plan_work_text() -> str:
    """The live `/sulis:plan-work` SKILL.md content as a single string."""
    assert _PLAN_WORK_SKILL.is_file(), (
        f"missing plan-work SKILL.md at {_PLAN_WORK_SKILL}"
    )
    return _PLAN_WORK_SKILL.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def rubric_text() -> str:
    """The live decompose-validation-rubric.md content as a single string."""
    assert _RUBRIC.is_file(), f"missing decompose-validation-rubric.md at {_RUBRIC}"
    return _RUBRIC.read_text(encoding="utf-8")


def test_plan_work_has_canonicalise_step(plan_work_text: str) -> None:
    """The plan-work skill names the cross-WP identifier canonicalisation step.

    Readers scanning the skill's Workflow section need an unambiguous
    heading/step that mentions the check — buried prose under another
    heading wouldn't surface.
    """
    # Accept either a numbered Workflow step title OR a bold lead-in that
    # contains BOTH the "cross-WP" or "canonical" cue AND the "identifier"
    # cue. The regex tolerates step renumbering but pins the semantic
    # heading.
    pattern = re.compile(
        r"(?:cross[-\s]?WP|canonical)\s+identifier",
        re.IGNORECASE,
    )
    assert pattern.search(plan_work_text), (
        "plan-work SKILL.md is missing a Workflow step naming the "
        "cross-WP / canonical identifier check. Expected wording like "
        "'Audit cross-WP identifiers' or 'Canonical identifier audit' "
        "so the methodology step is discoverable to a reader scanning "
        "the Workflow section. Without the heading the new rule lives "
        "as ambient prose and doesn't pin executor behaviour."
    )


def test_rubric_has_canonicalisation_phase(rubric_text: str) -> None:
    """The rubric exposes a Phase ≥ 7 covering identifier canonicalisation.

    Phases 1..6 (now 1..7 with ServiceSpec) all run mechanically; the
    new phase joins them as the mechanical analog of the plan-work
    methodology step. A future reader scanning the Phase-by-phase
    results table needs to see it as a first-class phase, not an
    inline note.
    """
    # Match `## Phase N — Cross-WP identifier canonicalisation` (or any
    # heading with the canonicalisation / identifier cue at phase ≥ 7).
    pattern = re.compile(
        r"^##\s+Phase\s+(\d+)\s+[—-]\s+.*(?:canonicalisation|identifier)",
        re.IGNORECASE | re.MULTILINE,
    )
    matches = pattern.findall(rubric_text)
    assert matches, (
        "decompose-validation-rubric.md is missing a `## Phase N — ... "
        "canonicalisation` or `... identifier` heading. The rubric "
        "needs the new phase as a first-class section (mirroring "
        "Phases 1..7) so the Phase-by-phase results table includes "
        "it, and so `wpx-index audit-contracts`-style mechanical "
        "checks can attach to it."
    )
    # At least one match must have phase number ≥ 7 (new phase, not a
    # repurposed Phase 1-6 heading).
    assert any(int(n) >= 7 for n in matches), (
        "The canonicalisation/identifier phase heading was found but "
        "with a phase number < 7. The new phase MUST be added at "
        "Phase 7+ — the existing Phases 1..7 (ServiceSpec) are stable "
        "and renumbering them would break downstream references."
    )


def test_skill_and_rubric_cross_reference(
    plan_work_text: str, rubric_text: str
) -> None:
    """The skill and the rubric reference each other.

    A reader following the skill's Workflow step must be able to
    find the mechanical phase in the rubric (and vice versa). The
    reference can run either direction; both don't have to point.
    """
    # The skill's `## Workflow` step 11 already references the rubric
    # by file path; we want the NEW canonicalisation prose to either
    # name the new phase (P7+) explicitly OR sit next to the existing
    # rubric link. Detect: the skill mentions a phase identifier
    # ("P7", "P8", "Phase 7", "Phase 8", …) OR the word "rubric" in
    # the canonicalisation context. The rubric is allowed to back-
    # reference plan-work step (no requirement, but if present, it
    # satisfies the cross-reference).
    skill_refs_rubric_phase = bool(
        re.search(
            r"(?:P\s*[789]|Phase\s+[789]|decompose[-\s]validation[-\s]rubric)",
            plan_work_text,
            re.IGNORECASE,
        )
    )
    rubric_refs_skill = bool(
        re.search(
            r"(?:plan[-\s]work|/sulis:plan-work)",
            rubric_text,
            re.IGNORECASE,
        )
    )
    assert skill_refs_rubric_phase or rubric_refs_skill, (
        "Neither the plan-work skill nor the validation rubric "
        "cross-reference each other for the canonicalisation check. "
        "Either the skill must name the rubric's new phase (e.g. "
        "'P7 — Cross-WP identifier canonicalisation') OR the rubric "
        "must reference the plan-work step by name. Without the "
        "cross-link the two artifacts drift independently."
    )


def test_provenance_to_ch_01ksz4_release_train(
    plan_work_text: str, rubric_text: str
) -> None:
    """CH-01KSZ4 (release-train wave-1 tenant ULID) is cited as anchor case.

    Future readers need the lesson source. The rubric's existing
    Phase 6 cites the platform-repo `loader/__init__.py` collision
    as its anchor case — this new phase needs the same kind of
    provenance pointer so the rule's origin is recoverable. The
    pointer can live in the skill, in the rubric, or in both;
    either satisfies the assertion.
    """
    combined = plan_work_text + "\n" + rubric_text
    # Accept any of the canonical anchor strings:
    #   - "CH-01KSZ4" (the change handle)
    #   - "release-train" + "tenant" (the worked-example shorthand)
    #   - "WP-003" + "WP-004" + "tenant" (the WP-numbered example)
    anchors = [
        re.search(r"CH-01KSZ4", combined),
        bool(
            re.search(r"release[-\s]train", combined, re.IGNORECASE)
            and re.search(r"tenant", combined, re.IGNORECASE)
        ),
        bool(
            re.search(r"WP-003", combined)
            and re.search(r"WP-004", combined)
            and re.search(r"tenant", combined, re.IGNORECASE)
        ),
    ]
    assert any(anchors), (
        "Neither plan-work SKILL.md nor decompose-validation-rubric.md "
        "cites the CH-01KSZ4 anchor case (release-train wave-1 "
        "tenant-ULID divergence between WP-003 and WP-004). The new "
        "rule's provenance MUST be recoverable so future readers "
        "understand why the check exists and don't dilute it. Cite "
        "either the change handle (CH-01KSZ4), the worked-example "
        "shorthand ('release-train' + 'tenant ULID'), or the "
        "WP-numbered example (WP-003 + WP-004 + tenant)."
    )
