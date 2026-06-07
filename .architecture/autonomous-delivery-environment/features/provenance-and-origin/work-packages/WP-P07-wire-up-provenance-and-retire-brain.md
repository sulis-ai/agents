---
id: WP-P07
title: "Wire up Provenance end to end + retire the old Brain view"
kind: integration
feature: provenance-and-origin
change_id: 01KT500K2JTE2EGW6TPPQ4D4VN
primitive: CONTRACT-Delete
group: contract
estimate: 2h
blast_radius: medium
dependsOn: [WP-P05, WP-P06]
adr: [ADR-011, ADR-014]
verification:
  adapter: frontend
  artifact: "apps/cockpit/client/src/tests/ProvenanceView.test.tsx"
estimated_token_cost: { input: "~16k", output: "~8k" }
status: pending
observed_acceptance:
  observable_result: "Opening a change shows Provenance (not Brain) in the nav; the dashboard gives the trust digest in ~10s; the run-log and coverage-map open from it; the old flat Brain view is gone."
  how_observed: "Run the cockpit against a change with real runs + entities. Open the change → Provenance. OBSERVE the four tiles incl. a real flagged gap; open the run-log (runs→steps→detail) and the coverage-map (Why/What/How/Tested + a focused trace). Confirm the old Brain view no longer appears."
  not_sufficient: "Green CI alone does NOT satisfy the DoD — only driving the app and seeing the dashboard + both lenses does."
---

## Context
Swap the WP-P06 mock for the real WP-P05 backend (CF-07), rename Brain →
Provenance in nav + route, and **deprecate-then-delete** the flat
`BrainView.tsx` + `BrainSection.tsx` front door (ADR-014). The `…/brain`
endpoint + `readBrain` **stay** (the projection composes them).

## Definition of Done
### Red
- [ ] Frontend still on the mock; `BrainView` still wired as the front door.
### Green
- [ ] Mock swapped for real `/api/changes/:id/provenance`; contract conformance passes (CF-07).
- [ ] Nav + route renamed Brain → Provenance; header reads "Provenance — what Sulis did, and why".
- [ ] `BrainView.tsx` + `BrainSection.tsx` removed; the quiet "Browse everything" link (if kept) reuses the grouped-list rendering internally, not the old front door (ADR-014).
- [ ] Full suite green; the read-only gate stays green.
### Blue
- [ ] **OBSERVED:** the dashboard + run-log + coverage-map drive correctly against real data (the `observed_acceptance`).
- [ ] No dead Brain code left behind (deprecate-then-delete complete; change-primitives MUST).
- [ ] `…/brain` endpoint retained and still tested (composed by the projection).
