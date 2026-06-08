# fix: wpx-worktree prefers local change-branch tip when ahead of origin

Closes #167.

## Problem

During CH-01KT61's run-all build (13 executor dispatches), every executor
hit the same friction: `wpx-worktree create --base-branch
change/<branch>` cut the feature worktree from `origin/change/<branch>`
even when the LOCAL change branch was ahead — the prior WPs had been
integrated locally but not yet pushed. Each executor had to detect this
and `git reset --hard $(git rev-parse change/<branch>)` by hand before
working. Deterministic, every-WP friction.

## Fix

For `change/*` base branches specifically, compare local vs origin after
the fetch and prefer the LOCAL ref when it is ahead of or equal to
origin. For non-change bases (main / dev), origin remains the source of
truth (those are integration lines the local copy may legitimately be
stale on).

New helper `_resolve_change_branch_base_ref(repo_root, base_branch, *,
fetch_succeeded, fetch_err)` encapsulates the four-case precedence:

1. Both refs exist + origin is ancestor of local → **LOCAL** wins
2. Both refs exist + origin is ahead → **origin/<branch>**
3. Only local exists → LOCAL
4. Only origin exists → origin/<branch>
5. Neither → existing not-found error

## Tests

- `test_create_prefers_local_change_branch_tip_when_ahead_of_origin` —
  set up: push the change branch, add a local-only commit, run create →
  worktree HEAD must equal the LOCAL tip (RED before the fix:
  `base_ref` returned `origin/change/...` and HEAD landed on origin's
  stale SHA).
- `test_create_uses_origin_when_origin_change_branch_is_ahead` —
  symmetric regression: a side clone advances origin; create must pick
  `origin/<branch>` so the worktree gets the freshest shared tip.
- Existing 4 wpx-worktree tests still pass; 26 worktree-related tests
  across suites green.
