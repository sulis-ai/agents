# ADR-001 — Roadmap is a sidecar label file, not an entity field

> Change: CH-01KT60 · Status: accepted · Pillar: Form
> Relates: FR-05 (Roadmap labelling), FR-07 (traverse lists Roadmap separately)

## Decision

Store the **Roadmap** flag in a per-repo sidecar file —
`.brain/labels/roadmap.jsonld` — keyed by entity id, **not** as a field on
the Opportunity or Requirement entity.

```jsonc
// .brain/labels/roadmap.jsonld
{
  "label": "roadmap",
  "members": [
    "dna:opportunity:01J...",
    "dna:requirement:01J..."
  ]
}
```

The capture path appends an id to `members` (idempotently — set semantics)
when the founder marks an idea Roadmap. The query seam reads this file to
compute the Roadmap view (ADR-006).

## Why (the constraint that forced it)

The SRD's grounding finding optimistically read the schemas as permitting an
extra label field (`additionalProperties` "not forbidden"). **Schema
inspection falsifies that.** All four backing-chain schemas set
`unevaluatedProperties: false`:

| Schema | `unevaluatedProperties` |
|---|---|
| `product-development/opportunity.schema.json` | `false` |
| `product-development/requirement.schema.json` | `false` |
| `product-development/product.schema.json` | `false` |
| `foundation/tenant.schema.json` | `false` |

An entity carrying a `roadmap: true` or `label: "roadmap"` property would
**fail validation** at the `LocalFileEntityAdapter.save()` boundary — the
adapter rejects on any unevaluated property (`_entity_adapter_local.py`
lines 83-100). The `_tenant_emission` module already documents this
("only emit when source-provided to keep `unevaluatedProperties:false`
clean", line 93-94). Roadmap-as-a-field is not an option; the validator's
tolerance question the SRD parked is answered: **strict, zero tolerance.**

## Alternatives considered

- **Reuse an existing entity field to encode Roadmap (rejected).** The
  closest candidates are `Opportunity.state` (`hypothesis|validated|
  defined|dropped`) and `Requirement.state` (`draft|approved|implemented|
  verified`). None has a "deferred/roadmap" member, and overloading
  `dropped` (which means "we decided NOT to pursue this") to mean
  "planned for later" inverts its meaning — a captured-but-set-aside idea
  is the opposite of dropped. Overloading would corrupt the state machine
  the opportunity-analyst (FR-11) relies on. Rejected: semantic collision.

- **Add a `label`/`tags` member to the schemas (rejected — out of scope
  and wrong layer).** The schemas are vendored compile outputs from the
  Brain↔OS contract (`brain/compiled/`, sourced from the `sulis-ai/plugins`
  repo's dna-runner). Editing a vendored schema forks it from its source of
  truth; the next re-vendor silently reverts the change. Schema evolution
  is a Brain-repo concern, not a marketplace-change concern. Rejected:
  wrong repo, creates drift.

- **A separate `RoadmapItem` entity (rejected — over-engineered).** Minting
  a new entity type to model a boolean flag is disproportionate, requires a
  new schema + emitter + validator, and re-introduces the same vendored-
  schema problem. Rejected: a label is not an entity.

- **Convention-by-naming (rejected — not queryable).** Encoding Roadmap in
  the entity id or filename can't be toggled without rewriting the entity
  and breaks deterministic-ULID idempotence (NFR-04). Rejected.

## Consequences

- The sidecar is the **boring, established convention** for cross-cutting
  tags that don't belong in the tagged record — the same shape Git uses for
  refs, the same shape a label index uses. It travels with the repo (FR-06),
  it's diff-friendly (sorted members), and it's independent of the strict
  entity schemas.
- The query seam gains a `roadmap-view` mode that reads the sidecar and
  resolves member ids against the entity store (ADR-006).
- **Best-effort symmetry (NFR-01):** if the sidecar is missing or malformed,
  the Roadmap view returns empty, never errors — same degradation contract
  as the entity store.
- **Idempotence (NFR-04):** membership is a set; re-marking the same id is a
  no-op. Matches the deterministic-emission discipline.
- The sidecar is marketplace-local convention. If the Brain contract later
  grows first-class labels, this migrates to that — the query seam is the
  single read point, so the migration touches one module.
