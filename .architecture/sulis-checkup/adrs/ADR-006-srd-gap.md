---
id: ADR-006
title: TDD produced without an SRD — recorded as gap, SRD authored after TDD review
status: accepted
date: 2026-05-23
deciders: [iain, sea-architect-agent]
---

## Context

`/sulis:draft-architecture`'s standard gotcha is "No SRD, no TDD". The skill should
refer the user back to `requirements-analyst` when no
`.specifications/{project}/` exists.

For `sulis-checkup`, no SRD exists at `.specifications/sulis-checkup/`.
No context index exists at `.context/sulis-checkup/`. The user provided a
detailed brief inline (the slash-command invocation message) describing
the investigation + design needs. The brief is rich enough to drive a
TDD but is not, by itself, an SRD — it doesn't enumerate FRs/NFRs, doesn't
list use cases, doesn't decompose primitives, doesn't run an adversarial
sweep.

The standard escape hatch in `sea:blueprint` is the **Early Handover**
pattern — when `HANDOFF_TO_SEA.md` exists instead of `SRD.md`, the skill
may proceed with a lightweight TDD provided the absent SRD is recorded as
the first ADR.

This ADR is that recording.

## Decision

**Proceed with TDD authorship despite the absent SRD, recording the gap
here.** The TDD serves as the investigation + design output the brief
asked for. An SRD should be authored after TDD review, before any
`/sulis:plan-work` step, using the TDD's Part 9 (gap list) and Part 10
(open questions) as the FR/NFR/MUC seed.

## Why this is acceptable for this case

1. **The brief is explicit that this is investigation + design.** The
   user wrote "INVESTIGATION + DESIGN — do not implement, do not write
   Work Packages." The TDD is the right primary artifact for that scope.
2. **The brief is rich.** It names the seven tiers, the 24-row coverage
   matrix, the existing healing patterns, the LangGraph investigation
   depth requirement, and the founder-facing constraints. It functions
   as a structured spec, even though it's not in SRD form.
3. **The TDD is reversible.** TDD content reads cleanly into an SRD's
   FR/NFR shape; the existing artifacts (matrix rows, healing prototypes,
   tier table) translate to specification language without rework.
4. **The marketplace already operates on a design-first cadence in
   greenfield contexts.** The sulis plugin's v0.1-v0.4 progression
   shipped without per-version SRDs; design artifacts and dogfood ran
   the calibration loop.

## Why this isn't a precedent for skipping SRD generally

The Early Handover pattern exists *because* the SRD step has a cost
(facilitation time, founder cycles) and *because* some inputs already
carry the SRD content in a different shape. It is not a "skip SRD"
license. The pattern's contract is:

1. The TDD is produced honestly (no requirement invention).
2. The absent SRD is recorded explicitly (this ADR).
3. An SRD is authored before any `/sulis:plan-work` step, using the TDD
   as seed input.
4. The SRD passes its own `requirements-validation` before WPs are
   decomposed.

## The recommended SRD path

When the founder accepts (or modifies) this TDD, the SRD-authoring
sequence is:

1. **Run `requirements-analyst`** at `.specifications/sulis-checkup/`.
2. **Feed it the TDD as input** (it's already designed to read TDD
   excerpts; the Part 9 gap list and Part 10 open questions are the
   highest-value seed material).
3. **Specifically prompt for:**
   - Use cases (the founder's mental model of "I run /sulis:checkup and
     get a report" needs to decompose into UC-01 first-time-run,
     UC-02 re-run-after-fixes, UC-03 dismiss-finding, etc.)
   - NFRs (NFR-01 max wall-clock time, NFR-02 resumability after crash,
     NFR-03 founder-facing-conventions compliance, etc.)
   - Misuse cases (MUC-01 founder runs against wrong project,
     MUC-02 secret-finding logged in report itself, MUC-03 OODA loop
     runaway, etc.)
4. **Run `/sulis:requirements-validation`** for the five-perspective
   completeness check.
5. **Then run `/sulis:plan-work`** against this TDD + the new SRD.

## Options Considered

### Option A — Refuse to proceed; refer back to SRD (rejected)

**Pros:** consistent with the standard `sea:blueprint` gotcha.

**Cons:**
- The user explicitly asked for investigation + design as the deliverable.
  Refusing would have surfaced "go run SRD first" — appropriate as a
  blanket policy, wrong for this specific brief shape.
- The brief is rich enough to drive a TDD honestly. Refusal would have
  cost a round-trip without changing the eventual artifact.

### Option B — Proceed under Early Handover (chosen)

**Pros:** matches the codified escape hatch. Records the gap honestly.
Sets up the SRD path explicitly.

**Cons:**
- The TDD will need cross-checking against the SRD when it lands.
  Mitigation: the SRD author should read this ADR first and treat the
  TDD as a draft that the SRD validates rather than the other way around.

### Option C — Produce an SRD inline alongside the TDD (rejected)

**Pros:** ships both at once. No follow-up step.

**Cons:**
- Skill scope creep. `/sulis:draft-architecture` is not `requirements-analyst`.
- The SRD facilitation flow is interactive (it prompts the founder for
  clarifications); doing it inside `/sulis:draft-architecture` would have blocked
  on questions outside the blueprint skill's design.

## Consequences

**Positive:**
- The investigation + design deliverable lands in the time the founder
  needs it.
- The gap is explicit and the SRD path is named, so it doesn't drift
  into "the TDD is the spec".
- This ADR becomes the source for the SRD's "why this exists" section.

**Negative:**
- Two-step authorship adds friction; the SRD step is required before
  decompose.
- Cross-check work may surface TDD revisions when the SRD lands.

**Neutral:**
- The pattern (Early Handover with first-ADR gap recording) is
  established for `sea:blueprint`; this is consistent application, not
  novel.
