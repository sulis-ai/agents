---
id: HD-001
title: Resolve recreate by full change_id, not the non-unique handle
change_id: 01KTV4SS9N8BP0XN8GCQAXT6PC
status: proposed
severity: high
pillar: form+armor
source: spec:fix-use-change-id-not-handle#scope-1
findings: [F-01, A-01]
scenarios: [1, 2, 3]
primitive: SUBSTITUTE-Replace
---

## Gap

The cockpit holds the unambiguous `change_id` (it read the record by id) but
re-resolves the change by its **non-unique handle** across the CLI seam:

- `apps/cockpit/server/routes/_recreate-on-demand.ts:126`
  `const outcome = await runner.recreate(record.handle);`
- `apps/cockpit/server/ports/RecreateRunner.ts:44-51` — the port method is
  `recreate(handle: string)`.
- `plugins/sulis/scripts/sulis-change` `recreate` verb has **no `--change-id`**
  option (only `--handle` / `--slug`), so the cockpit physically cannot pass the
  id it already holds.

A colliding handle here makes the CLI refuse (cockpit degrades to "couldn't
reach this shipped change's contracts") or, absent the #101 matcher, materialise
a sibling's worktree — the cockpit half of "session works on the wrong change".

## Failing characterisation test (proves the gap)

**Python** — `recreate` cannot be driven by id today:

```python
def test_recreate_accepts_change_id_and_resolves_exact_change(tmp_change_store):
    # Two changes share a handle; recreate must materialise THIS id's worktree.
    a, b = colliding_pair(handle="CH-COLLID")      # distinct change_ids
    result = run_cli(["recreate", "--change-id", a.change_id])
    assert result.exit_code == 0                    # FAILS today: argparse error
    assert result.json["branch"] == a.branch        # never a sibling's
```

Today: `sulis-change recreate --change-id <ULID>` exits non-zero
(`unrecognized arguments: --change-id`). RED proven.

**TypeScript** — the cockpit passes the handle, not the id:

```ts
it("drives recreate by changeId, never the non-unique handle", async () => {
  const runner = new FakeRecreateRunner();
  await resolveContractWorktree({ record: tidiedRecord, runner });
  expect(runner.lastArg).toBe(tidiedRecord.changeId);  // FAILS: gets handle
});
```

## Change (ADDED / MODIFIED)

- **ADDED** `plugins/sulis/scripts/sulis-change`: `recreate --change-id <ULID>`
  argument; `cmd_recreate` resolves by id first (look up the record by
  `change_id` directly — branch-independent, unambiguous), keeping `--handle`
  and `--slug` working unchanged for backward compatibility (an unambiguous
  handle still resolves; an ambiguous one still refuses).
- **MODIFIED** `apps/cockpit/server/ports/RecreateRunner.ts`: the port contract
  becomes `recreate(changeId: string)` (the cockpit owns this port; its identity
  key is the unique id). Doc updated.
- **MODIFIED** `apps/cockpit/server/adapters/SulisChangeRecreator.ts`: spawn
  `["recreate", "--change-id", changeId]`. Keep the change_id shape-guard
  (alphanumerics, no leading hyphen — reuse `changeHandleGuard`'s predicate,
  which already matches the id charset).
- **MODIFIED** `apps/cockpit/server/adapters/FakeRecreateRunner.ts`: same
  signature; record `lastArg`.
- **MODIFIED** `apps/cockpit/server/routes/_recreate-on-demand.ts:126`:
  `runner.recreate(record.changeId)`.

## Definition of Done

- RED: both failing tests above committed and observed red.
- GREEN: `recreate --change-id` resolves the exact change; cockpit passes
  `record.changeId`; both tests pass.
- BLUE: `--handle`/`--slug` recreate paths still pass their existing tests
  (backward-compat); the handle remains in the JSON output as a display label.
