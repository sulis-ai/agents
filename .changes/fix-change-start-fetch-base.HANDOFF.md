# Handoff — fix-change-start-fetch-base (CH-01KTP2) — issue #100

> Seed for this scoped session, written from the originating session while the bug was
> fresh — and confirmed live: THIS change was cut from the stale base by the very bug it
> fixes. Read this before `/sulis:recon` → `/sulis:specify`. Small, well-bounded `fix`.

## FIRST ACTION (MUST — before any build): re-anchor onto fresh origin/main

This worktree was created off LOCAL `main` (`860b6df`), which is **88 commits behind**
`origin/main` (`8c43a9e`) — the exact bug below. Before building anything:

```bash
git fetch origin
git rebase origin/main      # clean replay — this branch has only the seed commit
git push --force-with-lease
```

Then build against the fresh base. (If the rebase surfaces conflicts, stop and surface
them — but with only the seed commit on this branch it should be a clean replay.)

## The bug (issue #100)

`sulis-change start` (the `cmd_start` path in `plugins/sulis/scripts/sulis-change`)
branches the new change worktree off the **local** `main` ref with **no fetch** in the
start path. When local `main` lags `origin/main`, every new change is cut from a stale
base → the change designs/builds against an out-of-date codebase and invents phantom
dependencies on things already shipped (the cockpit false-dependency incident, and
#98/#99 both landed on the 78-behind base before that).

### Confirmed evidence (from the originating session)
- `cmd_start` ~line 469: `base_ref = args.base or "main"`
- ~line 499: `git_worktree_add(repo_root, branch, worktree_dest, base_ref)` — branches
  off the LOCAL `main` ref.
- ~line 504: `base_sha = rev-parse base_ref` (local).
- The ONLY `git fetch` in the file is ~line 819, in the rebase/back-integrate path
  (`_run(["git", "fetch", "origin", base_ref] …)`) — NOT in the start path.
- Proof it's live: `start` for THIS change reported `base_sha: 860b6df…` (local) while
  `origin/main` was already at `8c43a9e…` — 88 commits ahead.

## The fix

In `cmd_start`, before branching:
1. `git fetch origin {base_ref}` (best-effort — tolerate offline, like the rebase path).
2. Branch off `origin/{base_ref}` when the remote ref resolves; fall back to the local
   ref only when the fetch failed / no remote (fresh-clone-friendly).
3. Pin `base_sha` to the resolved (remote-preferred) ref.

Mirror the robust base-resolution already used by `wpx-worktree create`'s `--base-branch`
(local-vs-remote resolve) and the rebase path's fetch — established in-repo conventions,
not a new pattern.

## Test-first (MUST)
Author failing tests FIRST (reuse the git-fixture + `_run`-monkeypatch pattern from
`test_sulis_change_*.py`):
1. local `main` behind `origin/main` → `start` branches off `origin/main`'s SHA (fails today).
2. offline / no remote → falls back to local `main`, no crash (fresh-clone path).
3. `--base <branch>` honoured with the same fetch-then-remote-preferred resolution.

## Also fix the false prose (same change)
`plugins/sulis/skills/change/SKILL.md` start-contract currently CLAIMS
*"`sulis-change start` fetches `origin/main` before branching"* — that's false today and
is what masked the bug. After the code fix it becomes true; keep the wording, but verify
it matches the shipped behaviour (don't ship the claim ahead of the code).

## Downstream once this lands
- #98 (CH-01KTMA) and #99 (CH-01KTMJ) were both cut from the stale base — they each need
  the same one-time in-session re-anchor (`git fetch origin && git rebase origin/main`)
  before they build. This fix stops it recurring for every FUTURE change.

## Files in play
- `plugins/sulis/scripts/sulis-change` — `cmd_start` (the fix).
- `plugins/sulis/scripts/tests/unit/test_sulis_change_*.py` — tests.
- `plugins/sulis/skills/change/SKILL.md` — the false-prose correction.
- `plugins/sulis/scripts/wpx-worktree` — reference for the base-resolution pattern to mirror.

## Suggested next step
Re-anchor (top of this file) → `/sulis:recon` (confirm cmd_start's exact lines + the
wpx-worktree resolution pattern) → `/sulis:specify`. Small enough to specify + design +
build in one or two WPs.
