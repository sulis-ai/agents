---
founder_facing: false
---
# Spec — fix `sulis-change start` branching off stale local main

**Change:** CH-01KTP2 · fix

## What this should do
When a new piece of work is started, fetch the latest base branch (`main`)
from the server *before* creating the change branch + worktree, so work
always starts from the up-to-date main line — not a stale local copy. The
`start` command currently branches off whatever local `main` ref exists,
which can be behind `origin/main`; this adds the fetch step the sibling
paths in the same file already perform.

## How we'll know it's done
- A new test proves `start` fetches `origin/main` and branches off the
  fetched tip (RED before the fix, GREEN after).
- Starting a change when local `main` is behind `origin/main` produces a
  branch whose base SHA matches `origin/main`'s tip, not the stale local one.
- The full scripts test suite stays green.

## What to avoid
- Don't change the behaviour of the other subcommands.
- Don't hard-fail when there's no remote / no network — degrade gracefully
  (fall back to the local ref with a logged note), mirroring how the
  existing fetch paths in the same file handle failure.
- Follow the established `git fetch origin {base_ref}` pattern already in
  the file rather than inventing a new approach.
