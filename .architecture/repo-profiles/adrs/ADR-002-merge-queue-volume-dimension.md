---
id: ADR-002
title: Merge queue is governed by an orthogonal contribution-volume axis, not by profile
status: implemented in repository-contract-standard.md v0.3.0
date: 2026-05-25
author: SEA
relates_to: repository-contract-standard.md RC-03; git-workflow-standard.md GIT-05
supersedes: none
extends: none
---

# ADR-002 — Merge queue as an orthogonal volume dimension

## Decision

GitHub Merge Queue (RC-03) is governed by a **separate declared field**,
`contribution_model ∈ { team, solo }`, **orthogonal to the profile axis**
(ADR-001):

- **`team`** (default) — merge queue **MUST** be enabled per RC-03. PRs
  enter the queue; `merge_group` runs `merge-queue-ci`.
- **`solo`** — merge queue **MUST NOT** be enabled. Merges go direct to
  `dev` via squash on `branch-ci` green — the GIT-05 no-PR direct-merge
  path. The `merge-queue-ci.yml` workflow and the queue are absent.

The queue setting is decided by `contribution_model`, independent of
whether the repo is `deployable-web-app`, `published-artifact`, or
`internal-tool`.

## Why orthogonal, not part of the profile

The merge queue's value is **amortising CI cost and serialising merges
under concurrent merge pressure** — the speculative-batch patterns
(Shopify, debugg.ai) RC-03 cites. That pressure is a function of
*contribution volume*, not of *what the repo ships*:

- A `deployable-web-app` can be solo (a founder's SaaS) → no merge race →
  queue is ceremony.
- A `published-artifact` can be high-volume (popular OSS library, many
  contributors) → merge race → queue pays off.

Volume and deployability vary independently. Modelling the queue on the
profile axis would mis-classify both cases. A separate boolean-ish field
keeps each axis MECE on its own discriminator.

## Evidence (the live failure)

On the single-maintainer marketplace repo, the queue added pure ceremony
and then **actively blocked a validated green PR**: the `merge_group`
workflow wouldn't trigger and the queue stuck on `AWAITING_CHECKS`. At one
maintainer with a low PR rate there is no concurrent merge to serialise;
the queue's cost (a second CI surface, a second failure mode) is paid with
zero benefit.

## Alternatives considered

### Rejected: keep RC-03 a universal MUST

This is the v0.2.0 status quo. It forces speculative-batch machinery onto
repos with no concurrent merge pressure, where it is ceremony and a live
failure surface (the `AWAITING_CHECKS` block). Universality here optimises
for the high-volume case at the cost of breaking the low-volume case.

### Rejected: fold "low-volume" into the non-deployable profiles

Tempting because the repo that hit the problem is both non-deployable and
solo. But it conflates two independent properties. A high-volume OSS
library (non-deployable, `team`) genuinely benefits from the queue; a solo
deployable SaaS (deployable, `solo`) genuinely does not. Folding volume
into the profile would force the wrong default on both. ADR-001's MECE
partition is on deployability alone; volume rides a separate field.

### Rejected: auto-detect volume from PR history

Inferring `solo` vs `team` from recent merge frequency is non-deterministic
and would make the arrival check's behaviour drift as history changes —
violating the contract's "make assumptions explicit and fail predictably"
principle (RC provenance). The repo owner declares the model explicitly.

## Convention alignment (CP-04)

Disabling the merge queue on a low-volume repo is the **dominant industry
pattern**: GitHub's own guidance positions merge queues for busy repos
with frequent concurrent merges. The solo direct-merge-to-`dev`-on-green
flow is already the canonical path in GIT-05 (modelled on trunk-based
solo/CD flow — Netflix/Etsy-style). This is the boring, conventional
choice, not a bespoke relaxation.

## Backward compatibility

`contribution_model` absent → defaults to **`team`** → queue MUST, exactly
as v0.2.0. No existing repo changes behaviour without an explicit opt-in
to `solo`.

## Interaction with ADR-003 (RC-02 fix)

When `solo`, `merge-queue-ci` is not merely demoted from classic required
checks (ADR-003) — the whole queue and its workflow are absent. The
`solo` repo's `dev` protection requires `branch-ci` only and does not set
`require_merge_queue`. When `team`, ADR-003's fix applies:
`merge-queue-ci` is the queue's internal gate, never a classic required
check.

## Consequences

- `.sulis/repo-contract.yml` gains `contribution_model: solo|team`.
- The arrival check's RC-03 logic keys on `contribution_model`: `solo`
  verifies the queue is **absent**; `team` verifies it is **enabled**.
- The bootstrap skips the queue-enable step for `solo` and sets the
  GIT-05 direct-merge protection shape.
- The marketplace repo declares `contribution_model: solo`, removing the
  `AWAITING_CHECKS` block.
