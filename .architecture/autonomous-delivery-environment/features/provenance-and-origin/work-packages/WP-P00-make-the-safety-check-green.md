---
id: WP-P00
title: "Make the safety check green again (reconcile the read-only gate + fix the failing test harness)"
kind: backend
feature: provenance-and-origin
change_id: 01KT500K2JTE2EGW6TPPQ4D4VN
primitive: REINFORCE-Gate
group: reinforce
estimate: 4h
blast_radius: low
dependsOn: []
adr: [ADR-015]
verification:
  adapter: backend
  artifact: "apps/cockpit/server/tests/read-only-inventory.test.ts"
estimated_token_cost: { input: "~25k", output: "~12k" }
status: pending
---

## Context

The read-only gate (`apps/cockpit/scripts/check-read-only.sh` +
`server/tests/read-only-inventory.test.ts` + `check-read-only-script.test.ts`)
is **currently RED on this branch** — four violations (ADR-015). Plus the
pending test-harness fix: `useChatStream` / skeleton / inventory tests are not
wrapped in a `QueryClientProvider` and throw on `useQueryClient` (task #21).
This WP greens the safety check and the suite so the whole feature set ships on
a clean base. It is a **gate reconciliation, not a rewrite**: keep the gate,
add named + audited path-scoped exceptions per ADR-015.

## Contract (what this WP changes)

- `scripts/check-read-only.sh` — add an **operator-action** exception class:
  allow-list `server/routes/advanced.ts` (its two POST routes) and
  `server/lib/changeAdvanced.ts` (its non-zero `process.kill`); allow-list
  `server/lib/turnSummaries.ts` (its `writeFile` cache + `spawn("claude")`).
  Each documented in `--explain`.
- `server/tests/read-only-inventory.test.ts` + `check-read-only-script.test.ts`
  — parallel assertions that **exactly** these files are exception-listed; any
  other file with a write / non-zero signal / process-start / POST still fails.
- Test harness: wrap the `useChatStream` / skeleton / inventory client tests in
  a shared `QueryClientProvider` test helper (task #21).

## Definition of Done

### Red
- [ ] A test asserting `check-read-only.sh` exits 0 **fails** today (gate is red).
- [ ] The `useChatStream`/skeleton/inventory tests **fail** today on `useQueryClient`.

### Green
- [ ] `bash apps/cockpit/scripts/check-read-only.sh` exits **0** — clean scan.
- [ ] `read-only-inventory.test.ts` asserts the exact operator-action +
      summary-cache exception set; a synthetic new write in any other file still
      trips the gate (negative test).
- [ ] The client test suite passes (QueryClientProvider wrap added via a shared
      `renderWithClient` helper, not per-test duplication).
- [ ] The full cockpit test suite is green.

### Blue
- [ ] The QueryClientProvider wrap is a **single shared test helper** (EP-03 — no
      copy-paste across the three test files).
- [ ] The gate's `--explain` text documents each exception + rationale (ADR-015).
- [ ] No new exception beyond the four named in ADR-015; the diff to the gate is
      minimal and audited.

## Founder call folded in
ADR-015 recommends **keep-the-gate-with-named-exception**. If the founder
prefers **remove "stop a process"** instead, this WP drops the
`changeAdvanced.ts` kill + the `/stop` route rather than allow-listing them.
