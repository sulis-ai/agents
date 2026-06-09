---
title: ADR vs BDR is a kind discriminator on the existing decision entity
status: accepted
kind: adr
---

# ADR-006 — ADR vs BDR is a `kind` discriminator on the existing `decision` entity

## Context

FR-17 requires the methodology to support Business Decision Records (BDR)
alongside ADRs: a business/product decision (scope cut, sequencing, pricing) is
recorded distinct from a technical ADR; both are decision records, differing in
subject (GLOSSARY "NOT the Same As"). Today the `decision` brain schema
(`plugins/sulis/brain/compiled/product-development/decision.schema.json`) has
properties `sys_status / valid_from / valid_to / confidence / id / title /
state / context / decision / options_considered / consequences / supersedes` —
**no `kind`/`category` field**. `sulis-emit-decision --from-adr` exists and
parses Context/Decision/Options/Consequences. There is no way to tell an ADR
from a BDR in the brain.

## Decision

Add a `kind ∈ {adr, bdr}` discriminator to the `decision` entity (additive,
optional, default `adr` so every existing decision reads as an ADR — no
backfill required). Extend `sulis-emit-decision` to accept the kind (a
`--from-bdr` flag or a `--kind` argument, and/or inference from the source
directory `adrs/` vs `bdrs/`). The two record types share one entity and one
emitter — they differ only in the `kind` field and the directory they live in.
This keeps the brain's decision spine single-typed (one schema, one query
surface) while making the ADR/BDR distinction first-class and queryable.

## Options Considered

- **A `kind` field on the existing `decision` entity (CHOSEN).** Minimal,
  additive, default-compatible; one schema; one emitter; one query surface;
  the cockpit golden-thread view reads both with a `kind` facet.
- **A separate `business_decision` entity type** — rejected: duplicates the
  whole decision schema + emitter + query path for a one-field difference;
  doubles maintenance; splits the decision graph.
- **A naming convention only (ADR-* vs BDR-* filenames, no schema change)** —
  rejected: not queryable in the brain (NFR-D01 spirit — truth in the store,
  not the filename); the cockpit can't facet on a filename prefix.

## Consequences

- **Positive:** the ADR/BDR distinction is first-class and queryable;
  repudiation of a business decision (STRIDE-R) is mitigated (FR-17); existing
  decisions need no migration (default `adr`).
- **Negative:** a vendored compiled-schema change + emitter change (Phase 3);
  the schema is vendored, so the compile output must be regenerated.
- **Neutral:** the `.md` ↔ entity duality is unchanged; BDRs live in `bdrs/`
  and ADRs in `adrs/`, both emitting `decision` entities with the right `kind`.
