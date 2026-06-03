---
id: WP-002
title: Bump lifecyclerun schema 1.0.0 → 2.1.0 (step ref + step_label + used) and vendor compiled copy
status: pending
kind: contract
primitive: substitute-strangle
group: SUBSTITUTE
change_id: CH-01KT61
sequence_id: WP-002
dependsOn: []
blocks: [WP-003, WP-006, WP-007, WP-008]
removal_plan:
  deprecated_surface: "the `step_name` property and v1.0.0 validation path"
  target: "the v1 step_name field is removed in this bump; the deprecated `--step-name` CLI alias (WP-005) is removed in the next minor after downstream consumers migrate (tracked, not in this change)"
estimated_token_cost:
  input: 3k
  output: 3k
tdd_section: Form #3; Canonical Identifiers — Schema versions; ADR-004
adrs: [ADR-001, ADR-002, ADR-004]
verification:
  adapter: backend
  artifact: tests/unit/test_lifecyclerun_schema_v2.py::test_v2_requires_step_ref
---

## Context

The breaking grammar change at the spine of the migration (ADR-004): the
`lifecyclerun` schema swaps required `step_name` (free string) for required
`step` (a `^dna:step:<ulid>$` ref to a Step definition — ADR-001), adds the
additive `step_label` (free-text per-run specificity), and folds in the
additive `used` PROV edge (ADR-002, `prov:used` array). `$id` →
`https://sulis.co/dna/schema/lifecyclerun/2.1.0`.

This is `substitute-strangle`: a breaking field swap with a recorded
`removal_plan` (see frontmatter). The schema and its **vendored compiled copy**
at `plugins/sulis/brain/compiled/product-development/lifecyclerun.schema.json`
are the contract the adapter validates against (ADR-002 Consequences) — both
move together in this WP.

# canonical-source: TDD.md §Canonical Identifiers — Schema versions

## Contract

### Files modified

```
plugins/sulis/brain/<source schema>/lifecyclerun.schema.json          # source schema → 2.1.0
plugins/sulis/brain/compiled/product-development/lifecyclerun.schema.json  # vendored compiled copy
```

### Schema change (2.1.0)

| Field | v1.0.0 | v2.1.0 |
|---|---|---|
| `step_name` | required string | **removed** |
| `step` | — | **required** ref `^dna:step:[0-9A-HJKMNP-TV-Z]{26}$` (ADR-001) |
| `step_label` | — | optional string (the old per-run specificity; ADR-004) |
| `used` | — | optional array of refs `^dna:[a-z]+:[0-9A-HJKMNP-TV-Z]{26}$` (ADR-002 `prov:used`) |
| `@context` | `prov:` prefix present | `+ "used": "prov:used"` term map (ADR-002) |

`unevaluatedProperties: false` discipline preserved (`step_label` + `used`
declared in `properties`, `used` omitted from `required`).

## Definition of Done

### Red — Failing tests written

- [ ] `tests/unit/test_lifecyclerun_schema_v2.py::test_schema_id_is_2_1_0` — `$id` ends `/lifecyclerun/2.1.0`
- [ ] `tests/unit/test_lifecyclerun_schema_v2.py::test_v2_requires_step_ref` — a doc with `step` but no `step_name` validates; one with `step_name` and no `step` is rejected
- [ ] `tests/unit/test_lifecyclerun_schema_v2.py::test_step_ref_pattern` — `step` must match `^dna:step:<26 Crockford>$`
- [ ] `tests/unit/test_lifecyclerun_schema_v2.py::test_step_label_optional`
- [ ] `tests/unit/test_lifecyclerun_schema_v2.py::test_used_is_optional_ref_array`
- [ ] `tests/unit/test_lifecyclerun_schema_v2.py::test_context_maps_used_to_prov` — `@context.used == "prov:used"`
- [ ] `tests/unit/test_lifecyclerun_schema_v2.py::test_compiled_copy_matches_source` — vendored compiled == source (parity)

### Green — Implementation makes tests pass

- [ ] Source `lifecyclerun.schema.json` bumped to 2.1.0 per Contract
- [ ] Vendored compiled copy at `plugins/sulis/brain/compiled/product-development/lifecyclerun.schema.json` regenerated/updated to match

### Blue — Refactor complete

- [ ] No leftover `step_name` in `required` or `properties` (clean break, ADR-004)
- [ ] `used` ref pattern identical in shape to the other ref patterns in the schema (consistency)
- [ ] `@context` term ordering stable

## Sequence

- **dependsOn:** — (the schema can be authored before the Steps exist; the `step` *ref pattern* is generic, not a specific ULID). Pairs with WP-001 in wave 1.
- **blocks:** WP-003 (emitter targets this schema), WP-006 (migration re-validates against it), WP-007 (drift parity), WP-008 (PROV `used` rides this bump; `was_generated_by` needs the LifecycleRun ref shape this defines)

## Estimated Token Cost

- **Input:** ~3k (existing schema + ADR-002/004)
- **Output:** ~3k (schema diff + compiled copy)
- **Total:** ~6k

## Notes

- `substitute-strangle` not `expand`: a *breaking* required-field swap, not an
  additive change. The `removal_plan` records the deprecated-surface deletion.
- The vendored compiled copy moves in the **same** WP as the source — they are
  one contract; a split would risk the drift this change exists to prevent.
