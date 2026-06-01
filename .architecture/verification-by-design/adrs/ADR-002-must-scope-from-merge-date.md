---
id: ADR-002
title: P-VER is MUST for every new change from this refinement's merge date
status: accepted
change_id: 01KT2BPBFESCCDY8F7Y5M8RN4R
date: 2026-06-01
resolves: SRD Open Question 2
---

# ADR-002 — P-VER is MUST for every new change from this refinement's merge date

## Decision

The new rubric check **P-VER** is enforced as **MUST** for every change
record (`CH-NNNNNN`) created on or after this refinement's merge date to
`dev`. Changes shipped before that merge are **grandfathered** — P-VER
does not execute against their artifacts.

The merge-date constant lives at a machine-readable location (decided
in this ADR — see Implementation below). The rubric reads the constant
at evaluation time and compares against the candidate change's
`started_at` field in `.changes/{slug}.yaml`.

## Context

SRD Open Question 2 surfaced three options:

- (a) MUST for every new change from merge date.
- (b) Graduated — start as SHOULD with a 90-day calibration window, then
  promote to MUST if defect data supports it.
- (c) MUST only for the first N work packages of every change (an
  attention budget heuristic).

The founder's verbatim framing — *"verification can't be bolted on at
the end"* — and the dogfood acceptance criterion (NFR-005) both pressure
toward (a): if the change ships requiring its own P-VER to pass, then
every subsequent change must satisfy the same bar. Graduated rollout
(b) would mean shipping a methodology gate that does nothing for 90
days, which contradicts the founder's "now is the time" framing.
Per-WP attention budget (c) is a different concern (it's already
handled by P2 atomicity).

The two design-time incidents that motivated this change (release-train
unverified, discovery unverified) are concrete evidence that the
methodology needs a hard gate, not a soft signal.

## Alternatives considered

1. **Graduated SHOULD → MUST (rejected).** A 90-day SHOULD window
   would let the next 2-4 changes ship without verification plans,
   preserving the very failure mode this change exists to address.
   The standards-authorship convention in CLAUDE.md (*"New principles
   start at SHOULD with a 90-day calibration note"*) applies to
   speculative rules; this rule has anchor cases already in production
   (release-train, discovery), so the 90-day calibration is already
   complete in evidence terms.

2. **First-N-WPs only (rejected).** Attention budget is real but
   different — it's about cognitive load on the reader, not about
   what gates the design must satisfy. This concern is already covered
   by atomicity (P2). If a change has 30 WPs and 30 verification
   fields feels heavy, the answer is to split the change, not to skip
   verification on most of it.

3. **MUST from a future fixed date (e.g., next quarter)
   (rejected).** Adds a calendar dependency to a methodology change.
   The grandfather mechanism already gives transitional softness — old
   changes are grandfathered, new ones from this merge are gated. No
   calendar reason to delay.

## Implementation

**Merge-date constant location:** `plugins/sulis/references/decompose-validation-rubric.md`
contains a YAML front-matter constant `verification_required_from:`
that records this refinement's merge date (filled in by the
`sulis-change finish` flow when this change merges to `dev`). The
rubric reads this constant at evaluation time.

**Detection logic:**

```pseudocode
def is_grandfathered(change_id: str) -> bool:
    rubric_merge_date = read_constant("verification_required_from")
    change_started_at = read_change_record(change_id).started_at
    return change_started_at < rubric_merge_date
```

**Bootstrap edge:** Until this refinement merges, the constant is
absent / null. Per FR-014 acceptance criterion 3, the rubric falls
back to "not grandfathered" and applies P-VER normally **for new
changes created after this refinement's MR is opened** (concretely:
this change itself). This is what makes the dogfood property work —
this change must pass its own rubric before merging.

## Consequences

**Positive.**
- Sharpens the founder's framing into an enforceable contract.
- Aligns with the dogfood acceptance criterion (NFR-005) — both
  this change AND every following change satisfy the same bar.
- No retroactive penalty (NFR-003 PASS).

**Negative.**
- A change in flight at merge time (started before merge, finished
  after) is ambiguous. The implementation uses `started_at` — so
  in-flight changes inherit grandfather status. This is the safer
  choice; the alternative (using `merged_at`) would retroactively
  fail in-flight changes.

**Neutral.**
- Calibration data flows back through the same lessons-capture
  mechanism (`/sulis:capture-lessons`). If P-VER produces high
  false-positive rates in early use, the calibration window per
  Code Review Standard CR-10 catches it and tunes the check.
