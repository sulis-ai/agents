---
id: WP-003
title: "Cockpit recreate-on-demand drives the CLI by change_id, not the non-unique handle"
status: pending
change_id: 01KTV4SS9N8BP0XN8GCQAXT6PC
kind: backend
primitive: SUBSTITUTE-Replace
group: SUBSTITUTE
sequence_id: WP-003
dependsOn: [WP-001]
blocks: []
estimated_token_cost:
  input: 8k
  output: 6k
tdd_section: "§2 Form, §3 Armor, §5 Components; ADR-001, ADR-002"
adrs: [ADR-001, ADR-002]
hardening_delta: HD-001, HD-004
verification:
  adapter: backend
  artifact: "apps/cockpit/server/tests/recreate-on-demand.test.ts::recreates a tidied colliding change by its change_id, not its handle"
---

## Context

`resolveContractWorktree` (`apps/cockpit/server/routes/_recreate-on-demand.ts:126`)
calls `runner.recreate(record.handle)` though it holds `record.changeId` (read by
id at `requireChange`). The `RecreateRunner` port (`ports/RecreateRunner.ts:44-51`)
is keyed by the non-unique handle. Per ADR-001 the seam must carry the unique id.
Depends on WP-001 (the CLI must accept `--change-id` first — a real data
dependency, not a contract stub; ADR-002).

## Contract

- MODIFY `ports/RecreateRunner.ts`: `recreate(changeId: string)`; update doc.
- MODIFY `adapters/SulisChangeRecreator.ts`: spawn
  `["recreate", "--change-id", changeId]` (argv array, `shell: false`,
  bounded timeout, typed `RecreateOutcome` — all unchanged). Reuse the
  `changeHandleGuard` predicate to shape-guard the id before spawn (its charset
  already matches the ULID; rename the guard's intent comment if needed but keep
  the leading-hyphen rejection).
- MODIFY `adapters/FakeRecreateRunner.ts`: same signature; expose `lastArg`.
- MODIFY `routes/_recreate-on-demand.ts:126`: `runner.recreate(record.changeId)`.
- The serving path's malformed-key degrade (contract.ts) still maps to the typed
  `unavailable` note — never a spawn, never a throw into the request.

## Definition of Done

**Red**
- `recreate-on-demand.test.ts::recreates a tidied colliding change by its
  change_id, not its handle` — `FakeRecreateRunner.lastArg === record.changeId`
  and `!== record.handle`. Fails today (gets handle). (This is HD-004.)

**Green**
- The serving path passes `record.changeId`; the production adapter spawns
  `--change-id`; test passes.

**Blue**
- The three recreate-on-demand degrade-path tests (not-recreatable /
  recreate-failed / recreate-no-op) still pass — only the carried argument
  changed, not the three-state contract.
- The recreate source-hygiene test (no mutating git verb, `shell:false`) still
  passes.
- `npm run typecheck` clean (the port signature change ripples to both adapters
  + the one call site — all updated in this WP).
