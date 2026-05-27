---
id: ADR-003
title: RC-02 deadlock fix — merge-queue-ci is the queue's internal gate, never a classic required status check
status: implemented in repository-contract-standard.md v0.3.0 — shipped live to this repo (dev, PR #2); standard text now matches; companion tooling (wpx-arrival-check, bootstrap) edits still pending
date: 2026-05-25
author: SEA
relates_to: repository-contract-standard.md RC-02, RC-03, RC-04, RC-13
supersedes: none
extends: none
profile_invariant: true
independently_shippable: true
---

# ADR-003 — RC-02 `merge-queue-ci` deadlock fix

## Status — DONE (live config) / pending (standard + code)

This fix has **shipped live to `sulis-ai/agents`**. Verified 2026-05-25:

- `dev` classic required status checks = `["branch-ci"]` only (the fix).
  `merge-queue-ci` is no longer a classic required check.
- The repo's `dev-merge-queue` ruleset has been **deleted** — this repo is
  `contribution_model: solo` (ADR-002), so it runs no queue at all; merges go
  direct to `dev` on `branch-ci` green. The deadlock that surfaced this bug is
  gone because the queue is gone here, AND the classic-check list is corrected
  so the fix also holds for any future `team` repo.
- Merged via **PR #2** (`Complete pipeline bootstrap`, merged to `dev`
  2026-05-25T22:19Z).

**Still pending** (the v0.3.0 rewrite must carry these — they are NOT yet
done):

- `repository-contract-standard.md` RC-02 still lists *both* `branch-ci` and
  `merge-queue-ci` as `dev` classic required status checks (lines ~131-159),
  and RC-02's `Check:` block still asserts `grep -q merge-queue-ci`. The
  standard text is unchanged; only this repo's live config reflects the fix.
- `plugins/sulis/scripts/wpx-arrival-check` `_check_rc02_protections` still
  loops `for required in ("branch-ci", "merge-queue-ci")` (line 124) and the
  module-level required-checks constant (lines 33-34) still lists both. **Run
  against this very repo today, the arrival check would FAIL RC-02** —
  because the live repo (correctly) has only `branch-ci`, but the code
  (incorrectly) still demands `merge-queue-ci`. This is the concrete proof the
  code carries the bug; fixing the code is part of the v0.3.0 rewrite.
- `bootstrap-repo-contract.sh` / `wpx-bootstrap-repo` RC-02 block (when the
  bootstrap is reached) must write `contexts:["branch-ci"]`, not both.

So: **the decision is accepted and the live repo proves it correct; the
standard and tooling edits remain queued for the v0.3.0 rewrite.** The
fix is still independently shippable for those artifacts — it need not
wait for the profile/multi-artifact work.

## Decision

`merge-queue-ci` is the **merge queue's own internal gate**, run on the
`merge_group` event for the synthetic merged ref GitHub creates inside the
queue. It **MUST NOT** appear in `dev`'s classic branch-protection
`required_status_checks.contexts`. The only classic required status check
on `dev` is `branch-ci`.

Corrected `dev` protection (for any queue-enabled repo):

```
required_status_checks.contexts = ["branch-ci"]   # ONLY branch-ci
require_merge_queue = true                          # queue runs merge-queue-ci as its gate
```

This is a **profile-invariant** correction: it applies to **every** repo
that runs a merge queue, including `deployable-web-app`. It is a genuine
bug fix, **independent of the profile work**, and is independently
shippable now.

## The bug (deadlock)

RC-02 v0.2.0 lists two classic required status checks on `dev`:
`["branch-ci", "merge-queue-ci"]`.

- `branch-ci` fires on `pull_request` / `push` → runs on a PR's head ref →
  a PR can satisfy it.
- `merge-queue-ci` fires **only** on `merge_group` (RC-04, RC-13) → runs
  on the synthetic ref GitHub creates **after** a PR enters the queue.

A classic required status check must be green **before** a PR can enter
the queue. But `merge-queue-ci` cannot run until the PR is **in** the
queue. The PR waits for a check that cannot run until the PR stops
waiting:

```
PR open ──(branch-ci green)──> eligible for queue
          (merge-queue-ci required as classic check, but never runs outside the queue)
          ──> PR stuck AWAITING_CHECKS forever
```

Observed live on the marketplace repo: a validated green PR stuck on
`AWAITING_CHECKS`; `merge-queue-ci` never triggered.

## The fix and why it is correct

GitHub Merge Queue's designed role for the `merge_group` workflow is to be
**the gate for merging the batch**. Listing `merge-queue-ci` *also* as a
classic required check double-counts it in a place where it cannot run.
Removing it from classic checks leaves the flow deadlock-free while losing
no safety:

1. PR opened → `branch-ci` runs on head ref → green.
2. `branch-ci` is the only classic required check → PR eligible for queue.
3. PR enters queue → GitHub creates `merge_group` ref → `merge-queue-ci`
   runs → green → batch merges to `dev`.

`merge-queue-ci` still gates **every** merge to `dev` — as the queue's
gate, where it can actually run. No merge reaches `dev` without it. The
integration/e2e coverage RC-04 assigns to `merge-queue-ci` is fully
preserved.

Validated live: with `contexts:["branch-ci"]` and the queue enabled,
`merge-queue-ci` ran on the merge group and the green PR merged.

## Alternatives considered

### Rejected: make `merge-queue-ci` fire on `pull_request` too

Would let it satisfy a classic check, but it would then run on the PR head
ref (not the speculative merged ref), defeating its entire purpose — the
queue exists to test the *batched merged* state, not each PR in isolation.
That is what `branch-ci` already does. Duplicating `branch-ci` under a
second name is waste and confusion.

### Rejected: drop `merge-queue-ci` entirely, rely on `branch-ci`

Loses the speculative-merge integration/e2e gate that is the queue's whole
value for `team` repos. `branch-ci` runs per-PR-in-isolation; it does not
test the batched merged ref. Dropping `merge-queue-ci` would let a batch
that is individually-green but collectively-broken land on `dev`.

### Rejected: leave RC-02 as-is and document a workaround

The deadlock is not a misconfiguration of one repo — it is wrong in the
standard. Every repo bootstrapped from the standard inherits the deadlock.
A workaround note would leave the bug latent for every future repo. Fix
the standard.

## Profile applicability

| Repo | `merge-queue-ci` in classic required checks? | `merge-queue-ci` runs as queue gate? |
|---|---|---|
| Queue-enabled (`contribution_model: team`, any profile) | **NO** (this fix) | **YES** |
| Queue-disabled (`contribution_model: solo`, ADR-002) | NO (no queue) | N/A — no queue; `merge-queue-ci.yml` may be absent |

## Code changes (shippable independently of the profile rewrite)

Live config — **DONE** (PR #2):
- This repo's `dev` classic required checks set to `["branch-ci"]`.
- This repo's `dev-merge-queue` ruleset deleted (solo repo, ADR-002).

Standard + tooling — **PENDING** (carry into the v0.3.0 rewrite):
- **`wpx-arrival-check`** `_check_rc02_protections`: drop `merge-queue-ci`
  from the `for required in (...)` loop (line 124) and from the module-level
  required-checks constant (lines 33-34); require only `branch-ci` in
  `contexts`. (Queue-enabled verification stays in RC-03's check.) **Until
  this lands the arrival check is wrong against this repo** (see Status).
- **`bootstrap-repo-contract.sh` / `wpx-bootstrap-repo`** RC-02 dev block:
  write `"contexts": ["branch-ci"]`, not both.
- **`repository-contract-standard.md`** RC-02 `dev` required-status-checks
  list: `branch-ci` only, with a note that `merge-queue-ci` is the queue's
  internal gate. RC-02's existing `Check:` block drops the
  `grep -q merge-queue-ci` assertion.

## Consequences

- The live `AWAITING_CHECKS` block on this repo is gone (PR #2 shipped).
- Every queue-enabled repo (including existing `deployable-web-app` `team`
  repos) should re-run bootstrap or apply the one-line protection change to
  pick up the fix. It is a strict improvement — no safety property weakens;
  the queue still gates every merge.
- This fix is the one change existing conformant repos *should* adopt; it
  is safe, mechanical, and unblocks the queue.
- **Tooling lag is now a tracked debt:** the arrival-check code disagrees
  with the corrected live config until the pending edits land. Anyone re-
  running `wpx-arrival-check` against this repo before then will see a
  spurious RC-02 FAIL. The v0.3.0 rewrite closes this.
