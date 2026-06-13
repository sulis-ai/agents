# Recon — fix-spawn-machinery-from-installed-plugin

Stage 0 completed at: 2026-06-13T16:27:35Z

This marker file's existence indicates that `/sulis:recon` has been run for this
change. The spawned Sulis's stage-inference uses this file to distinguish
"post-recon" from "pre-spawn stub only".

## Root cause located
- `plugins/sulis/scripts/_terminal_launcher.py` resolves `scripts_dir =
  Path(__file__).resolve().parent` at lines 303 (viewer exec line) and 350
  (origin-hook GIT hooksPath + SULIS_SCRIPTS_DIR). When `sulis-change start` runs
  from a change worktree, `__file__` is the worktree copy, so the spawned window
  execs the worktree's `session_viewer.py`; the viewer (session_viewer.py:69) and
  daemon (session_manager_daemon.py:67) then resolve their own `__file__.parent`,
  so the whole chain runs from the worktree.

## Fix direction
- Resolve the INSTALLED plugin scripts dir (cache pick) for the spawned exec line
  + hooks dir. Reuse `_prune_cache.default_cache_root()`, `_version_pick.max_version()`,
  `_plugin_version.plugin_version()`. Provide a dev escape hatch + graceful
  no-install fallback. Next stage: /sulis:specify.
