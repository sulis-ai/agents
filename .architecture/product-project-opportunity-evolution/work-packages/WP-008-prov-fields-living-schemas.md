---
id: WP-008
title: Add was_generated_by to Product/Opportunity/Project schemas and @context PROV term maps; vendor compiled copies
status: pending
kind: contract
primitive: create
group: GENERATE
change_id: CH-01KT61
sequence_id: WP-008
dependsOn: [WP-002]
blocks: [WP-009]
estimated_token_cost:
  input: 3k
  output: 3k
tdd_section: Form #2; Canonical Identifiers — Schema versions; ADR-002
adrs: [ADR-002]
verification:
  adapter: backend
  artifact: tests/unit/test_prov_grammar_schemas.py::test_was_generated_by_on_living_schemas
---

## Context

The PROV grammar layer (ADR-002): add the optional `was_generated_by` ref
(`prov:wasGeneratedBy`, single `^dna:lifecyclerun:<ulid>$`) to the three living
entity schemas — Product 1.0.0→1.1.0, Opportunity 1.0.0→1.1.0, Project (foundation)
1.0.0→1.1.0 — and add the `@context` term map (`"was_generated_by":
"prov:wasGeneratedBy"`) to each. The complementary `used` edge on LifecycleRun
shipped in WP-002 (the v2.1.0 bump). Additive, non-breaking (declared in
`properties`, omitted from `required`, `unevaluatedProperties:false` preserved).

This is the **data contract** the evolve helper (WP-009/WP-012) writes against:
`_entity_evolve` is the single writer of `was_generated_by`. The vendored
compiled copies are the contract the adapter validates against (ADR-002
Consequences) — they move in this WP.

# canonical-source: TDD.md §Canonical Identifiers — Schema versions

## Contract

### Files modified

```
plugins/sulis/brain/<source>/product.schema.json            → 1.1.0
plugins/sulis/brain/<source>/opportunity.schema.json        → 1.1.0
plugins/sulis/brain/<source>/project.schema.json            → 1.1.0  (foundation)
plugins/sulis/brain/compiled/product-development/product.schema.json       # vendored
plugins/sulis/brain/compiled/product-development/opportunity.schema.json   # vendored
plugins/sulis/brain/compiled/foundation/project.schema.json                # vendored
```

### Field added (each of the 3)

| Field | PROV-O | Shape |
|---|---|---|
| `was_generated_by` | `prov:wasGeneratedBy` | optional single ref `^dna:lifecyclerun:[0-9A-HJKMNP-TV-Z]{26}$` |

`@context` gains `"was_generated_by": "prov:wasGeneratedBy"`. **No `wasRevisionOf`
anywhere** (ADR-002 — SPEC-forbidden). Snake_case on the wire, PROV-O IRI in
`@context` (ADR-002 rejected camelCase key).

## Definition of Done

### Red — Failing tests written

- [ ] `tests/unit/test_prov_grammar_schemas.py::test_was_generated_by_on_living_schemas` — all 3 declare the field, optional
- [ ] `tests/unit/test_prov_grammar_schemas.py::test_was_generated_by_pattern` — must match `^dna:lifecyclerun:<26 Crockford>$`
- [ ] `tests/unit/test_prov_grammar_schemas.py::test_context_maps_was_generated_by_to_prov` — each `@context.was_generated_by == "prov:wasGeneratedBy"`
- [ ] `tests/unit/test_prov_grammar_schemas.py::test_no_wasrevisionof_anywhere` — grep the 3 schemas: zero `wasRevisionOf`
- [ ] `tests/unit/test_prov_grammar_schemas.py::test_minor_version_bumps` — each `$id` at 1.1.0
- [ ] `tests/unit/test_prov_grammar_schemas.py::test_compiled_copies_match_source` — vendored == source for all 3

### Green — Implementation makes tests pass

- [ ] `was_generated_by` + `@context` map added to product / opportunity / project source schemas at 1.1.0
- [ ] 3 vendored compiled copies regenerated to match

### Blue — Refactor complete

- [ ] `was_generated_by` ref pattern identical across the 3 schemas (one shape)
- [ ] Additive only — no field moved into `required`; `unevaluatedProperties:false` intact
- [ ] `@context` term ordering stable across the 3

## Sequence

- **dependsOn:** WP-002 (`was_generated_by` points at a LifecycleRun whose v2.1.0 ref shape must exist; `used` already shipped in WP-002)
- **blocks:** WP-009 (the evolve helper writes `was_generated_by`, so the field must exist)

## Estimated Token Cost

- **Input:** ~3k (3 existing schemas + ADR-002)
- **Output:** ~3k (3 schema diffs + 3 compiled copies)
- **Total:** ~6k

## Notes

- Three schemas, one atomic field+context addition with identical shape — one
  mutually-consistent PROV-grammar contract, not three separable concepts.
- Vendored compiled copies move with source — same contract; a split risks drift.
