---
id: DR-031
title: Mint "Change" (PD work-unit Activity, sibling of LifecycleRun) + the change-provenance edges (produced_by_change / evolved_by_change)
status: DRAFT-for-ratification
date: 2026-06-12
decider: iain
gate: mint-admission (dna-mint-an-entity walk; playbook refined 2026-06-02 / DR-026)
element_type: entity ×1 (+ field-extension ×2 edges)
element_id: dna:change
domain: product-development
trajectory: Phase 4a (mint ONE entity — Change) + Phase 4b (additive optional provenance edges on PD generated entities)
artifact: schemas/product-development/change.schema.json (to author) + PD shared-base edge fields
schema_change: PD generated-entity schemas — additive optional produced_by_change + evolved_by_change
grounded_against: sulis-brain 0.14.0
run_id: 01KTYMQ8N4PV5XHW3K2BZRFD7A
admission: dna-runner admission → overall_score 1.0 / admit
---

## What is proposed

The **second `prov:Activity` in product-development** (LifecycleRun is the first), plus the reverse provenance
edges that make a Change a first-class transaction over the brain graph.

1. **Mint `Change`** — the coarse-grained, founder-initiated unit of work (a `prov:Activity`) that creates or
   evolves a Product and the brain entities beneath it. The **SIBLING of LifecycleRun**: LifecycleRun is the
   fine-grained step-run; Change is the work-unit that a set of LifecycleRuns occur *within*. State
   `{in-flight | shipped | nuked}` = the transaction lifecycle (ship=commit, nuke=rollback per Task #67).
   Mirrors LifecycleRun's base-field shape.
2. **Add the change-provenance edges** — `produced_by_change → dna:change:<ulid>` (prov:wasGeneratedBy) and
   `evolved_by_change → [dna:change:<ulid>]` (prov:wasRevisionOf), on a SHARED PD base so every generated
   entity answers "which change made / revised me?". Reverse-query = the transaction set for ship / nuke.

This is the modelling that underpins Task #67 (change-as-transaction) / #127 / #128. It does NOT build the
ship/nuke emitters — that is #67's separate scope.

## Context — why now

A converged critical-thinking spiral (run `01KTXJ3XZG0VYMRRFYYRM14TGT`) concluded that change-provenance must
become a real graph edge so a change is a first-class transaction over the brain graph — not just a local
SQLite row (#30) + git history. Today the work-unit exists only as machine-local session state (worktree /
`session.json` / a change-store row) and as git commits. Nothing in the brain says "this set of entity
creations and revisions belong to ONE unit of work, and that unit shipped or was nuked." Minting `Change` +
the two edges closes that gap and gives the ship/nuke transaction (#67) a graph to operate over.

## The crux — what `Change` is, and why one entity (not three)

The sharpest framing risk (pressure-tested at Phase 1.5): is `Change` three things falsely unioned —
a work-unit, a transaction, and git provenance? **No — one entity.** A DDD *unit of work* IS a transaction
(one concept, not two). The git fields (`base_sha`, `branch`) are *substrate attributes* of the work-unit,
exactly as `LifecycleRun.inputs_ref` / `outputs_ref` are substrate pointers — not co-equal siblings. The
Phase 1.5 critical-thinking spiral (forced spiral path, run correlated to this mint's run_id per DR-013/DR-018)
converged with ZERO unresolved anti-patterns: AP-04 (premature-abstraction), AP-07 (scope-creep), AP-08
(false-MECE) all explicitly checked and cleared. `Change` = a work-unit Activity + its transaction-state +
its substrate-location. **One concept.**

## The L1-vs-L3 tension, and how the LifecycleRun-sibling precedent resolved it

There was a real classification tension worth recording: a "change" sounds like **runtime / ABox** (L3) — it is
an instance of work, it has a pid and a worktree, it lives in a local daemon. Why is it L1 (a canonical entity)
and not L3 (a runtime fact deferred to a slice)?

**The LifecycleRun precedent resolves it.** LifecycleRun is *also* an instance-of-work record (a step ran, once)
and is *also* L1 — because the brain models the SHAPE of a run-instance as a canonical entity, while the
individual run ROWS are the ABox/runtime population. The same split applies to Change: the **shape** of a
work-unit (id / handle / intent / primitive / state / for_product / parent_change / provenance) is canonical
(L1); the **individual live change rows** in the SQLite store (#30) are the runtime population (L3). The
machine-local session fields (worktree / pid / tty / session.json) are the part that IS genuinely L3-only —
and they are DELIBERATELY EXCLUDED from the canonical entity for exactly that reason. So the L1/L3 tension is
resolved by the same partition LifecycleRun already established: **canonical shape (L1) ⟂ runtime rows (L3) ⟂
machine-local session state (excluded).** This is why `Change` is the sibling of LifecycleRun, not a runtime
slice.

## Altitude (Phase 2.5) + entity-test (JT-1)

**Altitude:** one up = Product (`for_product`); one down = the entities a Change produces/evolves. Change sits
at the **Activity altitude**, the same family as LifecycleRun. The parent (Product) already exists → no
upstream mint needed (contrast the brand-identity walk, which had to mint Brand first). **mint-here.**

**JT-1 (≥2 triggers = entity): 6/6.** Collection ✅ (many Changes per Product); many-to-one ✅ (many Changes →
one Product; many LifecycleRuns → one Change); independent-lifecycle ✅ (in-flight→shipped|nuked); cross-reference
✅ (referenced by every generated entity + self-referenced via parent_change); standard-models-it ✅ (PROV
prov:Activity; DDD unit-of-work; git commit/revert); queryability ✅ ("what did change X produce/evolve?",
"which changes contributed to product Y?", "what is change X's ancestry?"). **Decisively an entity.**

**JT-2 manifest-cross-cutting: <3 fire → PD domain, NOT foundation.** Only PD uses change-provenance today
(insurance has no Change usage). Mirrors LifecycleRun's placement (LifecycleRun lives in product-development,
not foundation). Lift to foundation when ≥3 domains need it (rule-of-three).

## Alternatives considered

**A. Make `Change` a runtime/ABox slice (L3), not a canonical entity.** REJECTED — it is the same modelling
error as treating LifecycleRun as runtime-only. The brain models run-instance SHAPES as L1 entities; the rows
are the L3 population. The machine-local fields (worktree/pid/tty) ARE the genuinely-L3 part, and they are
excluded. The shape is canonical.

**B. Fold `Change` into `LifecycleRun` with a grain-discriminator field.** REJECTED — the field sets are
disjoint (Change: intent/primitive/state{in-flight,shipped,nuked}/parent_change/for_product; LifecycleRun:
step/outcome{completed,failed,…}). A discriminated union would force the union of two disjoint shapes and bloat
both — the AP-08 false-MECE error in reverse. Two siblings is cleaner: LifecycleRun (fine) ⊂ Change (coarse)
via prov:wasInformedBy.

**C. Put the provenance edges ON `Change` (Change → the entities it produced), not on the generated entity.**
REJECTED — PROV `wasGeneratedBy` points FROM the generated entity TO the activity. Putting an array of produced
refs on Change would (a) invert the PROV direction, (b) make Change an ever-growing list that must be mutated on
every entity creation, and (c) make the reverse-query ("which change made THIS entity?") a full scan. The edge
belongs on the generated entity; the reverse-query reconstructs the transaction set.

**D. Mint a separate `Primitive` entity for the 22-value change vocabulary.** REJECTED — the vocabulary is a
closed L2 controlled vocabulary (like a country-code list) with no independent lifecycle / cross-reference /
queryability. Minting it as an entity on n=1 is the AP-04 premature-abstraction defect. Carried as a closed
enum on `Change.primitive` (cf. `LifecycleRun.outcome`, `Brand.state` carrying a vocabulary). Central authoring
single-sources the enum from the canonical vocabulary file (the LOW-severity residual from Phase 1.5).

**E. Place the provenance edges per-entity (each generated entity declares its own) rather than on a shared
base.** REJECTED in favour of the shared base — "which change touched me?" is a universal provenance question,
the same kind as the shared bitemporal envelope; per-entity placement fragments the ship/nuke reverse-query and
risks naming drift. Shared base is consistent with the brain's existing `_inherited_fields` convention.

## The provenance-edge placement decision — shared base, MINOR-bump sweep

`produced_by_change` + `evolved_by_change` go on the **shared PD base** (every PD generated entity inherits
them, additive + optional). Per DR-008 this is a coordinated **MINOR-bump sweep** (additive optional → MINOR,
NOT major) — pre-existing instances remain valid without the fields, so **no migration contract is required**.
The Phase 5 spiral surfaced "MAJOR-bump cascade" as a residual; Phase 5.5 reclassified it: additive optional =
MINOR, the residual defangs to planned additive work. Foundation-lift deferred to rule-of-three (JT-2 <3 today).

## Phase 5.7 — Polysemy resolution

"Change" is highly polysemous. Resolutions (each scope-anchored into `Change.what_its_not`):

| Term in the wild | Meaning | Resolution |
|---|---|---|
| **`Change`** (chosen) | the founder-initiated coarse work-unit / transaction | **MINT as `dna:change`** (prov:Activity; DDD unit-of-work). Preferred. |
| `LifecycleRun` | one fine-grained step-run | **DIFFERENT** — occurs WITHIN a Change. "NOT a LifecycleRun." |
| git commit / changeset | one VCS ship-event / diff | **DIFFERENT** — a Change may span many commits; base_sha/branch are git PROVENANCE on the Change. "NOT a git commit." |
| ITIL "change request" / CR | a governance ticket | **DIFFERENT** — Change is the work-unit, not an approval ticket. |
| `Diff` / code delta | the code output | **GENERIC** — a Change PRODUCES deltas; it is not itself a delta. |
| PD `Workflow` / `Step` / `Decision` | process DEFINITIONS | **DIFFERENT** — they define HOW; Change is a run-side instance. "NOT a Workflow or Step." |
| `primitive` (Change field) | the 22-value vocabulary | **ENUM, not an entity** (alternative D). |
| `produced_by_change` / `evolved_by_change` | the reverse edges | preferred edge names; mirror PROV wasGeneratedBy / wasRevisionOf. No collision with existing PD fields. |

GLOSSARY gets preferred terms with "NOT the same as" cross-links: **Change / LifecycleRun / commit / primitive /
produced_by_change / evolved_by_change.**

## Consequences

- product-development gets its **second prov:Activity** — `Change` (coarse work-unit) joins `LifecycleRun`
  (fine step-run). The two-altitude Activity model is now explicit.
- **A change becomes a first-class transaction over the brain graph.** The reverse-query
  `produced_by_change`/`evolved_by_change` reconstructs exactly the entity set a ship (commit) or nuke
  (rollback) operates on — the substrate Task #67 needs.
- **Ancestry (#123/#124) becomes durable graph data** via `parent_change` + `relationship{builds_on,depends_on}`,
  not just session-local carry.
- The machine-local session state stays OUT of the brain (worktree/pid/tty/session.json) — the canonical shape
  is portable; the daemon/store (#30) keeps the ephemeral part. Clean JT-6.
- A coordinated **MINOR-bump sweep** adds the two edges across PD generated-entity schemas (no migration
  contract; pre-existing instances stay valid).
- Validates the playbook on a **self-referential modelling target** — the brain modelling the unit-of-work that
  evolves the brain itself. The admission gate scored it 1.0/admit after a legitimate escalate-remediation cycle.

## Cross-repo source-edit + compile + emitter follow-on plan (per #65)

1. **Source edit (sulis-brain repo):** add `Change` to `sources/product-development.entities.jsonld`; add
   `produced_by_change` + `evolved_by_change` to the PD shared base.
2. **Compile:** `dna-runner compile` → `schemas/product-development/change.schema.json` + the swept generated-entity schemas.
3. **Re-point (this repo):** vendor the recompiled schemas into `plugins/sulis/brain/compiled/product-development/`.
4. **Red-green fixtures + rubric:** per FIELD-SPEC §6; `dna-runner validate` / `evaluate` C1–C9 → PASS/WARN.
5. **Narrative-docs sweep (L31/L32/L38):** CONSUMER_HOWTO entity catalogue + README schema counts/foundation
   list + INDEX regenerated marker. Plugin description NOT touched for version (release-on-merge owns bumps, L33).
6. **Emitter follow-on (Task #67 — SEPARATE scope):** wire the ship/nuke emitters + the deposit→evolve mechanism
   that populate `state` + `produced_by_change`/`evolved_by_change` on real entity rows. This DR is the modelling
   prerequisite, not the emitter build.

## Open questions (for ratification — surfaced in the return, not asked one-at-a-time)

1. **`primitive` enum membership** — the 22 values are candidate-asserted (from the brief). Central authoring
   must single-source them from the canonical change-primitive vocabulary file; if that file differs, the enum
   follows the file. (LOW-severity residual from Phase 1.5.)
2. **`relationship` required-when-parent-present** — currently fully optional; should `relationship` be required
   whenever `parent_change` is non-null (a conditional `if parent_change then relationship`)? Modelled optional
   for now; founder call.
3. **`shipped_at` semantics on nuke** — does `shipped_at` get set when a change is NUKED (i.e. it means
   "terminal-at"), or stay null (reserved for ship only)? Modelled as the lifecycle-terminal timestamp (set on
   ship OR nuke); founder call on whether nuke needs its own `nuked_at`.
