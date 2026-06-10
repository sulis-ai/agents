# fix: wpx-train keeps the local change worktree in sync with origin

Closes #266, #265.

## Problem

Two related defects left the local change worktree out of step with origin
after a train run — and the gate reviewers read the *local* worktree:

- **#266** (every batch): the commit phase squash-merges each WP into origin's
  change branch via the GitHub API and records `final_merge_sha`, but the
  local change worktree HEAD stays at the pre-batch tip. The run-all session's
  Step 10.5 / Step 11 reviewers read stale state — batch-1 security review
  literally reported "code not present". The operator had to
  `git fetch origin <branch> && git reset --hard <final_merge_sha>` after
  every batch.
- **#265** (`--change-worktree-path`): Step 0's back-integration is a LOCAL
  merge commit that was never pushed. The commit phase rebases WP branches
  onto `origin/{base}` (read via the GitHub API), so the squash-merges build
  off the OLD origin tip and the local branch (which carries the
  back-integration) diverges from origin — neither a descendant of the other.
  Recovery needed a manual reset.

## Fix

1. **#265 root cause** — `_step_0_arrival_check` now pushes the change branch
   to origin on a `merged_ok` back-integration (a fast-forward push; the local
   branch is ahead by the merge commit). The commit phase's
   `onto_sha = _gh_ref_sha(repo, base_branch)` then includes the
   back-integration, the squash-merges land on top, and there is no divergence.
   Non-fatal on push failure (train proceeds, may diverge as before).
2. **#266** — new `_sync_local_change_worktree_after_train`, called from BOTH
   `_finalise_success` and `_finalise_awaiting_gates` before `emit_result`,
   fast-forwards the local worktree to the pushed origin tip (reusing the
   `ff_local_change_branch_from_origin` helper from #141). **Fast-forward
   only** — never a destructive reset, so uncommitted work is safe; a genuinely
   diverged branch logs a clear recovery hint and continues (non-fatal). With
   the #265 fix in place, this is a true fast-forward.

The finalise functions gained `args` + `base_branch` params (both callers
already have them in scope). The sync goes *inside* finalise because
`emit_result` raises `SystemExit`, so code after the call never runs.

## Tests

`tests/unit/test_wpx_train_local_worktree_sync.py` (6 tests):
- sync skipped outside a change context; ff'd inside one; non-fatal +
  recovery-hint on divergence.
- Step 0 pushes the back-integration on `merged_ok`; no push when
  `already_current`; push failure is non-fatal (records False + warns).

Full train-related suite green (246 passed, 1 skipped).
