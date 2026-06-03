---
id: ADR-001
title: LifecycleRun IS the prov:Activity; Step is its type; the v2 `step` ref points at a Step definition
status: accepted
date: 2026-06-03
deciders: [iain]
---

## Context

The change makes the brain's evolution machinery write PROV — "which activity
generated this entity version". For that we need a concrete answer to: *what
is the Activity?*

Recon-verified facts that constrain the answer:

- `lifecyclerun.schema.json` already describes itself as
  *"a prov:Activity that consumes inputs and produces outputs"*. The Activity
  concept is already assigned to LifecycleRun in the grammar's intent, even
  though no PROV edges are written yet.
- An existing LifecycleRun instance on disk
  (`.brain/instances/.../lifecyclerun/01KT419R8MQBQ6BNZPXDSKZBHZ.jsonld`)
  already carries `prov` in its `@context` and informal underscore-prefixed
  `_workflow` / `_trigger` / `_inputs_ref` / `_outputs_ref` fields — a
  hand-rolled, un-grammared PROV shape.
- `step.schema.json` (foundation v1.2.0) is the **IDEF0 definition** of a
  transformation — the *contract* (Inputs/Controls/Outputs/Mechanism). It is
  the *type* of work, not an occurrence of it. Step instances already exist
  (e.g. the release-train and discover-project Workflows author Step instances).
- LifecycleRun v1.0.0 carries `step_name` as a free string. Scope item 1
  requires changing it to a required `step` **ref** to a Step entity (breaking).

The modelling question with a real consequence: **when a living entity (a
Product) changes and we record `wasGeneratedBy <Activity>`, what is that
Activity, and what does LifecycleRun v2's new `step` ref point at?**

## Decision

**LifecycleRun is the `prov:Activity`. A Step is the *type* of that activity
(its IDEF0 definition). LifecycleRun v2's required `step` ref points at the
Step entity that defines what kind of run this was.**

So the three-layer PROV shape is:

```
Step (the definition / type)  ◀── step ───  LifecycleRun (the Activity / occurrence)
                                                   │
                                                   │ wasGeneratedBy
                                                   ▼
                                          Product / Opportunity / Project (the Entity version)
```

- A living entity version records `wasGeneratedBy` → a **LifecycleRun**.
- That LifecycleRun records `step` → a **Step** (what kind of run produced it).
- The LifecycleRun records `used` → the input entity versions it consumed.

### The two operational Steps this change must define

Scope item 1 asks for "the modelling call: what Step does a change-start /
change-ship LifecycleRun point at." We define exactly two foundation Step
instances under a new canonical instance set, with deterministic ULIDs
(per the house Canonical-Identifiers discipline):

| Step name | Meaning | mechanism |
|---|---|---|
| `change-started` | a `sulis-change start` completed — a unit of work opened | `mixed` |
| `change-shipped` | a `sulis-change mark-shipped` completed — a unit of work landed | `mixed` |

`_brain_emit_helper.emit_change_started_event` / `emit_change_shipped_event`
today pass `step_name=f"change-started:{primitive}:{slug}"`. Under v2 they pass
`step=<change-started Step ULID>` and move the `{primitive}:{slug}` detail into
a descriptive field on the LifecycleRun, not into the Step ref (the Step is the
*reusable definition*; the per-run specifics belong on the run). The general
`emit_lifecycle_step_event` helper, which today takes an arbitrary
`step_name` string, gains a small Step-resolution shim — see ADR-004 for the
migration mechanics.

## Options Considered

- **Step IS the Activity (rejected).** Would make Step an occurrence, which
  contradicts its IDEF0 "definition/contract" semantics and would break every
  existing Step instance (which are definitions, authored once and referenced
  by many runs). Conflates type with token.
- **Invent a new `Activity` entity (rejected).** PROV-O's `prov:Activity` maps
  cleanly onto LifecycleRun, which already claims the role. A new entity would
  duplicate LifecycleRun and orphan the existing instances. Convention says use
  what is already the Activity (CP-01, prior-art-in-repo).
- **Keep `step_name` as a free string and attach PROV separately (rejected).**
  Leaves the Activity untyped — "which activity" can be answered but "what kind
  of activity" cannot be queried as data. The whole point of the `step` ref is
  to make the activity *type* a first-class queryable edge. Also leaves the
  informal `_workflow`/`_trigger` underscore fields un-grammared forever.

## Consequences

- LifecycleRun v2 gains a required `step` ref → see ADR-004 for the breaking
  migration.
- Two new canonical Step instances (`change-started`, `change-shipped`) must be
  authored with deterministic ULIDs and pinned in the TDD's Canonical
  Identifiers section.
- The existing informal `_workflow`/`_trigger`/`_inputs_ref`/`_outputs_ref`
  fields become candidates to formalise as PROV `used` edges (ADR-002), but the
  faithful-generation-harness run that wrote them is out of scope to migrate
  field-by-field — its `step` ref resolves to a generic harness Step and its
  informal fields are left as-is (they are valid `unevaluatedProperties:false`
  failures only if the schema forbids them; the migration in ADR-004 handles
  this).
