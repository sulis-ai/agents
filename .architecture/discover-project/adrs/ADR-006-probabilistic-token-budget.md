---
id: ADR-006
title: Probabilistic-inference token budget — pin at 10k, instrument, revisit v1.1
status: accepted
date: 2026-06-01
deciders: [iain]
resolves: SRD Open Question 3
---

## Context

The Infer phase (Step 5, `propose-configuration-values`) is the only
probabilistic Step in the discover-project Workflow. It calls an LLM
to propose values for Configuration Vocabulary fields the repo can't
unambiguously reveal.

SRD NFR-002 budgets the phase at ≤10,000 tokens (input + output
combined) per discovery run. Exceeding the budget triggers MUC-008
(`token-budget-exceeded`) — fallback to all-human-ask.

The 10k figure is inherited from release-train's NFR-010 (its
CHANGELOG-drafting Step has the same budget). It's a starting estimate
from a sibling workflow, not a number derived from discover-project's
actual usage.

Two alternatives:

- **Pin a different number now.** Reason from first principles —
  Configuration Vocabulary has ~12 fields; an LLM might use ~500-2000
  tokens to read a typical repo summary; output is small; ~5k might
  be enough.
- **No budget; rely on the LLM provider's own limits.** Skip
  NFR-002 enforcement entirely.

The marketplace's stated principle is *cost-conscious LLM use*
(release-train SRD intent). Skipping the budget is incompatible. Pinning
a different number without data is a guess in either direction.

## Decision

**Ship with 10k token budget for v1. Instrument actual usage. Revisit
at v1.1 with observed data.**

The token counter is enforced in `LLMConfigurationInferrer` —
`tokens_consumed` is summed across input + output and checked at the
end of the call (or streamed and checked incrementally to fail fast
on budget exceedance).

The skill emits the actual `tokens_consumed` value as part of the
structured stderr log:

```
[discover-project] Infer phase: proposing N configuration values (tokens used: K / 10,000)
```

After v1 ships, observed `tokens_consumed` values from real discovery
runs (marketplace itself + early adopters) inform the v1.1 calibration:

- If observed median is <5k, tighten to 5k.
- If observed P95 is >10k (frequent fallback to all-human-ask), loosen
  to 15k.
- If observed P95 is <8k and median is <5k, the budget is mostly
  irrelevant — keep at 10k as a defensive ceiling.

The 10k value is a deliberate ceiling, not a target. Most discovery
runs should consume well under it. Triggering the fallback is the
exception, and the fallback (all-human-ask) is itself safe.

## Worked example

A typical first-time discovery on a populated repo:

- Detect produces ~1k tokens of repo summary (manifests, CI workflows).
- The Infer prompt template adds ~500 tokens of structure.
- The LLM returns ~1k-2k tokens of `{field: {value, confidence}}` JSON.
- Total: 2.5k-3.5k tokens. Comfortable margin under 10k.

A pathological case (large monorepo with 50 CI workflow files):

- Detect summary could swell to 5k+ tokens.
- Output is bounded by Configuration Vocabulary's ~12 fields.
- Total could approach 8k-10k. Either lands inside budget or triggers
  fallback — both are safe outcomes.

## Options Considered

- **Ship 10k, instrument, revisit v1.1 (CHOSEN).** Same as
  release-train's stance for its analogous Step. Defensible default.
  Data-driven calibration at v1.1.
- **Pin a smaller number (5k) now** — rejected. First-time-consumer
  pathological cases (large monorepos) might routinely trigger
  fallback; degraded experience without evidence.
- **Pin a larger number (20k+) now** — rejected. Defeats the
  cost-conscious principle; no evidence the smaller budget is too
  tight; opens an attack-surface for prompt-injection cost amplification.
- **No budget** — rejected. Incompatible with the cost-conscious
  principle and the explicit NFR-002 commitment.

## Consequences

- **Positive:** Defensive default that maps to release-train's
  precedent. Instrumentation lets v1.1 calibrate from real data
  rather than guesses. Fallback path (NFR-006) is well-defined and
  safe — going over budget never produces a half-formed entity.
- **Negative:** 10k may be too generous or too tight for some
  discovery runs. v1.1 calibration is the answer. Founder may see
  occasional fallback triggers in v1 that v1.1 fixes.
- **Neutral:** The number is a tuning knob, not a load-bearing
  contract. Changing it in v1.1 is a single constant + a test update.

## Composition

WP-004 (Infer phase) implements the token-budget enforcement and the
fallback path. WP-010 (E2E dogfood) records the observed
`tokens_consumed` for the marketplace's own discovery run as the first
data point.

The v1.1 revisit becomes a follow-up change when enough data has
accumulated (~5-10 real discovery runs).
