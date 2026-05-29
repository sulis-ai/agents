# fix: widen wpx-train rollback helper except to FileNotFoundError

Closes #68.

## Problem

`_rollback_pre_merge_train_state(paths, train_id)` in `plugins/sulis/scripts/wpx-train`
guards its `read_train_state` call with `except RuntimeError`, after a
top-level `state_path.exists()` check. But `read_train_state` raises
`FileNotFoundError` (not `RuntimeError`) when the state file vanishes in the
TOCTOU window between the `exists()` check and the read. The catch therefore
misses that edge and the `FileNotFoundError` propagates into `cmd_run`'s
terminal error handlers.

Under `TrainLock` the window is effectively unreachable in practice (the
review of #62 rated this ADVISORY, not a blocker), but an unhandled exception
in an already-failing path adds noise without value.

## Fix

Widen the catch to `except (RuntimeError, FileNotFoundError)` so the helper
degrades cleanly — returns False, leaves state for manual inspection — on both
the corrupt-JSON (`RuntimeError`) and vanished-file (`FileNotFoundError`)
edges.

## Tests

- `tests/unit/test_wpx_train_rollback_toctou.py`:
  - simulates the vanish (state file passes `exists()`, then `read_train_state`
    raises `FileNotFoundError`) → asserts the helper returns False (RED before
    the fix: the exception propagated).
  - pins the pre-existing `RuntimeError` (corrupt JSON) path so widening the
    catch doesn't regress it.
- Train-related suites green (190 passed).
