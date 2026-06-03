# fix: wpx-worktree create normalises `--base-branch` prefix

Closes #105.

## Problem

`wpx-worktree create --base-branch origin/dev` failed: the cmd_create flow
prepends `origin/` to build `base_ref`, producing the literal
`origin/origin/dev`. The fetch + rev-parse both failed, so an executor that
passed the (equally-valid) `origin/dev` spelling had to retry with bare `dev`
after manually fetching the tracking ref. `refs/heads/dev` had the same
problem.

## Fix

Add `_normalise_base_branch()` that strips a leading `origin/` or
`refs/heads/` prefix before the fetch + ref-build. Both spellings now resolve
identically to bare `dev`. The default-`dev` path and the
`change/{primitive}-{slug}` local-fallback path are unchanged.

## Tests

- `test_create_normalises_origin_prefix` — `--base-branch origin/dev` → ok, ref
  resolves to `origin/dev`, HEAD matches.
- `test_create_normalises_refs_heads_prefix` — `--base-branch refs/heads/dev`
  → same.

Both RED before the fix (`git rev-parse origin/origin/dev` / `origin/refs/heads/dev`).
GREEN after. Existing 4 wpx-worktree tests still pass; broader worktree-related
suite (24 tests) green.
