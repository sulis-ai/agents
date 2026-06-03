# fix: wpx-pipeline fast-forwards the local change branch after squash-merge

Closes #141.

## Problem

During CH-01KT48 ship-of-WP, `wpx-pipeline` squash-merged the feature branch
into the change branch via the GitHub API (POST /merges) and pushed to
origin, but did NOT fast-forward the LOCAL change worktree. The subsequent
Step 11 security-review agent ran against the local working tree, read stale
pre-merge files, and returned a false "change not implemented — CANNOT
REVIEW" verdict. The calling session had to
`git merge --ff-only origin/<change-branch>` by hand, then re-dispatch the
review.

## Fix

Add `ff_local_change_branch_from_origin(repo_root, change_branch)` in
`_wpxlib`:

- fetches `origin/<change_branch>`
- checks if `origin/<change_branch>` is an ancestor of HEAD (already current)
- otherwise runs `git merge --ff-only origin/<change_branch>` (refuses a
  divergent merge — surfaces `ff_not_possible` instead of silently rebasing,
  preserving CW-04's no-rebase rule).

Wire it into `wpx-pipeline` as **Step 8d**, immediately after the successful
real `_merge_squash` and before Step 12.5 back-integration. Guarded by
`args.change_worktree_path AND base_branch.startswith("change/") AND not
merge_already_complete` — only the change-branch ship-of-WP path needs it.

Non-fatal on failure: the merge already landed on origin, so a logged
warning + downstream Step 0 reconciliation is sufficient defence in depth.
Result envelope carries `step_8d_local_ff` (`already_current` /
`fast_forwarded` / `fetch_failed` / `ff_not_possible` / `skipped`) so
callers can act on it if needed.

## Tests

- `tests/unit/test_ff_local_change_branch.py` — 4 tests covering the four
  branch outcomes (already_current, fast_forwarded with advance count,
  fetch_failed, ff_not_possible) via monkeypatched `_run`.
- Back-integrate + pipeline regression suites green (22 tests).
