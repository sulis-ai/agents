"""Structural verification for WP-003 (verification-by-design change).

WP-003 extends ``plugins/sulis/agents/requirements-analyst.md`` so that
during Phase 3 (Convergent Specification) the agent reads the canonical
20-question set + asks each applicable question in plain English, and
populates a ``## Verification Plan`` section in the produced SRD with
six required subsections.

Per the WP Contract (`Definition of Done > Red`), the agent prompt MUST:

  1. Cite ``plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md``
     by relative path at least once (FR-003 / NFR-006 citation
     discipline).
  2. Carry the canonical HTML-comment annotation shape so the P-VER
     rubric's citation-presence check matches (MUC-003 defence).
  3. Contain NO inline copies of the canonical question text. The agent
     reads the canonical at runtime; inlining drifts (NFR-004).
  4. Have its Phase 3 output spec name the six required subsection
     headings (per FR-001 — the SRD's Verification Plan section's
     contract).
  5. Cross-reference ADR-001 (the "Verification Plan" section name)
     and ADR-005 (the slice-end auto-draft trigger that governs how
     deferred infrastructure needs surface to follow-on changes).

Stdlib + pytest only, Python 3.11-safe. Resolves paths relative to
this test file so the suite is location-stable inside any worktree.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# tests/unit/ -> tests/ -> scripts/ -> sulis/ -> plugins/ -> repo-root
_REPO_ROOT = Path(__file__).resolve().parents[5]
_AGENT_PROMPT = _REPO_ROOT / "plugins" / "sulis" / "agents" / "requirements-analyst.md"
_CANONICAL_REL = "plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md"

# The six subsection headings the Phase 3 output spec must enumerate, per
# FR-001 of this change's SRD and the dogfooded TDD §Verification Plan
# worked example (TDD.md lines 558-720).
_REQUIRED_SUBSECTIONS = (
    "What user-observable behaviour are we verifying?",
    "Verification environment(s)",
    "Bootstrap-from-zero case",
    "Per-integration verification strategy",
    "Per-kind verification adapter",
    "Infrastructure needs surfaced (deferred)",
)

# Cross-references that MUST resolve in this agent prompt:
#   ADR-001 — section name "Verification Plan"
#   ADR-005 — slice-end auto-draft trigger (the agent's "infrastructure
#             needs surfaced (deferred)" entries feed this mechanism)
_REQUIRED_ADR_REFS = ("ADR-001", "ADR-005")

# Sentinel question-text strings drawn from the canonical's foundational
# group (Q1 + the per-kind adapter header phrasing). If any of these
# literal phrases appears in the agent prompt, the prompt has inlined the
# canonical and broken NFR-004's anti-duplication invariant. The list
# stays small + conservative: we look for question stems that would only
# appear if someone copy-pasted from the canonical, not for generic
# words like "verification".
#
# These strings are pulled verbatim from VERIFICATION_QUESTIONS.md
# Q1, Q5, Q14 stems — the kinds of literal phrasing that copy-paste
# would carry.
_FORBIDDEN_INLINED_QUESTION_STEMS = (
    # Q1 stem — the foundational question's actual interrogative phrasing.
    "What user-observable behaviour, in plain English, will tell us this change works?",
    # Q5 stem — per-integration kickoff.
    "For each integration this change touches, is the verification real, recorded, or simulated?",
    # Q14 stem — per-kind adapter kickoff.
    "What kind of change is this (one of: methodology / backend / frontend / async / infrastructure / documentation / contract)?",
)


@pytest.fixture(scope="module")
def agent_prompt_text() -> str:
    """Read the agent prompt once per test module."""
    if not _AGENT_PROMPT.exists():
        pytest.fail(
            f"requirements-analyst agent prompt missing at "
            f"{_AGENT_PROMPT}. WP-003 extends this file; the structural "
            "assertions cannot run until it exists."
        )
    return _AGENT_PROMPT.read_text(encoding="utf-8")


def test_agent_prompt_exists() -> None:
    """The agent prompt lives at the path the WP Contract names."""
    assert _AGENT_PROMPT.exists(), (
        f"requirements-analyst agent prompt missing at {_AGENT_PROMPT}."
    )


def test_agent_prompt_cites_canonical_path(agent_prompt_text: str) -> None:
    """The agent prompt cites the canonical by relative path (FR-003 /
    NFR-006). The literal path string must appear at least once."""
    assert _CANONICAL_REL in agent_prompt_text, (
        f"Expected the agent prompt to cite the canonical by relative "
        f"path `{_CANONICAL_REL}` (FR-003 / NFR-006). The cite must be "
        "literal so the P-VER citation-presence check parses it."
    )


def test_agent_prompt_has_html_comment_annotation(
    agent_prompt_text: str,
) -> None:
    """The agent prompt carries the canonical HTML-comment annotation
    shape so the P-VER citation-presence check matches consumers
    uniformly (MUC-003 defence)."""
    # The shape is fixed by WP-001's matcher pattern:
    #   <!-- VERIFICATION_QUESTIONS source: plugins/.../VERIFICATION_QUESTIONS.md v<X.Y.Z> -->
    pattern = (
        r"<!--\s*VERIFICATION_QUESTIONS\s+source:\s*"
        r"plugins/sulis/references/standards/VERIFICATION_QUESTIONS\.md"
        r"\s+v\d+\.\d+\.\d+\s*-->"
    )
    assert re.search(pattern, agent_prompt_text), (
        "Expected the HTML-comment annotation shape "
        "`<!-- VERIFICATION_QUESTIONS source: "
        "plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md "
        "vX.Y.Z -->` in the agent prompt (MUC-003 defence — the P-VER "
        "citation-presence check parses this exact comment shape)."
    )


def test_agent_prompt_does_not_inline_question_text(
    agent_prompt_text: str,
) -> None:
    """NFR-004 / MUC-003 anti-duplication invariant: the agent reads the
    canonical at runtime; inlining the question text would drift. None of
    the canonical's literal question stems may appear in this file."""
    leaks: list[str] = []
    for stem in _FORBIDDEN_INLINED_QUESTION_STEMS:
        if stem in agent_prompt_text:
            leaks.append(stem)
    assert not leaks, (
        f"Agent prompt contains inlined canonical question text "
        f"(NFR-004 violation): {leaks}. The agent must cite "
        f"`{_CANONICAL_REL}` and read the canonical at runtime — not "
        "copy the question text into the prompt."
    )


def test_agent_prompt_phase3_output_spec_has_six_subsections(
    agent_prompt_text: str,
) -> None:
    """The Phase 3 output spec extension names the six required
    Verification Plan subsection headings (per FR-001 and ADR-001).
    Each heading must appear at least once in the agent prompt so the
    agent knows to produce them in the SRD."""
    missing: list[str] = []
    for heading in _REQUIRED_SUBSECTIONS:
        if heading not in agent_prompt_text:
            missing.append(heading)
    assert not missing, (
        f"Agent prompt's Phase 3 output spec missing required "
        f"Verification Plan subsection headings: {missing}. All six "
        "are required by FR-001 / ADR-001 and must be enumerated in "
        "the agent prompt so the produced SRD carries them."
    )


def test_agent_prompt_section_heading_uses_adr001_literal(
    agent_prompt_text: str,
) -> None:
    """ADR-001 fixes the section heading literal: ``## Verification
    Plan`` (exact casing). The agent prompt must use this exact literal
    when instructing the agent to produce the SRD section, so the P-VER
    section-presence regex anchors on it."""
    assert "## Verification Plan" in agent_prompt_text, (
        "Expected the literal `## Verification Plan` in the agent "
        "prompt (ADR-001 — exact section heading; the P-VER "
        "section-presence regex anchors on this literal)."
    )


def test_agent_prompt_cross_refs_required_adrs(
    agent_prompt_text: str,
) -> None:
    """Cross-references resolve to the design's ADRs so the agent's
    instructions stay anchored to the design rationale: ADR-001 names
    the section, ADR-005 governs the slice-end auto-draft trigger that
    consumes the agent's deferred-need entries."""
    missing: list[str] = []
    for adr in _REQUIRED_ADR_REFS:
        if adr not in agent_prompt_text:
            missing.append(adr)
    assert not missing, (
        f"Agent prompt missing required ADR cross-references: "
        f"{missing}. ADR-001 fixes the section heading; ADR-005 "
        "governs the slice-end auto-draft trigger that consumes the "
        "agent's `Infrastructure needs surfaced (deferred)` entries."
    )
