# Entity design — `Scenario` (the living verification scenario)

> Validated by `sulis-brain:mint-coach` against the live ontology
> (`plugins/sulis/brain/compiled/`). Verdict: ACCEPT (design pass). This is the
> entity the testable-state DoD gate consumes. Mint = a separate tracked change
> (cross-repo — see Mint Plan). Captured 2026-06-02.

## What it is

`Scenario` — *"a living, reusable verification scenario: a named journey of
steps that proves one or more Requirements against a Design."* The durable test
**definition** the brain was missing (it had only the *events* — `TestRun`/
`TestResult`). LIVING entity; lives in the graph, never in a change dir.

## Name (Phase 5.7 polysemy — why not TestCase/Journey)

- **TestCase** — collides with the `Test*` *event* family (`TestRun`/`TestResult`);
  a living definition in an event-named family is a senses-trap. Rejected.
- **Journey** — collides with `JOURNEY.md` AND with `Workflow` (already "a journey
  of steps"). Rejected.
- **`Scenario`** — zero `@id`/prose collision; BDD-established (Gherkin) term for a
  named reusable verification narrative; reads as a *definition*, not an event.
  CP-01 boring-and-established. **Chosen.**

## Compose, not specialise (Decision 1)

`Scenario` is a NEW product-development entity that **composes** a foundation
`Workflow` (which composes IDEF0 `Step`s) — it is NOT a specialised `Workflow`.
Why:
1. `Workflow.type` is a closed enum with no test/verification member — adding one
   is a *foundation* edit that bleeds "test" into every tenant's process graph.
2. `Scenario` carries `verifies`/`exercises` edges a generic `Workflow` must not
   hold (test-domain semantics ≠ generic-process semantics).
3. Reuse stays maximal **by composition**: `Scenario.journey → Workflow` (a graph
   of IDEF0 Steps — the login→onboard→use path), zero schema change to
   Step/Workflow. EP-03 extend-don't-duplicate.

The journey, steps, preconditions-as-asserts, and inputs-as-needs all come for
free from the existing Step/Workflow primitives. The CI-runnable / manual-tester
/ founder-legible triple falls out of `Step.mechanism` (deterministic|human|mixed)
+ `agent_instructions` + `mechanism_detail`.

## Discriminator (Decision 3)

A `Workflow` is "a test journey" **iff** a `Scenario.journey` references it
(containment is the marker — no `Workflow.type` member needed). Plus
`Workflow.for_process: "verification"` as a cheap free-text filter tag.

## Edges (Phase 5.5 referential integrity — all resolve)

- `Scenario.verifies → Requirement[]` (M:N — which requirements it proves)
- `Scenario.exercises → Design` (which Solution it runs against)
- `Scenario.journey → Workflow` (the IDEF0/SIPOC step graph)

## Property set

```
required: [id, name, verifies, exercises, journey, state, sys_status]
id          dna:scenario:<ULID>
name        string
description  string
verifies     [dna:requirement:<ULID>]  (minItems 1)
exercises    dna:design:<ULID>
journey      dna:workflow:<ULID>
state        enum[draft, active, deprecated]
# bitemporal — FROM DAY ONE (this entity is the living-template):
sys_status   enum[active, archived, deleted, purged]  (required)
valid_from   date-time
valid_to     date-time
confidence   number 0..1
x-schema-org-extends: "schema:HowTo"
```

No per-step fields on Scenario — the journey Workflow's Steps already hold
needs/data/credentials (`input_artifacts`, with `deferred:<need>` for a missing
credential) and the asserts (`preconditions`/`postconditions`).

## Two corrections to the prior model (verified against schemas)

1. **TestRun/TestResult re-point is REVERSED from what we said.** The live edge
   is `TestResult.of_run → TestRun` (TestRun does NOT reference TestResult). So the
   re-point is: `TestRun.of_scenario → Scenario` (recommended) + `TestResult.scenario
   → Scenario`, and **`TestResult.verifies → Requirement[]` is RETAINED** — it's the
   *historical per-run assertion*; `Scenario.verifies` is the *evolving definition*.
   Both new fields additive/optional → backward-compatible.
2. **Bitemporal retrofit applies to `Requirement` ONLY, not `Decision`.** Requirement
   is living but lacks `valid_from/valid_to/confidence` (the real gap). Decision is
   correctly an EVENT — it should stay bitemporal-free. Don't over-apply the retrofit.

## Decisions taken (founder pre-authorised "follow your recommendation")

- **`Workflow.type` for a verification journey:** reuse the existing `"review"`
  bucket + `for_process: "verification"` tag (the real discriminator), rather than
  editing the foundation enum. Avoids a foundation change.
- **Re-point edges:** add BOTH `TestRun.of_scenario` and `TestResult.scenario`
  (run records the scenario; result keeps its historical `verifies`).

## Mint plan (cross-repo — the actual mint is a tracked change)

1. **Source ontology** (in the `sulis-ai/plugins` repo, NOT this one — compiled
   here is generated): add `Scenario` to
   `.specifications/business-dna/exemplars/product-development.entities.jsonld`.
2. New compiled `scenario.schema.json` (product-development; 18th entity).
3. Two additive re-point fields: `testrun.of_scenario`, `testresult.scenario`.
4. Emitter: scaffold a `Scenario`-from-source emitter via `add-entity-emitter`
   once an n=2 authoring pattern exists (non-blocking; matches #57–59).
5. Decision Record capturing the four rulings above.
6. Product-development ontology version bump (minor — new entity + additive fields).

## Consumer

The testable-state DoD gate (this change) is `Scenario`'s first consumer: the
gate runs the in-scope `Scenario`s against a standing app → `TestRun`/`TestResult`
→ pass-or-`deferred:<need>`. The manual-tester backlog = the set of `Scenario`s
for a Product; regression = the blast-radius slice.
