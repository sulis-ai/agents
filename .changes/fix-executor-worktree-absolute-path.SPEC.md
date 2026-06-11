# fix: relative executor worktree path anchors to --repo-root, not cwd

Closes #309.

## Problem

A run-all executor's `wpx-worktree create --worktree-path ../wp-NNN-worktree`
(relative) was resolved with `Path(...).resolve()`, which anchors a relative
path to the **process cwd**. When the calling run-all session's cwd was bound
to a DIFFERENT change (e.g. 01KTMF) than the one it was building (01KTV4), the
worktree landed under the wrong change's parent dir. One executor self-healed
by recreating with an absolute path.

## Fix

In `wpx-worktree cmd_create`, resolve a RELATIVE `--worktree-path` against
`--repo-root` (the TARGET change's repo) instead of the process cwd. Absolute
paths are honoured as-is. This makes `../wp-NNN-worktree` land beside the
target change regardless of where the session's cwd is bound — the structural
root-cause fix, independent of caller discipline.

Belt-and-braces prose: `executor.md` (Step 1 create row) and the run-all
`Per-executor isolation` note now state that a relative `--worktree-path`
anchors to `--repo-root`, so executors must pass `--repo-root
<target-change-worktree>`.

## Tests

`tests/unit/test_wpx_worktree.py::test_create_relative_worktree_path_anchors_to_repo_root_not_cwd`
— runs from an unrelated deep cwd, passes a relative `--worktree-path` +
`--repo-root <repo>`, asserts the worktree lands beside repo-root (not beside
cwd) and that the cwd-anchored path is never created. 15 worktree tests green.

(Note: 3 unrelated test modules fail to COLLECT locally on `ModuleNotFoundError:
hypothesis` — a missing local dev dep; CI installs it via `uv sync`.)
