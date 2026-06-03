---
id: ADR-002
title: PROV provenance edge reuses the EXISTING `prov_constraints` convention (wasGeneratedBy → lifecyclerun); applies to Product + Opportunity ONLY; Project + wasRevisionOf excluded
status: accepted
date: 2026-06-03
revised: 2026-06-03 — REWRITTEN against canonical. PROV is NOT greenfield: `prov:wasGeneratedBy` already exists in the PD `_predicate_map` and is already wired as a `prov_constraints` edge on five entities. The edge reuses that convention verbatim — NOT a new snake_case `was_generated_by` wire field. Project dropped (prov:Plan — type violation).
deciders: [iain]
---

## Context

An earlier draft of this ADR read "Recon confirmed PROV is **absent entirely**
from the grammar… Adding PROV is greenfield." **That premise was wrong**, and a
brain-governance review (the `wasGeneratedBy-provenance-edge` mint request,
2026-06-03) corrected it against the canonical source. The corrected facts:

- **`prov:wasGeneratedBy` is already in the PD `_predicate_map`**
  (`product-development.entities.jsonld:102`:
  `"wasGeneratedBy": "prov:wasGeneratedBy"`). It is not new vocabulary.
- **`prov:used` is also already in the map** (`:104`).
- **`wasGeneratedBy` is already wired as a `prov_constraints` block edge on five
  PD entities** — Component (`:221`, card `1..1`, `_step_name: "build"`),
  Release (`:257`, `release`), Metric (`:269`, `measurement`), TestResult
  (`:245`, → `testrun`), PostMortem (`:305`, → `incident`). The camelCase
  prov-key + typed `range` + explicit `card` shape is the **established
  convention in this exact artifact**.
- **The grammar already RESOLVES `prov:Activity` to `dna:entity:lifecyclerun`**
  (the `_prov_model` note, `:116`).

So provenance in this grammar has **one established mechanism**: a
`prov_constraints` block entry naming a camelCase PROV-O key, a typed `range`,
and a `card`. The question is not "how do we introduce PROV" — it is "how do we
add ONE MORE edge using the mechanism that already exists, on the right
entities".

The earlier draft's proposed `was_generated_by` snake_case scalar wire field
would have **forked provenance into a second, divergent mechanism** — a scalar
on the wire AND the `prov_constraints` edge everywhere else — which is exactly
the inconsistency CP-01 (default to the established convention) forbids.

## Decision

**Add a single optional `wasGeneratedBy → dna:entity:lifecyclerun` edge to the
`prov_constraints` blocks of Product and Opportunity, modelled identically to
the five existing producers — camelCase prov key, typed range, explicit `card`.
No new snake_case wire field. Project is excluded. `wasRevisionOf` stays
excluded.**

| Entity | Current `schema_version` | Proposed | The added edge | Cardinality |
|---|---|---|---|---|
| **Product** | 1.0.0 | **1.1.0** | `wasGeneratedBy → dna:entity:lifecyclerun` | `0..1` |
| **Opportunity** | 2.0.0 | **2.1.0** | `wasGeneratedBy → dna:entity:lifecyclerun` | `0..1` |
| **Project** | 1.0.0 | **no change** | none — see below | — |

The exact shape (reusing the convention verbatim):

```jsonc
// Product.prov_constraints — proposed 1.1.0
{ "is_a": "prov:Entity",
  "belongs_to_tenant": { "range": "dna:entity:tenant", "card": "1..1", "_predicate": "sulis:belongsToTenant" },
  "wasGeneratedBy": { "range": "dna:entity:lifecyclerun", "card": "0..1" } }

// Opportunity.prov_constraints — proposed 2.1.0
{ "is_a": "prov:Entity",
  "for_product": { "range": "dna:entity:product", "card": "1..1", "_predicate": "sulis:forProduct" },
  "wasGeneratedBy": { "range": "dna:entity:lifecyclerun", "card": "0..1" } }
```

The only deviation from the five existing producers is cardinality: they use
`1..1` (a Component is *always* built by exactly one run); these two
top-of-hierarchy entities use **`0..1`** — a Product or Opportunity may pre-date
the workflow engine or be hand-seeded, so the edge is optional. This matches the
mint request's resolved shape exactly.

`wasGeneratedBy` is already in the PD `_predicate_map`, so **no `_predicate_map`
edit is needed**. The edge compiles to `prov:wasGeneratedBy` via the existing
`prov:` prefix in `@context`, producing correct RDF triples, with zero new
vocabulary.

### Project is excluded — it is a `prov:Plan` (type violation)

**Project carries no `wasGeneratedBy` edge — not now, not at v0.7, not ever.**

- Project is `is_a: prov:Plan` (`foundation.entities.jsonld:251`). In PROV-O,
  `prov:wasGeneratedBy` is an **Entity → Activity** edge: "this *produced thing*
  came out of that activity." A `prov:Plan` is a *recipe*, not a produced
  thing — an Activity **uses** a Plan (via `prov:Association`); it never
  **generates** one. Putting `wasGeneratedBy` on a Plan is a PROV-O type
  violation, full stop.
- Product (`prov:Entity`, foundation:160) and Opportunity (`prov:Entity`,
  foundation:173) are both produced things — the edge is clean on both.
- Project loses nothing: its lineage is **already complete** via the bitemporal
  `valid_from`/`valid_to` window (inherited since v0.5.1), the `state` enum, and
  the `deprecated_for → project (0..1)` supersedes chain.
- The legitimate "which runs touched this Project?" question is answered by the
  separately-deferred **`LifecycleRun.for_project`** edge (L13 n=2, v0.7+), which
  lives **on the run**, pointing *at* the Project — never on Project. It requires
  no Project edit, now or later, and is out of scope here.

### Direction of the edges (PROV-O semantics, honoured)

- The **Entity** points up at the Activity that generated it
  (`Entity wasGeneratedBy Activity`). So `wasGeneratedBy` lives on
  Product / Opportunity.
- The **Activity** records what it consumed (`Activity used Entity`). `prov:used`
  is already in the `_predicate_map`; if/when the LifecycleRun records consumed
  inputs, it does so via the existing `used` predicate. **This change does not
  add a `used` field to the LifecycleRun** — DR-013 already settled the
  LifecycleRun's v2.1.0 field-set (the run carries `inputs_ref`/`outputs_ref` as
  content-addressed references, not inline `used` edge arrays), and the
  canonical v2.1.0 has no `used` field on the run record. Modelling consumed
  inputs as ABox `prov:used` triples is a separate concern that rides the
  existing predicate when it lands; it is **not** part of this change.

### `wasRevisionOf` is excluded and stays excluded

Confirmed absent from both the PD `_predicate_map` (`:99–114`) and the
foundation map. The "version N came from version N-1" lineage is carried by the
**bitemporal window chain** (the prior window's `valid_to` closes exactly as the
new window's `valid_from` opens — ADR-003) plus, for event entities, their
`supersedes` chain. PROV answers *which activity*; bitemporal answers
*as-of-when*; the two are complementary. Adding `wasRevisionOf` would introduce a
third, redundant lineage encoding and is forbidden.

### Where the edge is written at runtime

The brain's grammar change (adding the edge to the schema) is **upstream** —
routed through the mint request and a `/sulis-brain:mint-coach` walk that
compiles, runs the admission gate, writes the Decision Record, and re-vendors
the bumped Product/Opportunity schemas into
`plugins/sulis/brain/compiled/product-development/`. **The in-repo WP that wires
the emitter to write the edge cannot land until that upstream gate clears** (mint
accepted → recompiled → re-vendored). This is the upstream dependency the
decomposition flags explicitly.

Once the schema carries the edge, the evolve helper (ADR-003) is the single
writer of the `wasGeneratedBy` triple on the entity — it sets the edge to the
generating LifecycleRun's id when it opens a new window. No other code writes the
edge, keeping the grammar's provenance writes disciplined.

## Options Considered

- **Snake_case `was_generated_by` scalar wire field (rejected — forks the
  convention).** The earlier draft's proposal. It would create a second
  provenance mechanism (a scalar field on the wire) parallel to the
  `prov_constraints` edge that Component / Release / Metric / TestResult /
  PostMortem all use, diverging from the established pattern in the same
  artifact. CP-01: the established convention is `prov_constraints`; the bespoke
  scalar is the position requiring defence, and it is rejected.
- **Treat PROV as greenfield and invent the vocabulary (rejected — false
  premise).** PROV is not greenfield: `wasGeneratedBy`, `used`, and the
  `prov_constraints` mechanism already exist. Reuse, don't reinvent.
- **Apply the edge to Project too (rejected — PROV-O type violation).** Project
  is `prov:Plan`; `wasGeneratedBy` is an Entity→Activity edge. The obstacle is
  the semantics of the edge against the type, not a grammar limitation — no
  variant rescues it.
- **`wasRevisionOf` to chain versions (rejected — redundant + absent from map).**
  Duplicates the bitemporal window chain; not in the predicate map.
- **Add a `used` array to the LifecycleRun record (rejected — DR-013 settled
  the field-set).** Canonical v2.1.0 carries content-addressed
  `inputs_ref`/`outputs_ref`, not inline `used` arrays. ABox `prov:used` triples
  (via the existing predicate) are a separate, later concern.

## Consequences

- **Upstream (brain):** Product 1.0.0 → 1.1.0, Opportunity 2.0.0 → 2.1.0 — each
  a 1-file, zero-cascade, zero-migration MINOR additive edit (both PD-only; the
  `0..1` cardinality keeps pre-bump instances valid). Routed through the mint
  request + a mint walk; **not** authored in this repo.
- **In-repo (this change):** once the bumped Product/Opportunity schemas are
  re-vendored, the evolve helper (ADR-003) writes the `wasGeneratedBy` triple on
  the new window; the vendored compiled `product.schema.json` /
  `opportunity.schema.json` are updated to the bumped versions as part of the
  re-vendor. The WP that does this **`dependsOn` the upstream mint being
  accepted + re-vendored** — modelled as an external/upstream dependency.
- **Project:** no edit, no bump, no mirror cascade, no v0.7 watchlist item. Its
  `schema_version` stays 1.0.0.
- **No `_predicate_map` edit** (key already present). No new snake_case wire
  field anywhere.
- **The single writer** of the entity-side edge remains the evolve helper.
