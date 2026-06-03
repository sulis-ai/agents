---
id: WP-006
title: Build migrate_lifecyclerun_v1_to_v2 and migrate the marketplace's own .brain/instances
status: pending
kind: backend
primitive: create
group: GENERATE
change_id: CH-01KT61
sequence_id: WP-006
dependsOn: [WP-001, WP-002, WP-003]
blocks: []
estimated_token_cost:
  input: 4k
  output: 4k
tdd_section: Form #4; ADR-004 §Existing-instance migration; Proof §v1→v2 migration test
adrs: [ADR-004]
verification:
  adapter: backend
  artifact: tests/unit/test_lifecyclerun_migration.py::test_v1_fixture_migrates
---

## Context

The data-migration half of ADR-004 (no half-migrated state). A one-shot script
walks every `.brain/instances/*/lifecyclerun/*.jsonld`; for each v1 instance it
maps `step_name` → the matching Step ULID (via WP-004's map; unmappable →
`unclassified-lifecycle-step`), moves the old string to `step_label`, removes
`step_name`, adds `step`, **re-validates against v2.1.0 before writing**
(reject-on-invalid), and is **idempotent** (presence of `step` ⇒ skip). Runs
eager on the marketplace's own store in this change; lazy for downstream
consumers (graceful degradation).

# canonical-source: TDD.md §Canonical Identifiers — name→Step-ULID map

## Contract

### Files created

```
plugins/sulis/scripts/migrate_lifecyclerun_v1_to_v2.py
```

### Files modified (data — not counted toward touch-surface)

```
plugins/sulis/.brain/instances/*/lifecyclerun/*.jsonld   # the 2 on-disk v1 instances migrated
```

### Behaviour

```python
def migrate_instance(doc: dict) -> dict | None:
    """v1 → v2.1.0. Returns the migrated dict, or None if already v2 (idempotent).
    Re-validates against the 2.1.0 schema; raises on still-invalid (never writes)."""
```

Reuses WP-003 `compose_lifecyclerun` semantics for the v2 shape and WP-004's
`_resolve_step` for the name mapping (single source of truth — no second map).

## Definition of Done

### Red — Failing tests written

- [ ] `tests/unit/test_lifecyclerun_migration.py::test_v1_fixture_migrates` — `step_name` string in → v2 with resolved `step`, original in `step_label`, no `step_name`
- [ ] `tests/unit/test_lifecyclerun_migration.py::test_idempotent` — a v2 instance in ⇒ skipped (returns None)
- [ ] `tests/unit/test_lifecyclerun_migration.py::test_unmappable_to_unclassified` — `faithful-generation-harness` → `unclassified-lifecycle-step`
- [ ] `tests/unit/test_lifecyclerun_migration.py::test_rejects_invalid` — a doc that can't be made valid raises; nothing written
- [ ] `tests/unit/test_lifecyclerun_migration.py::test_revalidates_against_v2` — migrated output passes 2.1.0
- [ ] `tests/integration/test_migrate_marketplace_store.py::test_no_v1_remains_after_run` — after running on a temp copy of `.brain/instances`, zero `step_name`-bearing files remain

### Green — Implementation makes tests pass

- [ ] `migrate_lifecyclerun_v1_to_v2.py` authored per Contract (idempotent, reject-on-invalid)
- [ ] Run against the marketplace's own `.brain/instances`; the 2 v1 instances migrated to v2.1.0

### Blue — Refactor complete

- [ ] Migration reuses `_resolve_step` (WP-004) — no duplicate mapping
- [ ] Re-validation uses the same v2.1.0 schema (WP-002) the emitter targets — one validator
- [ ] Script is safe to re-run (idempotency proven by test)

## Sequence

- **dependsOn:** WP-001 (Step ULIDs), WP-002 (v2.1.0 schema to re-validate against), WP-003 (v2 instance shape)
- **blocks:** — (terminal step of the migration chain; ADR-004 lockstep step 6)

## Estimated Token Cost

- **Input:** ~4k (existing instances + ADR-004 + schema)
- **Output:** ~4k (script + tests)
- **Total:** ~8k

## Notes

- Migration atomicity (Armor): re-validate-before-write means no half-migrated
  instance is ever written; idempotency means a partial run is safe to resume.
