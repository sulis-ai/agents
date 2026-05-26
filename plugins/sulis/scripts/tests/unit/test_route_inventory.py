"""Unit tests for _route_inventory — value objects + auto-discovered inventory.

Test-first (RGB / Non-Negotiable #1): every behaviour below is written to fail
before _route_inventory.py exists.

Fixtures build a REAL skills/agents tree under tmp_path (real files, real
frontmatter), not monkeypatched parsers — MEA-09 / TDD §10.2. The bugs live in
the parse-and-walk seam, so the tests exercise the real filesystem-walk adapter
(`discover`) end-to-end with the pure domain (`build_inventory`, `route_set`).

The fixture-tree builder lives in the shared helper `_route_fixtures.py`
(extracted in the Blue phase for WP-005/006/007 reuse — EP-02; TDD §10.3).
"""

from unit._route_fixtures import build_fixture_tree, write_file

from _route_inventory import (
    InventoryEntry,
    Route,
    build_inventory,
    derive_invocation,
    discover,
    route_set,
)


# --- R3: inventory lists everything in the tree ----------------------------

def test_inventory_lists_all(tmp_path):
    """Every fixture skill and agent appears with the correct `kind`."""
    root = build_fixture_tree(tmp_path)
    skill_sources, agent_sources = discover(root)
    entries, parse_failures = build_inventory(skill_sources, agent_sources)

    assert parse_failures == []
    by_name = {e.name: e for e in entries}

    # All three skills present, kind == "skill".
    for skill_name in ("specify", "design", "status"):
        assert skill_name in by_name, f"{skill_name} missing from inventory"
        assert by_name[skill_name].kind == "skill"

    # Both agents present, kind == "agent".
    for agent_name in ("requirements-analyst", "sulis"):
        assert agent_name in by_name
        assert by_name[agent_name].kind == "agent"

    # Five entries total (3 skills + 2 agents), no silent drops.
    assert len(entries) == 5


# --- R4: invocation convention ---------------------------------------------

def test_inventory_invocation_convention(tmp_path):
    """Skill `name: foo` -> `/sulis:foo`; agent `name: bar` -> `bar`."""
    root = build_fixture_tree(tmp_path)
    entries, _ = build_inventory(*discover(root))
    by_name = {e.name: e for e in entries}

    assert by_name["specify"].invocation == "/sulis:specify"
    assert by_name["design"].invocation == "/sulis:design"
    # Agents are invoked by bare name.
    assert by_name["requirements-analyst"].invocation == "requirements-analyst"
    assert by_name["sulis"].invocation == "sulis"


def test_derive_invocation_is_single_authority():
    """`derive_invocation` computes the convention directly (no FS needed)."""
    assert derive_invocation("foo", "skill") == "/sulis:foo"
    assert derive_invocation("bar", "agent") == "bar"


# --- §7.5#2: invocation keys off frontmatter `name`, not the directory ------

def test_invocation_keys_off_name_not_dir(tmp_path):
    """A skill in directory `wp-status/` whose `name` is `status` derives
    `/sulis:status` — proving invocation reads `name`, never the dir name."""
    root = build_fixture_tree(tmp_path)
    entries, _ = build_inventory(*discover(root))
    by_name = {e.name: e for e in entries}

    # The entry is named `status` (from frontmatter), not `wp-status` (the dir).
    assert "status" in by_name
    assert "wp-status" not in by_name
    assert by_name["status"].invocation == "/sulis:status"
    # Provenance still points at the wp-status directory's SKILL.md.
    assert by_name["status"].source_path.endswith("wp-status/SKILL.md")


# --- R5: unparseable frontmatter is a surfaced parse_failure, not a skip ----

def test_unparseable_is_parse_failure_not_skip(tmp_path):
    """A SKILL.md with no `name` produces a parse_failure tuple and does not
    silently vanish from the result ("frontmatter is the contract")."""
    root = build_fixture_tree(tmp_path)
    # A skill whose frontmatter has NO `name` key.
    nameless = root / "plugins" / "sulis" / "skills" / "broken" / "SKILL.md"
    write_file(
        nameless,
        "---\ndescription: >\n  No name key here at all.\n---\n# broken\n",
    )

    entries, parse_failures = build_inventory(*discover(root))

    # It must NOT appear as a normal entry.
    assert all(e.name != "broken" for e in entries)
    # It MUST appear as a surfaced parse_failure with its source_path + a reason.
    failed_paths = [p for (p, _reason) in parse_failures]
    assert any(p.endswith("broken/SKILL.md") for p in failed_paths)
    # The reason is non-empty (surfaced, never swallowed).
    for path, reason in parse_failures:
        if path.endswith("broken/SKILL.md"):
            assert reason  # truthy, human-readable
            break
    else:
        raise AssertionError("broken/SKILL.md not found in parse_failures")


def test_malformed_frontmatter_is_parse_failure():
    """A source with no leading `---` fence raises FrontmatterError inside the
    reader; build_inventory catches it and surfaces a parse_failure (no bare
    except, no swallow). Exercised via the PURE source-tuple form — proves the
    domain needs no fixture filesystem."""
    bad = [("plugins/sulis/skills/x/SKILL.md", "no frontmatter fence at all\n")]
    entries, parse_failures = build_inventory(bad, [])
    assert entries == []
    assert len(parse_failures) == 1
    path, reason = parse_failures[0]
    assert path == "plugins/sulis/skills/x/SKILL.md"
    assert "frontmatter error" in reason


def test_build_inventory_is_pure_no_fs():
    """build_inventory operates purely on source tuples (no FS, no discover).

    Also covers the defensive branches: a non-list `routes_to`, a non-string
    `description`, and a route item that isn't a mapping — all degrade to safe
    empty/coerced values rather than raising."""
    skill_sources = [
        (
            "plugins/sulis/skills/foo/SKILL.md",
            "---\nname: foo\ndescription: >\n  A plain skill.\n---\nbody\n",
        )
    ]
    agent_sources = [
        # Orchestrator with a routes_to that is NOT a list (defensive: -> ()).
        (
            "plugins/sulis/agents/sulis.md",
            "---\nname: sulis\nroutes_to:\n---\nbody\n",
        )
    ]
    entries, parse_failures = build_inventory(skill_sources, agent_sources)
    assert parse_failures == []
    by_name = {e.name: e for e in entries}
    assert by_name["foo"].invocation == "/sulis:foo"
    # Malformed/absent routes_to degrades to an empty tuple, never raises.
    assert by_name["sulis"].routes == ()


def test_build_routes_skips_non_mapping_items():
    """A routes_to list with a non-dict item skips that item (defensive)."""
    # `- bare-string` parses to a scalar list item, not a mapping; the valid
    # mapping item still yields a Route.
    orch = (
        "plugins/sulis/agents/sulis.md",
        "---\n"
        "name: sulis\n"
        "routes_to:\n"
        "  - bare-string-not-a-mapping\n"
        "  - slug: real-route\n"
        '    description: "the real one"\n'
        "    triggers: [go]\n"
        "---\n"
        "body\n",
    )
    entries, _ = build_inventory([], [orch])
    routes = entries[0].routes
    assert len(routes) == 1
    assert routes[0].slug == "real-route"
    assert routes[0].triggers == ("go",)


# --- routes populated only for the orchestrator -----------------------------

def test_routes_populated_only_for_orchestrator(tmp_path):
    """`agents/sulis.md` with a routes_to block yields a non-empty `routes`
    tuple of Route; every other entry has `routes == ()`."""
    root = build_fixture_tree(tmp_path)
    entries, _ = build_inventory(*discover(root))
    by_name = {e.name: e for e in entries}

    orch = by_name["sulis"]
    assert isinstance(orch.routes, tuple)
    assert len(orch.routes) == 2
    assert all(isinstance(r, Route) for r in orch.routes)

    first = orch.routes[0]
    assert first.slug == "context-cartographer"
    assert first.description.startswith("Discover existing context")
    assert isinstance(first.triggers, tuple)
    assert "scan the codebase" in first.triggers

    # Every NON-orchestrator entry has an empty routes tuple.
    for name, entry in by_name.items():
        if name != "sulis":
            assert entry.routes == (), f"{name} should have no routes"


# --- route_set excludes listed names ----------------------------------------

def test_route_set_excludes_listed_names(tmp_path):
    """`route_set(entries, {"status"})` drops the entry named `status` and
    keeps the rest. Pure function: no state, no I/O."""
    root = build_fixture_tree(tmp_path)
    entries, _ = build_inventory(*discover(root))

    result = route_set(entries, frozenset({"status"}))
    result_names = {e.name for e in result}

    assert "status" not in result_names
    assert "specify" in result_names
    assert "design" in result_names
    assert "sulis" in result_names
    assert len(result) == len(entries) - 1


def test_route_set_empty_exclusions_returns_all(tmp_path):
    """Empty exclusion set returns every entry (route_set = inventory − ∅)."""
    root = build_fixture_tree(tmp_path)
    entries, _ = build_inventory(*discover(root))
    result = route_set(entries, frozenset())
    assert {e.name for e in result} == {e.name for e in entries}


# --- value objects are frozen + hashable ------------------------------------

def test_value_objects_are_frozen_and_hashable():
    """Route and InventoryEntry are frozen dataclasses (hashable, immutable)."""
    r = Route(slug="x", description="d", triggers=("a", "b"))
    e = InventoryEntry(
        name="x",
        kind="skill",
        invocation="/sulis:x",
        description="d",
        source_path="plugins/sulis/skills/x/SKILL.md",
        routes=(),
    )
    # Hashable (frozen) — can live in a set.
    assert {r, e}
    # Immutable.
    import dataclasses
    import pytest

    with pytest.raises(dataclasses.FrozenInstanceError):
        e.name = "y"  # type: ignore[misc]
