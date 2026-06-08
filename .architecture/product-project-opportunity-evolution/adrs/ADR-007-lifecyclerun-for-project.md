---
id: ADR-007
title: LifecycleRun.for_project — run→Project traceability; the run is the carrier (a plain ref, NOT a prov edge); a mint-gated v2.2.0 increment on top of the v2.1.0 spine
status: accepted
date: 2026-06-03
deciders: [iain]
supersedes: none
extends: ADR-001, ADR-006   # ADR-001 named for_project as the deferred run-side link; ADR-006 deferred run→Project to it. This ADR un-defers it (founder-directed) without reopening either decision.
---

## Context

The decision to add this edge is **made** (founder-directed, 2026-06-03). This
ADR records *how* it threads into the existing design, not *whether* to add it.

ADR-001 and ADR-006 both already named `LifecycleRun.for_project` — as the
**deferred** run-side link that answers "which runs touched this Project?"
without putting any edge on Project itself:

- ADR-001: *"the run→Project link is the separately-deferred
  `LifecycleRun.for_project` edge that lives on the run (L13 n=2, v0.7+), out of
  scope here."*
- ADR-006: *"the run→Project association is the deferred `LifecycleRun.for_project`
  edge on the run … requires no Project edit, now or later, and is out of scope
  for this change."*

This change un-defers it. The edge becomes in-scope: a new optional
`for_project: ref→project (0..1)` property on LifecycleRun, recording which
Project (release-unit / repo) a run operated in. With it, an app-started or
terminal-started change's emitted LifecycleRun links back to its Project, so the
run is traceable **up the full Tenant → Product → Opportunity → Project chain**.

Brain-confirmed facts that constrain the shape:

- **`sulis:forProject` and the `ref→project` shape already resolve.** They are
  **live on `Workflow.for_project`** (foundation v0.5.0 / Workflow v1.1.0, DR-017).
  The vendored `workflow.schema.json` carries `for_project` as a plain optional
  `properties` ref string with pattern `^dna:(project):[0-9A-HJKMNP-TV-Z]{26}$`
  (verified at `plugins/sulis/brain/compiled/foundation/workflow.schema.json:60`).
  The `LifecycleRun.for_project` edge reuses this exact precedent shape — a plain
  optional ref property, the same direction (an entity referencing a Project).
- **This is PD → foundation direction; it is NOT v0.7-gated.** LifecycleRun is a
  product-development entity; Project is foundation. The reference points from PD
  to foundation, which resolves today (the same direction
  `Opportunity.for_product`, `Workflow.for_project` already take). The ontology
  v0.7 NON-GOAL constrains only *unresolved cross-artifact resolution* of
  `belongs_to_product_ref`; a PD→foundation ref with a live predicate is not in
  that bucket.
- **It is a NEW upstream mint: LifecycleRun 2.1.0 → 2.2.0** (MINOR additive, both
  the PD canonical and its insurance mirror). The `wasGeneratedBy` mint
  (ADR-002 / WP-008) is a *different* mint on *different* schemas (Product +
  Opportunity); this is a third in-flight mint, on LifecycleRun. A `for_project`
  mint request is authored upstream in parallel. The in-repo re-vendor of v2.2.0
  + the emitter wiring DEPEND on that mint being accepted → recompiled →
  re-vendored — the **same gating shape** WP-008 has on the `wasGeneratedBy` mint.
- **The change-start emitter sets it.** The `_brain_emit_helper` change-started
  path (`emit_change_started_event`) and `sulis-emit-lifecyclerun` set
  `for_project` to the resolved Project ULID. **Optional, so it never breaks
  existing callers** — a run with no resolvable Project simply omits the field.

## Decision

**Add `LifecycleRun.for_project` as an optional plain ref property
(`ref→project`, card 0..1), upstream-minted as LifecycleRun v2.2.0 (MINOR
additive), re-vendored and emitter-wired as a SEPARATE, mint-gated increment ON
TOP OF the already-buildable v2.1.0 re-vendor spine. The run is the carrier
(consistent with ADR-006's "Project carries no edge"); the edge closes the
Tenant → Product → Opportunity → Project trace for app/terminal change-start.**

### 1. The run is the carrier (NOT Project) — consistent with ADR-006

`for_project` lives **on the LifecycleRun**, pointing *at* the Project. Project
itself carries no new edge — no schema edit, no bump. This is the same verdict
ADR-006 settled: Project's lineage is bitemporal + `state` + `deprecated_for`;
the run→Project association is recorded on the run. ADR-006 named this edge as
the deferred home for exactly this question; this ADR delivers it.

### 2. A plain ref, NOT a `prov_constraints` edge

`for_project` is a plain optional `properties` ref string — modelled exactly like
`Workflow.for_project`, NOT like `wasGeneratedBy`. The distinction:

| Edge | Mechanism | Why |
|---|---|---|
| `wasGeneratedBy` (ADR-002, WP-008) | `prov_constraints` PROV-O edge (Entity → Activity) | It is a provenance assertion: "this version came out of that run" |
| `for_project` (this ADR) | plain `properties` ref (`^dna:(project):…$`), `sulis:forProject` predicate | It is a scope assertion: "this run operated in that Project" — exactly `Workflow.for_project`'s shape |

`for_project` is **not** a PROV-O edge. It does not touch the `_predicate_map`'s
PROV vocabulary, does not assert generation, and carries no `prov:` semantics.
It reuses the live `sulis:forProject` predicate and the live `ref→project`
property shape. The vendored compiled schema gains one optional property in
`properties` (a ref string with the `dna:(project):…` pattern), mirroring
`workflow.schema.json` byte-for-shape.

### 3. NOT v0.7-gated (live Workflow.for_project precedent)

The reference is PD (LifecycleRun) → foundation (Project), with a predicate
(`sulis:forProject`) and a property shape (`ref→project`) that are **already in
the grammar and already compiled into a live vendored schema**
(`Workflow.for_project`). Nothing about this edge needs ontology v0.7. The v0.7
NON-GOAL (`belongs_to_product_ref` stays an unresolved string) is untouched —
that is a *different* ref, on a *different* entity, with no live predicate.

### 4. Optional (meta / pre-Project runs)

Card `0..1`. A LifecycleRun may have no resolvable Project — a meta-workflow run,
a run that pre-dates Project minting, the faithful-generation-harness run, a run
in a repo whose Project is not yet discovered. The emitter sets `for_project`
only when it can resolve a Project ULID; otherwise it omits the field
(`unevaluatedProperties:false` clean). This is the same optionality
`Workflow.for_project` carries for *"unscoped meta-workflows or … across multiple
Projects."* Pre-bump v2.1.0 instances stay valid under v2.2.0 (zero-migration
MINOR — no instance migration WP needed for this increment).

### 5. A separate, mint-gated increment — the v2.1.0 spine stays buildable-now

**This is the load-bearing threading decision.** WP-002 today re-vendors the
already-minted LifecycleRun **v2.1.0** + migrates the emitter (`step_name`→`step`)
in lockstep. That work needs NO mint and is buildable immediately (DR-009 + DR-013
already minted v2.1.0). **`for_project` does NOT change that.**

`for_project` threads as a SEPARATE increment:

- **WP-002 keeps v2.1.0 as its re-vendor target** — buildable now, not newly
  mint-gated. The step-ref emitter migration does not wait on the `for_project`
  mint.
- **A new WP (WP-016)** re-vendors **v2.2.0** (which supersedes WP-002's v2.1.0
  schema edit) and wires `for_project` into the change-start emit path. It
  `dependsOn` WP-002 (the v2.1.0 re-vendor + emitter core must exist first) AND
  starts `status: blocked` on the upstream `for_project` mint — **mirroring
  exactly how WP-008 is blocked on the `wasGeneratedBy` mint** (accepted →
  recompiled → re-vendored).

So the LifecycleRun schema has a **two-stage re-vendor**: v2.1.0 now (WP-002, the
step-ref spine, no mint needed), v2.2.0 as a mint-gated increment (WP-016, adds
`for_project`). The two stages are sequential on the same vendored file; v2.2.0 is
strictly additive over v2.1.0 (one optional property), so the supersession is a
clean drop-in.

### 6. Closes the Tenant → Product → Opportunity → Project trace

With `for_project` on the run, an app-started or terminal-started change's emitted
LifecycleRun is traceable up the full hierarchy:

```
Tenant
  └─ Product            (belongs_to_tenant)
       └─ Opportunity   (for_product)
            └─ Project   (belongs_to_product_ref — string ref, v0.7 resolves it later)
                 ▲
                 │ for_project  (THIS edge — the run records which Project it ran in)
            LifecycleRun (the prov:Activity / the change-start run)
```

The change-start run already records `step` (which Plan), `wasGeneratedBy` is
written on the *entities it generates*; `for_project` adds the *scope* axis —
which release-unit the run operated in. Together they answer "which run, running
what kind of work, in which Project, generated which entity version."

## Options Considered

- **Put the edge on Project, not the run (rejected — re-opens ADR-006).** Project
  is `prov:Plan`; ADR-006 settled that Project carries no run-side edge. The run
  is the carrier. Mirrors the existing `Workflow.for_project` ↔ Project shape.
- **Model `for_project` as a `prov_constraints` edge like `wasGeneratedBy`
  (rejected — wrong mechanism).** `for_project` is a scope ref, not a provenance
  generation assertion. The live `Workflow.for_project` is a plain `properties`
  ref; reuse that convention (CP-01, prior-art-in-repo). A `prov_constraints`
  encoding would invent a second representation for a shape the grammar already
  has.
- **Fold `for_project` into WP-002's v2.1.0 re-vendor (rejected — breaks
  buildable-now).** v2.1.0 is already-minted and buildable today; `for_project` is
  a NEW v2.2.0 mint not yet accepted. Folding it in would make the whole
  step-ref spine wait on the new mint — exactly the property the threading must
  preserve. Keep them separate: v2.1.0 now, v2.2.0 mint-gated.
- **Wait for ontology v0.7 (rejected — not gated).** The predicate
  (`sulis:forProject`) and the `ref→project` shape are live on
  `Workflow.for_project` today. PD→foundation references resolve now. v0.7 gates
  `belongs_to_product_ref` resolution only, a different ref.
- **Add an instance-migration WP for v2.2.0 (rejected — not needed).** v2.2.0 is a
  MINOR additive (one optional field). Pre-bump v2.1.0 instances validate
  unchanged under v2.2.0 (zero-migration). No instance-migration WP for this
  increment (contrast WP-006, which migrates the BREAKING v1→v2 swap).

## Consequences

- **One new mint** (upstream, in-flight, parallel to the `wasGeneratedBy` mint):
  LifecycleRun 2.1.0 → 2.2.0, +1 optional `for_project` ref property, both the PD
  canonical and the insurance mirror.
- **One new WP** (WP-016): re-vendor v2.2.0 + wire `for_project` at change-start.
  `dependsOn [WP-002, WP-013]` (v2.1.0 re-vendor first; serialise the
  `_brain_emit_helper.py` edit after WP-013's base_dir edit to that same file —
  P6 peer-collision); `status: blocked` on the `for_project` mint (mirror WP-008).
- **No Project schema edit** (consistent with ADR-006). No instance migration for
  v2.2.0 (zero-migration MINOR). No `_predicate_map` edit (`sulis:forProject`
  already present, used by `Workflow.for_project`). No `@context` map addition
  (the plain ref reuses the existing pattern shape).
- **WP-002 is unchanged** in its v2.1.0 re-vendor target and stays buildable-now.
  The two-stage re-vendor is recorded in ADR-004 (this change's edit to it).
- **The drift detector / vendored-schema parity** is updated for the v2.2.0
  compiled schema once WP-016's increment lands (the same parity machinery WP-007
  registers for the lifecycle-steps; the re-vendored v2.2.0 LifecycleRun is
  byte-faithful to the upstream-recompiled canonical + mirror).
- **WP count moves 13 → 14.** Critical path unchanged in length for the pre-gate
  spine; WP-016 is a leaf increment off WP-002/WP-013, gated on its own mint —
  it does not lengthen the wasGeneratedBy critical path.
