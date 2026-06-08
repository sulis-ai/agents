---
id: WP-P09
title: "Work out each file's likely origin (backend, inferred)"
kind: backend
feature: provenance-and-origin
change_id: 01KT500K2JTE2EGW6TPPQ4D4VN
primitive: EXPAND-Create
group: expand
estimate: 6h
blast_radius: low
dependsOn: [WP-P08]
adr: [ADR-012]
verification:
  adapter: backend
  artifact: "apps/cockpit/server/tests/correlate.test.ts"
  deferred-to-follow-on: recording-origin-correlation-fixture
estimated_token_cost: { input: "~28k", output: "~16k" }
status: pending
---

## Context
The `InferredOriginAttribution` adapter + the pure correlation: a file's
last-changing commit (author/timestamp/message, read via the ONE git site) ↔
a `lifecyclerun` window (→ autonomous) OR a conversation turn timestamp (→
assisted), else unknown. Every result is `attribution: "inferred"`. Producer
side; parallel with WP-P10 (CF-05).

## Contract (the code this WP adds)
- `lib/originAttribution/correlate.ts` — pure: given commit {author, at, message},
  the change's runs ({runId, at, outcome, confidence}), and conversation turns
  ({turn, at, summary}) → an `Origin`. Rules: commit-in-run-window →
  autonomous+run+confidence; commit-near-turn (and bot/relay author signal) →
  assisted+turn; neither → unknown. **A recorded trailer present → defer to
  recorded (P13)** — correlation is the fallback only.
- `adapters/InferredOriginAttribution.ts` — implements `OriginAttribution`;
  reads last-changing commit via the git site, runs via `readBrain`, turns via
  `groupTurns`/`turnSummaries`; calls `correlate`.
- `routes/origin.ts` — `GET /api/changes/:id/origin` (+ `?path=`); GET-only; no process start.

## Definition of Done
### Red
- [ ] `correlate.test.ts` + `OriginAttribution.contract.test.ts` **fail** (code absent).
### Green
- [ ] `correlate`: commit-in-run-window → autonomous+confidence; near-turn → assisted+turn-ref; neither → unknown; recorded-present → recorded wins.
- [ ] `InferredOriginAttribution` passes the **shared** `OriginAttribution.contract.test.ts` (the same suite P13's recorded adapter will pass).
- [ ] `routes.origin.test.ts`: 200 change-level + `?path=` file-level; `attribution:"inferred"` present; 404 unknown.
- [ ] Fail-soft: missing commit/run/turn → unknown, never an error.
### Blue
- [ ] `correlate` is a pure function (no I/O; boring-code; testable in isolation).
- [ ] Reads commits via the ONE git site (no new spawn; gate stays green).
- [ ] Conforms to WP-P08 shapes verbatim (CF-06).

## Deferred infra
`recording-origin-correlation-fixture` — commits + runs + turns with known-true origins, so inference accuracy is measurable.
