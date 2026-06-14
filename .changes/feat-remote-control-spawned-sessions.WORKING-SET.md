# Working Set — feat-remote-control-spawned-sessions

> Live reasoning state for this change/session. **Read at the START of every turn;
> update as a side-effect of each decision** (never as a separate chore — that's
> how it dies). Sections 1–5 are current-state (overwritten as thinking moves);
> section 6 is append-only (never edited). Crystallizes into Opportunity / Design
> / Decision at the session boundary; if a session ends abruptly, this file IS
> the handoff to the next. Spec: plugins/sulis/docs/working-set-and-session-chain.md.

## 1. Problem  (→ Opportunity)
Spawned change sessions should start with Claude's feature remote control enabled by default, so the founder doesn't enable it by hand each time.

## 2. Current best solution  (→ Design)
_(not yet established)_

## 3. Decisions in flight  (→ Decision; status: proposed)
_(none yet — one entry per non-trivial choice being weighed: the choice, options
considered, rejected alternatives + rationale, status proposed→accepted on lock)_

## 4. Open questions / unknowns
_(none yet — the live "what we still don't know" parking lot)_

## 5. Rejected so far  (→ Decision.rejected_alternatives)
_(none yet — paths tried and abandoned, **with the why**)_

## 6. Working log  (append-only)
- 2026-06-13T13:28:58Z — Working Set created.
- 2026-06-13T13:30:53Z — Recon: no --remote-control flag exists anywhere yet — net-new wiring.
- 2026-06-13T13:30:53Z — Two interactive spawn surfaces: PTY adapter (_session_manager/adapters/claude_pty.py spawn_argv, cockpit-attached) and terminal-window launcher (_terminal_launcher.py, claude --agent sulis in a window). Headless -p chat adapter (claude.py _BASE_ARGV) is NOT interactive — remote control likely N/A there.
- 2026-06-13T13:30:53Z — OPEN: confirm exact Claude Code flag name (founder says --remote-control) + whether it applies to PTY interactive spawn vs -p print mode.
- 2026-06-13T13:32:54Z — Spec written. Flag confirmed: --remote-control [name] (claude v2.1.177). It's interactive-only per --help, so target = claude_pty.py spawn_argv ONLY; NOT the headless -p chat adapter (claude.py _BASE_ARGV). Decided: on-by-default + env-var opt-out (CP convention); name the remote session after the change handle.
- 2026-06-13T13:40:20Z — Design done: single WP-001 (backend) wires --remote-control into claude_pty.py spawn_argv. Lint PASS, rubric PASS. Env knob SULIS_SESSION_REMOTE_CONTROL default-ON/opt-out (polarity inverted vs existing OS-window opt-in knob). Live 'remote control actually on' is observed-once manually; CI covers via argv unit tests.
