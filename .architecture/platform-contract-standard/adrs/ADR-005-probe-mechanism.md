---
id: ADR-005
title: Probe mechanism — a per-platform "probe recipe" section in each contract; heavy automation deferred
status: accepted
date: 2026-06-02
change: platform-contract-standard
relates-to: [FR-008, NFR-004, UC-004, MUC-005, "SRD:OpenQuestion-4"]
---

# ADR-005 — Probe mechanism per platform class

## Decision

Each Platform Contract carries a **`## Probe recipes` section**: per platform
class, a minimal, written-down recipe for empirically confirming a load-bearing
claim ("doc says X *and* platform does X"). A probe recipe names:

1. **The probe target** (e.g. for GitHub Actions: a scratch repo).
2. **The exercise** (the minimal steps that make the platform demonstrate the
   behaviour).
3. **The evidence shape** (what artifact proves the exercise ran — a captured
   workflow-run URL, a log, an observed pass/fail).

A claim's `probe-result` field is `confirmed | refuted | deferred:<canonical-need-id>`
and **MUST carry evidence** when `confirmed` — a bare `confirmed` without an
evidence reference is rejected (MUC-005).

**For the GitHub Actions n=1 dogfood:** the probe class is **scratch repo**. The
reusable-workflow-location probe and the bot-token probe are run manually once
during this change against a real scratch GitHub repo; their results +
evidence are recorded. The branch-protection probe needs a **paid private repo**
and is **deferred** (`probe-result: deferred:paid-private-repo-for-branch-protection-probe`).

**Heavy automation is deferred** — the *repeatable, CI-driven* probe pipeline is
the canonical deferred need **`scratch-github-actions-probe-repo`**.

## Why

- **A written recipe + evidence requirement is the minimum that makes MUC-005
  uncheatable.** The misuse case is a faked probe ("`confirmed` with no exercise
  run"). Requiring a named evidence artifact turns "I probed it" from an assertion
  into something a reviewer can open and check. That is the whole control; it
  needs no automation to be real.
- **Per-platform recipes belong in the contract, not in a central probe engine.**
  How you exercise GitHub Actions (scratch repo + `uses:`) is nothing like how
  you'd exercise Stripe (test-mode keys) or AWS (a sandbox account). A per-contract
  recipe section keeps the platform-specific knowledge co-located with the platform
  it describes — the same locality the contract already has for claims.
- **Manual-once-then-defer matches the slice.** The dogfood proves the discipline
  works with one real probe run; building the repeatable automation now would
  balloon scope. The deferral is *tracked* (canonical need id), not silent — which
  is exactly the pre-mortem reason 2 mitigation.

## Alternatives considered

- **A central probe-runner service / tool** that all contracts call. Rejected:
  over-engineered for n=1; the per-platform probe shapes are too divergent to
  share a runner usefully yet; and it would block the dogfood on building
  infrastructure. Revisit when n≥3 platforms share a probe shape (the
  extract-the-primitive trigger).
- **No probe, citation-only.** Rejected: citation proves "the doc says X"; it does
  not prove "the platform does X." The triggering incident's deeper lesson is that
  even a *correctly read* doc can be contradicted by platform reality; load-bearing
  claims need the empirical leg (FR-008 / NFR-004).
- **Accept `probe-result: confirmed` without evidence.** Rejected outright — this
  is MUC-005, the integrity failure of the probe mechanism itself. Evidence is the
  non-negotiable floor.
