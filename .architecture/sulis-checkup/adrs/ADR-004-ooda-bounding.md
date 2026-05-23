---
id: ADR-004
title: OODA per tier — bounded at 3 cycles, with cycle-2/3 entry conditions
status: accepted
date: 2026-05-23
deciders: [iain, sea-architect-agent]
---

## Context

Each tier runs an OODA loop internally (find → assess → evaluate → decide).
Without a bound, the loop can iterate indefinitely refining its assessment.
With too tight a bound, the loop fails to spot cross-primitive patterns.

The `sulis-security:codebase-assess` framework (the existing precedent)
calibrates at **3-5 cycles for code-only, 5-7 cycles with a deployed URL**.
The checkup must bound its loop similarly but tighter — the checkup runs
all seven tiers, so an unbounded loop per tier multiplies cost.

## Decision

**Bound per-tier OODA at max 3 cycles.** Cycle 1 always runs. Cycle 2
fires only if Cycle 1 verdict is `partial` AND the additional probe is
cheap (no new LLM call — only re-reading existing tool output with new
criteria, or running an additional deterministic tool). Cycle 3 reserved
for cross-primitive chaining (e.g. a tier-2 finding refines a tier-4
query).

When the bound is reached without a clean verdict, the tier's terminal
state is `stopped_by_iteration_exhausted` (borrowed from kinds-and-tools
FR-9). The verdict in that case is `partial` with a finding that names
the unresolved question.

## Options Considered

### Option A — Single cycle per tier (no OODA loop) (rejected)

**Pros:** simplest. Cheapest. Most predictable runtime.

**Cons:**
- Loses the cross-primitive chaining that's the whole point of an OODA
  approach. A tier-2 finding ("hardcoded credential in `cache.py`")
  could refine a tier-4 query ("now check if `cache.py` is on the
  critical path") if a second cycle existed.
- Forces every primitive to be hyper-thorough on cycle 1, which means
  every primitive does work that may not be needed.

**Rejected because:** the chaining is the value. The existing
sulis-security framework calibrated 3-5 cycles for a reason.

### Option B — Bound at 5 cycles (per sulis-security default) (rejected)

**Pros:** matches existing precedent. Familiar to security-reviewer
contributors.

**Cons:**
- Checkup runs *seven* tiers. 5 cycles per tier × 7 tiers = up to 35
  cycle-iterations per checkup run. Each cycle includes some LLM
  classification cost. The bill adds up.
- sulis-security calibrates 5 for **security depth in one category**;
  checkup is **breadth across seven categories**. Different shape.

**Rejected because:** the dimensions are different.

### Option C — Bound at 3 cycles with cycle-2/3 entry conditions (chosen)

**Pros:**
- Cap total cycle-iterations at 21 (7 tiers × 3 cycles) worst case.
  In practice most tiers terminate at cycle 1 with a clean verdict;
  worst case is realistic to ~12 cycle-iterations.
- Cycle 1 covers the bulk of tiers (mechanical primitive output is
  usually conclusive).
- Cycle 2 reserved for partial-verdict refinement (the "look closer"
  iteration), gated to cheap work.
- Cycle 3 reserved for cross-primitive chaining (the "consider tier-2
  evidence in tier-4 query" iteration). Expensive but high-value when
  fired.

**Cons:**
- Calibration is somewhat arbitrary. 3 is a guess that should be
  validated empirically.

**Accepted because:** matches the spirit of the existing OODA framework
while respecting the breadth-not-depth dimension of checkup. Bounds can
be relaxed if empirical evidence shows 3 is too tight.

## Cycle entry conditions

| Cycle | Always | Sometimes | Never |
|---|---|---|---|
| 1 | always | — | — |
| 2 | — | when cycle-1 verdict is `partial` AND additional probe is cheap (re-read existing tool output with new criteria, or run additional deterministic tool) | when cycle-1 verdict is `pass` or `fail` (no point); when additional probe requires fresh LLM call |
| 3 | — | when cycle-2 surfaced a finding that meaningfully changes a higher-tier query | when no cross-tier chaining is plausible from accumulated state |

Cycle 3 firing is rare. Most expected: a tier-2 access-control finding
in module M → cycle 3 in tier 4 refines its FMEA scope to focus on M.

## Bound enforcement

The bound is a hard cap in the LangGraph node logic:

```python
def tier_decide_node(state: CheckupState) -> dict:
    tier_state = state["tiers"][current_tier_id]
    if tier_state["ooda_cycle"] >= 3:
        return {"tier_verdict": "partial",
                "terminal_reason": "iteration_exhausted"}
    # ... regular decide logic
```

Empirical calibration plan: after first 20 real checkup runs, count
cycle distribution. If > 80% of tiers terminate at cycle 1, the bound
is fine. If > 5% hit the cycle-3 cap, consider raising to 4.

## Why this isn't just a counter

The bound is a counter. The interesting question is *what gates entry to
each cycle*. Without entry conditions, the loop runs the full 3 cycles
even when cycle 1 is conclusive — wasteful. The entry conditions are the
real load-bearing part of this decision.

## Consequences

**Positive:**
- Predictable cost ceiling.
- Cross-primitive chaining is possible (via cycle 3) without becoming
  the default.
- Cycle-1-only termination (the common case) keeps fast runs fast.

**Negative:**
- Some genuinely-hard assessments may hit the cap. The `partial` +
  `iteration_exhausted` terminal exposes this honestly rather than
  hiding it.
- Calibration is empirical. The first 20 runs may surface "we set this
  too tight" or "too loose".

**Neutral:**
- Bound matches the structure of the kinds-and-tools `max_iterations`
  pattern; contributors familiar with that pattern will recognise the
  shape.
