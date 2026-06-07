---
id: WP-P05
title: "Build the Provenance read: digest, run-log, coverage (backend)"
kind: backend
feature: provenance-and-origin
change_id: 01KT500K2JTE2EGW6TPPQ4D4VN
primitive: EXPAND-Create
group: expand
estimate: 6h
blast_radius: low
dependsOn: [WP-P01]
adr: [ADR-011]
verification:
  adapter: backend
  artifact: "apps/cockpit/server/tests/routes.provenance.test.ts"
  deferred-to-follow-on: seed-brain-entities-fixture
estimated_token_cost: { input: "~28k", output: "~16k" }
status: pending
---

## Context
The Provenance read projection over the existing brain tree (ADR-011) — digest
tiles + run-log + coverage + the per-requirement focused trace. Reads real
`lifecyclerun` fields (`outcome`, `confidence`, `_step_runs`, `_gaps`,
`_self_critique`, `_final_verdict`, `at`) — verified against real instances.
Producer side; parallel with WP-P06 (CF-05).

## Contract (the code this WP adds)
- `lib/readProvenance.ts` — compose `readBrain` + classify entities into the
  digest (did/covered/decided/flagged) + the run-log (runs→`_step_runs`) + the
  four coverage columns. **Flagged** surfaces a real `_gaps[].claim`/`reason` +
  `_self_critique`.
- `lib/provenanceEdges.ts` — pure edge resolver over `detail`
  (design.satisfies→requirement, design.decisions→decision,
  scenario.verifies→requirement, scenario.exercises→design,
  testresult.of_run/verifies/outcome) producing a `FocusedTrace` for one requirement.
- `routes/provenance.ts` — `GET /api/changes/:id/provenance` (+ `?focus=<reqId>`
  for the focused trace). GET-only; reading it starts **no** `claude` process.

## Definition of Done
### Red
- [ ] `readProvenance.test.ts` + `provenanceEdges.test.ts` **fail** (libs absent).
### Green
- [ ] Digest counts correct over `seed-brain-entities-fixture` incl. ≥1 real `lifecyclerun`; **flagged** shows a real gap + self-critique.
- [ ] Run-log: runs ordered by `at`, each with its `_step_runs` detail.
- [ ] Coverage: Why/What/How/Tested columns; `?focus=` returns one requirement's resolved trace.
- [ ] `routes.provenance.test.ts`: 200 happy, 200 empty-brain dashboard, 404 unknown; **no** process start on read (NFR-SEC-05 parity).
- [ ] Fail-soft: malformed run skipped; dangling edge omitted, never throws.
### Blue
- [ ] Composes `readBrain` — no new store, no second brain walk (ADR-011, EP-03).
- [ ] Edge resolve is a pure function (testable in isolation; boring-code).
- [ ] Conforms to WP-P01 shapes verbatim (CF-06).

## Deferred infra
`seed-brain-entities-fixture` (incl. ≥1 real `lifecyclerun` with `_gaps`/`_self_critique`) — deferred upstream by the parent change; this WP needs the run-bearing variant.
