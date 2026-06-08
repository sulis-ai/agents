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
each change leaves a closed prior window + a new open window. This turns the
brain's evolution machinery **ON** for living entities for the first time.
**REORGANISE-Refactor**, gated by the WP-011 characterisation test (EP-07 MUST:
baseline pinned and green before this WP touches code).

**Provenance is conditional (corrected per ADR-002 / ADR-006):**
- **Product + Opportunity** (`prov:Entity`) call `evolve_entity(..., generated_by=<run ref>)`
  → the new window carries the `wasGeneratedBy` edge.
- **Project** (`prov:Plan`) calls `evolve_entity(..., generated_by=None)`
  → the new window moves but writes **NO** `wasGeneratedBy` edge. Project's
  lineage is bitemporal + `state` + `deprecated_for`; `wasGeneratedBy` is a
  type violation on a Plan. The run→Project link is the separately-deferred
  `LifecycleRun.for_project` edge on the run (out of scope).

# canonical-source: TDD.md §Form #5 — evolve_entity call sites

## Contract

### Files modified

```
plugins/sulis/scripts/<product emitter module>
plugins/sulis/scripts/<opportunity emitter module>
plugins/sulis/scripts/<project emitter module>   # the brain-store emit path
```

Each emitter, at its persistence point, calls `evolve_entity` (WP-009) instead of
`repo.save` for the living-entity write. The Product + Opportunity emitters pass
`generated_by=<LifecycleRun ref>` (the run that produced the version); the Project
emitter passes `generated_by=None` (no provenance edge — `prov:Plan`). First emit
opens one window; subsequent emits evolve. Graceful-degradation discipline
preserved (emission stays best-effort — host operation never fails on emit
failure).

## Definition of Done

### Red — Failing tests written

- [ ] `tests/unit/test_emitters_evolve.py::test_product_emit_opens_window` — first Product emit → one open window
- [ ] `::test_product_re_emit_evolves_with_prov` — a changed Product emit closes prior + opens new WITH `wasGeneratedBy`
- [ ] `::test_opportunity_emit_evolves_with_prov` — Opportunity new window carries `wasGeneratedBy`
- [ ] `::test_project_emit_evolves_WITHOUT_prov` — Project re-emit closes prior + opens new window but writes NO `wasGeneratedBy` edge (generated_by=None)
- [ ] `::test_emit_failure_degrades_gracefully` — a failing evolve does not raise into the host operation
- [ ] WP-011 characterisation tests still green where the observable contract is unchanged

### Green — Implementation makes tests pass

- [ ] The 3 emitters call `evolve_entity` at their persistence point
- [ ] Product + Opportunity wire `generated_by` from the producing LifecycleRun ref; Project passes `generated_by=None`
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

### Scope note — Project emit-path application is deferred to WP-015 (executor, WP-012)

WP-012 applied evolve to the **Product** and **Opportunity** emitters in full:
`emit_product_from_yaml` / `emit_opportunity_from_srd` now delegate to
`evolve_entity(generated_by=<LifecycleRun ref>)` (the conditional
`wasGeneratedBy` edge fires for these `prov:Entity` types), preserving
graceful degradation (best-effort emit).

The **Project** emit path was **not** swapped to `evolve_entity` in this WP, by
design. Today Project does not persist through the `EntityRepository` port — it
mints a `project-instances` bag atomically via
`_discovery/minter.write_project_entity` into `.sulis/projects/{slug}.jsonld`.
`evolve_entity(repo=...)` requires a file-backed `EntityRepository` (it reads
the current open window via the port and writes the history envelope through
`instance_path`); the Project mint has no such `repo`. Routing Project through
the port so evolve applies is the **ADR-006 home-reconciliation**, which is
explicitly owned by **WP-015** and gated by **WP-014**'s minter characterisation
test (neither built yet). Overreaching into that here would do WP-015's
minter/`.sulis`-mirror reconciliation without its characterisation gate — a
REORGANISE MUST violation.

What WP-012 *does* lock in for Project: the windows-only / **no-prov** contract
(`generated_by=None` → window moves, no `wasGeneratedBy` edge), pinned at the
`evolve_entity` seam in `tests/unit/test_emitters_evolve.py`
(`TestProjectEvolvesWithoutProv`) so the semantics Project inherits at WP-015 are
unambiguous. The Project characterisation baseline
(`tests/characterisation/test_living_entity_emit_baseline.py::TestProjectEmitBaseline`)
is left UNCHANGED — it still pins the current single-snapshot bag behaviour,
which WP-015 will then evolve under its own characterisation gate.
