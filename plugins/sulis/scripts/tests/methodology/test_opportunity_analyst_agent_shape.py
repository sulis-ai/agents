"""Structural (shape) verification for WP-011 — the opportunity-analyst agent.

WP-011 creates ``plugins/sulis/agents/opportunity-analyst.md`` — the full
JTBD facilitation agent that pressure-tests and matures the *why*, mirroring
``requirements-analyst`` for the WHY rather than the WHAT.

These are *shape* tests (the agent body's structure + contract statements),
not *behavioural* tests. The pressure-test scenario journey — that a raw why
fed to the agent matures into an Opportunity advancing
hypothesis → validated/defined — is WP-013's job (run-from-graph), per the
WP Contract's "Behavioural coverage" note.

Per the WP Contract (``Definition of Done > Red``), the agent body MUST:

  1. Exist at the path the Contract names, with frontmatter carrying
     ``name`` / ``description`` / ``model`` / ``memory`` (mirroring
     requirements-analyst's frontmatter shape).
  2. Establish one-question-at-a-time JTBD facilitation and the
     opportunity state arc ``hypothesis → validated → defined``.
  3. Document emitting/updating the Opportunity via the single-idea
     emission path and RETURNING its ``dna:opportunity:<ulid>`` id as the
     hand-off medium (ADR-004 — analyst and capture share the ENTITY, never
     a code path), and that it does NOT call capture directly.
  4. Document BOTH modes: (a) invoked out-of-band by capture's ``full``
     path (returns the id capture reads back); (b) stand-alone (mature an
     existing opportunity by id later) — FR-11.
  5. State it stays in its lane: it emits ONLY Opportunities, never
     Requirements (that is capture's job; the no-orphan invariant stays
     with the orchestrator).

Stdlib + pytest only, Python 3.11-safe. Resolves paths relative to this
test file so the suite is location-stable inside any worktree.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# tests/methodology/ -> tests/ -> scripts/ -> sulis/ -> plugins/ -> repo-root
_REPO_ROOT = Path(__file__).resolve().parents[5]
_AGENT_PROMPT = (
    _REPO_ROOT / "plugins" / "sulis" / "agents" / "opportunity-analyst.md"
)

# The single-idea emission path WP-001 added (ADR-005). The agent's emission
# rides this; the body must reference it by name rather than reimplement
# Opportunity persistence (Green DoD).
_EMISSION_FN = "compose_opportunity_from_idea"
_EMISSION_SEAM = "sulis-emit-opportunity"

# The store hand-off id shape (ADR-004): the analyst returns this, capture
# reads it back by id.
_HANDOFF_ID_SHAPE = "dna:opportunity:"


@pytest.fixture(scope="module")
def agent_prompt_text() -> str:
    """Read the agent prompt once per test module."""
    if not _AGENT_PROMPT.exists():
        pytest.fail(
            f"opportunity-analyst agent prompt missing at {_AGENT_PROMPT}. "
            "WP-011 creates this file; the shape assertions cannot run "
            "until it exists."
        )
    return _AGENT_PROMPT.read_text(encoding="utf-8")


def _frontmatter(text: str) -> str:
    """Return the YAML frontmatter block (between the first two ``---``)."""
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    return m.group(1) if m else ""


def test_agent_frontmatter_and_jtbd_facilitation(
    agent_prompt_text: str,
) -> None:
    """The agent file exists; frontmatter has name/description/model/memory;
    the body establishes one-question-at-a-time JTBD facilitation and the
    hypothesis → validated → defined arc."""
    assert _AGENT_PROMPT.exists(), (
        f"opportunity-analyst agent prompt missing at {_AGENT_PROMPT}."
    )

    fm = _frontmatter(agent_prompt_text)
    assert fm, (
        "Expected YAML frontmatter delimited by `---` at the top of the "
        "agent prompt (mirroring requirements-analyst)."
    )
    assert re.search(r"^name:\s*opportunity-analyst\s*$", fm, re.MULTILINE), (
        "Expected frontmatter `name: opportunity-analyst`."
    )
    assert re.search(r"^description:\s*\S", fm, re.MULTILINE), (
        "Expected a non-empty frontmatter `description:` (founder-English)."
    )
    assert re.search(r"^model:\s*\S", fm, re.MULTILINE), (
        "Expected frontmatter `model:` (e.g. `inherit`)."
    )
    assert re.search(r"^memory:\s*\S", fm, re.MULTILINE), (
        "Expected frontmatter `memory:` (e.g. `project`)."
    )

    # One-question-at-a-time JTBD facilitation. The body must establish both
    # the cadence discipline and the JTBD frame ("when... I want... so I
    # can...").
    assert re.search(
        r"one[\s-]question[\s-]at[\s-]a[\s-]time", agent_prompt_text, re.IGNORECASE
    ), (
        "Expected the body to establish one-question-at-a-time facilitation "
        "(the requirements-analyst discipline, applied to the why)."
    )
    assert re.search(r"\bJTBD\b|job[\s-]to[\s-]be[\s-]done", agent_prompt_text, re.IGNORECASE), (
        "Expected the body to frame facilitation as job-to-be-done (JTBD)."
    )
    assert re.search(
        r"when[\s\S]{0,40}I want[\s\S]{0,40}so I can", agent_prompt_text, re.IGNORECASE
    ), (
        "Expected the JTBD job-statement frame "
        '("when... I want... so I can...") in the body.'
    )

    # The opportunity state arc.
    for state in ("hypothesis", "validated", "defined"):
        assert state in agent_prompt_text, (
            f"Expected the opportunity state `{state}` in the arc "
            "hypothesis -> validated -> defined."
        )
    assert re.search(
        r"hypothesis[\s\S]{0,80}validated[\s\S]{0,80}defined",
        agent_prompt_text,
        re.IGNORECASE,
    ), (
        "Expected the arc stated in order: hypothesis -> validated -> defined."
    )


def test_agent_emits_opportunity_by_id_handoff(
    agent_prompt_text: str,
) -> None:
    """The body documents emitting/updating the Opportunity and returning its
    id (ADR-004 store hand-off), reuses the single-idea emission path
    (ADR-005), and states it does NOT call capture directly."""
    # Emits/updates an Opportunity entity.
    assert re.search(r"\bOpportunit", agent_prompt_text), (
        "Expected the body to document emitting/updating the Opportunity "
        "entity."
    )

    # Reuses WP-001's single-idea emission path + the write seam (Green DoD —
    # does not reimplement persistence).
    assert _EMISSION_FN in agent_prompt_text, (
        f"Expected the body to reference the single-idea emission path "
        f"`{_EMISSION_FN}` (WP-001 / ADR-005) — the agent's emission rides "
        "this, it does not reimplement Opportunity persistence."
    )
    assert _EMISSION_SEAM in agent_prompt_text, (
        f"Expected the body to reference the `{_EMISSION_SEAM}` write seam "
        "(ADR-005 — generalised for single-opportunity intake)."
    )

    # Returns the dna:opportunity:<ulid> id as the hand-off medium (ADR-004).
    assert _HANDOFF_ID_SHAPE in agent_prompt_text, (
        f"Expected the body to document returning the `{_HANDOFF_ID_SHAPE}"
        "<ulid>` id as the hand-off medium (ADR-004 — analyst and capture "
        "share the entity, identified by id)."
    )
    assert "ADR-004" in agent_prompt_text, (
        "Expected the body to cite ADR-004 (the store hand-off decision)."
    )

    # Does NOT call capture directly — the hand-off is an entity, never a
    # code path / function call (ADR-004).
    assert re.search(
        r"(not|never|no)[\s\S]{0,80}(call|invoke|spawn|code path|function call)"
        r"[\s\S]{0,40}capture"
        r"|capture[\s\S]{0,60}(not|never|no)[\s\S]{0,40}"
        r"(call|invoke|spawn|directly|code path|function call)",
        agent_prompt_text,
        re.IGNORECASE,
    ), (
        "Expected the body to state it does NOT call capture directly — the "
        "hand-off is the entity (returned id), never a shared code path "
        "(ADR-004)."
    )


def test_agent_stands_alone_and_composes(agent_prompt_text: str) -> None:
    """The body documents BOTH modes: (a) the capture-composed mode (invoked
    out-of-band by capture's `full` path, returns the id capture reads back);
    (b) the stand-alone mode (mature an existing opportunity by id later) —
    FR-11."""
    # Mode (a): capture-composed / out-of-band, returns id capture reads back.
    assert re.search(
        r"\bfull\b[\s\S]{0,200}capture|capture[\s\S]{0,200}\bfull\b",
        agent_prompt_text,
        re.IGNORECASE,
    ), (
        "Expected the body to document the capture-composed mode — invoked "
        "out-of-band by capture's `full` path, returning the id capture "
        "reads back."
    )

    # Mode (b): stand-alone — mature an EXISTING opportunity by id later.
    assert re.search(r"stand[\s-]?alone", agent_prompt_text, re.IGNORECASE), (
        "Expected the body to document the stand-alone mode (FR-11)."
    )
    assert re.search(
        r"existing[\s\S]{0,60}opportunit|mature[\s\S]{0,60}by[\s-]?id"
        r"|opportunit[\s\S]{0,60}by[\s-]?id",
        agent_prompt_text,
        re.IGNORECASE,
    ), (
        "Expected the stand-alone mode to document maturing an EXISTING "
        "opportunity by id later."
    )


def test_agent_stays_in_lane(agent_prompt_text: str) -> None:
    """The body states it emits ONLY Opportunities, not Requirements (that is
    capture's job; the no-orphan invariant stays with the orchestrator)."""
    # Emits only Opportunities — does NOT emit Requirements.
    assert re.search(
        r"(only|solely)[\s\S]{0,60}Opportunit"
        r"|Opportunit[\s\S]{0,60}(only|solely|its lane|lane)",
        agent_prompt_text,
        re.IGNORECASE,
    ), (
        "Expected the body to state it writes ONLY Opportunities (its lane)."
    )
    assert re.search(
        r"(not|never|does not|doesn't)[\s\S]{0,80}emit[\s\S]{0,40}Requirement"
        r"|Requirement[\s\S]{0,80}(capture'?s? job|not[\s\S]{0,20}analyst)",
        agent_prompt_text,
        re.IGNORECASE,
    ), (
        "Expected the body to state it does NOT emit Requirements (that is "
        "capture's job; the no-orphan invariant stays with the orchestrator)."
    )
