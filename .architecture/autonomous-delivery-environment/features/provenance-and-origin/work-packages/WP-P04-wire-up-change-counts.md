---
id: WP-P04
title: "Wire up the change-counts end to end"
kind: integration
feature: provenance-and-origin
change_id: 01KT500K2JTE2EGW6TPPQ4D4VN
primitive: REINFORCE-Test
group: reinforce
estimate: 1h
blast_radius: low
dependsOn: [WP-P02, WP-P03]
adr: [ADR-010]
verification:
  adapter: backend
  artifact: "apps/cockpit/server/tests/routes.changed.test.ts"
estimated_token_cost: { input: "~12k", output: "~5k" }
status: pending
observed_acceptance:
  observable_result: "In the running app, every changed-file row shows +N −N, folders show the rolled-up total, and a binary file shows no count."
  how_observed: "Run the cockpit against a change with edits + an added file + a binary file. Open Files → Changed. OBSERVE +N −N per row, folder rollups, and no count on the binary file."
  not_sufficient: "Green CI alone does NOT satisfy the DoD — only driving the app and seeing the counts does."
---

## Context
Swap the WP-P03 mock for the real WP-P02 backend and run the contract-conformance
check (CF-07). The first observable files round-trip of this set.

## Definition of Done
### Red
- [ ] The frontend still points at the WP-P01 mock.
### Green
- [ ] Mock swapped for the real `/api/changes/:id/changed`; counts render from real numstat.
- [ ] Contract conformance: the real response validates against the WP-P01 schema; the consumer's expectations hold against real responses.
### Blue
- [ ] **OBSERVED:** the app, driven, shows real `+N −N` + folder rollups + binary-no-count (the `observed_acceptance`).
- [ ] No caller-side reshaping leaked in to "make it fit" (CF-06).
