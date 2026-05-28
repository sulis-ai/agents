---
founder_facing: false
---
# Spec — dashboard liveness check (tty vs pid) (closes TaskCreate #32)

## Bug

v0.36.0 fixed the underlying `pid`-vs-`tty` issue at the launcher
level: macOS-spawned sessions record `pid=null, pid_kind="session",
tty="/dev/ttys..."` because the launcher pid exits within ~1s
(`osascript` returns immediately). The real liveness handle is the
tab's tty.

BUT — the `dashboard` + `change` skills' liveness recipes still say:

```
kill -0 <pid> 2>/dev/null
```

…which fails on a `null` pid → false-negative → every macOS-spawned
session is reported as **"no live workspace"** in the dashboard +
during `change focus`.

## Fix

1. New `session_is_live(change_id) -> bool` helper in
   `_change_state.py`. Reads `{change_dir}/session.json`. Dispatch on
   `pid_kind`:
   - `"session"` (macOS happy path) → check `os.path.exists(tty)`
     AND the tty has at least one active process (`ps -t <tty>` non-
     empty). Both checks needed because the device file persists
     briefly after the terminal closes.
   - `"launcher"` (Linux/headless) → check `os.kill(pid, 0)`
     succeeds (raises ProcessLookupError if not).
   - Missing session.json, malformed JSON, neither field
     populated → False (no liveness signal).
2. Update `dashboard/SKILL.md` workspace-open check to call the
   helper rather than inline `kill -0 <pid>`.
3. Update `change/SKILL.md` `focus`/`list` liveness check the same way.

## How we'll know it's done

- New tests in `test_change_store.py`:
  - `pid_kind="session"` + tty exists + active process → True
  - `pid_kind="session"` + tty exists + no process → False
  - `pid_kind="session"` + tty file gone → False
  - `pid_kind="launcher"` + pid alive → True (use os.getpid() of self)
  - `pid_kind="launcher"` + pid dead → False
  - no session.json → False
  - malformed session.json → False (no exception)
- Dashboard + change SKILL.md updated; the `python3 -c` invocation
  cleanly calls `session_is_live`.
- Existing 814 tests still GREEN.
- Step 4.5 review gate PASS.

## What to avoid

- **Do NOT touch `_terminal_launcher.py`** — the launcher records
  the right data already (since v0.36.0). The bug is in the
  SKILL.md recipe, not the data.
- **Do NOT remove `pid_kind="launcher"` support.** Linux + headless
  paths still use it; the helper has to handle both.
- **Do NOT have the helper raise on missing session.json.** That's
  a normal state (change started but no terminal opened yet). Return
  False.

## References

- `_terminal_launcher.py` lines 228-260 — session.json schema
- `dashboard/SKILL.md:104-106` — current buggy recipe
- `change/SKILL.md` — same recipe duplicated
- v0.36.0 CHANGELOG entry — the launcher fix
