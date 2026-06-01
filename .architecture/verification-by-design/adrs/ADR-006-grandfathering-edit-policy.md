---
id: ADR-006
title: Edits to grandfathered changes inherit grandfathered status
status: accepted
change_id: 01KT2BPBFESCCDY8F7Y5M8RN4R
date: 2026-06-01
resolves: SRD Open Question 6
---

# ADR-006 — Edits to grandfathered changes inherit grandfathered status

## Decision

When a grandfathered change (one whose `started_at` precedes this
refinement's merge date) is later edited — a follow-on patch, a typo
fix, a backfill — the edit **does not** retroactively require a
Verification Plan section. The edit inherits the grandfathered status
of its parent change.

A genuinely new change — a new `CH-NNNNNN` record created on or after
the merge date — is **never** grandfathered, even if it patches code
shipped by a grandfathered ancestor. The trigger is *the change
record's `started_at` field*, not the lines of code being touched.

## Context

SRD Open Question 6 asked: if a grandfathered change is edited, does
the edit trigger P-VER?

Two interpretations exist:

- (a) Edits to grandfathered changes remain grandfathered.
- (b) Any edit creates a new compliance surface — the edit must
  produce a Verification Plan covering the changed scope.

The pragmatic answer is (a). Edit-triggered compliance is a
common-case footgun: a developer fixing a typo in a 2025 file would
suddenly be required to author a methodology artifact for a
behaviour-zero change. The CW-05 trivial-change carveout exists to
prevent this exact friction at the per-change level; the same rationale
applies at the grandfather boundary.

There is a real boundary case: a *substantial* edit to grandfathered
code (e.g., a refactor that changes 200 lines of behaviour). The answer
is the same: if the editor created a new `CH-NNNNNN` to scope the
refactor (the normal flow), the new change is gated by P-VER. The new
change's `started_at` postdates the merge, so it is not grandfathered.
The lines of code being touched have no bearing.

## Alternatives considered

1. **Edit creates new compliance surface (rejected).** This would
   require P-VER to introspect diff scope on grandfathered changes
   and decide on a line-count threshold for triggering. (a)
   Introduces a knob (the threshold) with no clear default. (b)
   Conflates two failure modes: missing-design-time-verification (the
   problem this change addresses) with insufficient-test-coverage-on-edit
   (a different problem covered by P-VER on the edit's own change
   record, if any). (c) Makes the grandfather boundary unstable —
   the same file could be grandfathered today and non-grandfathered
   after an edit, leading to unpredictable rubric verdicts.

2. **Sliding window — grandfather expires N days after merge
   (rejected).** Introduces calendar dependency. No principled value
   for N. Risk: changes that ship behaviourally complete but with
   pending small edits would tick over into non-grandfathered status
   and start failing rubrics without the team being able to act on
   it.

3. **Per-file grandfathering — file is grandfathered if its first
   commit predates merge (rejected).** Mixes the change-as-unit-of-work
   model (CW-01) with a file-centric one. The marketplace's
   methodology is change-centric throughout; grandfathering should be
   too.

## Edge case: substantial backfill on a grandfathered change

If a grandfathered change ships and then a follow-on `CH-NNNNNN` is
created to add substantial new behaviour (not just a fix), the
follow-on is a new change record with `started_at` postdating the
merge. It is **not** grandfathered. The Verification Plan covers the
follow-on's scope (the new behaviour added by the backfill), not the
ancestor's pre-merge scope. This is the right answer — the new
behaviour gets verified; the old behaviour stays grandfathered.

If someone creates a fake change record to dodge the rubric
(backdating `started_at`), the SRD itself surfaces this as an open
question for future hardening (out of scope for this change, see
MISUSE_CASES.md MUC-005-variant). The cheap defence is that
`.changes/{slug}.yaml` is committed to the change branch, and the
review process (code-review, PR review) catches unusual `started_at`
values.

## Consequences

**Positive.**
- Predictable rubric behaviour — grandfathered changes are
  grandfathered forever.
- No accidental trigger of P-VER on a typo fix.
- Simple to implement: P-VER reads `started_at` and compares to the
  merge-date constant. Done.

**Negative.**
- Backdating attack surface (covered by MUC-005-variant; deferred to
  future hardening).

**Neutral.**
- A change that genuinely needs P-VER and was incorrectly tagged as
  edit-on-grandfathered is fixable: create a new change record for
  the scope that needs verifying.
