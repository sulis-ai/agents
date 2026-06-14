# fix: resolve_current_change prefers the worktree over a stale SULIS_CHANGE_ID

Closes #244.

## Problem

A change session's worktree, git branch, and committed recon CONTEXT.md all
identified change B (`change/feat-...`), but the shell's inherited
`SULIS_CHANGE_ID` pointed at an unrelated change A (a stale value left over
from another change). `resolve_current_change()` reads the env var, so:

- step 1 (Self) correctly *declines* to return B's manifest (its change_id
  doesn't equal the env var A), then
- step 3 (sibling-worktree iteration) silently resolves A from wherever A's
  branch exists — the WRONG change.

The mismatch was silent. A naive `stage`/`ship` would then stamp / open a PR
against the wrong change. The worktree (branch + committed manifest) is the
reliable signal; the env var is the stale one.

## Fix

In `resolve_current_change` step 1: when the cwd IS a change worktree (current
branch is a `change/*` branch with a committed manifest) but its `change_id`
DISAGREES with `SULIS_CHANGE_ID`, **prefer the worktree's change** and emit a
loud stderr warning naming the stale env var + the `unset SULIS_CHANGE_ID`
recovery — instead of falling through to silently resolve the env var's
unrelated change at step 3. Resolution-layer fix, so every caller
(stage/ship/etc.) is protected at the root.

## Tests

`tests/unit/test_sulis_change.py::test_resolve_prefers_worktree_over_stale_env_var`
— env var = change A, cwd worktree = change B; asserts resolve returns B,
warns loudly (names A), and never iterates siblings to chase A. The 5 existing
resolve tests still pass.

(Note: `test_socket_server.py::test_open_threads_brief_change_id` fails locally
on macOS — pre-existing AF_UNIX-path-too-long from the long macOS tmpdir,
fails identically on clean main, green on CI's Linux /tmp; unrelated to this
change.)
