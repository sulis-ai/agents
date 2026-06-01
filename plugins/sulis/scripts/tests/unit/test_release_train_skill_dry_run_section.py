"""Docs-prose verification for WP-010 (release-train-as-entities change).

WP-010 extends ``plugins/sulis/skills/release-train/SKILL.md`` with a
new section that documents how ``/sulis:release-train --dry-run`` walks
the canonical Workflow (`plugins/sulis/instances/release-train/`) via
the brain's ``execute-workflow`` runner — instead of building the
preview from imperative YAML inspection. This module is the RED-phase
verification: the WP is `kind: docs`, so the failing-first cycle pins
the documented invariants on the live SKILL.md as structural assertions.

Per the WP Contract (`Definition of Done > Green` + the per-FR-011
spec): the new section MUST:

  1. Exist as a top-level ``##`` heading whose text contains the
     phrase ``Dry-run mode`` AND the phrase ``walk the canonical`` (so
     it's discoverable in the SKILL.md TOC and unambiguous about what
     the section adds).
  2. Reference the brain's ``execute-workflow`` agent (the mechanism)
     — the canonical-walking path delegates to
     ``/sulis-brain:execute-workflow``, and the prose MUST name it so
     a reader following the cross-reference knows where to look.
  3. Reference the canonical instances directory path
     (``plugins/sulis/instances/release-train/``) — both as the
     trigger for the canonical-walking path (existence check) and as
     the directory the brain agent reads.
  4. Cross-reference ADR-001 by name or ADR ID — the ADR is the
     authoritative justification for using the LLM-driven runner for
     dry-run only (Path A's v1 execution strategy).
  5. Cross-reference NFR-001 by ID — NFR-001 sets the token-budget
     envelope for the dry-run walk, and the section MUST surface that
     constraint so the founder knows the cost shape before invoking.
  6. Describe a fallback path when the canonical directory is absent
     (the skill MUST NOT break for marketplace forks that haven't
     authored the canonical) — the prose names the fallback so a
     reader knows the behaviour is graceful.

Stdlib + pytest only, Python 3.11-safe. Resolves paths relative to
this test file so the suite is location-stable inside any worktree.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# tests/unit/ -> tests/ -> scripts/ -> sulis/ -> plugins/sulis/
_SKILL_MD = (
    Path(__file__).resolve().parents[3] / "skills" / "release-train" / "SKILL.md"
)


@pytest.fixture(scope="module")
def skill_text() -> str:
    """The live release-train SKILL.md content as a single string."""
    assert _SKILL_MD.is_file(), f"missing release-train SKILL.md at {_SKILL_MD}"
    return _SKILL_MD.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def dry_run_section(skill_text: str) -> str:
    """The text of the new dry-run-walks-canonical section.

    Located by finding the ``##`` heading containing ``Dry-run mode``
    AND ``walk the canonical``; the section text runs to the next
    ``## `` heading at the same level (or end-of-file).
    """
    lines = skill_text.splitlines()
    start: int | None = None
    for idx, line in enumerate(lines):
        if (
            line.startswith("## ")
            and "Dry-run mode" in line
            and "walk the canonical" in line
        ):
            start = idx
            break
    assert start is not None, (
        "SKILL.md is missing the WP-010 section heading. Expected a "
        "top-level '## Dry-run mode ... walk the canonical' so the "
        "section is discoverable in the SKILL TOC and unambiguous "
        "about the canonical-walking behaviour."
    )
    end = len(lines)
    for idx in range(start + 1, len(lines)):
        if lines[idx].startswith("## "):
            end = idx
            break
    return "\n".join(lines[start:end])


def test_dry_run_section_heading_present(skill_text: str) -> None:
    """A top-level ``##`` heading naming the dry-run canonical walk.

    Readers scanning the SKILL.md TOC find the new behaviour via the
    heading; an inline note under another heading wouldn't surface.
    """
    lines = skill_text.splitlines()
    matches = [
        line
        for line in lines
        if line.startswith("## ")
        and "Dry-run mode" in line
        and "walk the canonical" in line
    ]
    assert matches, (
        "SKILL.md is missing the WP-010 section heading. Expected a "
        "top-level '## Dry-run mode ... walk the canonical' heading."
    )


def test_dry_run_section_names_brain_agent(dry_run_section: str) -> None:
    """The section names the underlying ``execute-workflow`` mechanism.

    The canonical-walking path dispatches to the brain's
    ``execute-workflow`` agent; a reader following the cross-reference
    needs the agent's slash-command form to find the actual runner.
    """
    assert "/sulis-brain:execute-workflow" in dry_run_section, (
        "The dry-run section MUST name the brain's "
        "'/sulis-brain:execute-workflow' agent — that's the actual "
        "mechanism that walks the canonical. Readers following the "
        "cross-reference need the slash-command form to find it."
    )


def test_dry_run_section_references_canonical_dir(dry_run_section: str) -> None:
    """The section references the canonical instances directory path.

    Both the existence check (which triggers the canonical-walking
    path) and the brain agent's input target are this directory.
    """
    assert "plugins/sulis/instances/release-train" in dry_run_section, (
        "The dry-run section MUST reference the canonical instances "
        "directory 'plugins/sulis/instances/release-train/' — it's "
        "both the trigger for the canonical-walking path and the "
        "directory the brain agent reads."
    )


def test_dry_run_section_cross_references_adr_001(dry_run_section: str) -> None:
    """The section cross-references ADR-001 by ID.

    ADR-001 is the authoritative justification for using the
    LLM-driven runner in dry-run only (Path A — canonical-as-spec +
    imperative + drift detector). A reader who wants to know *why*
    only dry-run uses the LLM path follows the ADR-001 reference.
    """
    assert "ADR-001" in dry_run_section, (
        "The dry-run section MUST cross-reference ADR-001 by ID. "
        "ADR-001 is the authoritative justification for using the "
        "LLM-driven runner only in dry-run (Path A — v1 execution "
        "strategy). Without the cross-reference, readers have no "
        "path to the rationale."
    )


def test_dry_run_section_cross_references_nfr_001(dry_run_section: str) -> None:
    """The section cross-references NFR-001 by ID.

    NFR-001 sets the token-budget envelope for the dry-run walk
    (imperative path stays zero-token). The section MUST surface that
    constraint so the founder knows the cost shape before invoking
    the canonical walk.
    """
    assert "NFR-001" in dry_run_section, (
        "The dry-run section MUST cross-reference NFR-001 by ID. "
        "NFR-001 sets the token-budget envelope for the dry-run "
        "walk; the founder needs the cost shape before invoking."
    )


def test_dry_run_section_describes_fallback(dry_run_section: str) -> None:
    """The section describes the absent-canonical fallback path.

    Marketplace forks that haven't authored the canonical MUST NOT
    see broken behaviour. The section names the fallback so a reader
    knows the canonical-absent case is handled gracefully (regression
    against today's imperative-only preview).
    """
    section_lower = dry_run_section.lower()
    assert "fallback" in section_lower or "falls back" in section_lower, (
        "The dry-run section MUST describe the fallback path when "
        "the canonical instances directory is absent. Marketplace "
        "forks that haven't authored the canonical MUST NOT see "
        "broken behaviour; the section MUST name the fallback so "
        "the graceful-degradation contract is explicit."
    )
