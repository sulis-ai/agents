# Migration analysis — adopting the session manager in `plugins/sulis/{skills,scripts}`

> Research + analysis (CH-01KTAD). Question: what would it take to migrate the
> existing terminal/session implementations in the foundation onto the new
> provider-neutral `_session_manager`?
>
> **Headline finding:** the existing foundation code and the new manager are
> *different shapes*. There is **no drop-in consumer** today. "Migration" is
> not a swap — it is either (a) building an unbuilt capability, or (b) a
> re-architecture that is really *new* work (the future agentic CLI). The
> manager's genuine first consumers are the **cockpit (phase 2)** and the
> **future Python CLI** — both new, neither a migration of existing code.

## 1. What exists today (inventory of every Claude/terminal/process site)

### The only real "terminal session" — and it is INTERACTIVE
| Site | What it does | Shape |
|---|---|---|
| `_terminal_launcher.py:428` `launch_change_terminal()` | Opens a **visible terminal window** running `claude --agent sulis` in a change worktree (macOS `osascript do script`; Linux gnome-terminal/konsole/xterm; headless-bash fallback) | **INTERACTIVE-TUI** — a human types into it; the launcher `exec`s claude and walks away |
| `_change_state.py` (liveness) | Tracks the spawned terminal's liveness via tty/pid + `session.json` for reattach (`/sulis:change focus`) | session **state tracking** around the launcher |
| `sulis-change` `cmd_start --spawn` / `cmd_focus`; `/sulis:change` SKILL | The CLI + prose that call the launcher | callers of the above |

The launcher does **not** read the process's stdout in code. The human is the
consumer. It is fire-and-launch.

### Not Claude sessions at all (utility subprocess — out of scope)
| Site | What it does | Shape |
|---|---|---|
| `_wpxlib.py:1022` `_run()` | `git` / `gh api` for branch/worktree/train orchestration | HEADLESS one-shot utility |
| `_discovery/verifier.py:155` | runs `check-canonical-drift.py` | one-shot utility |
| `_scenario_dispatch.py:78` | runs declared shell steps | one-shot utility |
| `_emit_ingest_cli.py:29` | `git rev-parse` | one-shot utility |

These are `subprocess.run(...)` calls for git/CLI tools. They are not Claude
sessions and have nothing to migrate.

### The executor (run-all / run-wp) — NOT a Python spawn
The executor is dispatched via Claude Code's **in-session Agent tool**
(`Agent({subagent_type: "sulis:executor"})`), not `subprocess.Popen("claude")`.
There is no Python-side Claude spawn in the executor path.

## 2. The core mismatch

The new manager owns a **headless** Claude (`claude -p --input-format
stream-json`): it holds the process's stdin/stdout pipes and drives the
conversation **in code** (send a message, read streamed events). That is the
cockpit/CLI shape.

The foundation's existing Claude work is the **interactive** shape: a window
handed to a human, never read back in code. The brief explicitly ruled out
"pty-hijacking" a human's terminal; the manager deliberately owns its *own*
headless process instead.

A headless engine cannot drive an interactive window, and vice-versa. So:

## 3. Migration candidates — what each would actually take

### Candidate A — the interactive change-terminal (`_terminal_launcher.py`)
**Status: BLOCKED on an unbuilt capability.**
To put the change-terminal on the manager you would need a **visible-session /
attached-viewer** capability: the manager owns a **PTY** from birth; a viewer
attaches to render it and feed keystrokes; "visible" = a viewer is attached,
"headless" = none. (This is exactly the model explored in the early
critical-thinking — manager-owned PTY, *not* pty-hijack.) Phase-1 built only
the headless path; the PTY + attach surface does not exist.

**Effort:** substantial — a new PTY-owning session type, an attach protocol,
and a terminal-rendering surface (web terminal / xterm.js, or a native
re-attach). Comparable in size to phase-1 itself.

**But also — question whether it is worth it.** The interactive
change-terminal is the founder's own full Sulis TUI (a session like the one
you're in now). The manager's value props — *warm, fast-after-first,
programmatic streaming* — mostly do not help a window the human already drives
and that is already warm. Migrating it risks being a solution without a
problem. **Recommendation: do not migrate the launcher onto the manager;
leave it as the interactive path.** Revisit only if a concrete need appears
(e.g. the cockpit wanting to *render* a change's interactive session in the
browser — which is a new feature, not a migration).

### Candidate B — the executor (run-all / run-wp), today via the Agent tool
**Status: a RE-ARCHITECTURE that is really NEW work — and it is the manager's
real future consumer.**
If the foundation's executor became a **Python program that offloads work to
managed warm Claude sessions** (instead of Agent-tool sub-agents), the manager
is exactly its engine — this is the *"long-running Python CLI that offloads
tasks and manages the session"* the architecture decision was built around
(ADR-001). That is the natural home.

But it is not a swap:
- The Agent tool gives the executor a lot the manager does not: an in-harness
  sub-agent with full tool access, isolation, and the existing wpx-* /
  worktree bookkeeping. A raw `claude -p` warm session provides the *session
  plumbing* (spawn / warm / stream / restart / evict / guard) — **not** the
  executor's agent behaviour (tool use, the RGB loop, journaling).
- So "migrating" the executor means **building a Python agentic executor on
  top of the manager** — i.e. building the future CLI consumer. That is net-new
  work (a future change), for which the manager is the foundation, not a
  migration of the current Agent-tool path.
- **Tradeoff to weigh:** moving off the Agent tool trades harness-native
  sub-agents (tools, isolation) for foundation-owned warm sessions (speed,
  cross-surface reuse, provider-neutrality). Whether that is worth it is the
  real strategic question — not a migration detail.

### Candidate C — everything else
The git/gh utility subprocess calls are unrelated. Nothing to do.

## 4. Bottom line + recommendation

- **There is no clean migration of existing foundation code onto the manager.**
  The interactive launcher is the wrong shape (needs the unbuilt visible-session
  capability); the executor is the wrong mechanism (Agent-tool, and replacing it
  is new work).
- **The manager's real first consumers are NEW:** the **cockpit chat (phase 2,
  already planned)** and the **future agentic Python CLI**. Build those; don't
  retrofit the old paths.
- **Concrete next steps, in order of value:**
  1. **Phase 2 — wire the cockpit to the manager** (already the planned next
     slice; the real, ready consumer). Kills the 40-60s chat lag.
  2. **Build the agentic Python CLI on the manager** (ADR-001's second
     consumer) — *this* is where "the foundation owns warm sessions" becomes
     real. New work, manager-backed.
  3. **Leave `_terminal_launcher.py` as the interactive path.** Only build the
     visible-session/PTY capability if a concrete feature needs it (e.g.
     rendering an interactive change-session in the cockpit).
- **What NOT to do:** do not force the interactive terminal launcher onto a
  headless engine, and do not treat the executor swap as a migration — it is a
  strategic re-architecture to schedule deliberately, if at all.

## 5. The one strategic question for the founder
Is the goal to **unify all Claude-spawning under the foundation** (which would
justify both the visible-session capability *and* the executor re-architecture
— a large, multi-change programme), or to **give the cockpit + a new CLI a fast
warm-session engine** (which phase-1 already delivered and phase-2 + the CLI
consume, with the launcher left alone)? The first is a platform programme; the
second is the path already in flight. The manager supports either, but they are
very different sizes of commitment.
