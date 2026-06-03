---
id: WP-012
title: Refactor Product/Opportunity/Project emitters to call evolve_entity (they become living)
status: pending
kind: backend
primitive: refactor
group: REORGANISE
change_id: CH-01KT61
sequence_id: WP-012
dependsOn: [WP-009, WP-011]
blocks: [WP-014]
characterisation_test: tests/characterisation/test_living_entity_emit_baseline.py
estimated_token_cost:
  input: 4k
  output: 4k
tdd_section: Form §Change-primitive classification (4 apply-evolve); Proof §Evolve characterisation test
adrs: [ADR-002, ADR-003]
verification:
  adapter: backend
  artifact: tests/unit/test_emitters_evolve.py::test_product_emit_opens_window
---

## Context

The apply-evolve refactor (ADR-003): the Product, Opportunity, and Project
emitters move from a plain `repo.save(...)` to `evolve_entity(repo=..., ...)` so
each change leaves a closed prior window + a new open window + a
`was_generated_by` PROV edge. This turns the brain's evolution machinery **ON**
for living entities for the first time. **REORGANISE-Refactor**, gated by the
WP-011 characterisation test (EP-07 MUST: baseline pinned and green before this
WP touches code).

# canonical-source: TDD.md §Form #5 — evolve_entity call sites

## Contract

### Files modified

```
plugins/sulis/scripts/<product emitter module>
plugins/sulis/scripts/<opportunity emitter module>
plugins/sulis/scripts/<project emitter module>   # the brain-store emit path
```

Each emitter, at its persistence point, calls `evolve_entity` (WP-009) instead of
`repo.save` for the living-entity write, passing the `was_generated_by`
LifecycleRun ref for the run that produced the version. First emit opens one
window; subsequent emits evolve. Graceful-degradation discipline preserved
(emission stays best-effort — host operation never fails on emit failure).

## Definition of Done

### Red — Failing tests written

- [ ] `tests/unit/test_emitters_evolve.py::test_product_emit_opens_window` — first Product emit → one open window
- [ ] `::test_product_re_emit_evolves` — a changed Product emit closes prior + opens new with `was_generated_by`
- [ ] `::test_opportunity_emit_evolves`
- [ ] `::test_project_emit_evolves`
- [ ] `::test_emit_failure_degrades_gracefully` — a failing evolve does not raise into the host operation
- [ ] WP-011 characterisation tests still green where the observable contract is unchanged

### Green — Implementation makes tests pass

- [ ] The 3 emitters call `evolve_entity` at their persistence point
- [ ] `was_generated_by` wired from the producing LifecycleRun ref
- [ ] Graceful degradation preserved (best-effort emit)

### Blue — Refactor complete

- [ ] No emitter re-implements window logic — all delegate to `evolve_entity` (one primitive, EP-03)
- [ ] No `repo.save` left on the living-entity persistence path (clean refactor)
- [ ] Characterisation baseline (WP-011) updated where evolve legitimately changes the observable output (windows now present), with the diff documented

## Sequence

- **dependsOn:** WP-009 (`evolve_entity`), WP-011 (characterisation baseline — MUST be green first)
- **blocks:** WP-014 (project-reconcile's characterisation test treats re-discovery as an evolve, which needs Project living)

## Estimated Token Cost

- **Input:** ~4k (3 emitters + evolve helper + ADR-003)
- **Output:** ~4k
- **Total:** ~8k

## Notes

- REORGANISE-Refactor on internal code — **not** a wrap. The emitters are edited
  in place to delegate to the shared primitive; no translation layer is added.
- Characterisation-test-first is the gate; WP-011 is the `dependsOn` that enforces it.
