# GitHub Merge Queue Spike — Can MQ replace wpx-train's rebase loop?

**Date:** 2026-05-23
**Author:** SEA spike for HD-006
**Status:** Proposed — recommendation is **PARTIAL** (adopt for the gate, keep
the train orchestrator). Informs HD-001's scope.
**Predecessor:** [`cicd-batching-analysis.md`](./cicd-batching-analysis.md)
(2026-05-19) — the strategic analysis that established Merge Queue as the
convention; this spike is the tactical follow-up against today's
implementation.

---

## TL;DR

**Recommendation: PARTIAL.** Adopt GitHub Merge Queue as the **integration
gate** (replaces our hand-rolled rebase loop + bundled-tip CI poll). Keep
`wpx-train`'s orchestrator (eligibility, batching, INDEX bookkeeping, train
state YAML, deploy/health/smoke per batch, ADR-212 revert path, per-WP
Step 11 fan-out). The train becomes a thin client that opens PRs, enables
auto-merge, and waits for the merge_group event to fire green — instead of
cloning and rebasing locally.

**Why not full ADOPT.** Three reasons:

1. **Portability.** MQ requires public repos in a managed org OR Enterprise
   Cloud; branch protection on free private repos is not available. The
   *founder-project* repo this train runs against is not always
   MQ-eligible. The train must keep its hand-rolled path as a fallback.
2. **Per-WP SHA bookkeeping.** MQ does populate `merge_commit_sha` on the PR
   after group merge, so the SHAs we need for INDEX entries and Step 11
   security review are recoverable — but only after merge, not during the
   group's CI run. The polling story shifts from "poll bundled-tip CI" to
   "poll each PR's merge_commit_sha until populated, in dep order".
3. **Operational changes the founder sees.** MQ surfaces its own UI
   (queue position, group composition, ejection reasons) that today the
   founder doesn't have to learn. The train summary must translate MQ
   events into Founder English. Doable, but it's net new code, not pure
   deletion.

**Why not REJECT.** MQ's auto-bisection on group failure is *better* than
HD-003's just-shipped per-merge try/except — it isolates the culprit
without needing the file-overlap heuristic at all. And the rebase loop is
~100 LOC of git-shell-out we'd happily delete.

**Show-stoppers for the sulis-ai/agents repo specifically (where we
develop):** none. The repo is public + in an org (`sulis-ai`), so MQ is
available free of charge. Branch protection on `dev` is required and is
currently not enabled — adding it is a one-time admin action.

**HD-001's scope under this recommendation.** HD-001 (cmd_run plan / commit
/ verify split) **proceeds as planned**, but is reshaped: the "commit"
phase becomes "wait for merge_group" when MQ is available, and falls back
to the hand-rolled rebase loop when it isn't. The split is *more*
useful, not less, because MQ-vs-fallback becomes a clean strategy
boundary at the phase seam.

---

## Status

Proposed; my recommendation is **PARTIAL ADOPT**. Decision to be confirmed
by the founder before HD-001 starts (Batch 5).

---

## Context

HD-006 (one of the audit findings from the SEA audit 2026-05-23) asks
whether GitHub Merge Queue can replace the sequential rebase + bundled-tip
CI poll + sequential squash-merge sub-loop inside
`plugins/sulis-execution/scripts/wpx-train`'s `cmd_run`.

Today's `cmd_run` (after HD-003 shipped in v0.21.4):

1. Clone repo to temp (`clone_repo_to_temp`, ~25 LOC)
2. **Sequential rebase** of each WP branch onto the previous rebased
   branch's HEAD (cmd_run lines 1266–1383; ~110 LOC including
   `PatchesAlreadyAppliedError` handling and per-WP BLOCKER write).
   Calls `rebase_branch_in_clone` (~95 LOC in `_wpxlib.py`).
3. Push rebased branches (force-with-lease) — done inside step 2.
4. **Bundled-tip CI poll** (cmd_run line 1407, calls `_poll_ci` ~25 LOC).
5. **Sequential squash-merge** (cmd_run lines 1440–1479; with HD-003's
   per-entry try/except wrapping `_merge_squash` ~15 LOC).
6. Deploy poll + health + smoke + ADR-212 revert path on failure.

Steps 2–5 are roughly 250 LOC of in-cmd_run code plus ~120 LOC of helpers
in `_wpxlib.py` — the section MQ could subsume.

**The predecessor research** (`cicd-batching-analysis.md`) established the
strategic case for Merge Queue at the topological-level granularity.
This spike answers the operational question: **given today's
implementation**, what actually replaces what, what stays, and what new
constraints does MQ impose?

---

## Findings

### F1. Plan availability — show-stopper-shaped, but not for sulis-ai/agents

Per [GitHub's Merge Queue GA announcement](https://github.blog/news-insights/product-news/github-merge-queue-is-generally-available/):

> Any team that is part of a **managed organization with public repositories**
> and **GitHub Enterprise Cloud** users will be able to enable this feature
> on their respective repository.

Translated to plan tiers (cross-referenced against [GitHub's branch
protection availability matrix](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/managing-a-branch-protection-rule)):

| Account type | Public repos | Private repos |
|---|---|---|
| Free (personal) | branch protection: no → MQ: no | branch protection: no → MQ: no |
| Free (org) | branch protection: yes → **MQ: yes** | branch protection: no → MQ: no |
| Pro (personal) | branch protection: yes → MQ: yes (limited) | branch protection: yes → MQ: yes (limited) |
| Team (org) | branch protection: yes → **MQ: yes** | branch protection: yes → **MQ: yes** |
| Enterprise Cloud | **MQ: yes everywhere** | **MQ: yes everywhere** |

**For `sulis-ai/agents` (where wpx-train is developed):** Public repo in an
org → MQ eligible, no extra cost. Branch protection on `dev` is currently
**not** configured (confirmed via `gh api repos/sulis-ai/agents` —
no `branch_protection_rules` in the response and `allow_*_merge` flags are
all permissive). Enabling MQ requires a one-time admin action to enable
"Require merge queue" branch protection on `dev`.

**For founder-project repos this plugin ships to:** unknown. The plugin
must keep the hand-rolled path as a fallback for repos where MQ is not
available (free-tier private repos in particular). This is the central
reason PARTIAL > full ADOPT.

### F2. Branch protection is mandatory

Per [GitHub's MQ docs](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue):

> Repository administrators can require a merge queue by enabling the branch
> protection setting "Require merge queue" on the base branch.

You cannot use MQ without branch protection on the target branch. This is
a meaningful change to how today's wpx-train operates — currently
wpx-train pushes directly to `dev` via `gh pr merge` (squash) without a
protected `dev` branch. Requiring branch protection means:

- All merges to `dev` must go through PRs (already true for sulis-ai/agents
  in practice, but not enforced)
- All required status checks must pass before `dev` accepts a merge
- Force-pushes to `dev` blocked (revert path needs to be a revert commit
  via PR, not a force-push — already what ADR-212 does)

The ADR-212 revert path already uses a wrapper revert commit pushed
through normal means rather than force-pushing `dev`, so this isn't a
regression. But the founder needs to know that adopting MQ means enabling
branch protection on `dev` — a per-repo admin action.

### F3. All PRs in a queue group target the same branch — true by construction

MQ groups are formed from PRs that target the same protected base branch.
This is the same constraint wpx-train already imposes (`--base-branch`
defaults to `dev`; per CW-04 the change-worktree case passes a different
branch consistently). No new constraint.

### F4. The train-state YAML stays useful, but its role shrinks

Today's train state captures phase transitions inside cmd_run because
cmd_run is the single source of truth for what's happening. With MQ as
the integration gate:

- **Still needed:** train_id, bundle composition (which WPs were grouped),
  pre_train_sha per WP (for revert path), deploy/health/smoke verdicts,
  per-WP merge SHA, ADR-212 revert SHAs.
- **No longer needed:** rebased_to_sha (MQ produces its own synthetic
  merge commits we don't track), bundled-tip-CI verdict (subsumed by
  merge_group event outcome).
- **New:** merge_group_check_run_id (so we can find the group's CI run),
  GitHub-assigned queue position per PR (for inspect / status output),
  ejection events from MQ (for failure handling).

`wpx-train inspect` / `wpx-train resume` / `wpx-train abort` continue to
work, but their phases change: `rebasing` collapses into `enqueueing`,
`ci_running` becomes `awaiting_merge_group`, `merging` becomes
`reconciling_merge_shas`. The phase machine in `_wpxlib.py` doesn't shrink
much — about the same shape, different names.

### F5. Per-WP merge SHAs are recoverable, but the timing shifts

After MQ atomically merges a group, each PR's `merge_commit_sha` is
populated and queryable via `gh pr view <num> --json mergeCommit`. So:

- **Today (post-rebase):** We know each branch's `rebased_to_sha` *before*
  merge. After `_merge_squash` succeeds we know `merge_sha_on_dev`. Both
  are captured during cmd_run.
- **With MQ:** We know nothing about merge SHAs until the group lands.
  Then we query each PR for its `merge_commit_sha`. Need to map PR-number
  ↔ WP via the train's bundle. Same SHA quality, polled differently.

The Step 11 security reviewer dispatched per-WP after batch deploy
(documented in run-all.md) takes the merge SHA as input. The reviewer
doesn't care whether the SHA came from `_merge_squash` or from
`gh pr view`. No change for the downstream consumer.

### F6. Failure handling is BETTER than today's HD-003 path

Per [tenki.cloud's analysis of GitHub MQ in 2026](https://tenki.cloud/blog/github-merge-queue-setup):

> When a batch fails, GitHub doesn't merge any PRs atomically. Instead, the
> system automatically bisects: "It splits the group, retests the halves,
> and identifies which PR broke things. The failing PR gets ejected, and
> the passing ones proceed."

This is significant. Today, after HD-003:

- Sequential merge — A succeeds, B fails. HD-003's try/except routes to
  `_handle_post_merge_failure` which reverts A. The whole batch is lost;
  B is flagged step-7-blocked; A goes back to step-7-complete to be picked
  up by next train.
- With MQ — A and B grouped together. Group CI fails. MQ bisects, finds B
  is the culprit, ejects B, **A merges in a new group without B**. We lose
  no work for the well-behaved WPs.

The HD-003 file-overlap heuristic (`compute_culprit_heuristic`) is
deterministic but a heuristic. MQ's bisection is empirical (actually
runs CI on subsets) and produces the right answer even when files don't
overlap (a regression in shared logic surfaced by one WP's tests, etc.).

**This is the strongest case for adopting MQ.** Better failure handling
without writing the bisection ourselves.

### F7. The polling story changes — webhook-first, polling-fallback

MQ emits webhook events:

- `merge_group` event on workflow runs (analogous to `pull_request` and
  `push` — fires when a group is built)
- Check-run events on the synthetic merge commit
- PR events when a PR's `merge_commit_sha` populates after group success

We don't have webhook infrastructure today. Two practical options:

- **Poll `gh pr view <num> --json mergeCommit,mergeStateStatus` for each
  PR in the bundle.** When all of them populate, the group succeeded. If
  one transitions to "blocked" or the PR is closed without merge, MQ
  ejected it.
- **Poll the `merge_group` workflow run via `gh api`.** Fewer requests but
  needs us to discover the run ID from the synthetic commit.

The first option composes naturally with `_poll_ci`'s existing per-branch
polling shape — same idea, different ref. About the same LOC as today's
`_poll_ci`.

### F8. The deploy / health / smoke loop is unchanged

MQ replaces the integration gate, not the post-merge deploy chain.
`cmd_run`'s `_poll_deploy`, `_poll_health`, `_run_smoke`, ADR-212 revert
path on deploy/health/smoke failure all stay verbatim. The deploy is
still triggered by the merge commit hitting `dev`; whether that commit
came from our `_merge_squash` or from MQ's atomic group merge is opaque
to the deploy workflow.

### F9. LOC delta — net reduction, but smaller than naively expected

What gets deleted (best case):

| Region | LOC (approx) |
|---|---|
| `clone_repo_to_temp` (no longer needed in cmd_run path) | ~25 |
| `rebase_branch_in_clone` | ~95 |
| `detect_already_applied_patches` + `PatchesAlreadyAppliedError` class | ~70 |
| Sequential rebase loop in cmd_run (incl. all error handling, BLOCKER writes) | ~110 |
| Bundled-tip CI poll call | ~5 |
| Sequential squash-merge loop (with HD-003's try/except) | ~30 |
| `compute_culprit_heuristic` (no longer needed — MQ bisects empirically) | ~40 (estimated; not read in this spike) |
| **Total deletion candidate** | **~375 LOC** |

What gets added:

| New code | LOC (estimated) |
|---|---|
| `gh pr create --base dev --head <branch>` per WP (with idempotency for re-runs) | ~30 |
| `gh pr merge <num> --auto --squash` per WP | ~10 |
| Poll per-PR `mergeCommit` + `mergeStateStatus` (replaces `_poll_ci` for the integration gate) | ~50 |
| MQ ejection detection (PR transitions to `BLOCKED` or closes without merge) | ~30 |
| `gh pr view <num> --json mergeCommit` after group success, populate bundle | ~20 |
| Founder-English translation of MQ states (queue position, ejection reason) for `inspect` output | ~40 |
| Fallback path detection (check repo MQ eligibility; route to legacy rebase loop if absent) | ~50 |
| **Total addition** | **~230 LOC** |

**Net:** ~145 LOC removed. Modest, not transformational. The real win is
the **kind** of code we delete — git shell-out + sequential rebase
arithmetic that was the source of v0.15.1 / v0.15.3 / v0.20.6 bug fixes
— replaced by GitHub API calls that don't fail in those particular ways.

If we drop the fallback path (full ADOPT), that's another ~50 LOC saved
and ~50 LOC of branching logic gone — but we lose portability to
non-MQ-eligible repos.

### F10. Reversibility — fallback path is the safety net

The hand-rolled rebase loop has been battle-tested through five bug
fixes (v0.15.1, v0.15.3, v0.18.0, v0.20.6, v0.21.4 / HD-003). It works,
and the codebase has extensive tests for it (250+ wpx tests). The
PARTIAL recommendation preserves it as the fallback for two purposes:

1. **Portability to non-MQ-eligible repos.** The plugin ships to founder
   projects we don't control; we can't assume every target repo has MQ.
2. **Escape hatch when MQ misbehaves.** Per the [tenki.cloud analysis](https://tenki.cloud/blog/github-merge-queue-setup),
   "cascading restarts" when a batch ejects mid-flight is "the single
   biggest source of frustration with merge queues" — when 5 PRs are
   queued and PR-2 ejects, PRs 3-5 all rebuild speculative merge commits
   and re-run CI. The founder can force-route to the legacy path by
   passing `--no-merge-queue` when MQ's behaviour becomes operationally
   painful, without losing access to wpx-train at all.

### F11. The cmd_run-split (HD-001) becomes a *better* refactor under MQ

HD-001 (as currently scoped in the audit report) splits cmd_run into
plan / commit / verify phases. Under MQ, the phase boundaries map even
more cleanly:

- **plan** — pack batch, open PRs (idempotent), record bundle in
  train-state. No production-mutating work.
- **commit** — enable auto-merge on each PR, poll for merge_group
  completion. The destructive work happens here, but it's GitHub's atomic
  group merge, not our sequential merge loop. Resume becomes trivial:
  re-poll the PR set; the group either landed or didn't.
- **verify** — deploy poll + health + smoke. Unchanged.

Today the equivalent split fights against the inline rebase+merge logic;
MQ makes the seam natural.

---

## Trade-offs

### What we gain

- **Better failure handling.** Empirical bisection > file-overlap heuristic.
  Well-behaved WPs in a failed group don't lose their merge progress.
- **Less custom git code.** ~145 LOC net deleted, including the regions
  that have historically been the buggiest (rebase loop, force-with-lease
  semantics, single-branch fetch refspec gotchas, patch-id-already-applied
  detection).
- **Standard pattern.** MQ is the convention (CP-01 — boring beats clever).
  Founder onboarding into the train mental model becomes "we use GitHub
  Merge Queue, plus a thin orchestrator on top" instead of "we have a
  bespoke train that does rebases in a temp clone".
- **HD-001 split becomes cleaner.** Phase seams align with MQ's natural
  state transitions.

### What we lose

- **Portability of the train to non-MQ-eligible repos.** Mitigated by the
  fallback path; not a hard loss but adds branching logic.
- **Per-stage observability we own.** Today we know the bundled-tip CI
  verdict the moment it completes via our `_poll_ci`. With MQ the same
  info comes from the `merge_group` workflow run, which we need to query
  separately. Equivalent fidelity, different API surface.
- **Founder cognitive load.** Founders now have *two* UIs to understand:
  ours (`wpx-train inspect`) and GitHub's (merge queue page). Mitigation:
  `inspect` translates MQ state into Founder English so the founder
  rarely has to look at GitHub's UI.

### What stays the same

- The ADR-212 revert path on deploy/health/smoke failure
- Step 11 per-WP security reviewer fan-out after batch deploy
- INDEX.md status flips + per-WP BLOCKER writes
- All deploy / health / smoke polling
- The train-state YAML (with renamed phases, same shape)
- The eligibility computation (`find_eligible_branches`, `pack_batches`)
- All `wpx-train` subcommands (queue-list / queue-add / queue-remove /
  status / inspect / resume / abort / skip-wp / retry-wp)

### Operational changes the founder sees

1. **One-time setup per project repo:** "Enable branch protection on `dev`
   with 'Require merge queue'". Reachable via repo settings UI or
   `gh api -X PUT repos/{owner}/{repo}/branches/dev/protection`.
2. **Founder-facing UI:** mostly unchanged. `wpx-train inspect <id>` still
   the primary tool; new states surface in Founder English.
3. **A train run takes longer end-to-end** when the queue is busy (waiting
   in line behind other groups). At our current scale (single founder,
   single train at a time) this is zero impact.
4. **A failing PR doesn't poison its peers.** MQ ejects + retries; we
   document this so founders understand why a batch of 3 sometimes ships
   as "2 succeeded, 1 ejected to step-7-blocked" instead of "all 3
   reverted".

---

## Migration cost

One-time:

- **Repo admin action:** enable branch protection + MQ on `dev`. ~5 min
  per repo. Documented in a new section of `references/lifecycle.md`.
- **CI workflow tagging:** any required CI workflow must add
  `on: merge_group:` alongside its existing `on: pull_request:` / `on:
  push:`. ~1 line per workflow file; typically 1-3 files per project.
- **cmd_run refactor:** the deletions + additions in F9, plus the
  fallback-path detection. Estimated effort: 1-2 days for implementation,
  another 1-2 days for the test rewrites against `gh pr` operations
  (composed with HD-005's GHClient protocol from Batch 4).

Ongoing:

- **None for MQ itself** — once enabled, GitHub maintains the queue.
- **Test fixture maintenance** for the GHClient mock (already on the
  roadmap as HD-002, Batch 4).

---

## Recommendation

**PARTIAL ADOPT.** Concretely, in implementation order:

1. **Adopt MQ as the integration gate (Batch 5, alongside HD-001).** When
   the repo is MQ-eligible, the train opens PRs, enables auto-merge, and
   polls per-PR `mergeCommit` for the group outcome. When the repo is not
   MQ-eligible, the train falls back to today's rebase + bundled-tip CI
   + sequential merge path.
2. **Detect MQ eligibility deterministically.** Probe
   `gh api repos/{owner}/{repo}/branches/dev/protection` at train start.
   If `required_status_checks.required_merge_queue` is `true`, use MQ
   path. Otherwise fall back. No founder-visible choice; the train
   self-selects.
3. **Keep `wpx-train`'s entire orchestrator** (eligibility, batching,
   train state, inspect / resume / abort / skip-wp / retry-wp, ADR-212
   revert on post-merge failure, Step 11 fan-out).
4. **Delete the heuristic culprit detector** (`compute_culprit_heuristic`)
   once the MQ path is verified; MQ's empirical bisection makes it
   unnecessary on the MQ path. Keep it for the fallback path only.

The HD-001 cmd_run split proceeds as planned in Batch 5, with the
amendment that "commit" phase has two strategies (MQ vs. legacy)
selected at runtime by F2's probe.

---

## Implications for HD-001 (Batch 5's scope)

**HD-001 still ships.** The plan / commit / verify split is independently
valuable — `wpx-train resume` becomes trivial when phases are factored
out as separate commands, regardless of which integration strategy the
"commit" phase uses internally.

**HD-001's scope grows by one item.** The "commit" phase needs a strategy
dispatcher:

- `_commit_via_merge_queue` (new, ~120 LOC including poll + ejection
  handling + per-PR SHA reconciliation)
- `_commit_via_rebase_loop` (extracted from today's cmd_run, ~250 LOC
  refactored from inline to a function)

This is a *natural* extension of HD-001's intent (factor the inline
integration logic into a callable). It does not change HD-001's red
test (still "cmd_run can be invoked phase-by-phase, with state
checkpointed between phases for resume") and does not change HD-007's
scope (Step 10.5 + 11 into a verify phase).

**Batch 5's verification additions:**

- New test: MQ-eligible repo path enqueues all batch WPs, waits for
  group success, reconciles per-PR merge SHAs into bundle.
- New test: MQ-ineligible repo path falls back to existing rebase loop
  (regression-pin for today's path).
- New test: MQ ejection of one PR mid-group flips that WP to
  step-7-blocked, leaves the others to be picked up by the next train.

**Batch 5's documentation additions:**

- Section in `references/lifecycle.md`: "Enabling Merge Queue per repo"
  with the one-time admin command.
- Section in `references/lifecycle.md`: "What founders see when MQ
  ejects a PR" — translates the MQ event vocabulary.
- New ADR (numbered after the highest in the External ADR Registry):
  "Use GitHub Merge Queue as the integration gate, with hand-rolled
  fallback for non-MQ-eligible repos". Supersedes ADR-212's "we'll
  build our own merge queue" framing as the strategic choice, but
  ADR-212's eligibility + paused-state + ADR-212-revert decisions all
  stay — they describe orchestration, not the gate.

---

## What I didn't investigate (deferred)

- **Webhook setup vs. polling cost.** I assumed polling for simplicity
  and to match today's `_poll_ci` shape. A webhook receiver would be
  lower-latency + lower-API-quota, but requires standing infrastructure
  the plugin doesn't have today. Not a blocker; can switch later.
- **MQ "maximum group size" tuning.** GitHub default is 5; Shopify uses 8.
  Our `--max-batch-size` default is 5 (matches GitHub default). Tuning
  is a setting on the branch protection rule, not in our code — out of
  scope for HD-001.
- **MQ behaviour with the change-worktree pattern (CW-04).** If `--base-branch`
  is a change branch (not `dev`), MQ would need to be enabled on the
  change branch too. Probably we just don't use MQ inside change
  worktrees (the legacy path handles this case fine; change branches
  are short-lived). Decision to be made in HD-001's implementation.
- **Cost of cascading restarts at our scale.** Tenki.cloud calls this
  "the biggest frustration", but it's a high-volume-team problem. At
  single-founder / single-train scale we'll almost never have ≥3 groups
  queued. Likely a non-issue; worth measuring once in production.

---

## References

### GitHub documentation cited

- [Managing a merge queue](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue) — admin setup, branch protection requirement
- [Merging a pull request with a merge queue](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/incorporating-changes-from-a-pull-request/merging-a-pull-request-with-a-merge-queue) — author flow, ejection behaviour
- [About merge queues](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/about-merge-queues) — concepts, plan availability
- [GitHub Merge Queue is generally available](https://github.blog/news-insights/product-news/github-merge-queue-is-generally-available/) — plan availability
- [Managing a branch protection rule](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/managing-a-branch-protection-rule) — plan tiers for branch protection
- [REST API: pulls endpoint](https://docs.github.com/en/rest/pulls/pulls?apiVersion=2022-11-28) — `merge_commit_sha` semantics after MQ merge

### Third-party analysis cited

- [Tenki — GitHub Merge Queue in 2026: How It Works & Handling Flaky Required Status Checks](https://tenki.cloud/blog/github-merge-queue-setup) — empirical bisection behaviour on group failure; cascading-restart frustration pattern

### Existing in-plugin research

- [`cicd-batching-analysis.md`](./cicd-batching-analysis.md) — strategic
  case for MQ (2026-05-19); this spike is the tactical follow-up
- [`adr-212-eligibility-amendment.md`](./adr-212-eligibility-amendment.md) —
  optimistic eligibility; paused-state recovery (v0.18.0)

### Codebase reads

- `plugins/sulis-execution/scripts/wpx-train` — `cmd_run` (lines 1169–1600)
  end-to-end
- `plugins/sulis-execution/scripts/_wpxlib.py` — `clone_repo_to_temp`,
  `rebase_branch_in_clone`, `detect_already_applied_patches`,
  `PatchesAlreadyAppliedError`, `_poll_ci`, `_merge_squash`, `_poll_deploy`
- `plugins/sulis-execution/.architecture/hardening-deltas/HD-003-partial-merge-failure-handling.md`
  — the failure mode just fixed; informs F6
- `plugins/sulis-execution/CHANGELOG.md` v0.11.0–v0.21.4 — historical
  bug fixes in the rebase/merge path that motivate the LOC-deletion case
- `gh api repos/sulis-ai/agents` — confirms public + org-owned + MQ-eligible
  (current state: branch protection on `dev` not enabled)
