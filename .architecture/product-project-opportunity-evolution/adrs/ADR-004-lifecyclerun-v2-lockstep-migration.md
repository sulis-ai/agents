---
id: ADR-004
title: LifecycleRun v1.0.0 -> v2.1.0 lockstep migration (schema + helper + CLI + existing instances)
status: accepted
date: 2026-06-03
deciders: [iain]
---

## Context

Scope item 1 + the BREAKING constraint: `lifecyclerun.schema.json` changes
`step_name` (required string) to `step` (required ref `^dna:step:<ulid>$`).
This is breaking — a v1.0.0 instance has no `step` field and a v2 validator
rejects it; a v1 validator rejects a v2 instance. The SPEC mandates **no
half-migrated state**: schema, `_brain_emit_helper`, `sulis-emit-lifecyclerun`,
and existing on-disk instances move together.

Verified blast radius (every site that reads/writes `step_name`):

| Site | What it does today |
|---|---|
| `lifecyclerun.schema.json` | `step_name` required string |
| `_lifecyclerun_emission.py` | `compose_lifecyclerun(step_name=...)` builds the dict; ID seeded from `step_name` |
| `_brain_emit_helper.py` | 3 helpers pass `step_name=f"...:{slug}"` strings |
| `sulis-emit-lifecyclerun` (CLI) | `--step-name` arg → `emit_lifecyclerun(step_name=...)` |
| existing instances | 2 on-disk `.jsonld` files with `step_name`, no `step` |

This ADR records *how* the lockstep is sequenced so the decomposition can build
it as the **first** piece (the PROV spine, per the SPEC build-order note).

## Decision

**One atomic migration, sequenced as a single dependency-ordered slice, with a
data-migration script that runs as part of the same change — never leaving a
mixed v1/v2 store.**

### The version bump: 1.0.0 → **2.1.0**

Major bump (breaking `step` swap) and the minor digit carries the additive
`used` PROV field from ADR-002 — so the single schema rev is `2.1.0`, matching
the SPEC's stated target. The `$id` becomes
`https://sulis.co/dna/schema/lifecyclerun/2.1.0`.

### Step-ref resolution at the call sites

Per ADR-001, the two operational Steps (`change-started`, `change-shipped`) get
deterministic ULIDs pinned in the TDD Canonical Identifiers section. The helper
functions resolve:

- `emit_change_started_event` → `step = <change-started ULID>`
- `emit_change_shipped_event` → `step = <change-shipped ULID>`
- `emit_lifecycle_step_event(step_name=...)` (the general one) → resolves the
  free string to a Step via a small **name→Step-ULID map** for known step
  names, and for unknown names mints/points at a generic
  `unclassified-lifecycle-step` Step (deterministic ULID). The per-run
  `step_name` detail is preserved on the LifecycleRun in a new descriptive
  field (`step_label`, additive) so no information is lost — the Step ref
  carries the *type*, `step_label` carries the *instance specificity* that used
  to live in `step_name`.

> The `change-started`/`change-shipped`/`unclassified-lifecycle-step` Steps are
> authored as canonical foundation Step instances (a new
> `plugins/sulis/instances/lifecycle-steps/steps.jsonld` set), Path-A style,
> with deterministic ULIDs. They are the reusable definitions the runs point at.

### Existing-instance migration

A one-shot migration script (`scripts/migrate_lifecyclerun_v1_to_v2.py`, or a
subcommand) walks every `.brain/instances/*/lifecyclerun/*.jsonld`, and for
each v1 instance:

1. maps `step_name` → the matching Step ULID (known names via the map; the
   harness instance's `faithful-generation-harness` → the
   `unclassified-lifecycle-step` Step), moving the old string to `step_label`;
2. removes `step_name`, adds `step`;
3. re-validates against v2.1.0 before writing (reject-on-invalid — never write a
   still-invalid instance);
4. is idempotent (a v2 instance is detected by presence of `step` and skipped).

The migration runs against the marketplace's own `.brain/instances` in this
change. Downstream consumer repos run it via the CLI/skill on next emit (or a
`sulis-emit-lifecyclerun --migrate` flag) — but because emission is best-effort
and graceful-degrading, a consumer that never migrates simply keeps its old v1
files until they touch them; the marketplace's own store is fully migrated here.

### Lockstep ordering inside the slice

```
1. author the canonical lifecycle Steps (definitions exist before anything refs them)
2. bump schema to 2.1.0 (vendored compiled copy) + add `used`
3. update _lifecyclerun_emission (compose_lifecyclerun: step + step_label; ID seed from step+timestamp)
4. update _brain_emit_helper (3 helpers resolve Step refs)
5. update sulis-emit-lifecyclerun CLI (--step resolves; --step-name kept as deprecated alias mapping to step_label + resolved step)
6. run the instance migration on .brain/instances
7. tests green at each step; suite green at the end
```

No commit in this sequence leaves the schema and the emitters disagreeing —
the schema bump (2) and the emitter updates (3–5) land together in the slice;
CI on the slice's PR is the gate.

## Options Considered

- **Make `step` optional to soften the break (rejected).** The SPEC says
  required; an optional ref re-admits the untyped-activity problem ADR-001
  closes. A clean break with a migration script is the boring, correct move.
- **Keep `step_name` alongside `step` for back-compat (rejected as permanent;
  kept only as a deprecated CLI alias).** Two fields meaning the same thing is
  the band-aid the SPEC's "no half-migrated state" forbids. `step_label` is
  *not* a duplicate of `step` — it is the free-text per-run specificity, a
  different concern, retained deliberately.
- **Lazy per-instance migration only, no upfront script (rejected for the
  marketplace's own store).** Would leave the marketplace store in mixed
  v1/v2 state indefinitely — exactly the half-migrated state forbidden. Upfront
  script for our own store; lazy is acceptable only for downstream consumers
  whose stores we don't own.

## Consequences

- This is build-order piece 1 (the PROV spine). ADR-002's `used` field and the
  PROV `@context` standardisation ride in the same schema rev.
- New canonical Step instance set `plugins/sulis/instances/lifecycle-steps/`.
- New migration script + its test (a v1 fixture in, a v2 instance out, idempotent
  on re-run, rejects unmappable).
- The drift detector / vendored-schema parity must be updated for the 2.1.0
  compiled schema.
