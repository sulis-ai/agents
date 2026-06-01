"""Structural verification for WP-004 (verification-by-design change).

WP-004 extends the engineering-architect agent prompt so it:

  1. Ingests the SRD's ``## Verification Plan`` section as a first-class
     input (not optional, not skippable) and parses each of the six
     subsections.
  2. Applies the per-kind adapter from
     ``plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md``
     matching the change's ``kind:`` value.
  3. Asks the concretion questions for each integration-strategy entry
     in the SRD's Verification Plan — resolving the SRD's
     ``real vs mocked`` framing into TDD-level specifics (test
     artifact path, mock identity / fixture location / sandbox
     endpoint, resilience primitive for HTTP/RPC integrations).
  4. Surfaces contradictions between the SRD's plan and the TDD's
     design explicitly (UC-002 alt-A) — never silently overrides.
  5. Lists ``## Verification Plan`` as a required TDD output section
     with the same six subsections as the SRD.
  6. Cites the canonical (relative path) and the HTML-comment
     annotation shape; no inline duplication of the 20 question texts.
  7. References ADR-003's three ``verification:`` frontmatter shapes
     (concrete / deferred / trivial-carveout) so the architect's TDD
     output is internally consistent with the WP frontmatter format
     ``/sulis:plan-work`` will emit downstream.

This module is the RED-phase verification: the agent prompt has no
runtime tests (prose), so the failing-first cycle pins the documented
invariants on the live file as structural assertions. Mirrors the
shape of ``test_verification_questions_standard.py`` (WP-001) and
``test_requirements_analyst_verification_phase.py`` (WP-003).

Stdlib + pytest only, Python 3.11-safe. Resolves paths relative to
this test file so the suite is location-stable inside any worktree.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# tests/unit/ -> tests/ -> scripts/ -> sulis/ -> plugins/ -> repo-root
_REPO_ROOT = Path(__file__).resolve().parents[5]
_AGENT = _REPO_ROOT / "plugins" / "sulis" / "agents" / "engineering-architect.md"
_CANONICAL_REL = "plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md"

# Substrings from the canonical 20-question set. If any of these appear
# verbatim in the agent prompt, the prompt has inlined canonical content
# — exactly the MUC-003 anti-pattern this change exists to prevent. The
# list is conservative: a few load-bearing phrases that would only
# appear in a verbatim copy, not in coincidentally-similar prose.
_FORBIDDEN_INLINE_QUESTION_TEXT = (
    "What user-observable behaviour are we verifying",
    "Verification environment(s)",
    "Bootstrap-from-zero case",
    "Per-integration verification strategy",
    "Per-kind verification adapter",
    "Infrastructure needs surfaced (deferred)",
)

# The six subsection headings the architect's TDD output spec must
# enumerate (same six the SRD carries). Match the wording used in this
# change's TDD section so the architect's prose stays consistent with
# the rest of the methodology.
_REQUIRED_TDD_SECTION_SUBSECTIONS = (
    "user-observable behaviour",
    "Verification environment",
    "Bootstrap",
    "Per-integration",
    "Per-kind",
    "Infrastructure needs",
)


@pytest.fixture(scope="module")
def agent_text() -> str:
    """Read the engineering-architect prompt once per test module."""
    if not _AGENT.exists():
        pytest.fail(
            f"engineering-architect prompt missing at {_AGENT}. "
            "WP-004 extends this file; the structural assertions cannot "
            "run until it exists."
        )
    return _AGENT.read_text(encoding="utf-8")


def test_agent_file_exists() -> None:
    """The engineering-architect agent prompt lives where the WP
    Contract names it."""
    assert _AGENT.exists(), f"engineering-architect prompt missing at {_AGENT}."


def test_agent_cites_canonical_by_relative_path(agent_text: str) -> None:
    """The agent prompt MUST contain a literal citation to the canonical
    file by relative path (per MUC-003 defence + WP Contract DoD Red)."""
    assert _CANONICAL_REL in agent_text, (
        f"Expected literal citation to `{_CANONICAL_REL}` somewhere in "
        "the engineering-architect prompt. The canonical is the single "
        "source of truth — the agent reads it by path, not by inlined "
        "copy (MUC-003 defence)."
    )


def test_agent_has_html_comment_annotation_marker(agent_text: str) -> None:
    """The architect's TDD output template MUST carry the HTML-comment
    annotation shape so the P-VER citation-presence check parses
    successfully. The same annotation shape is locked by the canonical
    (WP-001) and required by ADR-001 / P-VER failure mode 6."""
    # Pattern: <!-- VERIFICATION_QUESTIONS source: <path> v<semver> -->
    # Allow flexible whitespace and version-suffix formats.
    assert re.search(
        r"<!--\s*VERIFICATION_QUESTIONS\s+source:\s*"
        r"plugins/sulis/references/standards/VERIFICATION_QUESTIONS\.md"
        r"\s+v\d+\.\d+\.\d+\s*-->",
        agent_text,
    ), (
        "Expected HTML-comment annotation shape "
        "`<!-- VERIFICATION_QUESTIONS source: plugins/.../"
        "VERIFICATION_QUESTIONS.md v<semver> -->` somewhere in the "
        "engineering-architect prompt. P-VER's citation-presence check "
        "parses this comment (ADR-001 + P-VER failure mode 6)."
    )


def test_agent_does_not_inline_canonical_question_text(
    agent_text: str,
) -> None:
    """Anti-MUC-003: the architect's prompt MUST NOT inline the
    canonical question text. The prompt cites the canonical file by
    path; the agent reads it at runtime.

    The forbidden strings are load-bearing phrases that only appear in
    a verbatim copy of the canonical's question text. Their absence is
    the SSOT invariant the rubric defends.
    """
    leaks: list[str] = []
    for phrase in _FORBIDDEN_INLINE_QUESTION_TEXT:
        # Use case-sensitive substring search — these are
        # canonical-form headings, not casual prose.
        if phrase in agent_text:
            # ALLOW the phrase only if it appears inside an HTML comment
            # (annotation), inline code (`...`), or as a section
            # heading the architect's TDD output template references
            # by name (the SIX subsections are named, not their bodies
            # inlined). The forbidden case is verbatim BODY content
            # from the canonical.
            #
            # Detect heading-by-name: phrase appears in a list item or
            # short reference, not in a multi-paragraph block.
            #
            # We score by counting how many of the six subsection
            # headings appear: 0-6 is fine (the architect lists them by
            # name), but if the phrase appears followed by a paragraph
            # of canonical question text, it's a leak. A conservative
            # check: leak iff phrase occurs > 3 times (indicating
            # multiple paragraphs reciting the canonical body).
            count = agent_text.count(phrase)
            if count > 3:
                leaks.append(f"{phrase!r} (occurs {count}×)")
    assert not leaks, (
        f"Engineering-architect prompt inlines canonical question "
        f"content: {leaks}. Cite the canonical by path, do not duplicate "
        "(MUC-003 anti-pattern)."
    )


def test_agent_references_verification_plan_section(agent_text: str) -> None:
    """The architect MUST mention `## Verification Plan` as a section
    name the architect ingests from the SRD AND emits in the TDD."""
    assert "## Verification Plan" in agent_text, (
        "Expected the literal section heading `## Verification Plan` "
        "in the engineering-architect prompt — both as an SRD input "
        "the architect ingests and as a required TDD output section "
        "(ADR-001 locks the section name)."
    )


def test_agent_tdd_output_lists_six_subsections(agent_text: str) -> None:
    """The architect's TDD output spec MUST list (by name) the six
    canonical Verification Plan subsections. The architect's TDD
    concretises the SRD's plan — same shape, more specifics."""
    missing: list[str] = []
    for subsection in _REQUIRED_TDD_SECTION_SUBSECTIONS:
        # Case-insensitive substring — the architect's prose may use
        # title-case or plain wording. Failure means the subsection
        # name appears nowhere in the prompt.
        if subsection.lower() not in agent_text.lower():
            missing.append(subsection)
    assert not missing, (
        f"Engineering-architect prompt missing TDD Verification Plan "
        f"subsection names: {missing}. The six required subsections "
        "are the same as the SRD's (per ADR-001)."
    )


def test_agent_has_concretion_question_instruction(agent_text: str) -> None:
    """The architect MUST be instructed to resolve the SRD's abstract
    plan into TDD-level concretions (test artifact paths, mock identity
    / fixture location / sandbox endpoint, resilience primitive for
    HTTP/RPC integrations). This is the WP Contract's "Concretion
    questions" sub-section requirement."""
    # The prompt must contain BOTH the word "concretion" (the named
    # sub-section) AND at least one indicator of the TDD-specifics
    # being resolved (artifact path / fixture / sandbox / timeout etc.).
    assert re.search(r"\bconcretion\b", agent_text, re.IGNORECASE), (
        "Expected the word `concretion` (the named sub-section per the "
        "WP Contract) somewhere in the engineering-architect prompt."
    )
    # At least one of the concretion-specifics named in the WP Contract
    # must appear nearby — the architect's job is to resolve abstract
    # SRD strategies into one of these specifics.
    specifics = (
        r"test artifact path",
        r"fixture location",
        r"sandbox endpoint",
        r"resilience primitive",
        r"timeout",
        r"circuit breaker",
        r"port/adapter",
        r"test seam",
        r"mock contract",
    )
    assert any(
        re.search(pattern, agent_text, re.IGNORECASE) for pattern in specifics
    ), (
        "Expected at least one TDD-specifics indicator near the "
        "concretion instruction (test artifact path / fixture "
        "location / sandbox endpoint / resilience primitive / "
        "timeout / circuit breaker / port/adapter / test seam / "
        "mock contract). The architect resolves abstract SRD "
        "strategies into one of these specifics."
    )


def test_agent_has_contradiction_surface_marker(agent_text: str) -> None:
    """When the TDD's concretion of a strategy contradicts the SRD's
    plan, the architect MUST surface the contradiction explicitly
    (UC-002 alt-A). The prompt MUST contain the phrase
    `Contradiction with SRD` (or equivalent surface marker)."""
    # Two acceptable markers per the WP Contract:
    #   - inline callout: `**Contradiction with SRD:** ...`
    #   - or the explicit phrase in the Open Architecture Questions
    #     instruction.
    assert re.search(
        r"Contradiction with SRD",
        agent_text,
    ), (
        "Expected the literal phrase `Contradiction with SRD` in the "
        "engineering-architect prompt — the architect MUST surface SRD "
        "↔ TDD plan contradictions explicitly rather than silently "
        "override (UC-002 alt-A, WP Contract Concretion-surface)."
    )


def test_agent_instructs_open_architecture_questions_routing(
    agent_text: str,
) -> None:
    """When a contradiction surfaces, the architect routes it to a
    visible escalation surface — either a `## Open Architecture
    Questions` row, an inline callout, an ADR, or founder escalation.
    The prompt MUST name at least one of these routes near the
    contradiction-surface instruction."""
    # Look for one of the routes named in the WP Contract:
    routes = (
        r"Open Architecture Questions",
        r"inline.*callout",
        r"ADR",
        r"escalate.*founder",
        r"founder.*escalat",
    )
    assert any(re.search(pattern, agent_text, re.IGNORECASE) for pattern in routes), (
        "Expected at least one contradiction-routing surface named in "
        "the prompt: `Open Architecture Questions` / inline callout / "
        "ADR / founder escalation. Per WP Contract: when SRD↔TDD "
        "contradicts, the architect routes the contradiction to one "
        "of these visible surfaces."
    )


def test_agent_references_three_verification_shapes(agent_text: str) -> None:
    """The architect's TDD output must be internally consistent with
    the per-WP `verification:` frontmatter shape ADR-003 locks. The
    prompt MUST reference at least the THREE shape names so the
    architect's TDD prose stays consistent with what ``/sulis:plan-work``
    will emit downstream."""
    # ADR-003's three discriminated shapes:
    # 1. Concrete (adapter + artifact)
    # 2. Deferred (adapter + deferred-to-follow-on)
    # 3. Trivial carveout (na: true + justification)
    #
    # The prompt must name ADR-003 (or the field shape) somewhere, AND
    # name at least two of the three discriminators so the architect
    # knows the shape exists. (Naming all three is the Blue-phase
    # polish; naming two is the minimum-viable Green.)
    assert "ADR-003" in agent_text or "verification:" in agent_text, (
        "Expected reference to ADR-003 (or the literal `verification:` "
        "frontmatter field) — the architect's TDD output must be "
        "internally consistent with the per-WP frontmatter shape "
        "ADR-003 locks."
    )
    discriminators = (
        r"\bconcrete\b",
        r"\bdeferred\b",
        r"\btrivial\b",
        r"\bcarveout\b",
        r"deferred-to-follow-on",
        r"\bna:\s*true\b",
    )
    hits = sum(
        1 for pattern in discriminators if re.search(pattern, agent_text, re.IGNORECASE)
    )
    assert hits >= 2, (
        f"Expected at least two of ADR-003's three shape discriminators "
        f"(concrete / deferred / trivial-carveout) in the architect's "
        f"prompt; found {hits}. The architect's prose must signal "
        "which shape applies per integration so downstream "
        "`/sulis:plan-work` can emit the correct frontmatter."
    )


def test_agent_ingests_srd_verification_plan_as_first_class_input(
    agent_text: str,
) -> None:
    """The architect's "Integration with Upstream SRD Plugin" section
    (or equivalent reading-the-SRD prose) MUST instruct the architect
    to read the SRD's Verification Plan section as a first-class input,
    not optional or skippable."""
    # Strategy: find a non-trivial passage near `## Verification Plan`
    # that includes one of {`read`, `ingest`, `parse`} so the agent's
    # treatment of the SRD section is clearly an input ingestion, not
    # just a name-drop.
    pattern = (
        r"(?:read|ingest|parse).{0,200}?Verification Plan"
        r"|Verification Plan.{0,200}?(?:read|ingest|parse|input)"
    )
    assert re.search(pattern, agent_text, re.IGNORECASE | re.DOTALL), (
        "Expected the engineering-architect prompt to instruct the "
        "architect to read / ingest / parse the SRD's "
        "`## Verification Plan` section as a first-class input. The "
        "section is not optional — every consumer reads it (WP "
        "Contract: \"Extension to the agent's Reading the SRD "
        'section").'
    )
