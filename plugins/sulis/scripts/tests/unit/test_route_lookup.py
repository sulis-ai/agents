"""Unit tests for `lookup` — the explicit-invocation deterministic fast-path.

Test-first (RGB / Non-Negotiable #1): every behaviour below is written to fail
before `lookup` exists in `_route_inventory.py`.

`lookup` is the deterministic fast-path the brainstorm calls out (TDD §4.2,
§10.1 R6; ADR-001): an explicit `/sulis:foo` (or a bare agent name) is matched
*exactly* against `InventoryEntry.invocation` — no classification, no fuzzy
fallback, never a guess. Fuzzy candidate scoring is `match`'s job (WP-006), not
`lookup`'s; a partial match here would defeat the determinism contract
(Armor §9).

Fixtures build a REAL skills/agents tree under tmp_path (real files, real
frontmatter) via the shared WP-002 helper `_route_fixtures.build_fixture_tree`
(MEA-09 / TDD §10.2) — the same source of truth WP-002's own tests use, so the
inventory `lookup` queries is the genuine derived inventory, not a hand-built
list. The fixture tree contains skills `specify`, `design`, `status` and agents
`requirements-analyst`, `sulis`.
"""

from unit._route_fixtures import build_fixture_tree

from _route_inventory import build_inventory, discover, lookup


def _fixture_inventory(tmp_path):
    """Build the derived inventory from the real fixture tree."""
    root = build_fixture_tree(tmp_path)
    entries, parse_failures = build_inventory(*discover(root))
    assert parse_failures == [], parse_failures
    return entries


# --- R6: a known invocation returns exactly the one matching entry ---------

def test_lookup_known_returns_one(tmp_path):
    """`lookup(entries, "/sulis:specify")` returns exactly the `specify` entry."""
    entries = _fixture_inventory(tmp_path)

    result = lookup(entries, "/sulis:specify")

    assert result is not None
    assert result.name == "specify"
    assert result.invocation == "/sulis:specify"
    assert result.kind == "skill"


# --- agents are invoked by bare name ---------------------------------------

def test_lookup_agent_by_bare_name(tmp_path):
    """`lookup(entries, "requirements-analyst")` returns the agent entry —
    agents are invoked by bare name, not `/sulis:` prefix."""
    entries = _fixture_inventory(tmp_path)

    result = lookup(entries, "requirements-analyst")

    assert result is not None
    assert result.name == "requirements-analyst"
    assert result.invocation == "requirements-analyst"
    assert result.kind == "agent"


# --- R6: an unknown invocation returns None (clear not-found) --------------

def test_lookup_unknown_returns_none(tmp_path):
    """`lookup(entries, "/sulis:nope")` returns None — the CLI maps this to a
    clear not-found (`ok:false`, exit 1) in WP-007. Never a guess."""
    entries = _fixture_inventory(tmp_path)

    assert lookup(entries, "/sulis:nope") is None


# --- exact, not substring: no partial/fuzzy match in lookup ----------------

def test_lookup_is_exact_not_substring(tmp_path):
    """`lookup(entries, "/sulis:spec")` returns None, NOT the `specify` entry.

    A prefix/substring of a real invocation must not match — exactness is the
    whole point of the deterministic fast-path (fuzzy fallback is WP-006's
    `match`, Armor §9 / WP Notes)."""
    entries = _fixture_inventory(tmp_path)

    assert lookup(entries, "/sulis:spec") is None
