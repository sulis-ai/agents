---
id: WP-001
title: Author canonical lifecycle Step instances at instances/lifecycle-steps/steps.jsonld
status: pending
kind: contract
primitive: create
group: GENERATE
change_id: CH-01KT61
sequence_id: WP-001
dependsOn: []
blocks: [WP-003, WP-004, WP-006, WP-007]
estimated_token_cost:
  input: 4k
  output: 3k
tdd_section: Form #1; Canonical Identifiers — Canonical lifecycle Step instances
adrs: [ADR-001, ADR-004]
verification:
  adapter: backend
  artifact: tests/unit/test_lifecycle_steps_canonical.py::test_step_ulids_match_canonical
---

## Context

Authors the three canonical foundation **Step** instances the v2.1.0 LifecycleRun
`step` ref points at (ADR-001: LifecycleRun IS the `prov:Activity`; Step is its
type). These are the *reusable definitions* runs reference. Per Path A
(canonical-as-spec), this file is the contract — the emitter (WP-003), the
helper (WP-004), the CLI (WP-005), and the migration (WP-006) all resolve their
`step` refs to ULIDs authored **here**, never minted inline.

This WP is the head of the lifecyclerun-migration chain (build-order piece 1).

**Pre-canonicalised identifiers (P8 rubric MUST):** every ULID is sourced
verbatim from `TDD.md §Canonical Identifiers — Canonical lifecycle Step
instances`. This WP transcribes; it does not invent.

# canonical-source: TDD.md §Canonical Identifiers — Canonical lifecycle Step instances

## Contract

### Files created

```
plugins/sulis/instances/lifecycle-steps/steps.jsonld
```

### Canonical-source bindings

| Step name | Source anchor | ULID |
|---|---|---|
| `change-started` | TDD §Canonical Identifiers — change-started Step ULID | `dna:step:01KT61X5ST01CHANGESTART00A` |
| `change-shipped` | TDD §Canonical Identifiers — change-shipped Step ULID | `dna:step:01KT61X5ST02CHANGESH1PP00A` |
| `unclassified-lifecycle-step` | TDD §Canonical Identifiers — unclassified Step ULID | `dna:step:01KT61X5ST03VNC1ASS1F1ED0A` |

### Step shape (one entry — repeat for all 3)

```jsonld
{
  "id": "dna:step:01KT61X5ST01CHANGESTART00A",
  "name": "change-started",
  "kind": "lifecycle",
  "mechanism": "mixed",
  "version": "1.2.0",
  "state": "active",
  "sys_status": "active",
  "valid_from": "2026-06-03T00:00:00Z",
  "_about": "The definition of a change-start lifecycle activity: a sulis-change start completed and a unit of work was opened. LifecycleRuns that record a change being opened point their step ref here."
}
```

The three Steps validate against the existing foundation `step.schema.json`
v1.2.0 (the `step` ref target type, unchanged this change — TDD §Canonical
Identifiers schema table).

## Definition of Done

### Red — Failing tests written

- [ ] `tests/unit/test_lifecycle_steps_canonical.py::test_steps_jsonld_parses` — JSON round-trip
- [ ] `tests/unit/test_lifecycle_steps_canonical.py::test_steps_count_is_3`
- [ ] `tests/unit/test_lifecycle_steps_canonical.py::test_each_step_validates_against_foundation_step_schema` — validates against `plugins/sulis/brain/compiled/foundation/step.schema.json`
- [ ] `tests/unit/test_lifecycle_steps_canonical.py::test_step_ulids_match_canonical` — all 3 ULIDs byte-exact vs TDD §Canonical Identifiers
- [ ] `tests/unit/test_lifecycle_steps_canonical.py::test_ulids_are_crockford_clean` — 26 chars, no I/L/O/U

### Green — Implementation makes tests pass

- [ ] `plugins/sulis/instances/lifecycle-steps/steps.jsonld` authored — 3 Step entries per Contract
- [ ] All ULIDs match TDD.md §Canonical Identifiers byte-exact (no inline minting)

### Blue — Refactor complete

- [ ] Each Step carries an `_about` line (founder-readable, no internal taxonomy)
- [ ] Step shapes consistent across all three entries (same field order, same `mechanism: mixed`)
- [ ] File is byte-stable on a regenerate (deterministic field order)

## Sequence

- **dependsOn:** — (head of the lifecyclerun-migration chain)
- **blocks:** WP-003 (emitter resolves `step` to these ULIDs), WP-004 (helper name→ULID map keys on these), WP-006 (migration maps `step_name` → these), WP-007 (drift parity reads this file). WP-005 (CLI) reaches these ULIDs transitively through WP-003/WP-004 — not a direct block.

## Estimated Token Cost

- **Input:** ~4k (TDD §Canonical Identifiers + foundation step.schema.json)
- **Output:** ~3k (one JSON-LD file, 3 Steps)
- **Total:** ~7k

## Notes

- The three Steps collapse into one atomic WP: they share one file and are the
  single source the whole migration chain resolves against. Splitting would
  produce partial reference sets.
