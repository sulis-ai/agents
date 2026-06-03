---
id: WP-008
title: Consume the upstream-minted `wasGeneratedBy` prov_constraints edge on Product + Opportunity (re-vendor bumped schemas); Project excluded
status: blocked
blocked_reason: UPSTREAM — gated on the mint-request `wasGeneratedBy-provenance-edge-2026-06-03` being accepted → a mint walk recompiling → the bumped Product 1.1.0 + Opportunity 2.1.0 schemas re-vendored into canonical compiled output. The in-repo re-vendor cannot land until that upstream artifact exists.
kind: contract
primitive: substitute-strangle
group: SUBSTITUTE
change_id: CH-01KT61
sequence_id: WP-008
dependsOn: [WP-002]
upstream_dependsOn:
  - "mint-request: .specifications/business-dna/mint-requests/wasgeneratedby-provenance-edge-2026-06-03.md (PROPOSAL → must be ACCEPTED + walked + recompiled + re-vendored)"
  - "outcome: Product schema_version 1.0.0 → 1.1.0, Opportunity 2.0.0 → 2.1.0, each +1 optional prov_constraints wasGeneratedBy edge (card 0..1) → dna:entity:lifecyclerun"
blocks: [WP-009]
removal_plan:
  deprecated_surface: "the vendored Product 1.0.0 / Opportunity 2.0.0 compiled schemas (no prov edge)"
  target: "replaced in this WP by the bumped 1.1.0 / 2.1.0 copies once the upstream mint re-vendors them; no transitional surface retained"
estimated_token_cost:
  input: 3k
  output: 2k
tdd_section: Form #2; Canonical Identifiers — Schema versions; ADR-002
adrs: [ADR-002]
verification:
  adapter: backend
  artifact: tests/unit/test_prov_edge_schemas.py::test_was_generated_by_edge_on_product_and_opportunity
---

## Context

The provenance edge (ADR-002), **rewritten against the brain-governance review.**
PROV is **NOT greenfield** — `prov:wasGeneratedBy` is already in the PD
`_predicate_map` and already wired as a `prov_constraints` edge on five PD
entities (Component, Release, Metric, TestResult, PostMortem). This WP adds the
**same edge, the same way**, to **Product and Opportunity only**:

| Entity | schema_version | Added edge |
|---|---|---|
| **Product** | 1.0.0 → **1.1.0** | `wasGeneratedBy → dna:entity:lifecyclerun`, card `0..1` |
| **Opportunity** | 2.0.0 → **2.1.0** | `wasGeneratedBy → dna:entity:lifecyclerun`, card `0..1` |
| **Project** | **no change** | none — `prov:Plan`, type violation (ADR-002, ADR-006) |

**Three corrections from the earlier draft (old WP-008):**

1. **`prov_constraints` convention, not a snake_case wire field.** The earlier
   draft added a `was_generated_by` snake_case scalar to `properties` + a
   `@context` term map. That **forks provenance into a second mechanism**. The
   edge is modelled exactly like the five existing producers: a `prov_constraints`
   block entry, camelCase `wasGeneratedBy` key, typed `range`, explicit `card`.
   `wasGeneratedBy` is already in the `_predicate_map` — **no `_predicate_map`
   edit, no `@context` field-map, no snake_case field.**
2. **Product + Opportunity ONLY — Project is dropped.** Project is `prov:Plan`;
   `wasGeneratedBy` is an Entity→Activity edge — a type violation on a Plan. Its
   lineage is complete via bitemporal + `state` + `deprecated_for`.
3. **This is an UPSTREAM-GATED re-vendor, not an in-repo author.** The grammar
   change is routed through the mint request + a `/sulis-brain:mint-coach` walk
   (compile → admission gate → DR → re-vendor). This WP **consumes** the result:
   it re-vendors the bumped Product 1.1.0 + Opportunity 2.1.0 compiled schemas
   into `plugins/sulis/brain/compiled/product-development/`. **It cannot land
   until the upstream mint is accepted + recompiled + re-vendored** (see
   `blocked_reason` + `upstream_dependsOn`).

This is the **data contract** the evolve helper (WP-009/WP-012) writes against:
`_entity_evolve` is the single writer of the `wasGeneratedBy` triple on the new
window — for Product/Opportunity only.

# canonical-source: TDD.md §Canonical Identifiers — Schema versions

## Contract

### Files modified (in-repo, once upstream clears)

```
plugins/sulis/brain/compiled/product-development/product.schema.json       # RE-VENDOR → 1.1.0 (carries the wasGeneratedBy prov_constraints edge)
plugins/sulis/brain/compiled/product-development/opportunity.schema.json   # RE-VENDOR → 2.1.0 (carries the wasGeneratedBy prov_constraints edge)
```

**NOT modified:** `project.schema.json` (Project excluded — no edit, no bump).
No `_predicate_map` file. No `@context` field-map addition. No snake_case
`was_generated_by` property.

### The edge (reusing the convention verbatim)

```jsonc
// Product.prov_constraints — 1.1.0
{ "is_a": "prov:Entity",
  "belongs_to_tenant": { "range": "dna:entity:tenant", "card": "1..1", "_predicate": "sulis:belongsToTenant" },
  "wasGeneratedBy": { "range": "dna:entity:lifecyclerun", "card": "0..1" } }

// Opportunity.prov_constraints — 2.1.0
{ "is_a": "prov:Entity",
  "for_product": { "range": "dna:entity:product", "card": "1..1", "_predicate": "sulis:forProduct" },
  "wasGeneratedBy": { "range": "dna:entity:lifecyclerun", "card": "0..1" } }
```

`0..1` (not the producers' `1..1`) because a Product/Opportunity may pre-date the
workflow engine or be hand-seeded — pre-bump instances stay valid (zero-migration
MINOR). **No `wasRevisionOf` anywhere** (ADR-002 — absent from the predicate map).

## Definition of Done

### Red — Failing tests written

- [ ] `tests/unit/test_prov_edge_schemas.py::test_was_generated_by_edge_on_product_and_opportunity` — both vendored compiled schemas admit a `wasGeneratedBy` ref to a `dna:lifecyclerun:<ulid>`, optional
- [ ] `::test_edge_is_prov_constraints_not_scalar` — the schemas carry NO snake_case `was_generated_by` property in `properties`; the edge is expressed via the `prov_constraints` mechanism (the compiled schema's prov-constraint encoding), matching Component/Release/Metric
- [ ] `::test_cardinality_is_optional` — `0..1` (pre-bump instances without the edge still validate)
- [ ] `::test_project_schema_unchanged` — `project.schema.json` has NO `wasGeneratedBy` edge and stays at schema_version 1.0.0
- [ ] `::test_minor_version_bumps` — Product `$id` at 1.1.0, Opportunity `$id` at 2.1.0
- [ ] `::test_no_wasrevisionof_anywhere`
- [ ] `::test_revendored_copies_match_upstream` — the vendored copies are byte-faithful to the upstream-recompiled Product 1.1.0 / Opportunity 2.1.0

### Green — Implementation makes tests pass

- [ ] Upstream mint accepted + walked + recompiled (the gate — verified before this WP starts)
- [ ] Bumped Product 1.1.0 + Opportunity 2.1.0 compiled schemas re-vendored into `plugins/sulis/brain/compiled/product-development/`
- [ ] Project schema untouched

### Blue — Refactor complete

- [ ] The edge shape is identical to the five existing producers (one convention, EP-03)
- [ ] No snake_case `was_generated_by` field, no `@context` map, no `_predicate_map` edit anywhere
- [ ] Re-vendored copies are byte-faithful to upstream (drift detector parity)

## Sequence

- **dependsOn:** WP-002 (the re-vendored LifecycleRun v2.1.0 — `wasGeneratedBy` points at a LifecycleRun, whose ref shape must exist in the vendored tree first)
- **upstream_dependsOn:** the mint-request acceptance + walk + recompile + re-vendor (see frontmatter). **This is the upstream gate** — the WP starts `blocked` and is unblocked only when the bumped canonical compiled schemas exist.
- **blocks:** WP-009 (the evolve helper writes the `wasGeneratedBy` triple, so the edge must exist in the grammar for Product/Opportunity)

## Estimated Token Cost

- **Input:** ~3k (the bumped upstream schemas + ADR-002)
- **Output:** ~2k (2 re-vendored compiled copies + tests) — smaller than the old WP-008 because there is no new grammar to author, only a re-vendor of two files (and Project is dropped)
- **Total:** ~5k

## Notes

- `substitute-strangle`: the vendored Product 1.0.0 / Opportunity 2.0.0 schemas
  (no prov edge) are replaced by their 1.1.0 / 2.1.0 successors. The `removal_plan`
  records the replaced surface; no transitional surface is retained.
- **The upstream gate is the load-bearing dependency of this whole change's
  provenance story.** If the mint is rejected or altered, this WP changes
  accordingly — it is a pure consumer of the upstream decision, never an authority
  on the grammar.
- The single writer of the runtime edge remains `_entity_evolve` (WP-009),
  conditional on the entity being a `prov:Entity` type (Product/Opportunity) —
  Project's evolve writes no edge (ADR-003, ADR-006).
