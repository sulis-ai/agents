# HANDOFF_TO_SEA — terminal-launcher-port

> **Mode:** Early Handover (no upstream SRD; user arrived with predominantly technical content)
> **Source codebase analysed:** `/Users/iain/Documents/repos/ae/ae_task_executor/` (via `sulis:analyse-codebase` v0.42.0)
> **Target codebase:** `/Users/iain/Documents/repos/agents/` (this repo)
> **Linked Phase:** Phase 5 #5 of the change-as-primitive build (per `plugins/sulis/docs/change-as-primitive-design.md`)

## Recommended Command

`sulis:draft-architecture --mode lightweight` (tier-S expected).

## Why this is a Port, not a Build

`ae_task_executor/terminal_launcher.py` already implements proven cross-platform terminal spawning for a closely-adjacent use case (Claude Code session launch). The change-as-primitive design doc explicitly names this file as the port source.

We are NOT designing a terminal launcher from scratch. We are:

1. **Adopting** the proven `launch_terminal` + per-platform-dispatcher pattern (~150 LOC of load-bearing logic)
2. **Adapting** the `create_launch_script` shell-script generator (~250 LOC) — same scaffolding, different script body
3. **Dropping** task-ID parsing helpers (~75 LOC) — ae-specific story-ID format; sulis already has ULID + change handles
4. **Dropping entirely** `terminal_manager*.py` + `terminal_pool*.py` (~2000 LOC) — sulis doesn't need session pooling yet

## What needs to exist after this port

A new module at `plugins/sulis/scripts/_terminal_launcher.py` (or similar) that exposes:

- **`launch_change_terminal(change_id, worktree_path, *, visible=True) -> dict`** — primary entry point. Spawns a new terminal in the change worktree with `SULIS_CHANGE_ID` set to `change_id`, then runs `claude --agent sulis` (or the configured entry-point command) inside it.
- **Cross-platform support** via the same dispatch shape as ae's:
  - macOS → `osascript -e 'tell Terminal to do script ...'`
  - Linux → try `gnome-terminal` → `konsole` → `xterm` in order
  - Headless fallback → background subprocess (when `visible=False`)
- **Return value** — a structured dict with `pid`, `terminal_app_used`, `script_path`, `status` (`spawned` / `failed`). Caller persists pid for later reattach/cleanup.

## Non-functional needs (NFRs)

| ID | Need | Rationale |
|---|---|---|
| NFR-1 | **Cross-platform: macOS + Linux** | Sulis founders run on both. Windows deferred (the ae_task_executor reference doesn't cover it either). |
| NFR-2 | **No process pool** | Sulis is single-founder, single-machine for v1. Multi-session sync is a SaaS-phase concern. |
| NFR-3 | **Spawn time < 2s** | Founder UX — a slow `/sulis:change start` invocation undermines the "click and go" feeling. |
| NFR-4 | **Failure-mode honesty** | When the launcher can't spawn (no terminal app on Linux, osascript permission denied on macOS), surface the failure plainly. No silent fallback to headless when visible was asked for. |
| NFR-5 | **No new external deps** | Use stdlib `subprocess`, `platform`, `tempfile`, `pathlib`. Same as ae's launcher. |

## Misuse cases (light — port is small surface)

| MUC | Adversarial path | System Response |
|---|---|---|
| MUC-1 | Malicious change slug → shell injection via `claude --agent sulis` invocation | Validate change slug + change_id + worktree_path BEFORE constructing the shell script. Slug regex already enforced by `_wpxlib.validate_change_slug`; change_id Crockford-base32 by `_wpxlib.validate_change_ulid`. Worktree path resolved via `Path(...).resolve()` and asserted to be a real directory. |
| MUC-2 | Spawned terminal inherits secrets from the parent shell env | The launch script EXPLICITLY sets `SULIS_CHANGE_ID` + clears any unsanctioned env-var carry-over (per ae's pattern — it sets a clean env block at the top of the launch script). |

## Decisions already made (no need to re-derive)

1. **No process pool / multi-session sync.** v1 is single-machine, single-founder. Defer pooling to SaaS phase.
2. **No Windows.** v1 = macOS + Linux. Match ae_task_executor's scope.
3. **Shell-script-per-session** (not "exec claude directly in the terminal") — ae's pattern; enables clean env setup + logging + the script becomes a re-runnable artifact for debugging.
4. **No `tmux` integration in v1** (per design doc — "tmux sidebar deferred to UI phase").
5. **Terminal-app selection on Linux is best-effort, not configurable.** Try gnome-terminal → konsole → xterm; if none found, fail explicitly. (Configurability via env var is a follow-up if it's wanted.)

## What's NOT in scope

- Reattach-to-spawned-terminal flow (`/sulis:change focus`) — separate WP; needs pid persistence + os-specific window-focus calls. Defer to Phase 6 (founder-facing skills).
- Session pooling (terminal_pool.py, terminal_pool_visible.py) — out of scope per NFR-2.
- Multi-session orchestration (terminal_manager.py) — sulis already has wpx-train + run-all for this kind of thing.
- Heartbeat / dashboard (Phase 5 #4 SQLite work) — separate deliverable.

## Open questions for SEA

1. **Module home.** `plugins/sulis/scripts/_terminal_launcher.py` (matches `_wpxlib.py` convention — underscore-prefixed library importable by sibling scripts) — or `plugins/sulis/scripts/terminal_launcher.py` (no underscore)? Recommendation: underscore-prefix (matches the existing `_wpxlib.py` + `_change.py-not-yet-created` pattern).
2. **Should the launch script be a tempfile or persisted under `~/.sulis/changes/{change_id}/launch.sh`?** Tempfile is simpler but disposable; persisted enables debugging "what got spawned?". Recommendation: persist under the change run dir (composes with the design doc's `~/.sulis/changes/{ulid}/` directory).
3. **Test strategy.** End-to-end terminal-spawn testing is hard (CI doesn't have a desktop). Recommendation: mock-test the shell-script construction + the cross-platform dispatch logic; manual smoke-test the actual spawn.
