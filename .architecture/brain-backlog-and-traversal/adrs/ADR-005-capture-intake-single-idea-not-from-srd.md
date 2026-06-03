# ADR-005 — Capture emits from a single-idea intake, generalising the emitters beyond `--from-srd`

> Change: CH-01KT60 · Status: accepted · Pillar: Form
> Relates: FR-01 (lightweight capture), FR-03 (requirement from opportunity), FR-04 (wire orphaned emitters), NFR-04 (idempotent)

## Decision

Add a **single-idea** compose path alongside the existing `--from-srd` /
`--from-yaml` paths in the opportunity and requirement emission modules, and
wire it from the capture orchestrator. Concretely:

- `_opportunity_emission`: add `compose_opportunity_from_idea(*, job_statement,
  for_product, seed, state="hypothesis", evidence=None, impact=None)`
  returning the same Opportunity dict shape the SRD path produces.
- `_requirement_emission`: add `compose_requirement_from_idea(*, statement,
  source, seed, priority="must", acceptance_criteria=None)` returning the same
  Requirement dict shape.
- Both derive the entity ULID deterministically from a **stable seed**
  (`_deterministic_ulid_from(f"opportunity-from-idea:{seed}")` /
  `requirement-from-idea:{seed}`), reusing the existing Crockford-base32
  helper unchanged.

The from-SRD paths are untouched. The single-idea path is a sibling, not a
replacement.

## Why

All current emitters are document-shaped: `emit_*_from_srd` parses an SRD's
`## Summary` / `**FR-NN**` markers; `emit_product_from_yaml` parses a config
file. Capture has **no document** — it has a why-string and a what-string
typed in conversation (FR-01). The SRD parsers would have nothing to parse.

The boring, convention-respecting move is to **factor the persistence and
ID-derivation discipline (already proven in the from-SRD path) and feed it a
different front end** — not to fabricate a throwaway SRD file to satisfy the
existing parser. The compose/emit split the modules already use
(`compose_*` pure transform → `emit_*` persists) is exactly the seam for
this: add a second `compose_*` producing the same dict, route it through the
same `repo.save(...)`.

This also closes the synthetic-placeholder loop the from-SRD requirement
path documents (`_requirement_emission` lines 16-28): that path emits a
*synthetic* Opportunity ref because Opportunity emission "doesn't exist yet."
It exists now, and capture wires it — the single-idea Requirement's `source`
is a **real** Opportunity id the orchestrator just emitted, never synthetic.

## Alternatives considered

- **Write a temp SRD and feed `--from-srd` (rejected).** Round-tripping a
  conversation through a fake markdown document is the opposite of boring —
  it's a Rube Goldberg machine. It also can't carry the real Opportunity ref
  (the from-SRD path mints a synthetic one). Rejected: indirection for its
  own sake.

- **A wholly new emitter module for capture (rejected — duplication).** The
  ID derivation, the dict shape, the `repo.save` discipline, the
  graceful-degradation contract all already exist. A new module re-derives
  them and they drift. Rejected: violates check-before-building-new (EP-03);
  extract/extend the existing module instead.

- **Capture builds the entity dicts inline and calls `repo.save` directly
  (rejected — leaks the schema shape).** The compose functions are where the
  default-field discipline lives (`priority=must`, `state=draft`,
  `acceptance_criteria=["see ..."]`). Inlining duplicates it. Rejected: the
  compose function is the right home for shape + defaults.

## Consequences

- The orphaned `sulis-emit-opportunity` and `sulis-emit-product` CLIs are now
  reachable via the orchestrator (FR-04). The CLIs themselves keep their
  `--from-srd` / `--from-yaml` flags; the orchestrator calls the underlying
  `compose_*_from_idea` + `repo.save` directly (it doesn't shell out to the
  CLI — it imports the module, same as `_brain_emit_helper` does).
- **Seed strategy (NFR-04):** the orchestrator derives a stable seed from the
  idea — for the dogfood and tests, an explicit `--seed`; in conversation, a
  slug of the what (or why, if no what). Same seed ⇒ same ULIDs ⇒
  re-capturing overwrites in place, no duplicate. This matches the existing
  emit convention exactly.
- The `compose_*_from_idea` functions are **pure** (no I/O) — directly
  unit-testable without a store, mirroring the existing `compose_*` tests.
- `evidence`/`impact`/`confidence` on the Opportunity stay optional and
  unset on the quick path; the analyst (ADR-004) populates them on the full
  path. Optional-field discipline keeps `unevaluatedProperties:false` clean.
