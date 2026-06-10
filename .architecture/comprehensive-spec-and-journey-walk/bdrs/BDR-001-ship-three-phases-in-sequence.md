---
title: Ship the three phases in sequence (P1 decouple → P2 two-surface walk → P3 round-out)
status: accepted
kind: bdr
---

# BDR-001 — Ship the three phases in sequence (P1 → P2 → P3)

## Context

The change spans three phases (SRD §Summary): P1 decouple depth from
doc-existence; P2 two-surface walk + UC-derived scenarios + UC-flow-coverage
gate; P3 STRIDE + C4 + BDR + interface contract. They have a natural dependency:
the two-surface walk (P2) walks the use-case flows and the contract that the
always-comprehensive document (P1) and the contract section (P3) produce; the
UC-flow-coverage gate (P2) enumerates the UC flows the comprehensive document
(P1) carries. This is a sequencing/scope decision — business, not technical —
about what order to deliver value and where to cut a phase boundary if needed.

## Decision

Ship the phases **in sequence: P1 → P2 → P3**. P1 is the foundation (always-on
comprehensive document with use-case flows) — without it the UC-flow gate (P2)
has no flows to enumerate and the contract section (P3) has no document to live
in. P2 builds on P1's flows + document. P3 rounds out the document P1
established. Each phase is independently shippable and independently reversible
(§9.2 rollback), so a phase boundary is a safe pause point if scope or time
demands it. The phase boundaries are also the natural Work-Package slice
boundaries `/sulis:plan-work` will use.

## Options Considered

- **Sequential P1 → P2 → P3 (CHOSEN).** Respects the dependency; each phase
  ships value; safe pause points; clean WP slices.
- **All three at once (big-bang)** — rejected: a single large change with no
  intermediate shippable value; harder to review; the PR-hygiene size signal
  fires; no safe pause point.
- **P3 (STRIDE/C4/BDR) first as "cheap doc wins"** — rejected: the contract
  section (P3) depends on the always-comprehensive document (P1) existing to
  live in, and the contract is the source the P2 tool-walk reads — ordering P3
  first strands it without its consumers.

## Consequences

- **Positive:** intermediate value at each phase; safe pause points; WP slices
  fall out of the phase boundaries; the dependency is honoured.
- **Negative:** the full value (rounded-out doc + two-surface proof) isn't
  realised until P3 lands; founders on P1 only get the always-on document
  without the second-surface proof yet.
- **Neutral:** the phase order matches the SRD's own three-phase framing, so no
  re-framing for the founder.
