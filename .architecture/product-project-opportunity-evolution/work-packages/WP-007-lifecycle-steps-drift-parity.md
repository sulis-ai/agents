---
id: WP-007
title: Wire the lifecycle-steps canonical into the drift detector (Path-A parity gate)
status: pending
kind: backend
primitive: extend
group: EXPAND
change_id: CH-01KT61
sequence_id: WP-007
dependsOn: [WP-001, WP-002]
blocks: []
estimated_token_cost:
  input: 3k
  output: 2k
tdd_section: Proof §Drift-detector parity (Path A)
adrs: [ADR-001, ADR-004]
verification:
  adapter: backend
  artifact: tests/unit/test_check_canonical_drift_lifecycle_steps.py::test_conformance_exits_zero
---

## Context

Path A requires the canonical instances and the schema to stay in lock-step with
each other and with any prose that references them. This WP extends the existing
drift detector (`check-canonical-drift.py`) to cover the new lifecycle-steps
canonical (WP-001) + the v2.1.0 schema (WP-002): conformance → exit 0; a missing
or extra Step ULID, or a `step_name`-bearing schema regression → non-zero.

# canonical-source: TDD.md §Canonical Identifiers — Canonical lifecycle Step instances

## Contract

### Files modified

```
plugins/sulis/scripts/check-canonical-drift.py   # add lifecycle-steps to the checked set
```

The detector already exists and parses canonical ↔ prose annotations (reused,
not rebuilt — Reuse before build). This WP only registers the new canonical set
and the v2.1.0 schema parity in its checked inventory.

## Definition of Done

### Red — Failing tests written

- [ ] `tests/unit/test_check_canonical_drift_lifecycle_steps.py::test_conformance_exits_zero` — committed canonical + schema → detector exits 0
- [ ] `tests/unit/test_check_canonical_drift_lifecycle_steps.py::test_missing_step_ulid_fails` — drop a Step → non-zero
- [ ] `tests/unit/test_check_canonical_drift_lifecycle_steps.py::test_schema_step_name_regression_fails` — a `step_name` reappearing in the schema → non-zero

### Green — Implementation makes tests pass

- [ ] `check-canonical-drift.py` registers `instances/lifecycle-steps/steps.jsonld` + `lifecyclerun` 2.1.0 in its checked set

### Blue — Refactor complete

- [ ] No duplicate parsing logic — reuses the detector's existing canonical-set machinery
- [ ] The checked-set registration is data, not a new code path

## Sequence

- **dependsOn:** WP-001 (the canonical to check), WP-002 (the schema to check parity against)
- **blocks:** — (gate; nothing builds on it)
- **Parallelisable with:** WP-003..WP-006 (all read WP-001/WP-002; independent code surfaces)

## Estimated Token Cost

- **Input:** ~3k
- **Output:** ~2k
- **Total:** ~5k

## Notes

- `extend` not `create`: the drift detector is existing prior art; this registers
  a new checked set within it (EXPAND-Extend through an existing extension point).
