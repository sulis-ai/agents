# Recon — feat-remote-control-spawned-sessions

Stage 0 completed at: 2026-06-13T13:30:54Z

## What's already here (findings)

- No `--remote-control` flag exists anywhere in the codebase yet — this is net-new wiring.
- Spawned **interactive** sessions are built in two places:
  - `plugins/sulis/scripts/_session_manager/adapters/claude_pty.py` — `spawn_argv()` builds the
    interactive `claude` argv the daemon launches via `Popen` (the cockpit-attached session).
  - `plugins/sulis/scripts/_terminal_launcher.py` — writes a bash script that runs
    `claude --dangerously-skip-permissions --agent sulis` in a new terminal window. Entry-command
    whitelist regex is `^[a-z][a-z0-9 \-]+$`; `--remote-control` passes it (no injection concern).
- The headless chat adapter `_session_manager/adapters/claude.py` (`_BASE_ARGV`, `-p` print +
  stream-json) is NOT interactive — remote control almost certainly does not apply there.

## Open questions for specify/design

- Confirm the exact Claude Code flag name (founder calls it `--remote-control`).
- Confirm remote control applies to the PTY interactive spawn (vs only standalone interactive),
  and whether both surfaces (PTY adapter + terminal-window launcher) need it.

This marker's existence signals `/sulis:recon` has run for this change (stage-inference sentinel).
