# ADR-005 — A closing seam with no covering Scenario is `blocked`, distinct from `deferred`

- **Status:** accepted
- **Change:** CH-01KTP7 (`feat` · `seam-dod-gate`)
- **Date:** 2026-06-09

## Context

The reused `_acceptance_gate.gate_decision` knows three blocking-ish Scenario
verdicts: `fail` (a step broke), `manual-pending` (a human check unconfirmed),
and `deferred` (a Scenario exists but its real outcome wasn't driven — a
credential/infra/third-party hop absent). All three presuppose **a Scenario
exists**.

A closing seam can have a fourth state the ship gate never had to name: **no
covering Scenario at all.** The seam closed, but nothing in the change ever
authored an end-to-end check that drives real data across it. Under the old
ship-stage gate this was invisible — the gate iterated the change's authored
Scenarios; a seam with none simply contributed nothing and passed silently. That
silence is the bug.

## Decision

**A closing seam with no covering Scenario is `blocked`** — its real-data
behaviour was never driven. It is surfaced as a **distinct** founder-English
reason from `deferred`:

- **No covering Scenario:** *"this seam has no end-to-end check — nothing drove
  the real data across it."*
- **Deferred:** *"this seam has a check, but it couldn't run for real yet
  (needs: …)."*

Mechanically, the no-coverage case short-circuits to `blocked` inside
`_seam_close_gate` **before** `gate_decision` is called (there are no Scenario
results to fold), with its own reason string. The deferred case flows through
`gate_decision`'s existing `deferred` handling.

## Why (the recommendation, lead position)

- **It's the core bug.** The whole change exists to catch "ships green but never
  works." A seam that closes with nothing driving its real data is the purest
  instance: shape certified per-slice, real data never crossed. Treating it as a
  silent pass would leave the primary failure uncaught — defeating the change.
- **Observed-or-blocked is honest about absence.** "I have no check for this"
  must read as *not done*, exactly as "I couldn't run the check" does. Both are
  "not observed green." Same discipline as the #81/#83 deferred-blocks rule,
  extended to the no-check case.
- **Distinct reasons because the fix differs.** No-coverage → author a Scenario
  for the seam. Deferred → supply the missing credential/infra, or consciously
  `--allow-deferred`. Collapsing them into one message would point the founder
  at the wrong fix.

## Alternatives considered

- **No-coverage seam passes (legacy ship-gate behaviour).** **Rejected:** this
  is the exact silent pass the change is built to eliminate.
- **No-coverage seam is `deferred` (fold into the existing bucket).**
  **Rejected:** deferred implies a check exists that couldn't run, and is
  escapable via `--allow-deferred` as "a recorded gap." No-coverage has no check
  at all; the honest fix is to write one, and the message must say so. (It is
  still escapable via `--allow-deferred` for a consciously non-user-facing seam —
  the escape applies to both — but the *reason* shown is different.)

## Consequences

- `_seam_close_gate` computes coverage before driving: empty covering-Scenario
  set → `blocked` with the no-coverage reason; non-empty → drive + fold via
  `gate_decision`.
- AC-5 (`test_seam_no_covering_scenario_blocks`) asserts both the `blocked`
  verdict and the distinct-reason wording.
- The `--allow-deferred` escape still lets a knowingly-uncovered, non-user-facing
  seam proceed, recorded — consistent with ADR-002 / the ship gate's escape.
