---
id: WP-P11
title: "Wire up change origin end to end"
kind: integration
feature: provenance-and-origin
change_id: 01KT500K2JTE2EGW6TPPQ4D4VN
primitive: REINFORCE-Test
group: reinforce
estimate: 2h
blast_radius: low
dependsOn: [WP-P09, WP-P10]
adr: [ADR-012]
verification:
  adapter: frontend
  artifact: "apps/cockpit/client/src/tests/HowThisFileCameToBe.test.tsx"
estimated_token_cost: { input: "~14k", output: "~7k" }
status: pending
observed_acceptance:
  observable_result: "Each file shows a worded origin badge; opening a file shows its diff PLUS a 'How this file came to be' panel that traces to the run (autonomous) or the conversation (assisted); inferred origins honestly say so."
  how_observed: "Run the cockpit against a change with autonomous + assisted commits. Open Files. OBSERVE the badge per row. Open an autonomous file → trace to the run-log; open an assisted file → trace to the Turn Card + 'Open conversation'. OBSERVE the honesty banner on inferred origins."
  not_sufficient: "Green CI alone does NOT satisfy the DoD — only driving the app and seeing the badges + traces does."
---

## Context
Swap the WP-P10 mock for the real WP-P09 inferred backend (CF-07). The
observable origin round-trip (inferred). Stamping (P12) + recorded (P13) follow.

## Definition of Done
### Red
- [ ] Frontend still on the WP-P08 mock.
### Green
- [ ] Mock swapped for real `/api/changes/:id/origin`; contract conformance passes (CF-07).
- [ ] Badges + panel + lens drive from real inferred origins; full suite green; gate green.
### Blue
- [ ] **OBSERVED:** badges per row + the open-file trace to run-log / Turn Card, honesty banner on inferred (the `observed_acceptance`).
- [ ] No caller-side reshaping (CF-06).
