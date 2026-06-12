# Field-spec — `Change` (PD work-unit Activity) + the change-provenance edges

**Status:** DRAFT for central authoring
**Domain:** `product-development` (PD) — Change joins LifecycleRun as the second prov:Activity in the domain
**Trajectory:** Phase 4a (mint ONE new entity — `Change`) + Phase 4b (field-extension — two additive optional provenance edges on the PD generated entities)
**Grounded against:** sulis-brain 0.14.0 (highest vendored). Shape template: `lifecyclerun.schema.json` v2.1.0 + `product-development.entities.jsonld` LifecycleRun entry.
**Run:** dna-mint-an-entity 01KTYMQ8N4PV5XHW3K2BZRFD7A
**Admission:** dna-runner admission → overall_score 1.0, verdict admit (after the escalate-remediation cycle).

---

## 0. The crux resolved (the three framing questions)

### Q1 — Is `Change` one entity, or three things falsely unioned (work-unit + transaction + git-provenance)?

**ONE entity.** A DDD *unit of work* IS a transaction — not two concepts. The git fields (`base_sha`, `branch`)
are *substrate attributes* of the work-unit (where the work happened), exactly as `LifecycleRun.inputs_ref` /
`outputs_ref` are substrate pointers — not co-equal siblings. Phase 1.5 critical-thinking spiral confirmed:
no false-MECE (AP-08), no premature abstraction (AP-04), no scope-creep (AP-07). `Change` = a work-unit
Activity + its transaction-state + its substrate-location. One concept.

### Q2 — Is `Change` a sibling of LifecycleRun, or a duplicate / the same entity at a different grain?

**Sibling, not duplicate.** Both are `prov:Activity`. LifecycleRun is the **fine-grained** step-run (carries
`step`/`outcome{completed|failed|in-progress|cancelled}`); Change is the **coarse-grained** work-unit (carries
`intent`/`primitive`/`state{in-flight|shipped|nuked}`/`for_product`/`parent_change`). The field sets are
disjoint and the lifecycle states differ. A single entity with a grain-discriminator would force the union of
two disjoint shapes (worse modelling). The set of LifecycleRuns occur *within* a Change (`prov:wasInformedBy` /
activity-nesting). **Change mirrors LifecycleRun's BASE-FIELD shape** (the bitemporal envelope + the v2.1.0
optional run-grouping fields where they apply), per the brief's directive.

### Q3 — Where do the provenance edges live, and is `primitive` an entity or an enum?

- **The edges live on the GENERATED entity, pointing back to the Change** — per PROV `wasGeneratedBy`
  (the generated entity `wasGeneratedBy` the activity). Reverse-query gives the transaction set.
  **Placement: a SHARED PD base-field pair** (see §4), mirroring how `sys_status`/`valid_from` are a shared envelope.
- **`primitive` is a closed ENUM field, NOT a separate entity.** The 22-value change vocabulary is an L2
  controlled vocabulary (like a country-code list). It has no independent lifecycle / cross-reference /
  queryability of its own → minting a `Primitive` entity on n=1 would itself be the AP-04 premature-abstraction
  defect. Carried as an enum on Change (cf. `LifecycleRun.outcome`, `Brand.state` carrying a vocabulary).

---

## 1. `Change` — field spec

`Change` carries the **foundation bitemporal envelope** (identical to every entity, identical to LifecycleRun):
`id`, `sys_status`, `valid_from`, `valid_to`, `confidence`.

| Field | Type | Required | Notes / grounding |
|---|---|---|---|
| `id` | `string` pattern `^dna:change:[0-9A-HJKMNP-TV-Z]{26}$` | ✅ | ULID, Crockford base32 — mirrors `lifecyclerun` id pattern exactly. |
| `sys_status` | enum `active\|archived\|deleted\|purged` | ✅ | foundation envelope (record lifecycle — is this ROW live). |
| `valid_from` | date-time, nullable | — | bitemporal business-truth window start. |
| `valid_to` | date-time, nullable | — | bitemporal business-truth window end. |
| `confidence` | number 0..1 | — | instance reliability. |
| `handle` | string | ✅ | the short founder reference (`CH-xxxxx`). Human-facing key, DISTINCT from the ULID `id` (machine key) — like a PR number vs a commit sha. Load-bearing + collision-prone (Task #101). |
| `slug` | string | ✅ | kebab-case human name. |
| `intent` | string | ✅ | one-line statement of the work. |
| `primitive` | enum (22 values — see §2) | ✅ | the change vocabulary (create/feat/fix/refactor/harden/decompose/delete/replace/extend/…). Closed controlled vocabulary; the L2-convention part baked in as an enum, NOT a separate entity. |
| `state` | enum `in-flight\|shipped\|nuked` | ✅ | the TRANSACTION state. ship=commit, nuke=rollback (Task #67). ORTHOGONAL to `sys_status` (the record-lifecycle axis) — the three-axis pattern DR-030 ratified (bitemporal ⟂ transaction-state ⟂ record-status). |
| `for_product` | `^dna:product:[0-9A-HJKMNP-TV-Z]{26}$` | ✅ | → Product. The product this change contributes to. Resolves to an existing PD entity. Like `LifecycleRun.step`, this is the required upstream anchor. |
| `parent_change` | `^dna:change:[0-9A-HJKMNP-TV-Z]{26}$`, nullable | — | → Change (SELF-EDGE). The durable carry link (#123) + ancestry (#124). Nullable: a root change has no parent. ABox invariant: the ancestry graph must be acyclic (a DAG) — JT-7 cycle-tolerance; not schema-enforceable, a ref-integrity concern. |
| `relationship` | enum `builds_on\|depends_on`, nullable | — | qualifies `parent_change` (#124 ancestry). Null when `parent_change` is null. |
| `base_sha` | string, nullable | — | git provenance — the commit the change branched from (Task #44 — base_sha was the missing field that killed cockpit diffs). |
| `branch` | string, nullable | — | git provenance — the working branch. |
| `by_actor` | `^dna:actor:[0-9A-HJKMNP-TV-Z]{26}$`, nullable | — | → Actor. The founder/agent who ran the change (mirrors `LifecycleRun.by_actor`). prov:wasAttributedTo. NOT a login/auth identity. |
| `started_at` | date-time | ✅ | lifecycle timestamp — when the change went in-flight. |
| `shipped_at` | date-time, nullable | — | lifecycle timestamp — when the change shipped (or was nuked). Null while in-flight. |

### Required set (Change)
`id`, `handle`, `slug`, `intent`, `primitive`, `state`, `for_product`, `started_at`.
(All hold at the earliest lifecycle state `state=in-flight` — verified in Phase 5 attack B. `shipped_at` is
correctly NOT required; it is set only at ship/nuke.)

### prov_constraints
```
{ "is_a": "prov:Activity",
  "wasInformedBy": "the LifecycleRuns that occur within this Change (activity-nesting)",
  "wasAttributedTo": "by_actor (the founder/agent who ran the change)" }
```

### what_its_not (the antithesis — scope-anchored per JT-5 / Phase 5.7)
> NOT a `LifecycleRun` — that is ONE fine-grained step-run that occurs WITHIN a change; a Change is the coarse
> work-unit. NOT a git commit — a commit is one ship-event; a Change is the whole work-unit and may span many
> commits (base_sha/branch are git PROVENANCE on the Change, not the Change itself). NOT a `Product` — the
> durable thing a change contributes to (`for_product`). NOT a `Workflow` or `Step` — those DEFINE the process;
> a Change is a run-side work-unit instance. NOT an ITIL "change request" / governance ticket. NOT the machine
> session — `worktree_path` / `pid` / `tty` / `session.json` are machine-local session state (see §3).

`x-schema-org-extends`: **`schema:Action`** (mirrors LifecycleRun — both are prov:Activity ≈ schema:Action).

---

## 2. The `primitive` enum — the 22-value change vocabulary

Carried as a closed enum on `Change.primitive` (NOT a separate entity). Membership:

```
create | feat | fix | refactor | harden | decompose | delete | replace | extend |
test | docs | chore | perf | build | ci | revert | style | merge | spike |
migrate | deprecate | release
```

**`source_of_truth`:** the change-primitive controlled vocabulary is an L2 convention. The brief asserts the
22-value membership above; the FIELD-SPEC records it AS the enum, and the DR flags (LOW-severity residual from
Phase 1.5) that central authoring MUST cite the canonical vocabulary file the enum compiles from, so the enum
is single-sourced (not hand-copied). If the canonical list differs from the 22 above, the enum follows the
canonical file — the list here is the candidate-asserted set pending that reconciliation.

---

## 3. Deliberately EXCLUDED fields (confirmed — machine-local session state)

These are NOT on the canonical `Change` entity. They are machine-specific local session state, owned by the
local session daemon / global change store (Task #30), NOT shared brain truth:

| Excluded field | Why excluded | Where it lives instead |
|---|---|---|
| `worktree_path` | filesystem path of the working tree — machine-local, not portable | session daemon / change store row |
| `pid` | OS process id of the session — ephemeral, machine-local | session daemon |
| `tty` | terminal device of the session — ephemeral, machine-local | session daemon (the #32 liveness check substrate) |
| `session.json` contents | the full local session blob — machine-local working state | the worktree's `.sulis/session.json` |

JT-6 portability self-check: the entity records THAT the work happened + its provenance; the machine mechanics
(worktree, pid, tty) are the runner's concern. Including them would couple the canonical shape to one machine's
session model — the exact JT-6 violation the gate guards against.

---

## 4. The change-provenance edges (Phase 4b field-extension)

Two additive, optional fields placed on a **SHARED PD base** so every PD generated entity uniformly answers
"which change made / revised me?" (mirroring how `sys_status`/`valid_from`/`valid_to`/`confidence` are a shared
envelope). This is the reverse side of `Change` — the edges live on the GENERATED entity, per PROV.

```json
"produced_by_change": {
  "type": "string",
  "pattern": "^dna:change:[0-9A-HJKMNP-TV-Z]{26}$",
  "description": "the Change that created this entity (prov:wasGeneratedBy). Reverse-query gives a change's creation set."
},
"evolved_by_change": {
  "type": "array",
  "items": { "type": "string", "pattern": "^dna:change:[0-9A-HJKMNP-TV-Z]{26}$" },
  "description": "the Changes that revised this entity, in order (prov:wasRevisionOf-flavoured). Reverse-query gives a change's revision set."
}
```

- `produced_by_change` — singular, optional. The ONE change that generated the entity. prov:wasGeneratedBy.
- `evolved_by_change` — array, optional. The ordered set of changes that revised the entity. prov:wasRevisionOf.
- **Together, the reverse-query "what did change X produce/evolve?" = the transaction set** for ship=commit /
  nuke=rollback (Task #67).

### Placement decision — SHARED base vs per-entity (RECOMMENDED: shared)
Recommended **shared PD base-field pair**, per the brain's own conventions:
- The brain already inherits a shared envelope (`_inherited_fields`: sys_status/valid_from/valid_to/confidence)
  on every entity. "Which change touched me?" is the same kind of universal provenance question — it belongs in
  the shared envelope, not duplicated per-entity.
- A SHARED base means the ship/nuke transaction can reverse-query a single uniform field across all entity
  types; per-entity placement would fragment that query and risk drift (one entity names it differently).
- **Cost (Phase 5.5):** every PD entity schema gains two OPTIONAL fields → per DR-008 this is a coordinated
  **MINOR-bump sweep** (additive optional → MINOR, NOT major). Pre-existing instances remain valid without the
  fields → NO migration contract required. The "cascade" is reclassified as planned additive MINOR work.

Foundation-lift of these two fields is DEFERRED (rule-of-three; JT-2 <3 today — only PD needs change-provenance).
When a 2nd domain needs it, lift to the foundation shared base then.

---

## 5. What is deliberately DEFERRED (recorded, not skipped)

- **The ship/nuke EMITTERS + deposit→evolve mechanism** — Task #67. This mint is the MODELLING that underpins
  it; the emitter build is separate.
- **The C4b ABox lineage fixture** — requires populated Change instances (none exist at mint time). Re-run
  `dna-runner lineage --instances <set>` post-emission.
- **Foundation-lift of the provenance edges** — deferred to rule-of-three.
- **The `Change` ↔ Working-Set / session-chain link** (#91/#127) — separate mint.
- **The `primitive` enum single-sourcing** — central authoring cites the canonical vocabulary file (see §2).

---

## 6. Phase 6 generate-then-verify plan (for central authoring — cross-repo per #65)

1. Add `Change` to `sources/product-development.entities.jsonld` (in the sulis-brain source repo) → compile
   `schemas/product-development/change.schema.json`.
2. Add `produced_by_change` + `evolved_by_change` to the PD shared base (every PD generated entity schema) —
   additive optional, MINOR bump each.
3. Recompile + vendor into THIS repo's `plugins/sulis/brain/compiled/product-development/`.
4. Red-green fixtures:
   - ≥1 valid `Change` accepted; ≥1 rejected (bad ULID / missing `intent` / bad `primitive` / bad `state`).
   - ≥1 generated entity accepted WITH `produced_by_change` pointing at a valid Change; ≥1 rejected for a
     malformed change ref.
   - state-machine fixture: `state` transitions in-flight→shipped and in-flight→nuked accepted; shipped→in-flight rejected.
5. Run `DNA_VALIDATION_RUBRIC` C1–C9 (`dna-runner evaluate` / `validate`). Draft-complete at PASS/WARN.
