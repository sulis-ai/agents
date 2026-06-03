---
id: WP-014
title: Characterisation test pinning minter path-safety + atomic-write + MUC-003 before the reconcile refactor
status: pending
kind: backend
primitive: test
group: REINFORCE
change_id: CH-01KT61
sequence_id: WP-014
dependsOn: [WP-012, WP-013]
blocks: [WP-015]
characterisation_test: tests/characterisation/test_minter_reconcile_baseline.py
estimated_token_cost:
  input: 3k
  output: 3k
tdd_section: Form §Change-primitive classification (6 project-reconcile — characterisation first); Armor §Path-safety preserved on reconcile
adrs: [ADR-006]
verification:
  adapter: backend
  artifact: tests/characterisation/test_minter_reconcile_baseline.py::test_current_minter_safety_pinned
---

## Context

ADR-006's Project-reconcile is a **REORGANISE-Refactor** of `_discovery/minter.py`
(`write_project_entity` → canonical `repo.save("project", …)` + `write_project_mirror(…)`).
Per the change-primitive MUST and EP-07, the minter's safety behaviour is **pinned
first**, in this WP, before WP-015 touches it. The load-bearing behaviour to
preserve verbatim: `_assert_path_safety` (`.resolve()` + `is_relative_to`),
`_atomic_write`, `_assert_not_exists` (MUC-003), the stale-tmp sweep, and the
SIGINT handler.

## Contract

### Files created

```
plugins/sulis/scripts/tests/characterisation/test_minter_reconcile_baseline.py
```

Captures the current minter's observable safety behaviour against a real temp
repo (no mock, MEA-09): path-safety rejection of `..`/symlink targets, atomic
write, refuse-on-exists (MUC-003), partial-write cleanup on cancel. No production
code modified in this WP.

## Definition of Done

### Red — Failing tests written

- [ ] `tests/characterisation/test_minter_reconcile_baseline.py::test_current_minter_safety_pinned` — current `write_project_entity` writes the mirror safely (golden behaviour)
- [ ] `::test_path_safety_rejects_traversal` — a `..`/symlink target is refused today
- [ ] `::test_muc003_refuses_existing` — re-mint over an existing entity is refused
- [ ] `::test_partial_write_cleaned_on_cancel`

### Green — Implementation makes tests pass

- [ ] The baseline tests pass against the **unchanged** minter (confirms the pin is faithful)

### Blue — Refactor complete

- [ ] Golden behaviour captures the four safety properties as discrete assertions (so WP-015 knows exactly what must survive on the mirror write)
- [ ] Real temp repo, no mock

## Sequence

- **dependsOn:** WP-012 (Project is a living entity by reconcile time — re-discovery is an evolve), WP-013 (the reconciled home is whichever adapter the port has — central-home wiring must exist)
- **blocks:** WP-015 (the refactor cannot start until safety is pinned — EP-07 MUST)

## Estimated Token Cost

- **Input:** ~3k (existing `minter.py`)
- **Output:** ~3k
- **Total:** ~6k

## Notes

- This is the REINFORCE-Test WP the design flagged as required-first for the
  project-reconcile refactor (the second of the two REORGANISE pieces). Split
  from WP-015 deliberately — the safety pin must be green before the minter moves.
