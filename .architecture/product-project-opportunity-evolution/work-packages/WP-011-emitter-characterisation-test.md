---
id: WP-011
title: Characterisation test pinning current Product/Opportunity/Project emit behaviour before evolve refactor
status: pending
kind: backend
primitive: test
group: REINFORCE
change_id: CH-01KT61
sequence_id: WP-011
dependsOn: [WP-009]
blocks: [WP-012]
characterisation_test: tests/characterisation/test_living_entity_emit_baseline.py
estimated_token_cost:
  input: 3k
  output: 3k
tdd_section: Form §Change-primitive classification (4 apply-evolve — characterisation first); Proof
adrs: [ADR-003]
verification:
  adapter: backend
  artifact: tests/characterisation/test_living_entity_emit_baseline.py::test_current_save_behaviour_pinned
---

## Context

ADR-003's apply-evolve is a **REORGANISE-Refactor** of the existing Product /
Opportunity / Project emitters (they move from a plain `repo.save(...)` to
`evolve_entity(...)`). Per the CLAUDE.md non-negotiable (EP-07) and the
change-primitive MUST (Characterisation Tests Before Refactor), the **baseline
behaviour is pinned first**, in this WP, before WP-012 touches the emitters.

This WP writes the characterisation test that captures *what the emitters do
today*: the entity dict they compose, the file they write, the validation they
pass. WP-012's refactor must keep this green (where the observable contract is
unchanged) and extend it (where evolve adds windows).

## Contract

### Files created

```
plugins/sulis/scripts/tests/characterisation/test_living_entity_emit_baseline.py
```

Captures, for each of the three living-entity emit paths, the current observable
output (composed dict shape, write location, schema it validates against) against
a real temp-dir file adapter (no mock, MEA-09). No production code is modified in
this WP.

## Definition of Done

### Red — Failing tests written

- [ ] `tests/characterisation/test_living_entity_emit_baseline.py::test_current_save_behaviour_pinned` — Product emit composes + writes the current shape (written against the live emitter, captures golden output)
- [ ] `::test_opportunity_emit_baseline`
- [ ] `::test_project_emit_baseline`

(These pass against the *current* code — a characterisation test confirms
present behaviour, then guards the refactor. They are "Red" only in the sense of
being written-first; they go green against unchanged code, which is the
EP-07 confirm-passes step.)

### Green — Implementation makes tests pass

- [ ] The three baseline tests pass against the **unchanged** emitters (confirms the pin is faithful)

### Blue — Refactor complete

- [ ] Golden outputs are minimal (load-bearing fields only — not brittle on incidental fields)
- [ ] Tests exercise the real file adapter against a temp dir (no mock)
- [ ] Each test documents which observable contract it pins (so WP-012 knows what must survive)

## Sequence

- **dependsOn:** WP-009 (the evolve helper must exist so the test can reference the target behaviour it will guard, and so the test file lives alongside the evolve contract)
- **blocks:** WP-012 (the refactor cannot start until the baseline is pinned — EP-07 MUST)

## Estimated Token Cost

- **Input:** ~3k (the 3 existing emitters)
- **Output:** ~3k (3 characterisation tests)
- **Total:** ~6k

## Notes

- This is the REINFORCE-Test WP the design flagged as required-first for the
  apply-evolve refactor. Splitting it from WP-012 is deliberate: the test must
  exist and pass against unchanged code before any emitter is touched.
