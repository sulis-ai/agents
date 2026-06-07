---
id: WP-P13
title: "Read the recorded origin (exact, replaces inferred)"
kind: backend
feature: provenance-and-origin
change_id: 01KT500K2JTE2EGW6TPPQ4D4VN
primitive: EXPAND-Create
group: expand
estimate: 3h
blast_radius: low
dependsOn: [WP-P12]
adr: [ADR-012, ADR-013]
verification:
  adapter: backend
  artifact: "apps/cockpit/server/tests/RecordedOriginAttribution.test.ts"
  deferred-to-follow-on: fixture-stamped-commits
estimated_token_cost: { input: "~18k", output: "~9k" }
status: pending
observed_acceptance:
  observable_result: "For a file whose commit carries a Sulis-Origin trailer, the badge reads the exact origin with NO 'likely' hedge and NO honesty banner (it's recorded, not inferred). Files without a trailer still fall back to inferred."
  how_observed: "Run the cockpit against stamped commits (from WP-P12 on the founder machine). Open Files. OBSERVE the badge on a stamped file reads recorded (no hedge); an unstamped file still reads inferred (with hedge)."
  not_sufficient: "Green CI alone does NOT satisfy the DoD — only driving the app against real stamped commits and seeing the hedge drop does."
---

## Context
The `RecordedOriginAttribution` adapter (ADR-012) — reads the `Sulis-Origin:`
trailer / sidecar (from WP-P12) and returns the exact origin with
`attribution: "recorded"`. It passes the **same** `OriginAttribution.contract.test.ts`
the inferred adapter (P09) passes (fake-vs-adapter parity). Recorded **overrides**
inferred at the route (ADR-012), so the badge flips inferred → recorded with **no
UI change** (the frontend already keys off `attribution`).

## Contract (the code this WP adds)
- `adapters/RecordedOriginAttribution.ts` — read the trailer (via the ONE git
  site `git log`/`interpret-trailers` read) or the sidecar; map to `Origin` with
  `attribution: "recorded"`.
- `routes/origin.ts` — precedence: recorded-if-present, else inferred (compose
  the two adapters; recorded wins).

## Definition of Done
### Red
- [ ] `RecordedOriginAttribution.test.ts` **fails** (adapter absent).
### Green
- [ ] The recorded adapter passes the **shared** `OriginAttribution.contract.test.ts` (same suite as P09).
- [ ] Reads `Sulis-Origin:` trailer + sidecar from `fixture-stamped-commits`; maps to `attribution:"recorded"`.
- [ ] Route precedence: a stamped file → recorded; an unstamped file → inferred (P09 fallback).
### Blue
- [ ] **OBSERVED:** the hedge/banner drops on a recorded file; an unstamped file still reads inferred (the `observed_acceptance`).
- [ ] Trailer read uses the ONE git site (no new spawn; gate green).
- [ ] No UI change needed — `attribution` already drives the badge (ADR-012 — the swap property).
