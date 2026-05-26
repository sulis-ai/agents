"""Unit tests for `_route_gate` — the coverage gate (no-orphan / no-duplicate).

Test-first (RGB / Non-Negotiable #1): every behaviour below is written to fail
before `_route_gate.check` / `GateResult` exist.

The gate is the routing spine's referential-integrity check (TDD §7, ADR-004),
modelled on REFERENTIAL_INTEGRITY_STANDARD (RI-01 dangling / RI-02 registry
drift) rather than a new validation vocabulary (CP-01). `GateResult.passed` is
the AND of three clean conditions: no orphans (RT-01), no duplicates (RT-02),
no parse_failures (frontmatter-is-the-contract, Armor §9).

Two test surfaces:

  * Pure-domain tests drive `check` directly with hand-built `InventoryEntry`
    lists + a `RubricData` — exercising the algorithm in isolation (the
    function is pure, TDD §2.2).
  * The live-tree characterisation test (R10) builds the REAL marketplace
    inventory via the WP-002 discovery adapter + WP-003 rubric loader and
    asserts the gate PASSES — proving the spine against reality, not just
    fixtures (TDD §10.2). It is achievable now that WP-004 removed the
    `/sulis:status` duplicate and WP-009 relocated the stray non-agent report.
"""

from __future__ import annotations

from pathlib import Path

from _route_gate import GateResult, check
from _route_inventory import InventoryEntry, build_inventory, discover
from _route_rubric import RubricData, load


# ─── Helpers ───────────────────────────────────────────────────────────────


def _skill(name: str, *, source_path: str | None = None) -> InventoryEntry:
    """A minimal skill InventoryEntry with the derived `/sulis:` invocation."""
    return InventoryEntry(
        name=name,
        kind="skill",
        invocation=f"/sulis:{name}",
        description=f"{name} description",
        source_path=source_path or f"plugins/sulis/skills/{name}/SKILL.md",
    )


def _rubric(exclusions: frozenset[str] = frozenset()) -> RubricData:
    return RubricData(exclusions=exclusions, trigger_keywords={})


# ─── R10 / clean fixture: the gate passes when every skill is accounted for ──


def test_gate_passes_clean_fixture():
    """Every discovered skill is routable (none excluded, none orphaned) →
    passed=True, empty orphans/duplicates/parse_failures."""
    entries = [_skill("specify"), _skill("design"), _skill("plan-work")]

    result = check(entries, parse_failures=[], rubric=_rubric())

    assert isinstance(result, GateResult)
    assert result.passed is True
    assert result.orphans == ()
    assert result.duplicates == ()
    assert result.parse_failures == ()


def test_gate_passes_with_excluded_skill():
    """A skill that is NOT in the route-set but IS in rubric.exclusions is a
    legitimate non-route, not an orphan (ADR-004 — exclusion is consent)."""
    entries = [_skill("specify"), _skill("requirements-templates")]
    rubric = _rubric(frozenset({"requirements-templates"}))

    result = check(entries, parse_failures=[], rubric=rubric)

    assert result.passed is True
    assert result.orphans == ()


def test_gate_passes_clean_marketplace():
    """R10 (TDD §10.2): the gate PASSES against the LIVE marketplace tree.

    Characterisation test — proves the spine against reality. Achievable now
    that WP-004 corrected `wp-status`'s `name` (removing the `/sulis:status`
    duplicate) and WP-009 relocated the stray `sulis.VERIFICATION_REPORT.md`
    out of `agents/` (removing the lone parse_failure). A regression in either
    upstream condition resurfaces here as a gate failure — which is the point.
    """
    # tests/unit/ -> tests/ -> scripts/ -> sulis/ -> plugins/ -> repo root
    repo_root = Path(__file__).resolve().parents[5]

    entries, parse_failures = build_inventory(*discover(repo_root))
    rubric = load(repo_root)

    result = check(entries, parse_failures, rubric)

    assert result.passed is True, (
        f"live-tree gate failed — orphans={result.orphans} "
        f"duplicates={result.duplicates} parse_failures={result.parse_failures}"
    )
    assert result.orphans == ()
    assert result.duplicates == ()
    assert result.parse_failures == ()


# ─── R11: the gate fails on an orphan ────────────────────────────────────────


def test_gate_fails_on_orphan():
    """A skill present in the inventory but neither routable nor excluded is an
    orphan → passed=False, the orphan named (RT-01, ADR-004).

    Constructed by passing a rubric whose exclusions are out of sync with the
    route-set the caller derived — i.e. the route-set derivation invariant has
    been broken. The gate must catch it (closed-world: silence is never
    consent)."""
    routed = _skill("specify")
    orphan = _skill("rogue-skill")
    # The orphan is in the inventory but the caller's route_set omits it AND
    # the rubric does not exclude it.
    entries = [routed, orphan]
    rubric = _rubric()  # no exclusions

    result = check(
        entries,
        parse_failures=[],
        rubric=rubric,
        route_set_names={routed.name},  # rogue-skill deliberately omitted
    )

    assert result.passed is False
    assert "rogue-skill" in result.orphans


def test_gate_orphan_check_ignores_agents():
    """RT-01 (TDD §7.1) scopes the orphan rule to `kind == "skill"`. An agent
    absent from the route-set is not an orphan — agents are not founder-route
    targets in the same closed-world sense."""
    skill = _skill("specify")
    agent = InventoryEntry(
        name="requirements-analyst",
        kind="agent",
        invocation="requirements-analyst",
        description="agent",
        source_path="plugins/sulis/agents/requirements-analyst.md",
    )
    result = check(
        [skill, agent],
        parse_failures=[],
        rubric=_rubric(),
        route_set_names={"specify"},  # agent omitted, but agents aren't orphans
    )

    assert result.passed is True
    assert result.orphans == ()


# ─── R12: the gate fails on a duplicate invocation ──────────────────────────


def test_gate_fails_on_duplicate():
    """Two entries sharing an invocation token → passed=False, the duplicate
    reported as (invocation, path_a, path_b) (RT-02, TDD §7.2)."""
    a = InventoryEntry(
        name="status",
        kind="skill",
        invocation="/sulis:status",
        description="status one",
        source_path="plugins/sulis/skills/status/SKILL.md",
    )
    b = InventoryEntry(
        name="status",  # same derived invocation as a
        kind="skill",
        invocation="/sulis:status",
        description="status two",
        source_path="plugins/sulis/skills/wp-status/SKILL.md",
    )

    result = check([a, b], parse_failures=[], rubric=_rubric())

    assert result.passed is False
    assert len(result.duplicates) == 1
    invocation, path_a, path_b = result.duplicates[0]
    assert invocation == "/sulis:status"
    assert path_a == "plugins/sulis/skills/status/SKILL.md"
    assert path_b == "plugins/sulis/skills/wp-status/SKILL.md"


# ─── parse_failures force a gate failure ────────────────────────────────────


def test_gate_fails_on_parse_failure():
    """A parse_failure (a SKILL.md whose frontmatter can't be read) forces
    passed=False and is surfaced with its source_path — "frontmatter is the
    contract" landing in Armor (TDD §7, §9)."""
    entries = [_skill("specify")]
    parse_failures = [
        ("plugins/sulis/skills/broken/SKILL.md", "frontmatter has no parseable 'name'")
    ]

    result = check(entries, parse_failures=parse_failures, rubric=_rubric())

    assert result.passed is False
    assert result.parse_failures == (
        ("plugins/sulis/skills/broken/SKILL.md", "frontmatter has no parseable 'name'"),
    )


def test_gate_result_is_frozen():
    """GateResult is an immutable value object (boring, hashable, explicit —
    TDD §3)."""
    result = check([_skill("specify")], parse_failures=[], rubric=_rubric())
    try:
        result.passed = False  # type: ignore[misc]
    except AttributeError:
        pass
    else:  # pragma: no cover - defensive
        raise AssertionError("GateResult should be frozen (immutable)")


def test_gate_route_set_names_defaults_to_derived():
    """When `route_set_names` is not supplied, the gate derives it from
    inventory − exclusions (the §3.4 invariant), so a non-excluded skill is
    never spuriously flagged as an orphan."""
    entries = [_skill("specify"), _skill("design")]

    # No route_set_names passed: gate derives route_set = inventory - {} = all.
    result = check(entries, parse_failures=[], rubric=_rubric())

    assert result.passed is True
    assert result.orphans == ()
