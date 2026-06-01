---
id: ADR-005
title: Follow-on auto-draft triggers at slice-end review, not immediately
status: accepted
change_id: 01KT2BPBFESCCDY8F7Y5M8RN4R
date: 2026-06-01
resolves: SRD Open Question 5
---

# ADR-005 — Follow-on auto-draft triggers at slice-end review, not immediately

## Decision

The auto-draft of a follow-on change for a repeated deferred infrastructure
need fires at **slice-end review**, not at the moment a second design flags
the same need. The slice-end review:

1. Scans every change in the slice for `Infrastructure needs surfaced
   (deferred)` entries.
2. Tallies entries by canonical need identifier.
3. Auto-drafts one follow-on change per identifier flagged by 2+
   designs in the slice.
4. Surfaces singletons (flagged by exactly one design) to the founder
   for explicit defer-or-draft disposition.

The scan is idempotent — running it twice over the same slice produces
one follow-on, not two.

## Context

SRD Open Question 5 surfaced the timing choice:

- (a) Fire immediately on the 2nd flag (real-time auto-draft).
- (b) Wait for slice-end (batched).

Two arguments push toward (b):

1. **Aligns with the existing slice-end review pattern.** The
   marketplace already has a slice-end review (referenced in
   `lifecycle.md`, used by the concierge), and it already surfaces
   follow-on opportunities to the founder for disposition. Adding a
   real-time auto-draft would introduce a second, parallel mechanism
   for the same concept (auto-drafting follow-ons) without any
   distinguishing rationale — extra surface, drift risk.

2. **Founder load.** Real-time auto-drafts mid-design would interrupt
   the design conversation. The founder is in the middle of running
   `/sulis:specify` when, somewhere in the background, a previously-
   deferred need ticks over to its 2nd flag and a follow-on
   auto-drafts. That's noise during a moment when the founder needs
   focus on the current design. Batched at slice-end means the
   founder consumes auto-drafts as one decision-batch, not as
   interruptions.

The cost of waiting is bounded: at most one slice-cycle of delay (the
existing slice cadence). That delay is shorter than the time-to-build
of any of the actual follow-on infrastructure (test OAuth pipeline,
recording mocks, etc.), so it does not move the critical path.

## Alternatives considered

1. **Real-time on 2nd flag (rejected).** Reasons above.
   Additionally: real-time would require the agent that adds the
   deferred entry (during `/sulis:specify`) to also know about the
   global tally of needs across the slice. That's a wider read
   surface than the agent currently has and would require additional
   coupling (slice-tracking infrastructure) that this change
   explicitly tries to avoid.

2. **Manual trigger only — never auto-draft (rejected).** Removes
   the "design-side surfaces needs to infrastructure-side"
   feedback loop that the founder explicitly described as the
   second half of the two-sides-of-coin framing. Manual trigger
   defeats the loop — needs would accumulate without being acted on.

3. **Fire after N changes flag the same need, where N is configurable
   (rejected).** Adds a knob with no clear default. N=2 is the
   simplest threshold that still distinguishes "real recurring need"
   from "singleton". Configurability defers a decision the rubric
   already makes for us.

## Idempotency mechanism

The auto-draft logic checks for an existing follow-on with the same
canonical need identifier before drafting. Specifically:

```pseudocode
def auto_draft_follow_on(need_id: str, slice_id: str) -> None:
    existing = find_change_record(
        change_kind="infrastructure",
        infrastructure_need=need_id,
        status=["draft", "designed", "decomposed", "in-progress"]
    )
    if existing:
        return  # idempotent: already drafted
    create_change_record(...)
```

This makes the scan safe to run multiple times within a slice (debugging,
manual re-runs) and safe to run again next slice (already-drafted
follow-ons aren't redrafted).

## Singleton surfacing

For an identifier flagged by exactly one design, the slice-end review
emits a founder-facing prompt:

> *Change A's verification plan flagged 'recording-mock-sendgrid' as a
> needed piece of infrastructure. So far only this one design has
> flagged it. Defer further (wait to see if another design flags it
> next slice) or draft as a follow-on now?*

Founder responds per-need. *Defer further* re-enters next slice's scan
input. *Draft now* triggers the same auto-draft path as the repeated case.

## Consequences

**Positive.**
- One mechanism for follow-ons (the existing slice-end review),
  extended consistently.
- No mid-design interruption for the founder.
- Idempotency is a natural property of the slice-end pattern.

**Negative.**
- One-slice-cycle latency between need surfacing and follow-on draft.
  Acceptable given the timescale of actually building infrastructure.

**Neutral.**
- Configurability of the threshold (N=2) deferred. If calibration data
  later shows N=2 is too tight or too loose, the standards-authorship
  process tunes it.
