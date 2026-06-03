---
id: WP-003
title: Update _lifecyclerun_emission compose to emit step + step_label and re-seed ID from step+timestamp
status: pending
kind: backend
primitive: substitute-strangle
group: SUBSTITUTE
change_id: CH-01KT61
sequence_id: WP-003
dependsOn: [WP-001, WP-002]
blocks: [WP-004, WP-005, WP-006]
estimated_token_cost:
  input: 3k
  output: 3k
tdd_section: Form #3; ADR-004 §Step-ref resolution
adrs: [ADR-001, ADR-004]
verification:
  adapter: backend
  artifact: tests/unit/test_lifecyclerun_emission_v2.py::test_compose_emits_step_ref
---

## Context

`compose_lifecyclerun(...)` in `plugins/sulis/scripts/_lifecyclerun_emission.py`
today takes `step_name` and seeds the instance ID from
`f"lcrun:{step_name}:{timestamp}:{by_actor}"`. Under v2.1.0 it takes a resolved
`step` ref (a Step ULID from WP-001) plus an optional `step_label`, and re-seeds
the ID from `step + timestamp` (TDD Form #3). This is the imperative half of the
breaking swap WP-002 made in the grammar — `substitute-strangle`, the call-site
side of the same removal.

# canonical-source: TDD.md §Canonical Identifiers — Schema versions

## Contract

### Files modified

```
plugins/sulis/scripts/_lifecyclerun_emission.py
```

### Function shape

```python
def compose_lifecyclerun(
    *,
    step: str,              # was step_name; now a resolved dna:step:<ulid> ref
    outcome: str,
    step_label: str = "",   # optional per-run specificity (the old step_name text)
    at: str | None = None,
    by_actor: str = "",
    used: list[str] | None = None,  # optional prov:used refs (ADR-002)
) -> dict:
    ...
    run = {
        "id": "dna:lifecyclerun:" + _ulid(f"lcrun:{step}:{timestamp}:{by_actor}"),
        "step": step,                 # required ref
        # step_label, used emitted only when provided (unevaluatedProperties:false clean)
        "at": timestamp,
        "outcome": outcome,
        "sys_status": "active",
    }
```

`step` must match `^dna:step:[0-9A-HJKMNP-TV-Z]{26}$` (reject otherwise). The
emitted dict validates against the v2.1.0 schema (WP-002).

## Definition of Done

### Red — Failing tests written

- [ ] `tests/unit/test_lifecyclerun_emission_v2.py::test_compose_emits_step_ref` — output has `step`, no `step_name`
- [ ] `tests/unit/test_lifecyclerun_emission_v2.py::test_compose_rejects_non_step_ref` — a non-`dna:step:` value raises
- [ ] `tests/unit/test_lifecyclerun_emission_v2.py::test_step_label_emitted_when_provided`
- [ ] `tests/unit/test_lifecyclerun_emission_v2.py::test_used_emitted_when_provided`
- [ ] `tests/unit/test_lifecyclerun_emission_v2.py::test_id_seeded_from_step_and_timestamp` — deterministic ID for fixed (step, timestamp)
- [ ] `tests/unit/test_lifecyclerun_emission_v2.py::test_output_validates_against_v2_schema` — emitted dict passes `lifecyclerun` 2.1.0

### Green — Implementation makes tests pass

- [ ] `compose_lifecyclerun` signature + body updated per Contract
- [ ] ID seed changed from `step_name` to `step`; `step_label`/`used` emitted only when present

### Blue — Refactor complete

- [ ] No `step_name` reference left in the module
- [ ] Ref-validation regex shared with the module's existing `_ACTOR_ID_RE` style (one idiom)
- [ ] Docstring updated to describe `step` / `step_label` / `used`

## Sequence

- **dependsOn:** WP-001 (the Step ULIDs the ref points at), WP-002 (the v2.1.0 schema the output validates against)
- **blocks:** WP-004 (helpers call this `compose`), WP-005 (CLI calls this `compose`), WP-006 (migration re-uses the composer to rebuild instances)

## Estimated Token Cost

- **Input:** ~3k (existing module + v2 schema + ADR-004)
- **Output:** ~3k (function rewrite + tests)
- **Total:** ~6k

## Notes

- `substitute-strangle` (call-site side): this is part of the same breaking swap
  as WP-002; the schema and composer must agree at the slice boundary (ADR-004
  "no commit leaves schema and emitters disagreeing").
