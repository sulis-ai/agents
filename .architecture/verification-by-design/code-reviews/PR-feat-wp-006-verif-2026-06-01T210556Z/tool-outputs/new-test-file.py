"""Structural verification for WP-006 (verification-by-design change).

WP-006 wires P-VER into the three orchestrator skills (`specify`,
`draft-architecture`, `requirements-validation`) and adds the
``## Verification Plan`` template block to `requirements-templates`.

Per the WP Contract (`Definition of Done > Red`), the four SKILL.md
files MUST:

  1. Cite ``plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md``
     (the canonical 20-question set) by relative path at least once
     (FR-001 / FR-002 / FR-009 / NFR-006 citation discipline).
  2. Cite ``plugins/sulis/references/decompose-validation-rubric.md``
     and name **P-VER** explicitly so the orchestration prose names the
     rubric phase it invokes (MUC-003 defence).
  3. Cross-reference ADR-001 (the section name decision — "Verification
     Plan", exact casing) so downstream regex anchors stay stable.
  4. Contain NO inline copies of the canonical question text (NFR-004 /
     MUC-003 anti-duplication invariant).
  5. For `requirements-templates/SKILL.md`: host a literal
     ``## Verification Plan`` template block carrying the HTML-comment
     annotation + all six required subsection headings in order +
     placeholder instructions referencing the canonical (Q1..Q20)
     rather than inlining the question stems.

Stdlib + pytest only, Python 3.11-safe. Resolves paths relative to
this test file so the suite is location-stable inside any worktree.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# tests/unit/ -> tests/ -> scripts/ -> sulis/ -> plugins/ -> repo-root
_REPO_ROOT = Path(__file__).resolve().parents[5]
_SKILLS_DIR = _REPO_ROOT / "plugins" / "sulis" / "skills"

_SPECIFY = _SKILLS_DIR / "specify" / "SKILL.md"
_DRAFT_ARCH = _SKILLS_DIR / "draft-architecture" / "SKILL.md"
_REQ_VAL = _SKILLS_DIR / "requirements-validation" / "SKILL.md"
_REQ_TPL = _SKILLS_DIR / "requirements-templates" / "SKILL.md"

_CANONICAL_REL = "plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md"
_RUBRIC_REL = "plugins/sulis/references/decompose-validation-rubric.md"

# The six subsection headings the template block (and the Phase 3 output
# spec) must enumerate, per FR-001 of this change's SRD.
_REQUIRED_SUBSECTIONS = (
    "What user-observable behaviour are we verifying?",
    "Verification environment(s)",
    "Bootstrap-from-zero case",
    "Per-integration verification strategy",
    "Per-kind verification adapter",
    "Infrastructure needs surfaced (deferred)",
)

# The HTML-comment annotation shape MUC-003 + WP-001 fixed. Every
# consumer that depends on the canonical carries this shape verbatim
# so the P-VER citation-presence check matches uniformly.
_HTML_COMMENT_PATTERN = (
    r"<!--\s*VERIFICATION_QUESTIONS\s+source:\s*"
    r"plugins/sulis/references/standards/VERIFICATION_QUESTIONS\.md"
    r"\s+v\d+\.\d+\.\d+\s*-->"
)

# Sentinel question-text strings drawn from the canonical's
# foundational + per-integration + per-kind groups. If any of these
# literal phrases appears in the orchestrator skills or the template
# block, the consumer has inlined the canonical and broken NFR-004's
# anti-duplication invariant. Conservative list: only Q-stem
# phrasings a copy-paste would carry.
_FORBIDDEN_INLINED_QUESTION_STEMS = (
    # Q1 stem — foundational question's interrogative phrasing.
    "What user-observable behaviour, in plain English, will tell us this change works?",
    # Q5 stem — per-integration kickoff.
    "For each integration this change touches, is the verification real, recorded, or simulated?",
    # Q14 stem — per-kind adapter kickoff.
    "What kind of change is this (one of: methodology / backend / frontend / async / infrastructure / documentation / contract)?",
)


# ---------------------------------------------------------------------------
# Module-scoped fixtures: one read per SKILL.md
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def specify_text() -> str:
    if not _SPECIFY.exists():
        pytest.fail(
            f"specify SKILL.md missing at {_SPECIFY}. WP-006 extends "
            "this file; the structural assertions cannot run until it "
            "exists."
        )
    return _SPECIFY.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def draft_arch_text() -> str:
    if not _DRAFT_ARCH.exists():
        pytest.fail(
            f"draft-architecture SKILL.md missing at {_DRAFT_ARCH}. "
            "WP-006 extends this file; the structural assertions cannot "
            "run until it exists."
        )
    return _DRAFT_ARCH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def req_val_text() -> str:
    if not _REQ_VAL.exists():
        pytest.fail(
            f"requirements-validation SKILL.md missing at {_REQ_VAL}. "
            "WP-006 extends this file; the structural assertions cannot "
            "run until it exists."
        )
    return _REQ_VAL.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def req_tpl_text() -> str:
    if not _REQ_TPL.exists():
        pytest.fail(
            f"requirements-templates SKILL.md missing at {_REQ_TPL}. "
            "WP-006 extends this file; the structural assertions cannot "
            "run until it exists."
        )
    return _REQ_TPL.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Shared helper assertions
# ---------------------------------------------------------------------------


def _assert_cites_canonical(skill_name: str, text: str) -> None:
    assert _CANONICAL_REL in text, (
        f"Expected {skill_name} to cite the canonical by relative path "
        f"`{_CANONICAL_REL}` (FR-001 / FR-002 / FR-009 / NFR-006). The "
        "cite must be literal so the P-VER citation-presence check "
        "parses it."
    )


def _assert_cites_rubric(skill_name: str, text: str) -> None:
    assert _RUBRIC_REL in text, (
        f"Expected {skill_name} to cite the rubric "
        f"`{_RUBRIC_REL}` (FR-009 — the orchestrator's job is to "
        "invoke P-VER, which lives in the rubric)."
    )


def _assert_names_p_ver(skill_name: str, text: str) -> None:
    assert "P-VER" in text, (
        f"Expected {skill_name} to name `P-VER` explicitly. The "
        "orchestrator prose must name the rubric phase it invokes so "
        "the founder reading the skill sees what the gate is "
        "(MUC-003 defence — orchestrator skills are the most tempting "
        "place to silently skip the gate)."
    )


def _assert_cites_adr001(skill_name: str, text: str) -> None:
    assert "ADR-001" in text, (
        f"Expected {skill_name} to cross-reference ADR-001 — the "
        "section-name decision (`## Verification Plan`, exact casing). "
        "Downstream regex anchors and citation-presence checks depend "
        "on this literal staying stable."
    )


def _assert_no_inlined_questions(skill_name: str, text: str) -> None:
    leaks: list[str] = []
    for stem in _FORBIDDEN_INLINED_QUESTION_STEMS:
        if stem in text:
            leaks.append(stem)
    assert not leaks, (
        f"{skill_name} contains inlined canonical question text "
        f"(NFR-004 / MUC-003 violation): {leaks}. The skill must cite "
        f"`{_CANONICAL_REL}` and reference questions by ID (Q1..Q20) "
        "— not copy the question text into the skill prose."
    )


# ---------------------------------------------------------------------------
# specify/SKILL.md — orchestrates requirements-analyst; invokes P-VER on
# the produced SRD.
# ---------------------------------------------------------------------------


def test_specify_exists() -> None:
    assert _SPECIFY.exists(), (
        f"specify SKILL.md missing at {_SPECIFY}."
    )


def test_specify_cites_canonical(specify_text: str) -> None:
    _assert_cites_canonical("specify/SKILL.md", specify_text)


def test_specify_cites_rubric(specify_text: str) -> None:
    _assert_cites_rubric("specify/SKILL.md", specify_text)


def test_specify_names_p_ver(specify_text: str) -> None:
    _assert_names_p_ver("specify/SKILL.md", specify_text)


def test_specify_cites_adr001(specify_text: str) -> None:
    _assert_cites_adr001("specify/SKILL.md", specify_text)


def test_specify_does_not_inline_questions(specify_text: str) -> None:
    _assert_no_inlined_questions("specify/SKILL.md", specify_text)


# ---------------------------------------------------------------------------
# draft-architecture/SKILL.md — orchestrates engineering-architect;
# invokes P-VER on the produced TDD; surfaces SRD<->TDD contradictions.
# ---------------------------------------------------------------------------


def test_draft_arch_exists() -> None:
    assert _DRAFT_ARCH.exists(), (
        f"draft-architecture SKILL.md missing at {_DRAFT_ARCH}."
    )


def test_draft_arch_cites_canonical(draft_arch_text: str) -> None:
    _assert_cites_canonical("draft-architecture/SKILL.md", draft_arch_text)


def test_draft_arch_cites_rubric(draft_arch_text: str) -> None:
    _assert_cites_rubric("draft-architecture/SKILL.md", draft_arch_text)


def test_draft_arch_names_p_ver(draft_arch_text: str) -> None:
    _assert_names_p_ver("draft-architecture/SKILL.md", draft_arch_text)


def test_draft_arch_cites_adr001(draft_arch_text: str) -> None:
    _assert_cites_adr001("draft-architecture/SKILL.md", draft_arch_text)


def test_draft_arch_names_verification_plan_section(
    draft_arch_text: str,
) -> None:
    """The skill that produces the TDD must name the literal section
    heading (ADR-001) so the produced TDD carries it for P-VER to find."""
    assert "## Verification Plan" in draft_arch_text, (
        "Expected the literal `## Verification Plan` in "
        "draft-architecture SKILL.md — the skill that produces the TDD "
        "must name the section heading (ADR-001) so the agent it "
        "dispatches produces it."
    )


def test_draft_arch_does_not_inline_questions(
    draft_arch_text: str,
) -> None:
    _assert_no_inlined_questions("draft-architecture/SKILL.md", draft_arch_text)


# ---------------------------------------------------------------------------
# requirements-validation/SKILL.md — invokes P-VER as part of the rubric
# pass; P-VER FAIL => overall verdict GAPS_FOUND.
# ---------------------------------------------------------------------------


def test_req_val_exists() -> None:
    assert _REQ_VAL.exists(), (
        f"requirements-validation SKILL.md missing at {_REQ_VAL}."
    )


def test_req_val_cites_canonical(req_val_text: str) -> None:
    _assert_cites_canonical("requirements-validation/SKILL.md", req_val_text)


def test_req_val_cites_rubric(req_val_text: str) -> None:
    _assert_cites_rubric("requirements-validation/SKILL.md", req_val_text)


def test_req_val_names_p_ver(req_val_text: str) -> None:
    _assert_names_p_ver("requirements-validation/SKILL.md", req_val_text)


def test_req_val_cites_adr001(req_val_text: str) -> None:
    _assert_cites_adr001("requirements-validation/SKILL.md", req_val_text)


def test_req_val_says_p_ver_fail_means_fail(req_val_text: str) -> None:
    """Verdict semantics: when P-VER fails, the overall validation
    verdict is GAPS_FOUND (FR-009 — P-VER is a MUST-blocking phase in
    the rubric, so the rubric-invocation skill must reflect that
    pass-through). The skill prose must contain the verdict
    pass-through explicitly so a reader knows which failure modes block
    the spec from progressing."""
    # Look for a phrase tying P-VER failure to GAPS_FOUND in the
    # verdict semantics. Two acceptable phrasings (we don't pin a
    # single literal — the author can choose between them):
    accepted = (
        "P-VER FAIL",
        "P-VER fail",
        "P-VER failure",
    )
    has_failure_term = any(term in req_val_text for term in accepted)
    has_verdict_term = (
        "GAPS_FOUND" in req_val_text or "FAIL" in req_val_text
    )
    assert has_failure_term and has_verdict_term, (
        "Expected requirements-validation/SKILL.md to state that a "
        "P-VER failure produces a GAPS_FOUND / FAIL overall verdict. "
        "FR-009 makes P-VER a MUST-blocking rubric phase; the "
        "rubric-invocation skill must surface that verdict "
        "pass-through explicitly."
    )


def test_req_val_does_not_inline_questions(req_val_text: str) -> None:
    _assert_no_inlined_questions("requirements-validation/SKILL.md", req_val_text)


# ---------------------------------------------------------------------------
# requirements-templates/SKILL.md — hosts the Verification Plan SRD
# template block.
# ---------------------------------------------------------------------------


def test_req_tpl_exists() -> None:
    assert _REQ_TPL.exists(), (
        f"requirements-templates SKILL.md missing at {_REQ_TPL}."
    )


def test_req_tpl_has_verification_plan_block(req_tpl_text: str) -> None:
    """The literal `## Verification Plan` heading must appear at least
    once — it is the SRD template's section header (ADR-001)."""
    assert "## Verification Plan" in req_tpl_text, (
        "Expected the literal `## Verification Plan` heading in the "
        "requirements-templates SRD template block (ADR-001 — exact "
        "section heading; the P-VER section-presence regex anchors on "
        "this literal)."
    )


def test_req_tpl_block_has_html_comment_annotation(
    req_tpl_text: str,
) -> None:
    """The template block carries the canonical HTML-comment
    annotation so generated SRDs inherit it verbatim and the P-VER
    citation-presence check matches (MUC-003 defence)."""
    assert re.search(_HTML_COMMENT_PATTERN, req_tpl_text), (
        "Expected the HTML-comment annotation shape "
        "`<!-- VERIFICATION_QUESTIONS source: "
        "plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md "
        "vX.Y.Z -->` in the template block. Generated SRDs inherit it "
        "verbatim, so the P-VER citation-presence check matches "
        "(MUC-003 defence — consumers cannot silently skip the "
        "canonical)."
    )


def test_req_tpl_block_has_six_subsections(req_tpl_text: str) -> None:
    """The Verification Plan template block names the six required
    subsection headings (FR-001). Each heading must appear at least
    once in the template block so generated SRDs carry them."""
    missing: list[str] = []
    for heading in _REQUIRED_SUBSECTIONS:
        if heading not in req_tpl_text:
            missing.append(heading)
    assert not missing, (
        f"requirements-templates SKILL.md missing required Verification "
        f"Plan subsection headings: {missing}. All six are required by "
        "FR-001 / ADR-001 and must be enumerated in the template block "
        "so generated SRDs carry them in order."
    )


def test_req_tpl_subsections_appear_in_order(req_tpl_text: str) -> None:
    """The six subsections appear in the order FR-001 mandates so the
    P-VER section-order check passes (foundation -> environment ->
    bootstrap -> per-integration -> per-kind adapter -> deferred)."""
    indices: list[tuple[str, int]] = []
    for heading in _REQUIRED_SUBSECTIONS:
        idx = req_tpl_text.find(heading)
        if idx == -1:
            pytest.fail(
                f"Subsection heading missing: `{heading}`. The "
                "order-check cannot run until all six are present."
            )
        indices.append((heading, idx))
    sorted_by_index = sorted(indices, key=lambda pair: pair[1])
    assert sorted_by_index == indices, (
        "Verification Plan subsections appear in the wrong order. "
        f"Expected (FR-001 order): {[h for h, _ in indices]}. "
        f"Found order: {[h for h, _ in sorted_by_index]}."
    )


def test_req_tpl_block_cites_canonical(req_tpl_text: str) -> None:
    _assert_cites_canonical("requirements-templates/SKILL.md", req_tpl_text)


def test_req_tpl_block_cites_adr001(req_tpl_text: str) -> None:
    _assert_cites_adr001("requirements-templates/SKILL.md", req_tpl_text)


def test_req_tpl_block_cites_adr007(req_tpl_text: str) -> None:
    """ADR-007 fixes the seven-adapter table. The Verification Plan
    template block's `Per-kind verification adapter` subsection cites
    ADR-007 so the author following the template knows which adapter
    rows are authoritative."""
    assert "ADR-007" in req_tpl_text, (
        "Expected requirements-templates/SKILL.md to cite ADR-007 — "
        "the seven-adapter table that the `Per-kind verification "
        "adapter` subsection draws its adapter one-liner from."
    )


def test_req_tpl_block_does_not_inline_questions(req_tpl_text: str) -> None:
    """The template block uses placeholder instructions
    (`{agent populates with answer to Q1}`) referencing the canonical
    by question ID, never inlining the question stems."""
    _assert_no_inlined_questions("requirements-templates/SKILL.md", req_tpl_text)
