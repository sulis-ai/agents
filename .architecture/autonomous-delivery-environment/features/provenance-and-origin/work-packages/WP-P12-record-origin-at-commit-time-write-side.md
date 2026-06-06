---
id: WP-P12
title: "Record origin exactly at commit time (executor + chat write paths)"
kind: backend
feature: provenance-and-origin
change_id: 01KT500K2JTE2EGW6TPPQ4D4VN
primitive: EXPAND-Create
group: expand
estimate: 5h
blast_radius: medium
dependsOn: [WP-P08]
adr: [ADR-013]
verification:
  adapter: backend
  artifact: "tests for the executor/relay stamp writer (path TBD by where the commit step lives)"
  deferred-to-follow-on: fixture-stampable-commit
estimated_token_cost: { input: "~24k", output: "~14k" }
status: pending
observed_acceptance:
  observable_result: "A real autonomous commit carries a 'Sulis-Origin: autonomous; run=…' trailer; a real assisted (chat-relay) commit carries 'Sulis-Origin: assisted; conversation=…; turn=…'. A stamp failure leaves the commit intact."
  how_observed: "On the founder machine: run a real executor commit and a real chat-relay commit; `git log --format=%B` shows the Sulis-Origin trailer on each. Force a stamp failure; OBSERVE the commit still lands and origin falls back to inferred."
  not_sufficient: "Unit tests + CI alone do NOT satisfy the DoD — a real executor/relay commit on the founder machine must show the trailer."
  human_hops: "Founder machine — a real executor run + a real relay commit; cannot fully bootstrap in CI."
---

## Context
Origin-stamping (ADR-013) — **outside `apps/cockpit/`**, in the executor's and
the chat-relay's existing commit step. Append-only commit-trailer metadata; no
new commit, no process, no network; **stamp failure is non-fatal** (commit
lands, origin stays inferred). This is what turns inference (P09) into recorded
fact (P13). **No cockpit read-only gate change** (it lives in the write paths).

## Contract (the code this WP adds)
- A `stampOrigin(commitRef, origin)` writer using a **git commit trailer**
  (`Sulis-Origin: …`, the established trailer convention — CP-01); **sidecar
  fallback** `.sulis/origin/<sha>.json` where a trailer can't be written.
- Hook it into the **executor** commit (autonomous + run-ulid + confidence) and
  the **chat-relay** commit (assisted + conversation + turn).
- A structured log line per stamp (`{sha, origin, ref, outcome: stamped|skipped}`); never the message text.

## Definition of Done
### Red
- [ ] A test asserting an executor commit carries a `Sulis-Origin: autonomous` trailer **fails** (writer absent).
### Green
- [ ] The executor stamp writes `Sulis-Origin: autonomous; run=<ulid>; confidence=<n>`; the relay writes `Sulis-Origin: assisted; conversation=<id>; turn=<n>` (unit, against `fixture-stampable-commit`).
- [ ] **Stamp-failure-is-non-fatal:** a simulated failure leaves the commit intact and origin falls back to inferred (graceful degradation).
- [ ] No new write/process inside `apps/cockpit/`; the cockpit gate stays green.
### Blue
- [ ] **OBSERVED on the founder machine:** a real autonomous + a real assisted commit each carry the trailer (the `observed_acceptance`).
- [ ] Trailer/sidecar shape matches the WP-P08 pinned constant (CF-11).
- [ ] No secret/PII in the stamp (ulid/id/confidence only — TDD §3.4).

## Founder call folded in
ADR-013 recommends the **commit trailer**. If the founder prefers commit
messages untouched, this WP ships the **sidecar-only** variant
(`.sulis/origin/<sha>.json`, no trailer).
