---
id: WP-007
title: "Phase 1 — pure-core property tests: handle/match/resolve/refuse/path invariants over generated inputs"
status: pending
change_id: 01KTV4SS9N8BP0XN8GCQAXT6PC
kind: backend
primitive: REINFORCE-Test
group: REINFORCE
sequence_id: WP-007
dependsOn: [WP-006]
blocks: []
estimated_token_cost:
  input: 9k
  output: 8k
tdd_section: "§Verification Plan (property-based method); proves SPEC invariants behind Scenarios 1,4,5,6 universally"
adrs: []
fixtures_created:
  - plugins/sulis/scripts/tests/unit/test_change_identity_properties.py
verification:
  adapter: backend
  artifact: "plugins/sulis/scripts/tests/unit/test_change_identity_properties.py::test_matching_handle_is_sound_and_complete"
---

## Context

The example-based tests prove the safe-resolution invariants on one fixed
population. This WP proves them UNIVERSALLY: for any generated change-set (any
collision structure), the pure resolution functions hold. The five invariants
map to the SPEC's safety guarantees — exact-id resolution (Scenarios 1, 4),
ambiguity-always-refuses (Scenario 5), mint/lookup agreement (Scenario 6), and
the id-keyed worktree fallback being collision-proof (Scenario 3 DiD). All five
functions under test are pure (records / ids passed as arguments), so each
property runs thousands of examples with zero store or git seeding.

Consumes the strategies module from WP-006
(`_change_identity_strategies.py`). Own test file — no overlap with WP-008's
stateful file or with the WP-001..005 example-based files.

## Contract

- **`plugins/sulis/scripts/tests/unit/test_change_identity_properties.py`** (NEW,
  own file) — `@given`-driven properties over the WP-006 strategies. Imports the
  pure functions under test:
  - `ulid_handle`, `change_worktree_path` from `_wpxlib`.
  - `_changes_matching_handle`, and the explicit-handle resolution arm of
    `_select_change_id_refusing_conflict`, from `sulis-change` via the existing
    `SourceFileLoader` pattern (mirror `_load_sulis_change()` in
    `test_change_identity_resolution.py`). Ambiguity refusal is observed by
    patching `emit_error` / `_emit_ambiguous_match` to raise, so a refusal is
    detectable in-process (same technique the example-based suite uses).

## Definition of Done

**Red** — one property per invariant; each MUST currently pass against the
shipped code (these are characterising the already-built behaviour universally),
and MUST fail if the corresponding safety property is broken (verify by a local
mutation during authoring, then revert):

- `test_handle_is_pure_function_of_tail` — for any two valid ULIDs,
  `ulid_handle(a) == ulid_handle(b)` IFF `a[10:16] == b[10:16]`. (Invariant 1)
- `test_matching_handle_is_sound_and_complete` — for any generated change-set
  and any queried handle, `_changes_matching_handle` returns EXACTLY the records
  whose `ulid_handle(change_id) == queried_handle`: no record whose handle
  matches is dropped (complete), no record whose handle differs is returned
  (sound). (Invariant 2)
- `test_by_id_resolution_is_exact` — for any generated change-set (arbitrary
  collision structure), each member's `change_id` resolves to THAT member and
  never a sibling that merely shares its handle. (Invariant 3)
- `test_ambiguity_always_refuses_never_guesses` — for any change-set, a handle
  held by ≥2 records makes the explicit-handle resolution REFUSE with the exact
  candidate set (all colliding records, none missing/extra); a handle held by
  exactly 1 resolves to that one. Never silently returns one of several.
  (Invariant 4)
- `test_id_keyed_worktree_path_is_injective` — for any two distinct
  `change_id`s, `change_worktree_path(repo_root, primitive, slug,
  change_id=...)` returns distinct paths even when `primitive`+`slug` are
  identical. (Invariant 5)

**Green**
- All five properties pass under `uv run pytest
  tests/unit/test_change_identity_properties.py -q`. Each runs Hypothesis's
  default example budget (≥100 examples/property); no `@example` shortcuts that
  would mask a generated counterexample.

**Blue**
- No flakiness: a `--hypothesis-seed=0` run and a default run both pass; no
  `HealthCheck` suppressions beyond a justified `function_scoped_fixture` note if
  one is needed. Properties carry a one-line docstring naming the SPEC invariant
  each proves. No overlap with the example-based suite's assertions restated —
  these are the universal complement, cross-referenced in a module docstring.
