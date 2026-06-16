---
id: HD-004
title: Cockpit recreate-on-demand carries change_id (behavioural test)
change_id: 01KTV4SS9N8BP0XN8GCQAXT6PC
status: proposed
severity: medium
pillar: proof
source: spec:fix-use-change-id-not-handle#scope-1
findings: [P-01]
scenarios: [1, 2]
primitive: REINFORCE-Test
---

## Gap

No cockpit test asserts that the recreate-on-demand serving path passes the
**unique change_id** (not the handle) across the `RecreateRunner` seam. Without
it, HD-001's cockpit change could silently regress back to `record.handle`.

## Failing characterisation test (proves the gap)

```ts
// apps/cockpit/server/tests/recreate-on-demand.test.ts (extend)
it("recreates a tidied colliding change by its change_id, not its handle", async () => {
  const runner = new FakeRecreateRunner();           // records lastArg
  const record = tidiedRecordWithCollidingHandle();   // changeId unique, handle shared
  await resolveContractWorktree({ record, runner });
  expect(runner.lastArg).toBe(record.changeId);       // FAILS today (gets handle)
  expect(runner.lastArg).not.toBe(record.handle);
});
```

`FakeRecreateRunner` is the real in-memory adapter for the port (MEA-09 — not an
ad-hoc mock); it records the argument it was driven with. Today the resolver
passes `record.handle`, so `lastArg` is the handle → RED.

## Change (ADDED / MODIFIED)

- **MODIFIED** `apps/cockpit/server/adapters/FakeRecreateRunner.ts`: expose
  `lastArg` (the value passed to `recreate`) for behavioural assertion, on the
  new `recreate(changeId)` signature from HD-001.
- **ADDED** the test above to `recreate-on-demand.test.ts`.

## Definition of Done

- RED: test committed and observed red against the pre-HD-001 handle-passing
  resolver.
- GREEN: with HD-001 wired, the resolver passes `record.changeId`; test passes.
- BLUE: the existing recreate-on-demand degrade-path tests (not-recreatable /
  recreate-failed / recreate-no-op) still pass — the change is the argument
  carried, not the three-state contract.
