"""CLI smoke tests for `sulis-route` — the composition root (TDD §4).

Test-first (RGB / Non-Negotiable #1): every behaviour below is written to fail
before the `sulis-route` executable exists.

`sulis-route` is the sibling CLI to `sulis-change`: an executable with no `.py`
extension, `argparse` subcommand dispatch via `_wpxlib.cli_main(parser,
HANDLERS)`, emitting the established JSON envelope (`{"ok": true, "data": …}` /
`{"ok": false, "error": …}`) with the same exit-code contract (0 success / 1
expected failure / 2 internal error). It is the ONLY place that does file I/O +
`print` + `sys.exit`; it wires the WP-002/003/005/006 adapters → the pure
domain → the envelope (TDD §2.2 dependency direction).

These tests invoke the real executable via subprocess (the `run_tool` fixture),
against REAL fixture trees on disk (MEA-09 / TDD §10.2 — real adapters, not
mocks). They prove the four subcommands are wired (inventory / lookup / match /
check) and that `check` exits 1 on a gate failure — the CI-blocking contract
WP-008 depends on.
"""

from __future__ import annotations

from pathlib import Path

from unit._route_fixtures import (
    build_fixture_tree,
    skill_md,
    write_file,
)

# The live marketplace repo root: tests/unit/ -> tests/ -> scripts/ ->
# sulis/ -> plugins/ -> repo root.
_REPO_ROOT = Path(__file__).resolve().parents[5]


# ─── inventory: emits the envelope with inventory / route_set / excluded ─────


def test_cli_inventory_emits_envelope(run_tool, tmp_path):
    """`sulis-route inventory --repo-root <fixture>` → {"ok": true, "data":{…}}
    with `inventory`, `route_set`, and `excluded` keys, exit 0."""
    root = build_fixture_tree(tmp_path)
    # A rubric is required for route-set derivation; the fixture tree has none,
    # so write a minimal one (empty exclusions → route_set == inventory skills).
    write_file(
        root / "plugins" / "sulis" / "references" / "routing-rubric.md",
        "# Routing Rubric\n\n## Exclusions\n\n| Skill | Reason |\n|---|---|\n",
    )

    result = run_tool("sulis-route", "inventory", "--repo-root", str(root))

    assert result.returncode == 0, result.stderr
    assert result.ok
    data = result.data
    assert "inventory" in data
    assert "route_set" in data
    assert "excluded" in data
    # The fixture tree has three skills (specify, design, status) + two agents.
    inv_names = {e["name"] for e in data["inventory"]}
    assert {"specify", "design", "status"} <= inv_names


def test_cli_inventory_route_set_excludes_rubric_entries(run_tool, tmp_path):
    """`route_set` is `inventory − exclusions`: a rubric-excluded skill appears
    in `excluded`, not in `route_set` (TDD §3.4)."""
    root = build_fixture_tree(tmp_path)
    write_file(
        root / "plugins" / "sulis" / "references" / "routing-rubric.md",
        "# Routing Rubric\n\n## Exclusions\n\n| Skill | Reason |\n|---|---|\n"
        "| design | meta; not a route |\n",
    )

    result = run_tool("sulis-route", "inventory", "--repo-root", str(root))

    assert result.ok, result.stderr
    route_names = {e["name"] for e in result.data["route_set"]}
    assert "design" not in route_names
    assert "design" in result.data["excluded"]
    assert "specify" in route_names


# ─── lookup + match: the deterministic + fuzzy fast-paths are wired ─────────


def test_cli_lookup_known_returns_entry(run_tool, tmp_path):
    """`sulis-route lookup /sulis:specify` returns the single matching entry
    (WP-005 result through the envelope)."""
    root = _fixture_with_rubric(tmp_path)

    result = run_tool("sulis-route", "lookup", "/sulis:specify",
                      "--repo-root", str(root))

    assert result.returncode == 0, result.stderr
    assert result.ok
    assert result.data["entry"]["name"] == "specify"
    assert result.data["entry"]["invocation"] == "/sulis:specify"


def test_cli_lookup_unknown_exits_1(run_tool, tmp_path):
    """`sulis-route lookup /sulis:nope` → ok:false, exit 1 (clear not-found,
    never a guess — TDD §4.2)."""
    root = _fixture_with_rubric(tmp_path)

    result = run_tool("sulis-route", "lookup", "/sulis:nope",
                      "--repo-root", str(root))

    assert result.returncode == 1
    assert result.json is not None
    assert result.json["ok"] is False


def test_cli_lookup_and_match_wired(run_tool, tmp_path):
    """`match` returns ranked candidates (WP-006 result through the envelope),
    proving the composition root wires the fuzzy fast-path too."""
    root = _fixture_with_rubric(tmp_path)

    result = run_tool("sulis-route", "match", "/sulis:specify the work",
                      "--repo-root", str(root))

    assert result.returncode == 0, result.stderr
    assert result.ok
    candidates = result.data["candidates"]
    assert candidates, "expected at least one ranked candidate"
    # The explicit invocation in the intent ranks `specify` first (W_INVOCATION).
    assert candidates[0]["entry"]["name"] == "specify"
    assert candidates[0]["score"] >= 100
    assert "matched_signals" in candidates[0]


def test_cli_match_top_n_caps_results(run_tool, tmp_path):
    """`--top-n` caps the candidate list (TDD §5.3)."""
    root = _fixture_with_rubric(tmp_path)

    result = run_tool("sulis-route", "match", "specify design status work",
                      "--top-n", "1", "--repo-root", str(root))

    assert result.ok, result.stderr
    assert len(result.data["candidates"]) <= 1


# ─── check: passes on the clean live tree, exits 1 on a gate failure ────────


def test_cli_check_exit_0_clean(run_tool):
    """`sulis-route check --repo-root <live repo>` PASSES (exit 0) against the
    real marketplace tree (R10 at the CLI boundary). Achievable post-WP-004
    (duplicate removed) + WP-009 (stray report relocated)."""
    result = run_tool("sulis-route", "check", "--repo-root", str(_REPO_ROOT))

    assert result.returncode == 0, (
        f"live-tree gate should pass; stderr={result.stderr} "
        f"data={result.data}"
    )
    assert result.ok
    assert result.data["passed"] is True
    assert result.data["orphans"] == []
    assert result.data["duplicates"] == []
    assert result.data["parse_failures"] == []


def test_cli_check_exit_1_on_fail(run_tool, tmp_path):
    """`sulis-route check` against a fixture tree with a DUPLICATE invocation
    exits 1 (the CI-blocking contract WP-008 wires). Two skill directories
    whose frontmatter `name` collides derive the same `/sulis:` invocation."""
    root = build_fixture_tree(tmp_path)
    write_file(
        root / "plugins" / "sulis" / "references" / "routing-rubric.md",
        "# Routing Rubric\n\n## Exclusions\n\n| Skill | Reason |\n|---|---|\n",
    )
    # Inject a second skill directory whose frontmatter name collides with the
    # existing `specify` skill → duplicate `/sulis:specify` invocation.
    write_file(
        root / "plugins" / "sulis" / "skills" / "specify-dup" / "SKILL.md",
        skill_md("specify", description="A colliding duplicate."),
    )

    result = run_tool("sulis-route", "check", "--repo-root", str(root))

    assert result.returncode == 1, (
        f"gate should fail (exit 1) on a duplicate; got rc={result.returncode}"
    )
    assert result.json is not None
    assert result.data["passed"] is False
    assert result.data["duplicates"], "the duplicate invocation must be reported"


def test_cli_check_exit_1_on_parse_failure(run_tool, tmp_path):
    """`sulis-route check` exits 1 when a SKILL.md has unreadable frontmatter
    (frontmatter-is-the-contract; the gate fails loud, never silently skips)."""
    root = build_fixture_tree(tmp_path)
    write_file(
        root / "plugins" / "sulis" / "references" / "routing-rubric.md",
        "# Routing Rubric\n\n## Exclusions\n\n| Skill | Reason |\n|---|---|\n",
    )
    # A SKILL.md with no YAML frontmatter at all → parse_failure.
    write_file(
        root / "plugins" / "sulis" / "skills" / "broken" / "SKILL.md",
        "# Broken skill\n\nNo frontmatter here.\n",
    )

    result = run_tool("sulis-route", "check", "--repo-root", str(root))

    assert result.returncode == 1
    assert result.data["passed"] is False
    assert result.data["parse_failures"], "the parse failure must be surfaced"


# ─── unknown subcommand → expected error (exit 1), not a crash ──────────────


def test_cli_no_subcommand_errors(run_tool):
    """Invoking with no subcommand is an argparse usage error, not a crash."""
    result = run_tool("sulis-route")
    # argparse with required subparsers exits 2 (its own usage-error code);
    # this asserts the CLI doesn't hang or 0-exit on no args.
    assert result.returncode != 0


# ─── Helpers ────────────────────────────────────────────────────────────────


def _fixture_with_rubric(tmp_path: Path) -> Path:
    """A fixture skills/agents tree plus a minimal (empty-exclusion) rubric."""
    root = build_fixture_tree(tmp_path)
    write_file(
        root / "plugins" / "sulis" / "references" / "routing-rubric.md",
        "# Routing Rubric\n\n## Exclusions\n\n| Skill | Reason |\n|---|---|\n",
    )
    return root
