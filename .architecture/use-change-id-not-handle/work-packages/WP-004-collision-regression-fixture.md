---
id: WP-004
title: "Regression: 26-collision fixture proves every change resolves to itself across all four verbs"
status: pending
change_id: 01KTV4SS9N8BP0XN8GCQAXT6PC
kind: backend
primitive: REINFORCE-Test
group: REINFORCE
sequence_id: WP-004
dependsOn: [WP-001, WP-002]
blocks: []
estimated_token_cost:
  input: 8k
  output: 8k
tdd_section: "§4 Proof; HD-003"
adrs: []
hardening_delta: HD-003
verification:
  adapter: backend
  artifact: "plugins/sulis/scripts/tests/unit/test_change_identity_resolution.py::test_every_colliding_change_resolves_to_itself_across_all_verbs"
---

## Context

The matcher is unit-tested, but no regression reproduces the **live collision
state** (26 colliding handles, one shared by 4 changes) and proves self-resolution
across all four verbs. SPEC Verification Plan §3 requires the fixture to build its
own temp store + worktrees (no `~/.sulis` dependence). Depends on WP-001 +
WP-002 (the recreate-by-id and nuke-via-matcher paths must exist to assert on).

## Contract

- ADD a `collision_fixture` pytest fixture under
  `plugins/sulis/scripts/tests/` that seeds a temp `SULIS_STATE_DIR` with 26
  colliding handles (mirroring `CH-01KSNX`→4): each change a distinct ULID, a
  real branch, a record; temp git worktrees so resolution exercises real
  branch/worktree logic. Self-contained (passes from a fresh clone).
- ADD the cross-verb self-resolution suite (recreate / mark-shipped / nuke /
  focus-binding) + the shared-by-four disambiguation test.

## Definition of Done

**Red**
- Suite committed and observed red (fixture + helpers absent).

**Green**
- `test_every_colliding_change_resolves_to_itself_across_all_verbs` — for each of
  the 26 changes: `recreate --change-id` → own branch; ship/nuke resolve own id;
  `SULIS_CHANGE_ID` resolves self.
- `test_ambiguous_handle_lists_candidates_and_refuses` — the shared-by-four
  handle yields a 4-candidate refusal (handle + name + branch).

**Blue**
- Fixture builders reused across tests (no per-test copy-paste).
- The fixture seeds via the real record/worktree writers (not hand-rolled JSON)
  so it stays correct as the record schema evolves.
