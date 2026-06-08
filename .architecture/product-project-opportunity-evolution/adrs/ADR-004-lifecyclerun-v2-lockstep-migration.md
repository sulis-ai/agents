---
id: ADR-004
title: LifecycleRun v1.0.0 → v2.1.0 — surgically RE-VENDOR the already-minted canonical schema (do not author), lockstep/atomic with the emitter migration
status: accepted
date: 2026-06-03
revised: 2026-06-03 — REWRITTEN against canonical. LifecycleRun v2.1.0 is ALREADY MINTED upstream (DR-009 did step_name→step as v2.0.0; DR-013 added run_id/deterministic/inputs_ref/outputs_ref as v2.1.0). The action is a SURGICAL RE-VENDOR of the canonical compiled schema — NOT authoring a new shape. step_label + used-on-run DROPPED. Re-vendor + emitter migration are one atomic WP.
deciders: [iain]
note: 2026-06-03 — ADDED the two-stage re-vendor note (v2.1.0 now, v2.2.0 as a separate mint-gated increment adding for_project — see ADR-007). The "re-vendor not author" decision + the step_label/used drop are UNCHANGED; this WP's target stays v2.1.0 and stays buildable-now.
---

## Context

An earlier draft of this ADR treated the v2.1.0 LifecycleRun as a shape **this
change authors** — and invented a `step_label` field and a `used`-on-the-run
field to carry per-run detail. A brain-governance review corrected both against
the canonical source:

- **LifecycleRun v2.1.0 is ALREADY MINTED upstream.** Two Decision Records did
  it: **DR-009** lifted process knowledge and did the breaking `step_name: text`
  → `step: ref→step` swap (v1.0.0 → **v2.0.0**); **DR-013** added four optional
  fields (`run_id`, `deterministic`, `inputs_ref`, `outputs_ref`) as the additive
  minor (v2.0.0 → **v2.1.0**). The canonical compiled schema already exists at
  `.specifications/business-dna/compiled/schemas/product-development/lifecyclerun.schema.json`.

- **The invented v2.1.0 shape was WRONG and COLLIDES with the real version.**
  The earlier draft's `step_label` + `used`-on-LifecycleRun do not exist in
  canonical v2.1.0, and DR-013 explicitly rejected payload-on-the-run-record
  (option 1: *"inline the payloads… rejected: the run record stays a small
  audit-log row"*). Authoring a divergent "v2.1.0" would fork the vendored schema
  from the canonical one at the same version number — the worst possible drift.

The canonical v2.1.0 field-set, verified at
`product-development.entities.jsonld:316–319`:

```jsonc
"field_spec": { "id": "id", "step": "ref→step", "at": "datetime",
                "by_actor": "ref→actor", "outcome": "enum[completed|failed|in-progress|cancelled]",
                "run_id": "text?", "deterministic": "bool?",
                "inputs_ref": "text? x-sensitive", "outputs_ref": "text? x-sensitive" },
"required": ["id", "step", "at", "outcome"],
"prov_constraints": { "is_a": "prov:Activity",
                      "wasAssociatedWith": { "range": "dna:entity:actor", "card": "0..*" },
                      "step": { "range": "dna:entity:step", "card": "1..1", "_predicate": "sulis:viaStep" } }
```

No `step_label`. No `used`. The breaking change is still real (`step_name`
required string → `step` required ref); only its **provenance** changes from
"we author it" to "we re-vendor the already-minted canonical".

Verified blast radius (every in-repo site that reads/writes `step_name`):

| Site | What it does today |
|---|---|
| `plugins/sulis/brain/compiled/product-development/lifecyclerun.schema.json` | vendored at v1.0.0 (`step_name` required string) |
| `_lifecyclerun_emission.py` | `compose_lifecyclerun(step_name=...)` builds the dict; ID seeded from `step_name` |
| `_brain_emit_helper.py` | 3 helpers pass `step_name=f"...:{slug}"` strings (lines 131, 163, 198) |
| `sulis-emit-lifecyclerun` (CLI) | `--step-name` arg → `emit_lifecyclerun(step_name=...)` |
| existing instances | 2 on-disk `.jsonld` files with `step_name`, no `step` |

## Decision

**Surgically re-vendor the canonical compiled v2.1.0 LifecycleRun schema into
`plugins/sulis/brain/compiled/product-development/lifecyclerun.schema.json`,
and migrate the emitter (`_lifecyclerun_emission` + the three
`_brain_emit_helper` helpers + the CLI) in LOCKSTEP — one atomic WP, never a
loose schema commit ahead of the emitter.**

### Two-stage re-vendor: v2.1.0 now, v2.2.0 as a mint-gated increment (ADR-007)

The LifecycleRun schema is re-vendored in **two stages**, on the same vendored
file, sequentially:

1. **v2.1.0 NOW (this WP, WP-002).** The already-minted canonical v2.1.0
   (`step_name`→`step` from DR-009 + the four DR-013 optional fields). This needs
   **no mint** and is **buildable immediately** — it is the breaking step-ref
   spine everything else hangs off. **This WP's re-vendor target stays v2.1.0 and
   is NOT newly mint-gated by the `for_project` work.**
2. **v2.2.0 as a SEPARATE increment (WP-016, ADR-007).** A MINOR additive bump
   adding one optional `for_project: ref→project (0..1)` property (run→Project
   traceability). It is a **NEW upstream mint** (LifecycleRun 2.1.0 → 2.2.0, both
   the PD canonical and its insurance mirror), authored in parallel. Its in-repo
   re-vendor + emitter wiring `dependsOn` this WP's v2.1.0 re-vendor AND start
   `blocked` on the `for_project` mint being accepted → recompiled → re-vendored
   — the same gating shape WP-008 has on the `wasGeneratedBy` mint.

v2.2.0 supersedes v2.1.0 on the vendored file as a clean additive drop-in (one
optional property; pre-bump v2.1.0 instances validate unchanged under v2.2.0 — no
instance migration for the increment). The "re-vendor not author" discipline and
the `step_label`/`used` drop below apply identically to both stages: v2.2.0 is
re-vendored from the upstream-minted canonical, never authored in-repo, and adds
**no** `step_label` and **no** `used` — only the canonical `for_project` ref.

### Why a surgical re-vendor, not `sync-from-canonical.sh`

The marketplace's vendored brain (`plugins/sulis/brain/compiled/`) is an
**intentional mixed-version vendor** (see that directory's `README.md`):
product-development is mirrored at ontology **v0.5.0**, with `scenario` /
`testrun` / `requirement` / `decision` surgically vendored from **v0.9.0**
because each is additive + standalone. The README explicitly tracks
`lifecyclerun v1.0.0 → 2.1.0` as the breaking item *"deliberately NOT bundled"*,
needing *"the emitter (`_brain_emit_helper`) migrated in lockstep"*.

- The wholesale `scripts/sync-from-canonical.sh` targets the **separate
  `sulis-brain` plugin** in the dna repo (a full vendor of all schemas at a
  single ontology version) — **not** the marketplace's surgically mixed
  `plugins/sulis/brain/compiled/` tree. Running it here would overwrite the
  intentional mixed-version vendor and pull in unrelated breaking changes.
- The correct move is a **surgical, single-file re-vendor**: copy the canonical
  compiled `lifecyclerun.schema.json` (v2.1.0) over the vendored v1.0.0 copy,
  respecting the README's mixed-version discipline. The schema is a clean drop-in
  (the canonical compiled output already includes the bitemporal/`sys_status`
  envelope fields the vendored copies carry, so no hand-merge is needed — diff
  confirms only `step_name`→`step` + the four DR-013 optional fields change).

### Lockstep / atomic with the emitter migration (the README mandate)

The README mandates lockstep: the schema and `_brain_emit_helper` move together.
Therefore the **re-vendor and the emitter migration are ONE work package**, not
a schema commit followed later by an emitter commit. No intermediate state where
the vendored schema is v2.1.0 but the emitter still composes `step_name` (every
emit would reject-on-invalid), and none where the emitter composes `step` but the
schema still requires `step_name`.

Inside that one WP, the ordered moves are:

```
1. author the canonical lifecycle Step instances (definitions exist before anything refs them) — see ADR-001
2. re-vendor: copy canonical compiled lifecyclerun.schema.json (v2.1.0) → plugins/sulis/brain/compiled/product-development/
3. update _lifecyclerun_emission (compose_lifecyclerun: `step` ref, NOT step_name; ID seed from step+timestamp)
4. update _brain_emit_helper (3 helpers resolve a Step ULID for `step`; per-run detail goes in run_id, not step_label)
5. update sulis-emit-lifecyclerun CLI (--step resolves a Step; --step-name kept as a deprecated alias that resolves the legacy string to a Step)
6. run the instance migration on .brain/instances (step_name → step)
7. tests green throughout; suite green at the end
```

The WP carries a `removal_plan` for the two deprecated surfaces it introduces
(the `--step-name` CLI alias; any transitional string-resolution path) with a
target date.

### Step-ref resolution at the call sites

Per ADR-001, the operational Steps (`change-started`, `change-shipped`, and a
generic `unclassified-lifecycle-step` fallback) get deterministic ULIDs pinned in
the TDD Canonical Identifiers section. The helpers resolve:

- `emit_change_started_event` → `step = <change-started ULID>`
- `emit_change_shipped_event` → `step = <change-shipped ULID>`
- `emit_lifecycle_step_event(step_name=...)` (the general one) → resolves the free
  string via a **name→Step-ULID map** for known names; unknown names resolve to
  the generic `unclassified-lifecycle-step` Step.

The per-run specificity that used to live in the `step_name` string (e.g.
`{primitive}:{slug}`) is carried by the LifecycleRun's **existing canonical**
`run_id` field (the workflow-run trace identifier) — **not** by a new
`step_label` field, which does not exist in canonical v2.1.0 and is dropped.

> The `change-started` / `change-shipped` / `unclassified-lifecycle-step` Steps
> are authored as canonical foundation Step instances (a new
> `plugins/sulis/instances/lifecycle-steps/steps.jsonld` set), Path-A style,
> with deterministic ULIDs. They are the reusable Plans the runs instantiate.

### Existing-instance migration

A one-shot migration script (`scripts/migrate_lifecyclerun_v1_to_v2.py`) walks
every `.brain/instances/*/lifecyclerun/*.jsonld`, and for each v1 instance:

1. maps `step_name` → the matching Step ULID (known names via the map; the
   harness instance's `faithful-generation-harness` → the
   `unclassified-lifecycle-step` Step). The old `step_name` string is **dropped**
   (not preserved into a `step_label` — there is no such field); where genuinely
   needed, run-grouping is carried by `run_id`;
2. removes `step_name`, adds `step`;
3. re-validates against the re-vendored v2.1.0 before writing
   (reject-on-invalid — never write a still-invalid instance);
4. is idempotent (a v2 instance is detected by presence of `step` and skipped).

The migration runs against the marketplace's own `.brain/instances` in this
change (eager-for-our-own). Downstream consumer repos migrate lazily on next
emit (graceful-degradation: a consumer that never migrates keeps its old v1 files
until they touch them).

## Options Considered

- **Author a new v2.1.0 shape with `step_label` + `used` (rejected — collides
  with the real canonical v2.1.0).** The earlier draft. The invented fields are
  not in canonical v2.1.0; DR-013 rejected payload-on-the-run-record. Authoring a
  divergent schema at the same version number is the worst drift.
- **Run the wholesale `sync-from-canonical.sh` (rejected — wrong target).** That
  script vendors the *separate sulis-brain plugin* at a single ontology version;
  it would overwrite the marketplace's intentional mixed-version vendor and pull
  in unrelated breaking changes. The surgical single-file re-vendor respects the
  README's mixed-version discipline.
- **Split the re-vendor and the emitter migration into two WPs (rejected —
  breaks the README's lockstep mandate).** Any ordering of two separate commits
  leaves a window where schema and emitter disagree and every emit
  reject-on-invalids. One atomic WP, gated by CI on its PR.
- **Make `step` optional to soften the break (rejected).** Canonical requires it;
  an optional ref re-admits the untyped-activity problem ADR-001 closes.
- **Keep `step_name` alongside `step` for back-compat (rejected as permanent;
  kept only as a deprecated CLI alias with a `removal_plan`).** Two fields meaning
  the same thing is the band-aid "no half-migrated state" forbids.

## Consequences

- This is build-order piece 1 (the PROV spine), now a **re-vendor + emitter
  lockstep**, delivered as **one atomic WP** (not a schema WP + an emitter WP).
- The re-vendored schema is the canonical compiled v2.1.0 — `$id`
  `https://sulis.co/dna/schema/lifecyclerun/2.1.0`, `step` required ref, the four
  DR-013 optional fields present, **no `step_label`, no `used`**.
- New canonical Step instance set `plugins/sulis/instances/lifecycle-steps/`
  (`change-started`, `change-shipped`, `unclassified-lifecycle-step`).
- New migration script + its test (a v1 fixture in, a v2 instance out, idempotent
  on re-run, rejects unmappable).
- The drift detector / vendored-schema parity is updated for the re-vendored
  v2.1.0 compiled schema. No `used` field and no `step_label` appear anywhere —
  the vendored schema is byte-faithful to canonical v2.1.0 (modulo the standard
  vendored envelope fields).
- **The v2.2.0 increment (ADR-007 / WP-016) lands separately and later**, gated on
  its own mint. This WP (v2.1.0) is unaffected by that gate and lands with the
  pre-gate spine. When v2.2.0 lands, it re-vendors over this WP's v2.1.0 file
  (additive `for_project` only) and the drift parity is re-pointed at v2.2.0 — the
  vendored schema stays byte-faithful to the upstream-recompiled canonical at
  whichever version is current.
