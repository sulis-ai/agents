# Manual smoke — `launch_change_terminal` (raw launcher)

> Launcher mechanism (WP-001..WP-003 + WP-006). Not run in CI (CI has no
> desktop). Run by hand on macOS and Linux.

> **Default-on (CH-01KTK7).** A visible launch opens the change's terminal by
> default — no environment flag is required. This is the sanctioned
> change-start launcher (`sulis-change start --spawn`). The
> `SULIS_TERMINAL_OS_WINDOW` flag remains only as an explicit override knob; it
> does NOT gate the default-on behaviour. The in-cockpit live terminal (the
> cockpit's Terminal tab) is a separate, browser-rendered capability — not a
> replacement for popping a focused terminal here.

## Goal

Confirm a visible launch (`launch_change_terminal(..., visible=True)`) opens a
NEW terminal window by default, cd's to the worktree, exports
`SULIS_CHANGE_ID`, and runs the entry command.

## Pre-conditions

- A real directory to use as the worktree (any existing dir works for the
  smoke; use a change worktree for realism).
- A valid 26-char Crockford-base32 ULID (any change's `change_id`).

## Procedure (macOS)

```bash
python3 - <<'PY'
import sys
sys.path.insert(0, "plugins/sulis/scripts")
from _terminal_launcher import launch_change_terminal
r = launch_change_terminal(
    "01HYQC71000000000000000000",
    "/tmp",  # use a real worktree path
    pre_prompt="You are Sulis. Say hello and confirm SULIS_CHANGE_ID is set.",
)
print(r)
PY
```

## Expected

- A new Terminal.app window opens.
- The returned dict has `status="spawned"`, `terminal_app_used="Terminal.app"`,
  an int `pid`, and a `session_json_path`.
- `cat ~/.sulis/changes/01HYQC71000000000000000000/launch.sh` shows the
  env-scrub line, the `export SULIS_CHANGE_ID=...` line, the `cd "/tmp"`
  line, and an `exec ... "$(cat <sidecar>)"` line that reads the pre_prompt
  from the `pre_prompt.txt` sidecar (#86 — the brief is delivered via a file,
  never inline in the script).
- In the new window: `echo $SULIS_CHANGE_ID` prints the ULID.

## Procedure (Linux)

Same script. Expected `terminal_app_used` is the first available of
`gnome-terminal` / `konsole` / `xterm`. If none are installed the dict is
`{"status": "failed", "error": "no supported terminal app found; ..."}`
(NFR-4 — no silent headless fallback). Pass `visible=False` for headless.

## Fail signals

- `status="failed"` with `unsupported platform` → not macOS/Linux.
- `status="failed"` with `no supported terminal app found` (Linux) → install
  `gnome-terminal` / `konsole` / `xterm`, or pass `visible=False` for headless.
- The pre_prompt body appears inline in `launch.sh` with `$HOME` expanded →
  the brief was embedded instead of read from the sidecar (regression against
  the #86 sidecar-delivery fix).
