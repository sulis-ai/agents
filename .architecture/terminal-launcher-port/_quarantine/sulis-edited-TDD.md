# Technical Design Document — terminal-launcher-port

> **ARCH-ID:** ARCH-001
> **Status:** designed
> **Sized:** tier S (sFPC=2, ASR=6); target ~100–200 lines
> **Source:** `.specifications/terminal-launcher-port/HANDOFF_TO_SEA.md` (early-handoff mode — no SRD)
> **Linked phase:** Phase 5 #5 of the change-as-primitive build

---

## Overview

Port the cross-platform terminal-spawning capability from `ae_task_executor/terminal_launcher.py` (504 LOC) into `plugins/sulis/scripts/_terminal_launcher.py`. The port enables `/sulis:change start` (and future `/sulis:change focus`) to open a new terminal window in the change worktree with `SULIS_CHANGE_ID` set, running `claude --agent sulis` inside it.

Strip ae-specific surface (task-ID parsing, session pooling, multi-session manager). Adopt the proven shell-script-per-session + per-platform dispatcher pattern.

---

## Source Specification

- `.specifications/terminal-launcher-port/HANDOFF_TO_SEA.md` — port intent + NFRs + MUCs + decisions-already-made
- `ae_task_executor/terminal_launcher.py` — proven reference (read directly during discover)
- `plugins/sulis/docs/change-as-primitive-design.md` § "Session-per-change" — operational specification

---

## Form — Structural Design

### Component inventory

| Component | Location | Purpose |
|---|---|---|
| `_terminal_launcher.py` | `plugins/sulis/scripts/` | The port. New module. |
| `sulis-change start` | `plugins/sulis/scripts/sulis-change` (existing) | Caller — invokes the launcher when --spawn flag is set |
| `~/.sulis/changes/{change_id}/launch.sh` | runtime artifact | Persisted launch script per session (debuggable; re-runnable) |
| `~/.sulis/changes/{change_id}/session.json` | runtime artifact | Records `pid`, `terminal_app_used`, `spawned_at` for later reattach (Phase 6 deferred) |

### Public API

```python
def launch_change_terminal(
    change_id: str,
    worktree_path: Path | str,
    *,
    visible: bool = True,
    entry_command: str = "claude --agent sulis",
    extra_env: dict[str, str] | None = None,
) -> dict:
    """Spawn a new terminal in the change worktree with SULIS_CHANGE_ID set.

    Returns:
        {
            "status": "spawned" | "failed",
            "pid": int | None,
            "terminal_app_used": str | None,  # "Terminal.app" | "gnome-terminal" | ...
            "script_path": str,  # absolute path to the launch.sh
            "session_json_path": str,  # absolute path to session.json
            "error": str | None,
        }

    Raises ValueError on invalid inputs (bad change_id / bad worktree path).
    """
```

### Internal structure (mirrors ae's shape, stripped)

```
_terminal_launcher.py (~250 LOC target)
├── Public:
│   └── launch_change_terminal(change_id, worktree_path, *, visible, ...)
├── Shell-script construction:
│   └── _build_launch_script(change_id, worktree_path, entry_command, extra_env) -> str
├── Platform dispatchers (private):
│   ├── _launch_macos(script_path, change_id, visible) -> dict
│   ├── _launch_linux(script_path, change_id, visible) -> dict
│   └── _launch_headless(script_path, change_id) -> dict   # visible=False fallback
└── Session bookkeeping (private):
    └── _write_session_json(change_dir, pid, terminal_app, script_path) -> Path
```

### Composition root

`sulis-change start` calls `launch_change_terminal(...)` when invoked with a new `--spawn` flag (defaults to true on macOS + Linux; false on unknown platforms with a clean warning). The current `cmd_start` (in `sulis-change`) writes the manifest first, then optionally invokes the launcher last.

### Dependency graph

```
sulis-change (caller)
  └── _terminal_launcher.launch_change_terminal()
        ├── _wpxlib.validate_change_ulid() [existing]
        ├── _wpxlib.validate_change_slug() [existing]
        ├── _build_launch_script() [new]
        └── _launch_{macos|linux|headless}() [new]
              └── subprocess.Popen [stdlib]
```

No new external dependencies. All operations use stdlib only (per NFR-5).

---

## Armor — Operational Hardening

### Input validation (MUC-1 — shell injection)

Every input passed into the launch script construction is validated before string concatenation:

| Input | Validator | Rejects |
|---|---|---|
| `change_id` | `_wpxlib.validate_change_ulid()` (existing) | non-Crockford-base32 or wrong length |
| `worktree_path` | `Path(input).resolve()` + `.is_dir()` check | non-existent directory, symlink to non-dir |
| `entry_command` | regex `^[a-z][a-z0-9 \-]+$` whitelist (default `"claude --agent sulis"`) | injection via metacharacters |
| `extra_env` keys | regex `^[A-Z_][A-Z0-9_]*$` (POSIX env-var convention) | injection via `;`, `\n`, `$()`, backticks |
| `extra_env` values | `shlex.quote()` before insertion into the script | shell metacharacter escape |

Failures raise `ValueError` before any subprocess is launched.

### Env-leak prevention (MUC-2)

The generated launch script begins with an explicit env-reset preamble:

```bash
#!/usr/bin/env bash
set -euo pipefail
# Phase 5 #5: launch script generated by sulis _terminal_launcher.py
# Carry-over env: only PATH, HOME, USER, TERM, LANG, LC_*.
unset $(compgen -v | grep -Ev '^(PATH|HOME|USER|TERM|LANG|LC_.*)$')
export SULIS_CHANGE_ID="{change_id}"
# extra_env (shlex-quoted at generation time)
{extra_env_block}
cd "{worktree_path}"
exec {entry_command}
```

The `compgen -v | grep -Ev '...' | xargs unset` line is the env-scrub. Variables not in the whitelist (e.g., the parent shell's `AWS_SECRET_ACCESS_KEY`, `GITHUB_TOKEN`) are scrubbed before `claude --agent sulis` runs.

### Failure-mode honesty (NFR-4)

Per-platform launchers return a structured `dict` with `status` and `error`. On Linux, if none of gnome-terminal / konsole / xterm are on `PATH`, the launcher returns `{"status": "failed", "error": "no supported terminal app found; install gnome-terminal, konsole, or xterm — or pass visible=False for headless"}`. No silent fallback to headless.

### Observability

`logger = logging.getLogger("sulis.terminal_launcher")`. Spawn attempts log at INFO; failures log at WARNING with the failure mode. No trace IDs (port is too small to need OpenTelemetry); the session.json artifact is the operational record.

---

## Proof — Verification Protocol

### Unit tests (mocked subprocess)

| Test target | Strategy |
|---|---|
| `_build_launch_script` | Build the script with various inputs; snapshot the output; verify env-scrub line + `SULIS_CHANGE_ID` line + `cd` line are present in expected order |
| Input validators | Inject bad inputs (bad ULID, bad slug, path with `;`, env-var name with `\n`); assert ValueError |
| `_launch_macos` | Mock `subprocess.Popen` and `subprocess.run`; assert osascript invocation shape; assert returned dict has expected keys |
| `_launch_linux` | Mock `shutil.which` (none found → failed; gnome-terminal found → invoked); assert correct terminal app selection |
| `_launch_headless` | Mock subprocess; assert background invocation shape |
| `launch_change_terminal` | End-to-end with mocked dispatchers; assert session.json written; assert structured-dict return |

### Manual smoke test (not CI)

A `Procfile.smoke` (or equivalent) in `plugins/sulis/scripts/tests/manual/` documents:

```
# After implementation lands:
python3 -c "
from _terminal_launcher import launch_change_terminal
result = launch_change_terminal('01HYQC71000000000000000000', '/tmp/test-worktree', visible=True)
print(result)
"
# Expected: a new Terminal.app window (macOS) or gnome-terminal (Linux) opens,
# cd's to /tmp/test-worktree, exports SULIS_CHANGE_ID, then runs `claude --agent sulis`.
```

### Chaos / failure-mode tests

- **NFR-4 honesty**: assert that on Linux-with-no-terminal-app, the function returns `{"status": "failed", ...}` rather than silently falling through to headless.
- **MUC-1 shell-injection**: parametrized test injects shell metacharacters into each input; asserts ValueError before any subprocess call.
- **MUC-2 env-leak**: build a script, assert the `unset` line lists the whitelist exactly + nothing else.

---

## Trade-offs

| Decision | Chosen | Rejected | Reason |
|---|---|---|---|
| Module placement | `plugins/sulis/scripts/_terminal_launcher.py` | `plugins/sulis/scripts/terminal_launcher.py` (no underscore) | Matches existing `_wpxlib.py` convention — underscore signals "library importable by sibling scripts, not a CLI entry point" |
| Script lifetime | Persisted at `~/.sulis/changes/{change_id}/launch.sh` | tempfile (auto-deleted) | Debuggability — operator can re-run the exact script to reproduce a failed spawn |
| Linux terminal selection | Built-in priority (gnome-terminal → konsole → xterm) | Configurable via env var | Match ae's pattern; configurability is a future-when-needed change |
| No Windows | macOS + Linux only | macOS + Linux + Windows | Match ae_task_executor scope; Windows port deferred to when there's signal |
| No process pool | Single-spawn per call | Pooled / reusable sessions | NFR-2 + design doc — single-founder single-machine v1 |
| Stdlib only | `subprocess`, `platform`, `tempfile`, `pathlib`, `shlex`, `logging` | `python-fire` or other CLI sugar | Per NFR-5 — no new dependencies |
| Test strategy | Mock subprocess for unit; manual smoke for spawn | Integration tests that actually spawn | CI doesn't have a desktop; manual smoke is the only realistic path for real spawn verification |

---

## Open questions

(None blocking — all design-question marks resolved in the handoff.)

**Reserved-Vocabulary Sweep:** 6 proposed abstracts checked (`launch_change_terminal`, `_build_launch_script`, `_launch_macos`, `_launch_linux`, `_launch_headless`, `_write_session_json`) against the marketplace's K8s/Sulis-reserved set (none found via inspection — no `apiVersion:` + `kind:` YAML in this repo; sulis manifests not yet in play). No collisions.

---

## ADRs

- **ADR-001** — Port shape: strip + adapt + drop matrix from ae_task_executor source
- **ADR-002** — Module placement convention (`_terminal_launcher.py` underscore-prefixed lib alongside `_wpxlib.py`)

## Phase 5 + Phase 6 integration (added 2026-05-25 after user-flagged gap)

The TDD as originally drafted covered the **launcher mechanism in isolation**. After the plan-work step produced WPs 001-004, the user flagged that the design doc's "/sulis:change start opens a new terminal in the worktree with focused Sulis" experience requires three additional integration concerns:

1. **Pre-spawn reconnaissance** — `sulis-change start` must write `~/.sulis/changes/{change_id}/CONTEXT.md` BEFORE the terminal opens. The HERE-DOC pre-prompt references this file; without recon, the file doesn't exist and the prompt references nothing.
2. **HERE-DOC pre-prompt** — the spawn must invoke `claude --agent sulis "{pre-prompt}"` where the pre-prompt briefs the agent on the change ("You are focused on change CH-X: 'fix the auth bug'. ..."). Per the design doc § Session binding mechanics.
3. **Session-bound Sulis behaviour** — the Sulis agent body must read `SULIS_CHANGE_ID` at session start, resolve the change manifest via `_wpxlib.resolve_current_change()` (already shipped at Phase 5 #2), read the recon CONTEXT.md, and greet the founder in change-context mode.

These are captured as **WP-005**, **WP-006**, **WP-007** in the work-packages index. The original WPs 001-004 stay valid (they're the foundation); WPs 005-007 add the integration layer.

**Explicitly out of scope for this WP set** (Phase 6 work):
- `/sulis:change start` slash command (founder-facing wrapper around `sulis-change start --spawn`)
- `/sulis:changes` smartlog / dashboard view (also needs Phase 5 #4 SQLite — deferred)
- `/sulis:change focus CH-NNN` reattach to spawned terminal (needs session.json pid + window-focus)

After WPs 001-007 land at v0.43.0, founders running `sulis-change start --slug X --primitive Y --spawn` get the design-doc UX end-to-end. The slash-command wrapper + dashboard + reattach are Phase 6 work.

---

## Sizing Report

See `SIZING.md` for the full sFPC + ASR breakdown. Highlights:

- Tier: S (computed; user-accepted; 7-WP set after Phase 5+6 integration expansion remains within Tier-S 3-8 WP target)
- TDD length: ~245 lines (target was 100–200 for original 4-WP scope; integration section pushed it to 1.5× tier-S ceiling — accepted because the integration section is reference-shaped, not new design)
- ADRs produced: 2 (target: 1–2) ✓
- WPs produced: 7 (target tier-S: 3–8) ✓
- Pillar coverage applied: Form=gap-filled; Armor=gap-filled; Proof=gap-filled
- Authoritative sources referenced: 0 (no context index for this project; port draws from ae_task_executor reference + stdlib conventions + the change-as-primitive design doc itself)
- Sections that referenced rather than restated: Phase 5+6 integration section references the design doc + WPs 005-007 rather than restating
- Circuit breakers triggered: none
- Reserved-Vocabulary Sweep: 6 abstracts checked / 0 collisions / 0 renames / 0 shared-dispatch ADRs
