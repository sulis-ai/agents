---
id: ADR-001
title: LifecycleRun IS the prov:Activity; it INSTANTIATES a Step (a prov:Plan); the v2 `step` ref points at that Step definition
status: accepted
date: 2026-06-03
revised: 2026-06-03 — terminology corrected against canonical (run *instantiates* a Plan, it is not "typed by" one); Step + Project are both prov:Plan; LifecycleRun is prov:Activity
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

**LifecycleRun is the `prov:Activity`. A Step is a `prov:Plan` (its IDEF0
definition — the recipe). The LifecycleRun *instantiates* the Step: it is the
occurrence of running that recipe. LifecycleRun v2's required `step` ref points
at the Step entity that defines what kind of run this was, via the canonical
`sulis:viaStep` predicate.**

This is the canonical PROV-O reading, verified against the source: the
LifecycleRun's `prov_constraints` carries `"is_a": "prov:Activity"` and
`"step": { "range": "dna:entity:step", "card": "1..1", "_predicate":
"sulis:viaStep" }` (`product-development.entities.jsonld:319`); the Step's
`prov_constraints` carries `"is_a": "prov:Plan"`
(`foundation.entities.jsonld:149`). The canonical `what_it_is` for LifecycleRun
reads *"a prov:Activity that **instantiates** a prov:Plan (the Step)"*
(`product-development.entities.jsonld:314`). A Plan→Activity instantiation, not
a type-of relationship.

> **Terminology correction.** An earlier draft of this ADR called Step "the
> *type* of the activity". That is loose: in PROV-O an Activity does not have a
> Plan as its *type* — it **instantiates** the Plan (the recipe it followed).
> The `step` ref records *which Plan this run instantiated*. The decision (the
> required `step` ref pointing at a Step) is unchanged and correct; only the
> word is fixed.

So the PROV shape is:

```
Step (the prov:Plan / the recipe)  ◀── step (sulis:viaStep) ───  LifecycleRun (the prov:Activity / the run that instantiated it)
                                                                        │
                                                                        │ wasGeneratedBy
                                                                        ▼
                                                Product / Opportunity (the prov:Entity version)
```

- A living **Entity** version (Product, Opportunity) records `wasGeneratedBy`
  → a **LifecycleRun**, modelled as a `prov_constraints` edge (ADR-002).
- That **LifecycleRun** records `step` → a **Step** (the Plan it instantiated),
  via `sulis:viaStep`.
- **Project is excluded** from `wasGeneratedBy`: Project is *also* a `prov:Plan`
  (`foundation.entities.jsonld:251`), not a `prov:Entity`. `wasGeneratedBy` is a
  PROV-O Entity→Activity edge — a type violation on a Plan. See ADR-002 and
  ADR-006. Project's lineage is carried by its bitemporal window + `state` enum
  + `deprecated_for` supersedes chain; the run→Project link is the separately-
  deferred `LifecycleRun.for_project` edge that lives *on the run* (L13 n=2,
  v0.7+), out of scope here.

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
`step=<change-started Step ULID>` (the Plan ref). The `{primitive}:{slug}`
per-run specificity that used to be smuggled into the `step_name` string is
carried by the LifecycleRun's **existing** v2.1.0 fields — `run_id` (the
workflow-run trace identifier) and the content-addressed `inputs_ref` /
`outputs_ref` — not by an invented field.

> **Correction — no `step_label`.** An earlier draft proposed adding a new
> `step_label` field to the LifecycleRun to hold the per-run specificity. The
> canonical v2.1.0 LifecycleRun has **no such field** and DR-013 already
> rejected payload-on-the-run-record (option 1, "inline the payloads… rejected:
> the run record stays a small audit-log row"). The per-run detail belongs in
> `run_id` (trace grouping) and `inputs_ref`/`outputs_ref` (content-addressed),
> all of which are already canonical v2.1.0 fields. **`step_label` is dropped
> entirely** — it would diverge the vendored schema from canonical and re-open
> the exact "payload on the run record" question DR-013 closed.

The general `emit_lifecycle_step_event` helper, which today takes an arbitrary
`step_name` string, gains a small name→Step-ULID resolution shim — see ADR-004
for the migration mechanics. The schema it migrates to is the **canonical**
v2.1.0, surgically re-vendored, not an authored shape.

## Options Considered

- **Step IS the Activity (rejected).** Would make Step an occurrence, which
  contradicts its `prov:Plan` "definition/contract" semantics and would break
  every existing Step instance (which are Plans, authored once and instantiated
  by many runs). Conflates the Plan with the Activity that instantiates it.
- **"Step is the *type* of the LifecycleRun" (rejected — terminology).** A
  LifecycleRun does not have a Step as its `rdf:type`; it `prov:instantiates`
  the Step (Plan). The corrected reading is Plan→Activity instantiation via
  `sulis:viaStep`, matching canonical `what_it_is`.
- **Add a `step_label` field for per-run specificity (rejected).** Not in
  canonical v2.1.0; DR-013 already rejected payload-on-the-run-record. The
  per-run detail is carried by the existing canonical `run_id` /
  `inputs_ref` / `outputs_ref` fields.
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

- LifecycleRun v2.1.0 carries a required `step` ref (already canonical) → see
  ADR-004 for the breaking migration, which is now a **surgical re-vendor of the
  canonical compiled v2.1.0 schema**, not an authored bump.
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
