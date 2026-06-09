# ADR-001 — Change-health is derived from tests + rigor-for-stage only; scope-drift is deferred

> **Status:** accepted
> **Date:** 2026-06-09
> **Deciders:** SEA (from the signed-off design)

## Context

The signed-off design (IDEAS.md, Concern 2) specifies a per-change **health**
verdict on the board card with three states — *On track* / *Worth a look* /
*Off track* — derived from three inputs:

1. **Tests** — CI / test state, green vs red.
2. **Rigor-for-stage** — does the change have the artifacts it should for its
   stage (a spec before design, a design/plan before implement, tests with the
   code)?
3. **Scope-drift** — is the change building *beyond* what the spec/plan agreed?

The design's own "Honest build note" flags that scope-drift has **no existing
detector** and overlaps directly with the in-flight `change-stage-ooda-spiral`
work (sitting in Specify on this very board), which is building a stage-level
drift signal. Building a second drift detector here would duplicate that work
and create two sources of truth for the same question.

## Decision

The first cut of change-health is derived from **tests + rigor-for-stage
only**, yielding **two states: On track / Off track**.

- **Off track** when tests are red OR a required-for-stage artifact is missing.
- **On track** otherwise.

The **"Worth a look" middle state** and the **scope-drift input** are
**deferred**. When `change-stage-ooda-spiral` lands its drift signal, a
follow-on change consumes that signal to (a) add scope-drift to the rollup and
(b) introduce "Worth a look" as the neutral middle. The board's health
component is built so a third state slots in without a re-layout (the mockup
already renders all three; the data simply never emits "look" until then).

## Why (Convention Preference + honest scope)

- **Consume, don't duplicate (CP-01 priority 0 — internal prior art).** The
  OODA-spiral change *is* the drift detector. Building a parallel one here
  violates "check before building new" (EP-03) and would diverge.
- **Ship the cheap, certain inputs first.** Tests is a real status the change
  has-or-hasn't; rigor-for-stage is checkable today from the change's own
  artifacts (we know the stage and can see which artifacts exist). Both are
  honest, server-derivable signals. Scope-drift is heuristic and genuinely new
  — gating the whole feature on it would block the two free reads.
- **The verdict stays honest.** A two-state On/Off-track read derived from real
  signals is truthful; a three-state read with an invented drift heuristic
  would not be.

## Consequences

- The health rollup is a **pure server-side function** (`computeHealth`) over
  `{ testsState, rigorForStage }`, returning `"on-track" | "off-track"` now,
  widened to include `"worth-a-look"` later. The wire `Change.health` field is
  added with the three-value type from the start (forward-compatible), but the
  producer only emits two of the three until the OODA signal lands.
- The card component renders all three states (per the mockup); the absence of
  "worth-a-look" data is not a gap, it is the deferral working as designed.
- **Follow-on dependency recorded:** `consume change-stage-ooda-spiral drift
  signal → add scope-drift + worth-a-look` is logged as a deferred need
  (`health-drift-ooda-signal`).

## Alternatives rejected

- **Build all three inputs now (incl. a bespoke scope-drift detector).**
  Rejected: duplicates `change-stage-ooda-spiral`, creates a second drift
  source of truth, and gates two free reads behind a heuristic one.
- **Ship tests-only (drop rigor-for-stage too).** Rejected: rigor-for-stage is
  checkable today and is the input that catches the classic "vibe-coding" drift
  (code with nothing behind it) the founder most wants surfaced early. Dropping
  it would make health little more than a CI badge.
