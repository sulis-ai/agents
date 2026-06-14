---
id: WP-006
title: "Hypothesis strategies module + dev-dependency wiring (foundation for the property layer)"
status: pending
change_id: 01KTV4SS9N8BP0XN8GCQAXT6PC
kind: backend
primitive: EXPAND-Create
group: EXPAND
sequence_id: WP-006
dependsOn: []
blocks: [WP-007, WP-008]
estimated_token_cost:
  input: 8k
  output: 7k
tdd_section: "§Verification Plan (property-based method, added); reuses ulid_handle / _changes_matching_handle / change_worktree_path"
adrs: []
fixtures_created:
  - plugins/sulis/scripts/tests/unit/_change_identity_strategies.py
verification:
  adapter: backend
  artifact: "plugins/sulis/scripts/tests/unit/test_change_identity_strategies_selftest.py::test_colliding_ulid_group_shares_handle"
---

## Context

The example-based identity/collision tests (WP-001..005, `done`) prove the
safe-resolution invariants on a *fixed* 26-change population
(`test_collision_regression.py`). This change adds a Hypothesis property layer
that proves the same invariants UNIVERSALLY over generated inputs. That layer
needs two foundations, both delivered here:

1. **A reusable strategies module** that generates valid ULIDs, controlled
   handle-collision groups, change records, and change-sets with a chosen
   collision structure. WP-007 (pure-core properties) and WP-008 (stateful
   model) both consume it.
2. **`hypothesis` declared as a test-only dependency** the SAME way `pytest`
   is, so CI installs it. The runtime CLI scripts stay stdlib-only per the
   plugin contract — Hypothesis is dev-group only.

The pure functions the strategies target are confirmed pure (records passed as
arguments, no store/git I/O): `ulid_handle(ulid)` (`_wpxlib.py:4197`),
`_changes_matching_handle(handle, records)` (`sulis-change:1363`),
`change_worktree_path(repo_root, primitive, slug, change_id=None)`
(`_wpxlib.py:4373`).

## Dependency-wiring approach

`pytest>=7.4` is declared in `plugins/sulis/scripts/pyproject.toml` under
`[dependency-groups].dev` (PEP 735), with `uv.lock` alongside. CI runs
`uv run pytest tests/unit/ -q` from `working-directory: plugins/sulis/scripts`
(`branch-ci.yml:60`), which resolves the dev group automatically. Add
`hypothesis` to that SAME `dev` group — one line, one source of truth — and
regenerate the lockfile. No workflow edit is needed (the workflow already runs
`uv run pytest`, which installs the dev group). This mirrors the in-file rationale
the pyproject already carries ("New runtime deps go here, declared ONCE").

## Contract

- **`plugins/sulis/scripts/pyproject.toml`** — ADD `"hypothesis>=6.100"` to
  `[dependency-groups].dev` (sibling of `pytest>=7.4`). Keep runtime
  `dependencies` (jsonschema, pyyaml) untouched — Hypothesis is dev-only.
  Regenerate `uv.lock` (`uv lock`) so `uv sync --frozen` in CI resolves it.
- **`plugins/sulis/scripts/tests/unit/_change_identity_strategies.py`** (NEW,
  underscore-prefixed so pytest does not collect it as a test module) — a
  Hypothesis strategies module exporting:
  - `valid_ulid() -> SearchStrategy[str]` — 26-char Crockford-base32 strings
    over the alphabet `0123456789ABCDEFGHJKMNPQRSTVWXYZ` (excludes I, L, O, U
    by construction — that IS the Crockford alphabet `_CROCKFORD_BASE32` in
    `_wpxlib.py:4157`). Every drawn value satisfies `validate_change_ulid`.
  - `colliding_ulid_group(n: int) -> SearchStrategy[list[str]]` — `n` distinct
    valid ULIDs that SHARE `tail[10:16]` (so all map to the same
    `ulid_handle`) and DIFFER in `tail[16:26]` (so they are distinct ids).
    Builds the shared 6-char handle-tail once, then draws `n` distinct
    10-char trailing-randomness suffixes and `n` (arbitrary) 10-char heads.
  - `change_record(change_id=None) -> SearchStrategy[dict]` — a record dict
    shaped like the store records `_changes_matching_handle` reads:
    `{change_id, handle, slug, intent, branch, primitive}`. `handle` is the
    stored `ulid_handle(change_id)` (so stored- and recomputed-handle paths
    agree by default); a variant strategy MAY set a stale head-derived handle
    to exercise the migration-robust recompute path.
  - `change_set(min_size=1, max_size=12, max_collision_groups=3) -> SearchStrategy[list[dict]]`
    — a list of `change_record`s with a CONTROLLABLE collision structure:
    zero or more handle-collision groups (each built from
    `colliding_ulid_group`) plus singleton changes, all ids globally distinct.
    Returns the records; callers derive the expected handle→records grouping.
- The module imports `ulid_handle` / `validate_change_ulid` from `_wpxlib`
  (importable via the conftest `sys.path` injection) — it does NOT re-implement
  the handle derivation; the shared tail is constructed and `ulid_handle` is the
  oracle the generators are built to agree with.

## Definition of Done

**Red**
- `test_change_identity_strategies_selftest.py` (NEW, own file) —
  meta-properties that pin the generators themselves before any consumer relies
  on them:
  - `test_valid_ulid_always_validates` — every drawn ULID passes
    `validate_change_ulid` and contains no I/L/O/U.
  - `test_colliding_ulid_group_shares_handle` — for any `n`, all members of a
    `colliding_ulid_group(n)` share one `ulid_handle` and are pairwise distinct
    ids.
  - `test_change_set_ids_globally_distinct` — no `change_set` ever yields two
    records with the same `change_id`.
  - `test_change_set_collision_structure_is_controllable` — the number of
    handles held by ≥2 records matches the requested collision-group count.

**Green**
- `hypothesis` added to the `dev` group; `uv.lock` regenerated.
  `uv run pytest tests/unit/test_change_identity_strategies_selftest.py -q`
  collects and passes (proves the dep resolves AND the strategies are sound).
- The strategies module is import-clean and pytest does not collect it as tests
  (underscore prefix).

**Blue**
- No runtime script imports `hypothesis` (grep the non-test scripts: still
  stdlib-only). `uv run pytest tests/unit/ -q` for the full existing suite still
  green (the new dev dep does not perturb the existing 259 unit tests).
- Strategy helpers carry docstrings stating the invariant each generator
  guarantees, so WP-007/008 authors consume them without re-reading this WP.
