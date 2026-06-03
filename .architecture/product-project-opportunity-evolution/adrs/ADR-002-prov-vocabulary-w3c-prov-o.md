---
id: ADR-002
title: PROV vocabulary added as W3C PROV-O Activity-generates-Entity (wasGeneratedBy / used); wasRevisionOf excluded
status: accepted
date: 2026-06-03
deciders: [iain]
---

## Context

Recon confirmed PROV is **absent entirely** from the grammar — no
`wasGeneratedBy`, no `used`, no `wasRevisionOf` in any schema or emission code.
The only PROV trace is the `prov:` `@context` prefix and informal underscore
fields on one hand-authored LifecycleRun instance. Adding PROV is greenfield.

The SPEC fixes the idiom (Constraint): **Activity-generates-Entity
(`wasGeneratedBy` / `used`)**, grounded in W3C PROV-O, and explicitly forbids
`wasRevisionOf`. CP-01 (default to the established convention) makes W3C PROV-O
the non-negotiable reference — it is the W3C Recommendation for provenance and
the brain already namespaces `prov:` to `http://www.w3.org/ns/prov#`.

The question with a real consequence: *how are `wasGeneratedBy` and `used`
modelled in a JSON-Schema-2020-12 + JSON-LD grammar whose schemas set
`unevaluatedProperties: false`?*

## Decision

**Add two PROV edges to the living-entity schemas, as optional ref-typed
fields, named exactly per W3C PROV-O.**

| Field | PROV-O term | Shape | On which entities |
|---|---|---|---|
| `was_generated_by` | `prov:wasGeneratedBy` | a single ref `^dna:lifecyclerun:<ulid>$` | every living entity version (Product, Opportunity, Project) |
| `used` | `prov:used` | an array of refs `^dna:<type>:<ulid>$` | the LifecycleRun (the Activity records what it consumed) |

JSON-LD term mapping is carried in each instance's `@context`
(`"was_generated_by": "prov:wasGeneratedBy"`, `"used": "prov:used"`) so the
JSON-LD compiles to correct RDF triples while the on-disk JSON key stays
snake_case and consistent with every other field. The `prov:` prefix is
already in the `@context` of the existing instance — we make it standard.

**Direction of the edges (PROV-O semantics, honoured):**

- The **Entity** points up at the Activity that generated it
  (`Entity wasGeneratedBy Activity`). So `was_generated_by` lives on
  Product/Opportunity/Project.
- The **Activity** points at the Entities it consumed (`Activity used Entity`).
  So `used` lives on LifecycleRun.

This is the canonical PROV-O reading and keeps each edge on the side PROV-O
puts it on — no inverted or invented direction.

**`wasRevisionOf` is excluded and stays excluded.** The lineage of "version N
came from version N-1" is carried by the **bitemporal window chain** (the prior
window's `valid_to` closes exactly as the new window's `valid_from` opens — see
ADR-003) plus, for event entities, their existing `supersedes` chain. PROV
answers *which activity*; bitemporal answers *as-of-when*; the two are
complementary (a SPEC constraint). Adding `wasRevisionOf` would introduce a
third, redundant lineage encoding and is forbidden by the SPEC.

### Schema mechanics under `unevaluatedProperties: false`

The living-entity schemas already permit `valid_from`/`valid_to`/`confidence`
without listing them in `required`. The two new fields are added the same way —
declared in `properties`, omitted from `required` — so they are accepted but not
mandatory. This is a **non-breaking, additive** schema change for Product /
Opportunity / Project (a minor schema bump each: e.g. product 1.0.0 → 1.1.0).
It is distinct from the LifecycleRun change, which is breaking for a *different*
reason (the `step_name`→`step` swap — ADR-004), not because of PROV.

## Options Considered

- **`wasRevisionOf` to chain versions (rejected — SPEC-forbidden + redundant).**
  Duplicates the bitemporal window chain. The SPEC is explicit: not in the
  grammar, must not be introduced.
- **A separate PROV side-file / triple store (rejected).** Splits an entity
  version from its provenance across two artifacts; breaks the single-file
  reject-on-invalid discipline the adapter depends on. Inline ref fields keep
  provenance co-located and schema-validated with the entity.
- **camelCase `wasGeneratedBy` as the JSON key (rejected).** Every other field
  in these schemas is snake_case. Use snake_case on the wire, map to the PROV-O
  IRI in `@context` — the JSON-LD layer is where the W3C term lives. Consistency
  beats literal-match of the spec word in the key.

## Consequences

- Product / Opportunity / Project schemas each gain `was_generated_by` (additive,
  minor bump).
- LifecycleRun schema gains `used` (additive — folded into the v2.1.0 bump that
  ADR-004 is already making for the breaking `step` change).
- The evolve helper (ADR-003) is the single writer of `was_generated_by`; the
  LifecycleRun emitter is the single writer of `used`. No other code writes PROV
  edges, keeping the grammar's first PROV writes disciplined.
- Drift-detector / validation: the new fields must be reflected in the vendored
  compiled schemas (the `plugins/sulis/brain/compiled/` copies are the contract
  the adapter validates against).
