# fix: isolate ambient SULIS_ORIGIN in the autonomous-origin hook tests

Closes #245.

## Problem

Two tests asserting the commit-stamping hook is a no-op when its env is
absent failed when the suite ran inside a Sulis-assisted session:

- `test_prepare_commit_msg_hook.py::test_hook_is_noop_without_env`
- `test_executor_autonomous_origin.py::test_no_export_leaves_the_commit_unstamped`

Both files' `_commit` helper snapshots `dict(os.environ)` into the commit's
environment. A Sulis session exports `SULIS_ORIGIN`, so the
`prepare-commit-msg` hook stamped the 'no env → no-op' commits and the
assertions failed. Proof it is environmental: `env -u SULIS_ORIGIN pytest …`
passes; CI (no `SULIS_ORIGIN`) passes. The false-red only hits a developer /
founder running the suite from within a Sulis-assisted session.

## Fix

Add an `autouse` `_isolate_sulis_origin(monkeypatch)` fixture to each file
that `monkeypatch.delenv("SULIS_ORIGIN", raising=False)`. The stamped-path
tests pass their own `SULIS_ORIGIN` via the `env=` arg / `autonomous_env(...)`,
which re-adds it after the clear, so they are unaffected. `SULIS_ORIGIN` is
the only env var the hook reads (hooks/prepare-commit-msg line 57), so it is
the complete isolation set.

## Tests

- Both target files green with `SULIS_ORIGIN` set (the false-red scenario):
  15 passed.
- Both files green with the var unset (CI scenario): 15 passed.
