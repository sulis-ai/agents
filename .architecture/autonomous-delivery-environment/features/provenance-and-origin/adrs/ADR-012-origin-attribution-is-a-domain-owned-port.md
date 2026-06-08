# ADR-012 — Change origin is a domain-owned port with inferred + recorded adapters

- **Status:** accepted
- **Date:** 2026-06-05
- **Change:** CH-01KT50 · feature: provenance-and-origin
- **Deciders:** SEA

## Decision

Change-origin attribution is a **domain-owned port** `OriginAttribution`
(`originFor(change, path?) → Origin`), with **two adapters satisfying one
contract test**:

- **`InferredOriginAttribution`** (now) — correlates a file's last-changing
  commit (author / timestamp / message) to either a `lifecyclerun` window
  (→ `{ kind: "autonomous", run, confidence }`) or a conversation turn
  (→ `{ kind: "assisted", conversation, turn, summary }`), else
  `{ kind: "unknown" }`. Every result carries `confidence: "inferred"`.
- **`RecordedOriginAttribution`** (after stamping, ADR-013) — reads the
  `Sulis-Origin:` commit trailer / sidecar and returns the exact origin with
  `confidence: "recorded"`. A recorded origin **overrides** inference.

`Origin` is a discriminated union on `kind` (`autonomous` / `assisted` /
`unknown`) carrying `confidence: "inferred" | "recorded"`. Served by
`GET /api/changes/:id/origin` (optional `?path=`).

## Why this is the convention

This is the cockpit's established **ports-and-adapters** pattern (parent §2.1,
MEA-01): the public face is the cockpit's own port; the `git log` / trailer
reads are *called by* the adapter — **EXPAND-Create, not SUBSTITUTE-Wrap**. Two
adapters sharing **one contract test** is the cockpit's existing fake-vs-adapter
parity discipline, which guarantees the inferred and recorded paths are
behaviourally interchangeable from the consumer's view. The badge can flip
inferred → recorded with zero UI change.

## Alternatives considered

- **Inline the correlation in the route (rejected).** Couples the inference
  logic to HTTP; can't swap to the recorded adapter without rewriting the route;
  no shared contract test. The port is the seam that makes inferred→recorded a
  swap, not a rewrite.
- **Only build the inferred path now, design the recorded one later (rejected).**
  Designing the contract once, now, is what lets stamping (ADR-013) drop in as a
  second adapter against the same test. Deferring the contract invites a second,
  divergent shape at integration time (the anti-pattern CF-01 exists to prevent).
- **A single adapter that does both (rejected).** Mixes two data sources behind
  one class; the "recorded overrides inferred" rule is clearer as a thin
  composing adapter or a route-level precedence over two clean adapters.

## Consequences

- One new port, two adapters, one shared contract test, one GET endpoint, one
  pure correlation lib. `Origin` shapes pinned in WP-P08.
- The honesty property (ADR — never present inference as fact) is enforced by
  the always-present `confidence` field (§3.3 of the TDD).
