---
title: UC-flow-coverage is a third companion gate, not a rewrite
status: accepted
kind: adr
---

# ADR-004 — UC-flow-coverage is a third companion gate, not a rewrite

## Context

FR-12 requires a UC-flow-coverage gate that blocks a change if any
main/alternate/exception flow of any in-scope use case has no covering
scenario. FR-13 requires it to be a **companion** to the scenario-required
gate (#103, `_scenario_required_gate.py`) and the journey-coverage gate (#86,
`_verify_scenario_coverage.py`) — all three apply, each can independently
block. C-05 requires coverage to reuse the brain as objective source of truth;
NFR-S04 requires fail-closed; NFR-D01 requires brain-sourced verdicts.

The existing `_verify_scenario_coverage.py` classifies coverage per *scenario*
within a journey (green/planned/out-of-scope/GAP). It has no UC-flow dimension
(it cannot tell an exception flow has no scenario) and no surface dimension.
The GLOSSARY ("NOT the Same As") establishes that journey-coverage checks
*hops within a scenario's journey* while UC-flow-coverage checks *a scenario
exists per flow* — neither subsumes the other.

## Decision

Build `_verify_uc_flow_coverage.py` as a **new, third companion gate** — not a
modification of `_verify_scenario_coverage.py`. It enumerates every UC flow
(main + alternate + exception), maps each to its covering scenario(s) via the
brain (NFR-D01), and returns `covered`/`gaps` with a fail-closed default
(NFR-S04: an uncovered flow with no out-of-scope record is a gap). It reuses
the existing brain query helpers (`find_scenarios_for_journey`,
`find_passing_testresults_for_scenario`) for consistency with #86 (C-05). The
three gates run on every behavioural change; each can independently block
(FR-13). Logic stays distinct; reporting unifies (BDR-002).

## Options Considered

- **New third gate, distinct logic, shared brain helpers (CHOSEN).** Honours
  FR-13's "companion, not replacement"; each gate's blocking semantics stay
  independent and auditable; no risk of regressing #86's existing behaviour.
- **Add a UC-flow dimension inside `_verify_scenario_coverage.py`** — rejected:
  conflates two distinct checks (hops-within-scenario vs scenario-per-flow);
  one verdict would hide which check failed; regresses the #86 contract.
- **A single mega-gate replacing all three** — rejected: violates FR-13;
  collapses three independently-meaningful verdicts into one; the founder loses
  the ability to see *which* discipline a change failed.

## Consequences

- **Positive:** the happy-path-only bypass (MUC-03) and silent-flow-drop
  (MUC-04) are caught at flow granularity; #86 is untouched; fail-closed by
  construction. Fast (NFR-03: < 3 s combined for ≤ 20 flows).
- **Negative:** three gates can produce three verdicts — gate fatigue risk
  (pre-mortem 3); mitigated by BDR-002's unified rollup.
- **Neutral:** the UC flow inventory must be enumerable — the comprehensive
  document's §6 use-case flows (always present post-ADR-002) are that source.
