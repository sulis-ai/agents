"""Unit tests for _route_frontmatter — the discovery-layer frontmatter reader.

Test-first (RGB / Non-Negotiable #1): every behaviour below was observed
failing before _route_frontmatter.py existed.

Fixtures are copied verbatim from real marketplace frontmatter so the tests
prove behaviour against reality, not a simplified mock (WP-001 Notes; TDD
§10.2 MEA-09 — real adapters, not mocks).
"""

import pytest

from _route_frontmatter import FrontmatterError, parse_frontmatter


# --- Verbatim fixtures from the live marketplace ---------------------------

# From plugins/sulis/skills/specify/SKILL.md (head). The `description: >`
# folded scalar is the shape used by EVERY skill — losing it is fatal to
# discovery (ADR-006 / TDD §2.3).
SPECIFY_SKILL = """---
name: specify
description: >
  Use when the founder is ready to write down what a piece of work should
  do — Stage 1 (Specify) of a change. Produces a SPEC.md at the right depth:
  a quick three-line note for a small fix, a short facilitated spec for most
  work, or a full requirements document with flows for a new feature. The
  skill proposes a depth, the founder confirms or overrides, then it runs
  that mode. Usage: /sulis:specify (run inside a change).
user_invocable: true
---
# Specify

Body content here.
"""

# From plugins/sulis/agents/sulis.md — the orchestrator's routes_to block,
# a YAML list of mappings. The existing _wpxlib parser yields raw strings;
# discovery needs list[dict] (ADR-006 / TDD §3.2).
ORCHESTRATOR_ROUTES = """---
name: sulis
routes_to:
  - slug: context-cartographer
    description: "Discover existing context, conventions, ADRs, and prior art in a codebase"
    triggers: ["what already exists", "scan the codebase", "Phase 2", "discover", "/sulis:discover-context"]
  - slug: requirements-analyst
    description: "Long-form requirements interview producing SRD + NFR + PRIMITIVE_TREE + GLOSSARY + MISUSE_CASES"
    triggers: ["interview me", "capture requirements", "Phase 3", "what does it need to do", "claude --agent requirements-analyst"]
---
Orchestrator body.
"""


# --- R1: folded scalar ------------------------------------------------------

def test_folded_scalar_joins_text():
    """A `description: >` block returns the full joined paragraph, not '>'."""
    mapping, _body = parse_frontmatter(SPECIFY_SKILL)
    desc = mapping["description"]
    assert desc != ">"
    # Folded: continuation lines join with single spaces into one paragraph.
    assert desc.startswith("Use when the founder is ready to write down")
    assert desc.endswith("Usage: /sulis:specify (run inside a change).")
    # No newline because the source folded block has no blank line in it.
    assert "\n" not in desc
    # The em-dash and the joined seam ("should do") survive the fold.
    assert "what a piece of work should do" in desc
    assert "Stage 1 (Specify) of a change" in desc


def test_folded_scalar_blank_line_is_newline():
    """A blank line inside a folded block produces a paragraph break (\\n)."""
    text = """---
description: >
  First paragraph line one
  first paragraph line two.

  Second paragraph after a blank line.
---
body
"""
    mapping, _body = parse_frontmatter(text)
    desc = mapping["description"]
    assert desc == (
        "First paragraph line one first paragraph line two.\n"
        "Second paragraph after a blank line."
    )


# --- literal block ----------------------------------------------------------

def test_literal_block_preserves_newlines():
    """A `|` literal block joins lines with newlines, indentation stripped."""
    text = """---
body: |
  line one
  line two
    indented under the block
name: x
---
rest
"""
    mapping, _body = parse_frontmatter(text)
    assert mapping["body"] == "line one\nline two\n  indented under the block"
    # Sibling key after the block is still parsed.
    assert mapping["name"] == "x"


# --- R2: nested list-of-mappings -------------------------------------------

def test_nested_list_of_mappings():
    """`routes_to:` returns list[dict] with slug/description/triggers keys."""
    mapping, _body = parse_frontmatter(ORCHESTRATOR_ROUTES)
    routes = mapping["routes_to"]
    assert isinstance(routes, list)
    assert len(routes) == 2
    first = routes[0]
    assert isinstance(first, dict)
    assert first["slug"] == "context-cartographer"
    assert first["description"] == (
        "Discover existing context, conventions, ADRs, and prior art in a codebase"
    )
    assert isinstance(first["triggers"], list)
    assert first["triggers"] == [
        "what already exists",
        "scan the codebase",
        "Phase 2",
        "discover",
        "/sulis:discover-context",
    ]
    assert routes[1]["slug"] == "requirements-analyst"
    assert "claude --agent requirements-analyst" in routes[1]["triggers"]


# --- regression floor: plain scalar + inline list --------------------------

def test_plain_scalar_and_inline_list():
    """Plain `name:` and an inline `[a, b]` list still parse correctly."""
    text = """---
name: specify
keys: [a, b, c]
user_invocable: true
---
the body
"""
    mapping, body = parse_frontmatter(text)
    assert mapping["name"] == "specify"
    assert mapping["keys"] == ["a", "b", "c"]
    # quotes/booleans are returned as their scalar string form (boring reader,
    # not a type-coercing YAML engine).
    assert mapping["user_invocable"] == "true"
    assert body.strip() == "the body"


def test_block_list_of_scalars():
    """A block sequence (`- a` / `- b`) parses to list[str]."""
    text = """---
standards:
  - REFERENTIAL_INTEGRITY_STANDARD
  - CRITICAL_THINKING_STANDARD
name: foo
---
body
"""
    mapping, _body = parse_frontmatter(text)
    assert mapping["standards"] == [
        "REFERENTIAL_INTEGRITY_STANDARD",
        "CRITICAL_THINKING_STANDARD",
    ]
    assert mapping["name"] == "foo"


# --- malformed block --------------------------------------------------------

def test_malformed_block_raises_FrontmatterError():
    """No leading '---', or an unterminated block, raises FrontmatterError."""
    # No leading delimiter at all.
    with pytest.raises(FrontmatterError):
        parse_frontmatter("name: specify\nno frontmatter fence here\n")

    # Unterminated block (opening '---' but no closing fence).
    with pytest.raises(FrontmatterError):
        parse_frontmatter("---\nname: specify\nstill inside, never closes\n")


def test_FrontmatterError_is_value_error():
    """FrontmatterError is a ValueError subclass (contract in WP)."""
    assert issubclass(FrontmatterError, ValueError)
