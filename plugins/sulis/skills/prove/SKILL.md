---
name: prove
description: Point it at something that's been built and it tells you what's genuinely working vs stubbed/faked — it finds the critical scenarios (user journeys + non-functional mechanisms), drives them for real against the real interface, validates the actual saved output, and returns an observed-or-blocked verdict with evidence.
---

# Prove it — is this real, or vibe-coded?

## Conclusion (lead with the answer)

`/sulis:prove` answers one question honestly: **does this actually work, or does it
just look like it works?** Point it at a built thing — a change, a service, an MCP
server, a pipeline — and it (1) finds the **critical scenarios** (the user journeys
*and* the non-functional production mechanisms whose failure means it doesn't really
work), (2) **drives each one for real** against the real interface as a consumer
would — real model, real data, no stubs or mocks, (3) **validates the actual saved
output by looking at it**, not by trusting that it ran, and (4) returns a per-scenario
**observed-or-blocked** verdict with the evidence.

The bar is the one this whole methodology turns on: *"it ran without error" is not a
pass; "here is the correct saved result I opened" is.* A scenario that can't be driven
for real, or whose mechanism is stubbed, reads as **blocked** — never as done.

## The loop (run it in this order)

### 1. Find the critical scenarios
"Critical" = the ones whose failure means the thing doesn't actually work — not every
test, the load-bearing ones. Gather them from three places, in order:
- **The brain** — if the change has authored Scenarios, pull the full set for its
  journey (`find_scenarios_for_journey`). These are the user-journey round-trips.
- **The non-functional mechanisms (NFRs)** — the production muscles that decide whether
  real use survives: cost, storage limits, resumability, latency, throughput, data
  integrity. These are the ones UI polish hides and that get stubbed. List them from
  the spec/NFRs; if none are written down, derive them from what the thing must do
  under real load.
- **Derive from spec + code** if neither exists — the user-facing round-trips end to
  end, plus the production mechanisms above.

State the critical set explicitly before testing. If you can't name what "working"
means for each, you haven't found the test yet.

### 2. Drive each one for real
Be a **consumer** of the real interface (the MCP server / API / CLI / running app) —
the path a real user or agent hits. Real model execution, real input data, **no stubs,
no mocks, no happy-path shortcut**. For a non-functional check, exercise the real
condition: push a genuinely large file, kill the process mid-run, run a real batch and
measure the spend. (This is the journey-rigor "verifier drives the real flow"
discipline + `sulis-verify-acceptance` where Scenarios are authored.)

### 3. Validate the saved output — by looking
Go to where the result actually lands (the store, the records, the raw/refined/ready
zones, the audit trail) and **inspect it against the source**. Did each input produce a
correct, complete saved record? Where did data actually get written? Did any real input
breach a limit? Is the audit trail present and replayable? **Observed, not assumed** —
open the artifact and read it.

### 4. Flag stubs and fakes
A scenario that "passes" can still be hollow. Check for:
- `TODO` / `slots in here` / `NotImplemented` / dead-code-with-no-callers in any
  load-bearing path,
- a check that passed against a **mock** while the real producer was never exercised,
- output that looks right while a production mechanism (cost, storage, resume) was
  stubbed — the "breadth of UI polish masking missing depth" pattern.

### 5. Verdict — observed-or-blocked, per scenario
For each critical scenario: **observed-green** (a real run produced the correct saved
output — cite it) or **blocked** (it failed, was stubbed, ran only against a mock, or
couldn't be driven — say which, with evidence). Report the set as: *driven & green: [N]
· blocked: [N, each with the evidence]*. The honest headline is the blocked list.

## When to invoke
- You suspect something "works in the demo" but isn't production-real ("feels like vibe
  coding").
- Before trusting a build / before shipping — to confirm the real flows survive, not
  just the tests.
- After a long build session where UI/happy-path got polished — to check the
  unglamorous production mechanisms got built, not stubbed.

## When NOT to invoke
- A trivial change (CW-05) with no real flow to drive.
- Pure design/spec work — there's nothing built to drive yet.
- As a substitute for the per-stage gates — `prove` is the consumer-level reality
  check, not a replacement for journey-rigor's design/plan/done gates.

## Gotchas
- **"It ran without error" is not a pass.** A green log with no inspected saved record
  is exactly the failure this skill exists to catch. Open the result.
- **Testing against a mock proves nothing about the real producer.** If the real
  interface wasn't exercised, the scenario is blocked, not green.
- **Don't soften a check to make it pass.** If a check fails on the stubbed version,
  that's the check working — fix the mechanism, not the check.
- **Critical ≠ exhaustive.** Don't drown in every edge case; drive the load-bearing
  round-trips + the production mechanisms whose failure means it doesn't work.
- **Name the cost/measurement gaps you couldn't run.** If a fitness check needs a
  measurement helper that isn't built yet, say "not driven — needs X", never imply it
  passed (no silent caps).

## Composes with
- `../../references/standards/` journey-rigor (observed-or-blocked; the scenario set;
  the verifier-drives-the-real-flow discipline).
- `../../scripts/sulis-verify-acceptance` — drives authored Scenarios against a standing
  app; `prove` uses it where Scenarios exist and drives the interface directly where
  they don't.
- `verify-architecture` (does the build match the design — the paper check) and the
  `verify` skill (run-and-observe). `prove` is the consumer-level "is it actually real"
  layer over both.
