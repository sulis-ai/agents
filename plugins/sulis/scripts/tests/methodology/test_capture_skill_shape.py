"""Structural (shape) verification for WP-009 — the /sulis:capture skill.

WP-009 creates ``plugins/sulis/skills/capture/SKILL.md`` — the founder-facing
front door for capture (FR-01). It walks the why-then-what in one sitting
(FR-02), speaks only plain English (NFR-02 — no entity/IDEF0/ref vocabulary),
recommends the opportunity-analyst for the full path (ADR-004), and invokes
the ``sulis-capture`` CLI (WP-006) under the hood rather than re-implementing
capture logic in prose.

These are *shape* tests (the skill body's structure + contract statements),
not *behavioural* tests. The behavioural coverage — that a captured idea with
a why + what lands an Opportunity + a draft Requirement, and that a why-less
attempt is refused in plain English — is the capture scenario journey authored
in WP-013 (run-from-graph), per the WP Contract's "Behavioural coverage" note.

Per the WP Contract (``Definition of Done > Red``), the skill body MUST:

  1. Exist at the path the Contract names, with frontmatter carrying
     ``name: capture`` and a non-empty founder-English ``description`` — and
     the body must contain NO banned jargon tokens (``dna:``, ``--seed``,
     ``ULID``, ``IDEF0``, ``unevaluatedProperties``, ``for_product``,
     ``belongs_to_tenant``, ``tool_ref``).
  2. Reference ``sulis-capture`` as the invocation seam (not a
     re-implementation of capture logic in prose).
  3. Contain the ``claude --agent opportunity-analyst`` recommendation for
     the full path (ADR-004).

Stdlib + pytest only, Python 3.11-safe. Resolves paths relative to this
test file so the suite is location-stable inside any worktree.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# tests/methodology/ -> tests/ -> scripts/ -> sulis/ -> plugins/ -> repo-root
_REPO_ROOT = Path(__file__).resolve().parents[5]
_SKILL = _REPO_ROOT / "plugins" / "sulis" / "skills" / "capture" / "SKILL.md"

# The CLI the skill drives (WP-006). The body must reference it by name rather
# than re-implement capture logic in prose (the invocation seam).
_CLI_SEAM = "sulis-capture"

# The full-path recommendation (ADR-004 store hand-off — same agent-recommend
# pattern the Sulis agent uses for requirements-analyst).
_ANALYST_RECOMMENDATION = "claude --agent opportunity-analyst"

# NFR-02 — internal vocabulary that must NEVER appear in the founder-facing
# body. The founder is never instructed to type entity types, ref ids, ULIDs,
# --seed, or dna:* strings.
_BANNED_TOKENS = (
    "dna:",
    "--seed",
    "ULID",
    "IDEF0",
    "unevaluatedProperties",
    "for_product",
    "belongs_to_tenant",
    "tool_ref",
)


@pytest.fixture(scope="module")
def skill_text() -> str:
    """Read the skill body once per test module."""
    if not _SKILL.exists():
        pytest.fail(
            f"capture skill missing at {_SKILL}. WP-009 creates this file; "
            "the shape assertions cannot run until it exists."
        )
    return _SKILL.read_text(encoding="utf-8")


def _frontmatter(text: str) -> str:
    """Return the YAML frontmatter block (between the first two ``---``)."""
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    return m.group(1) if m else ""


def _body(text: str) -> str:
    """Return the body (everything after the frontmatter block)."""
    m = re.match(r"^---\n.*?\n---\n(.*)$", text, re.DOTALL)
    return m.group(1) if m else text


def test_skill_frontmatter_and_no_jargon(skill_text: str) -> None:
    """The skill file exists; frontmatter has ``name: capture`` and a non-empty
    founder-English ``description``; and the body carries no banned jargon
    tokens (NFR-02)."""
    assert _SKILL.exists(), f"capture skill missing at {_SKILL}."

    fm = _frontmatter(skill_text)
    assert fm, (
        "Expected YAML frontmatter delimited by `---` at the top of the skill "
        "(mirroring recon / specify)."
    )
    assert re.search(r"^name:\s*capture\s*$", fm, re.MULTILINE), (
        "Expected frontmatter `name: capture`."
    )
    assert re.search(r"^description:\s*\S", fm, re.MULTILINE), (
        "Expected a non-empty frontmatter `description:` (founder-English, no "
        "internal IDs)."
    )

    # NFR-02 — no internal vocabulary in the founder-facing body. We check the
    # whole file (frontmatter description must be founder-English too).
    for token in _BANNED_TOKENS:
        assert token not in skill_text, (
            f"Banned jargon token {token!r} found in the capture skill — the "
            "founder is never instructed to type entity types, ref ids, "
            "ULIDs, --seed, or dna:* strings (NFR-02)."
        )


def test_skill_invokes_capture_cli(skill_text: str) -> None:
    """The body references ``sulis-capture`` as the invocation seam — it drives
    the CLI rather than re-implementing capture logic in prose."""
    body = _body(skill_text)
    assert _CLI_SEAM in body, (
        f"Expected the body to invoke the `{_CLI_SEAM}` CLI (WP-006) as the "
        "capture seam — the skill drives the CLI, it does not re-implement "
        "capture logic in prose."
    )


def test_skill_recommends_analyst_for_full(skill_text: str) -> None:
    """The body contains the ``claude --agent opportunity-analyst``
    recommendation for the full path (ADR-004 store hand-off — the same
    agent-recommendation pattern the Sulis agent uses for
    requirements-analyst)."""
    body = _body(skill_text)
    assert _ANALYST_RECOMMENDATION in body, (
        f"Expected the body to recommend `{_ANALYST_RECOMMENDATION}` for the "
        "full path (ADR-004) — capture and the analyst compose through the "
        "store, not a direct call."
    )
    assert "ADR-004" in body, (
        "Expected the body to cite ADR-004 (the analyst store hand-off "
        "decision) for the full path."
    )
