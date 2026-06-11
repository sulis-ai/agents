---
id: WP-008
title: "Phase 2 — stateful model-based test: change lifecycle never acts on the wrong id; ambiguous handle always refuses"
status: pending
change_id: 01KTV4SS9N8BP0XN8GCQAXT6PC
kind: backend
primitive: REINFORCE-Test
group: REINFORCE
sequence_id: WP-008
dependsOn: [WP-006]
blocks: []
estimated_token_cost:
  input: 10k
  output: 9k
tdd_section: "§Verification Plan (property-based method); sequence-level analogue of the per-call safety properties"
adrs: []
fixtures_created:
  - plugins/sulis/scripts/tests/unit/test_change_lifecycle_stateful.py
verification:
  adapter: backend
  artifact: "plugins/sulis/scripts/tests/unit/test_change_lifecycle_stateful.py::ChangeLifecycleStateMachine"
---

## Context

The Phase-1 properties (WP-007) prove each resolution call is safe in isolation.
This WP proves the SAME safety holds across arbitrary OPERATION SEQUENCES — the
sequence-level analogue. A Hypothesis `RuleBasedStateMachine` drives random
sequences of `start` / `ship` / `nuke` / `recreate` / `focus` over a store
model, and after EVERY step asserts the change-identity safety invariant:
**no operation ever acts on a change whose id ≠ the requested id, and an
ambiguous handle always refuses.** This is the sequence-level guard against the
two observed symptoms in the SPEC (a session on the wrong change; two sessions
braided into one workspace).

Consumes the WP-006 strategies for generating the colliding/non-colliding
populations the rules act over. Own test file — disjoint from WP-007's pure-core
file and from the WP-001..005 example-based files, so WP-007 and WP-008 run in
parallel with no add/add conflict.

## Design decision — store model (recorded)

Prefer an **in-memory / dict-backed store model**: the rules call the SAME pure
resolution functions the real CLI uses (`_changes_matching_handle`,
`change_worktree_path`, and the explicit-handle arm of
`_select_change_id_refusing_conflict`) against an in-process `dict[change_id ->
record]` model of the store, with worktree paths computed (not materialised on
disk). This keeps thousands of generated sequences fast and deterministic and
keeps the machine focused on the IDENTITY invariant (which is pure logic), not
on git/filesystem mechanics already covered by the example-based
`test_collision_regression.py` real-store suite. The destructive verbs (`ship`,
`nuke`) are modelled as state transitions (record removed / marked shipped) gated
on a SAFE resolve — exercising "the resolve picked the right id" without spawning
git. A thin real-store variant is acceptable ONLY if a verb's identity logic
cannot be exercised purely; default to the in-memory model.

## Contract

- **`plugins/sulis/scripts/tests/unit/test_change_lifecycle_stateful.py`** (NEW,
  own file) — a `hypothesis.stateful.RuleBasedStateMachine` subclass
  `ChangeLifecycleStateMachine` with:
  - **Model state:** a `dict[str, dict]` of live change records (id → record),
    a set of shipped ids, a set of nuked ids, and a `Bundle` of known
    change_ids / handles to draw selectors from.
  - **Rules:**
    - `start` — draw a new change (from `change_record` / `colliding_ulid_group`
      via the WP-006 strategies, mixing fresh-handle and colliding-handle
      changes) and add it to the model.
    - `recreate` / `focus` — pick a known selector (an id, OR a handle that may
      be ambiguous) and resolve it through the same pure resolution path the CLI
      uses; assert the resolved id is EXACTLY the requested id (for id
      selectors) or that an ambiguous handle REFUSES (raises, no silent pick).
    - `ship` / `nuke` — same resolve-then-act, transitioning the model only on a
      SAFE exact resolve; an ambiguous handle must refuse (model unchanged).
  - **Invariant(s)** (checked after every step via `@invariant` and inside each
    rule's assertion):
    - `no_operation_acts_on_wrong_id` — whenever a rule resolved a selector to
      act, the acted-on id equals the requested id (id selector) or the unique
      member (single-match handle); never a sibling.
    - `ambiguous_handle_always_refuses` — any handle held by ≥2 live records,
      when used as a selector, refuses rather than resolving to one.
    - `distinct_ids_keep_distinct_worktrees` — for every pair of live changes,
      their id-keyed `change_worktree_path` values differ (no two live changes
      ever share a worktree — the braided-session guard).

- The test exposes the machine as a `TestCase` (`ChangeLifecycleTest =
  ChangeLifecycleStateMachine.TestCase`) so pytest collects and runs it under the
  default step budget. Resolution refusal is observed via the same
  `emit_error` / `_emit_ambiguous_match` patch-to-raise technique WP-007 and the
  example-based suite use.

## Definition of Done

**Red**
- `ChangeLifecycleStateMachine` runs and its invariants currently HOLD against
  the shipped safe-resolution code (this characterises the built behaviour at the
  sequence level). Confirm the machine has teeth: during authoring, temporarily
  swap the resolve to a first-match-wins (the pre-#101 bug) and confirm the
  machine produces a minimal failing sequence; then revert.

**Green**
- `uv run pytest tests/unit/test_change_lifecycle_stateful.py -q` passes; the
  machine explores `start`/`ship`/`nuke`/`recreate`/`focus` sequences including
  colliding-handle populations (the strategy mix guarantees ambiguous handles
  appear).

**Blue**
- Deterministic: `--hypothesis-seed=0` and a default run both pass; step count is
  the Hypothesis default (no artificially tiny `max_examples` that would skip the
  collision states). No on-disk git/worktree side effects (in-memory model — the
  autouse `SULIS_STATE_DIR`/`SULIS_CHANGE_ID` isolation in `conftest.py` still
  applies as a backstop). Module docstring states the invariant and references
  WP-007 as the per-call analogue and `test_collision_regression.py` as the
  example-based real-store complement. Full `uv run pytest tests/unit/ -q` green.
