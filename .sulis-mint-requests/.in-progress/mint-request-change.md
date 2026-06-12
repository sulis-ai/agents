# Mint request — `Change` (PD work-unit Activity) + the change-provenance edges

**Submitted:** 2026-06-12
**Run:** dna-mint-an-entity 01KTYMQ8N4PV5XHW3K2BZRFD7A
**Requesting context:** a converged critical-thinking spiral (run 01KTXJ3XZG0VYMRRFYYRM14TGT) concluded change-provenance must become a real edge so a change is a first-class transaction over the brain graph. This mint is the modelling that underpins Task #67 (change-as-transaction) / #127 / #128.
**Grounded against:** sulis-brain 0.14.0 (highest vendored). Canonical source ontology is CROSS-REPO in the sulis-brain plugin; this repo carries only `plugins/sulis/brain/compiled/`. Follows the Scenario-mint cross-repo pattern (#65): source-ontology edit + recompile + re-point + DR.
**Companion DR:** DR-031 (draft).
**Trajectory:** Phase 4a (mint ONE new entity — `Change`) + Phase 4b (field-extension — two additive optional provenance edges on the existing PD generated entities).

---

## Candidates (slice 1)

1. **`Change`** — the coarse-grained, founder-initiated unit of work — a **prov:Activity** — that creates or evolves a Product and the brain entities beneath it. The **SIBLING of LifecycleRun**: LifecycleRun is the fine-grained step-run Activity; Change is the work-unit Activity that a set of LifecycleRuns occur *within*. The transaction boundary over the brain graph (ship = commit, nuke = rollback per #67). Mirrors LifecycleRun's base-field shape.

2. **The change-provenance edges** — a PROV-O `wasGeneratedBy`-aligned pair living on the GENERATED entity, pointing back to the Change that made it:
   - `produced_by_change → dna:change:<ulid>` (the Change that created the entity) — prov:wasGeneratedBy.
   - `evolved_by_change → [dna:change:<ulid>]` (the Changes that revised it) — prov:wasRevisionOf-flavoured.
   Reverse-query "what did change X produce/evolve?" = the transaction set for ship=commit / nuke=rollback.

## One-paragraph use case

A founder starts a piece of work (a `Change`): a bug fix, a feature, a refactor. The work creates or evolves a Product and the brain entities beneath it (Opportunity / Requirement / Design / Decision / Scenario / LifecycleRun). Today that work-unit lives only as local machine session state (a worktree, a `session.json`, a SQLite row in the change store) and as git history — there is no first-class brain entity that says "this set of entity creations and revisions belong to ONE unit of work, and that unit shipped (committed) or was nuked (rolled back)." We want `Change` as a graph entity — the coarse-grained sibling of LifecycleRun — so the ship/nuke transaction can be expressed against the brain graph, ancestry (#123/#124) is durable, and every generated entity can answer "which change made me, and which changes revised me?" via the two provenance edges. The machine-local session state (worktree_path / pid / tty / session.json contents) is DELIBERATELY EXCLUDED — it is not shared brain truth.

## Classification (Phase 0.5 — PRE-COMPLETED this session)

- layer-verdict: **L1** for both. `Change` is a canonical entity (prov:Activity). The provenance edges are fields ON a canonical (generated) entity, not a standalone entity.
- routing-decision: proceed-to-mint.

## Phase checklist (autonomous walk — full trace in `.runs/01KTYMQ8N4PV5XHW3K2BZRFD7A.md`)

- **P1 convention scan:** W3C PROV-O (prov:Activity / wasGeneratedBy / wasInformedBy); ULID; Conventional Commits + git (base_sha/branch; ship≈commit, nuke≈revert); DDD unit-of-work/transaction; foundation bitemporal envelope. **All ADOPTED.** Lone brain-local call defended: `primitive` as a closed 22-value enum (NOT a separate entity). Verdict: aligned-with-deviation.
- **P1.5 critical-thinking (framing):** spiral-converged, zero unresolved anti-patterns → candidate-confidence-verdict **STRONG**. False-MECE / premature-abstraction / scope-creep all checked and cleared.
- **P2 discovery probes P0..P11:** audit/provenance (P8) + lifecycle (P9) + graph (P10) central; payments/sanctions/regulatory N/A; P11 confirmed exclusions (worktree/pid/tty/session.json).
- **P2.5 altitude:** mint-here. Parent (Product) already exists → no upstream mint (unlike brand-identity). Activity altitude, sibling of LifecycleRun.
- **P3 pyramid:** domain product-development; sibling LifecycleRun; upstream Product; downstream-produced Opportunity/Requirement/Design/Decision/Scenario/LifecycleRun.
- **P4 qualitative (JT):** JT-1 **6/6**; JT-2 **<3 → PD domain (not foundation)**, mirrors LifecycleRun placement; JT-3 no asymmetric pair; JT-5 polysemy resolvable; JT-6 clean (records THAT work happened); JT-7 ancestry is a DAG. Absolute checks pass (production domain / encodable / not a duplicate). Verdict **admit-draft**.
- **P4.5 numeric (dna-runner admission):** first run 0.0/reject (artifact-envelope omission) → **admission-score-escalate FailureMode → remediate envelope (_inherited_fields / _predicate_map / _brain_OS_contract / prov_constraints.is_a / source_of_truth) → re-run 1.0/admit (exit 0)**.
- **P5 critical-thinking (conclusion):** spiral-converged. One low-severity residual (shared-base edge placement → schema sweep) routed to P5.5, not a defeater. No cycle-back.
- **P5.5 referential-integrity:** all outbound refs resolve (for_product→Product, by_actor→Actor, parent_change→Change self-edge). The "MAJOR-bump cascade" reclassified: additive optional edges = DR-008 MINOR bumps, no migration contract. violations = []; remediation planned.
- **P5.7 disambiguation:** Change scope-anchored vs LifecycleRun / git-commit / change-request / Workflow+Step / Diff / primitive-enum. Vocabulary LOCKED.
- **P6 generate-then-verify:** this request + `change-FIELD-SPEC.md` + `DR-031-mint-change-DRAFT.md`; rubric C1-C9.

## Relations (the graph edges this mint introduces)

- `Change.for_product → Product` (the product this change contributes to).
- `Change.parent_change → Change` (self-edge; #123 durable carry, #124 ancestry, qualified by `relationship{builds_on|depends_on}`).
- `Change.by_actor → Actor` (the founder/agent who ran it).
- `Change` ⟂ `LifecycleRun` (sibling Activities; LifecycleRuns occur within a Change via prov:wasInformedBy).
- **On every PD generated entity** (Opportunity / Requirement / Design / Decision / Scenario / LifecycleRun): `produced_by_change → Change` (prov:wasGeneratedBy) + `evolved_by_change → [Change]` (prov:wasRevisionOf). Placement: a SHARED PD base-field pair (recommended — see DR §placement).

## Schema work for central authoring (cross-repo)

- **NEW:** add `Change` to `sources/product-development.entities.jsonld` → compile `schemas/product-development/change.schema.json`.
- **EDIT (additive, optional, MINOR):** add `produced_by_change` + `evolved_by_change` to the PD shared base (every PD generated entity schema).
- **RE-POINT:** recompile + vendor into `plugins/sulis/brain/compiled/product-development/` (this repo carries compiled only).
- **NEW (later):** GLOSSARY entries — Change / LifecycleRun / commit / primitive / produced_by_change / evolved_by_change with "NOT the same as" cross-links.

## Deliberately EXCLUDED (recorded — machine-local session state, not shared brain truth)

`worktree_path`, `pid`, `tty`, `session.json` contents. These live in the local session daemon / change store (#30), NOT in the canonical entity. Confirmed in the FIELD-SPEC §exclusions.

## Reserved / deferred (recorded so they're additive later)

- Foundation-lift of the provenance edges — deferred until a 2nd domain needs change-provenance (rule-of-three; consistent with JT-2 <3).
- The ship/nuke EMITTERS + the deposit→evolve mechanism — Task #67 (this mint is the modelling that underpins it, not the emitter build).
- The `Change` ↔ Working-Set / session-chain link (#91/#127) — separate mint.
