# Technical Design Document — terminal-launcher-port

> **ARCH-ID:** ARCH-001
> **Status:** designed
> **Sized:** tier S (sFPC=2, ASR=6); target ~100–200 lines (revised target ~200–250 to absorb the integration surface, with rationale below)
> **Source:** `.specifications/terminal-launcher-port/HANDOFF_TO_SEA.md` (early-handoff mode — no SRD)
> **Linked phase:** Phase 5 #5 of the change-as-primitive build

---

## Overview

Port the cross-platform terminal-spawning capability from `ae_task_executor/terminal_launcher.py` (504 LOC) into `plugins/sulis/scripts/_terminal_launcher.py`. The port enables `sulis-change start --spawn` to open a new terminal window in the change worktree, with `SULIS_CHANGE_ID` exported and a focused `claude --agent sulis` session inside it. The agent receives a briefing pre-prompt about the change and reads a pre-spawn `CONTEXT.md` recon at session start.

Strip ae-specific surface (task-ID parsing, session pooling, multi-session manager). Adopt the proven shell-script-per-session + per-platform dispatcher pattern.

**Scope.** The TDD covers two cohesive concerns:
- **Launcher mechanism** — module, validators, dispatchers, public entry-point (WP-001..WP-003).
- **Session integration** — the recon write, the pre-prompt body, the agent's session-start behaviour, and the `sulis-change start` composition that wires them together (WP-004..WP-007).

Both concerns ship together at v0.43.0 because shipping the mechanism without the integration produces a working spawn that opens a cold Sulis session — not the founder UX the design doc describes.

---

## Source Specification

- `.specifications/terminal-launcher-port/HANDOFF_TO_SEA.md` — port intent, NFRs, MUCs, decisions-already-made
- `ae_task_executor/terminal_launcher.py` — proven reference (read directly during discover)
- `plugins/sulis/docs/change-as-primitive-design.md` § "Session binding" — operational specification of the founder UX
- Phase 5 #2 helper: `_wpxlib.resolve_current_change()` — already shipped; used by WP-007 agent body

---

## Form — Structural Design

### Component inventory

| Component | Location | Purpose | Introduced by |
|---|---|---|---|
| `_terminal_launcher.py` | `plugins/sulis/scripts/` | The port — script builder, validators, dispatchers, entry-point | WP-001..003, extended in WP-006 |
| `_change_context.py` | `plugins/sulis/scripts/` | Pre-spawn recon writer (`write_change_context`) | WP-005 |
| `sulis-change` (modified) | `plugins/sulis/scripts/` | Caller — orchestrates recon → pre-prompt build → spawn | WP-004 |
| `sulis.md` agent body (modified) | `plugins/sulis/agents/` | Session-start behaviour when `SULIS_CHANGE_ID` is present | WP-007 |
| `~/.sulis/changes/{change_id}/launch.sh` | runtime artefact | Persisted launch script per session (debuggable; re-runnable) | WP-003 |
| `~/.sulis/changes/{change_id}/CONTEXT.md` | runtime artefact | Pre-spawn recon — change identity + git state + suggested next step | WP-005 |
| `~/.sulis/changes/{change_id}/session.json` | runtime artefact | `pid`, `terminal_app_used`, `spawned_at` for later reattach (Phase 6 deferred) | WP-003 |

### Public API — `_terminal_launcher`

```python
def launch_change_terminal(
    change_id: str,
    worktree_path: Path | str,
    *,
    visible: bool = True,
    entry_command: str = "claude --agent sulis",
    extra_env: dict[str, str] | None = None,
    pre_prompt: str | None = None,
) -> dict:
    """Spawn a new terminal in the change worktree with SULIS_CHANGE_ID set.

    Returns:
        {
            "status": "spawned" | "failed",
            "pid": int | None,
            "terminal_app_used": str | None,  # "Terminal.app" | "gnome-terminal" | ...
            "script_path": str,
            "session_json_path": str,
            "error": str | None,
        }

    Raises ValueError on invalid inputs (bad change_id, bad worktree path,
    invalid entry_command, invalid extra_env keys, invalid pre_prompt).
    """
```

### Public API — `_change_context`

```python
def write_change_context(
    change_id: str,
    metadata: dict,
    repo_root: Path,
) -> Path:
    """Gather pre-spawn recon and write CONTEXT.md to
    ~/.sulis/changes/{change_id}/CONTEXT.md. Returns the absolute path.

    Pure-read — never modifies the repo.
    """
```

### Internal structure

```
_terminal_launcher.py  (~280 LOC target)
├── Validators (pure functions):
│   ├── validate_entry_command(cmd) -> tuple[bool, str]
│   ├── validate_extra_env_key(key) -> tuple[bool, str]
│   ├── validate_worktree_path(path) -> tuple[bool, Path]
│   └── _validate_pre_prompt(text) -> tuple[bool, str]              # WP-006
├── Shell-script construction:
│   └── _build_launch_script(change_id, worktree_path, entry_command,
│                            extra_env, pre_prompt) -> str          # extended WP-006
├── Platform dispatchers (private):
│   ├── _launch_macos(script_path, change_id, visible) -> dict
│   ├── _launch_linux(script_path, change_id, visible) -> dict
│   └── _launch_headless(script_path, change_id) -> dict
├── Session bookkeeping (private):
│   └── _write_session_json(change_dir, pid, terminal_app, script_path) -> Path
└── Public entry-point:
    └── launch_change_terminal(change_id, worktree_path, *, visible,
                               entry_command, extra_env, pre_prompt) -> dict

_change_context.py  (~120 LOC target)
├── _PRIMITIVE_NEXT_STEP_HINTS: dict[str, str]   # opinionated per-primitive next step
├── _head_sha / _base_sha / _ahead_behind (private git helpers)
├── _render_context_md(change_id, metadata, git_state) -> str
└── write_change_context(change_id, metadata, repo_root) -> Path
```

### Composition root — `sulis-change start --spawn`

```
sulis-change cmd_start
  ├── existing: validate inputs, create branch + worktree, write metadata
  ├── (always) _change_context.write_change_context(change_id, metadata, repo_root)
  └── (when --spawn) _build_change_pre_prompt(change_id, handle, slug, intent,
                                              primitive, context_md_path)
                     ↓
                     _terminal_launcher.launch_change_terminal(
                         change_id, worktree_path, visible=True,
                         pre_prompt=<built body>)
                     ↓
                     emit_ok(data={..., context_md_path, spawn_result})
```

### Dependency graph

```
sulis-change (caller)
  ├── _change_context.write_change_context()
  │     └── _wpxlib._run [existing — git subprocess helper]
  └── _terminal_launcher.launch_change_terminal()
        ├── _wpxlib.validate_change_ulid() [existing]
        ├── validate_worktree_path() [new — WP-001]
        ├── _validate_pre_prompt() [new — WP-006]
        ├── _build_launch_script() [new — WP-001, extended WP-006]
        └── _launch_{macos|linux|headless}() [new — WP-002]
              └── subprocess.Popen [stdlib]
```

No new external dependencies. All operations use stdlib only (per NFR-5).

### Agent session-start behaviour

The Sulis agent (`plugins/sulis/agents/sulis.md`, modified by WP-007) gains a new section *"Change context (when `SULIS_CHANGE_ID` is set)"* immediately after its identity / required-reading / workflow sections. The section codifies three branches: env-resolves-to-change (greet with recon's suggested next step), env-resolves-to-null (stale env, surface three options), env-unset (default behaviour, no regression). This makes the spawned Sulis session change-aware regardless of whether the pre-prompt is delivered or not — the env var alone is sufficient priming.

---

## Armor — Operational Hardening

### Input validation (MUC-1 — shell injection)

Every input passed into launch-script construction is validated before string concatenation:

| Input | Validator | Rejects |
|---|---|---|
| `change_id` | `_wpxlib.validate_change_ulid()` (existing) | non-Crockford-base32 or wrong length |
| `worktree_path` | `validate_worktree_path` → `Path(input).resolve()` + `.is_dir()` | non-existent directory, symlink to non-dir |
| `entry_command` | regex `^[a-z][a-z0-9 \-]+$` (default `"claude --agent sulis"`) | injection via metacharacters |
| `extra_env` keys | regex `^[A-Z_][A-Z0-9_]*$` | injection via `;`, `\n`, `$()`, backticks |
| `extra_env` values | `shlex.quote()` before insertion into the script | shell metacharacter escape |
| `pre_prompt` | `_validate_pre_prompt` — rejects bodies containing `SULIS_PROMPT_EOF` (heredoc-tag collision) or > 50_000 bytes (pathological size) | early-close of heredoc; runaway prompts |

Failures raise `ValueError` before any subprocess is launched.

### Pre-prompt delivery (ADR-003)

The pre-prompt is delivered as `claude`'s first positional argument via a quoted HERE-DOC:

```bash
exec {entry_command} "$(cat <<'SULIS_PROMPT_EOF'
{pre_prompt body verbatim}
SULIS_PROMPT_EOF
)"
```

The single-quoted heredoc tag (`<<'SULIS_PROMPT_EOF'`) disables bash parameter expansion and command substitution inside the body. `$HOME`, `${USER}`, backticks, `$(...)` in the prompt pass through verbatim — they are never re-interpreted by the shell. The validator's reject-if-tag-in-body rule prevents the body from prematurely closing the heredoc. See ADR-003 for the full mechanism comparison.

### Env-leak prevention (MUC-2)

The generated launch script begins with an explicit env-reset preamble:

```bash
#!/usr/bin/env bash
set -euo pipefail
# Carry-over env: only PATH, HOME, USER, TERM, LANG, LC_*.
unset $(compgen -v | grep -Ev '^(PATH|HOME|USER|TERM|LANG|LC_.*)$')
export SULIS_CHANGE_ID="{change_id}"
{extra_env_block}
cd "{worktree_path}"
exec {entry_command}{pre_prompt_heredoc if any}
```

The `compgen` line scrubs parent-shell variables not on the whitelist (e.g. `AWS_SECRET_ACCESS_KEY`, `GITHUB_TOKEN`) before `claude --agent sulis` runs.

### Failure-mode honesty (NFR-4)

Per-platform dispatchers return a structured dict with `status` and `error`. On Linux, if none of gnome-terminal / konsole / xterm are on `PATH`, the launcher returns `{"status": "failed", "error": "no supported terminal app found; install gnome-terminal, konsole, or xterm — or pass visible=False for headless"}`. No silent fallback to headless when visible was asked.

When `sulis-change start --spawn` is invoked and the spawn fails, the change-creation work is **not** unwound — the branch, worktree, metadata, and recon are committed. The JSON output surfaces `spawn_result.status == "failed"` so the founder can fall back to `cd worktree && claude --agent sulis` manually.

### Observability

`logger = logging.getLogger("sulis.terminal_launcher")`. Spawn attempts log at INFO; failures log at WARNING with the failure mode. No OpenTelemetry — port is too small to need it; `session.json` is the operational record. The recon `CONTEXT.md` doubles as a forensic artefact: any operator can `cat ~/.sulis/changes/{change_id}/CONTEXT.md` to see what the spawned Sulis was briefed on.

---

## Proof — Verification Protocol

### Unit tests (mocked subprocess)

| Test target | Strategy |
|---|---|
| `_build_launch_script` (no pre-prompt) | Snapshot generated script; verify env-scrub + `SULIS_CHANGE_ID` export + `cd` + `exec` lines in expected order |
| `_build_launch_script` (with pre-prompt) | Assert script contains `<<'SULIS_PROMPT_EOF'` (single-quoted tag); assert pre-prompt body appears verbatim including `$HOME` and backticks |
| Validators | Inject bad inputs (bad ULID, bad slug, path with `;`, env-var name with `\n`, pre-prompt containing heredoc tag, oversize pre-prompt); assert `ValueError` raised before any subprocess call |
| `_launch_macos` | Mock `subprocess.Popen`; assert osascript invocation shape; structured-dict return |
| `_launch_linux` | Mock `shutil.which` per dispatch order; verify NFR-4 honest failure when no terminal app found |
| `_launch_headless` | Mock subprocess; assert background invocation shape |
| `launch_change_terminal` | End-to-end with mocked dispatchers; assert session.json written; structured-dict return; `pre_prompt` kwarg forwarded |
| `write_change_context` (WP-005) | Build CONTEXT.md with mocked git helpers; verify change identity + git state + primitive-specific hint present; verify the recon does not modify the repo (git status before/after identical) |
| `_build_change_pre_prompt` (WP-004) | Verify the produced body contains the handle, intent, and absolute `context_md_path`; verify the body does not contain the heredoc tag |
| `sulis-change cmd_start` (WP-004) | Mock both `write_change_context` and `launch_change_terminal`; verify (a) recon always runs, (b) spawn only when `--spawn` set, (c) call order is recon-then-spawn, (d) spawn failure does not error the CLI |

### Manual smoke tests (not CI — CI has no desktop)

Documented procedures under `plugins/sulis/scripts/tests/manual/`:

- `smoke_terminal_launcher.md` — `python3 -c "launch_change_terminal(...)"` on macOS and Linux; verify new terminal opens, cd's to worktree, exports `SULIS_CHANGE_ID`, runs `claude --agent sulis`
- `smoke_sulis_change_start_spawn.md` — full `sulis-change start --slug X --primitive create --intent "..." --spawn` walkthrough; verify CONTEXT.md written, terminal opens, Sulis greets in change-context mode (composes with WP-007)
- `smoke_sulis_change_id_resolves.md` — set `SULIS_CHANGE_ID` to a valid existing ULID; run `claude --agent sulis "Hi"`; verify the greeting includes change identity + suggested next step
- `smoke_sulis_change_id_stale.md` — set `SULIS_CHANGE_ID` to a non-existent ULID; verify stale-env three-option response
- `smoke_sulis_change_id_unset.md` — `SULIS_CHANGE_ID` unset; verify default greeting (no regression)

### Chaos / failure-mode tests

- **NFR-4 honesty:** assert that on Linux-with-no-terminal-app, the launcher returns `{"status": "failed", ...}` rather than silently falling through to headless
- **MUC-1 shell-injection:** parametrised test injects shell metacharacters into each validated input; asserts `ValueError` before any subprocess call
- **MUC-2 env-leak:** build a script; assert the `unset` line lists the whitelist exactly + nothing else
- **Pre-prompt safety (WP-006):** parametrised test inserts `SULIS_PROMPT_EOF` as a substring of the prompt body; asserts `ValueError`
- **Pre-prompt no-expansion:** prompt body containing `$HOME`, backticks, `$(...)` appears verbatim in the generated script

---

## Trade-offs

| Decision | Chosen | Rejected | Reason |
|---|---|---|---|
| Module placement (launcher) | `plugins/sulis/scripts/_terminal_launcher.py` | `terminal_launcher.py` (no underscore) | Matches existing `_wpxlib.py` convention — underscore signals "library importable by sibling scripts". See ADR-002. |
| Module placement (recon) | `plugins/sulis/scripts/_change_context.py` (new module) | Adding to `_wpxlib.py` | `_wpxlib.py` is 3679 LOC and growing; recon is a logically distinct concern that deserves its own module |
| Script lifetime | Persisted at `~/.sulis/changes/{change_id}/launch.sh` | tempfile (auto-deleted) | Debuggability — operator can re-run the exact script to reproduce a failed spawn |
| Linux terminal selection | Built-in priority (gnome-terminal → konsole → xterm) | Configurable via env var | Match ae's pattern; configurability is a future-when-needed change |
| Pre-prompt delivery | Quoted HERE-DOC into positional argv | `--prompt` flag, stdin, tempfile, unquoted heredoc | See ADR-003 — only mechanism that simultaneously preserves multiline content, disables shell interpretation, and matches `claude`'s documented argv contract |
| Pre-prompt construction site | `sulis-change cmd_start` (caller) | Inside `_terminal_launcher` | Keeps the launcher free of Sulis-specific copy; prompt is a literal-string concern co-located with where change metadata is already in hand |
| Recon write timing | Unconditional (always runs in `cmd_start`) | Only when `--spawn` is set | Cost is small (3 git subprocess calls + one Markdown file); benefit is that future `/sulis:change focus` and `/sulis:changes` skills find the artefact already on disk |
| No Windows | macOS + Linux only | + Windows | Match ae_task_executor scope; Windows port deferred to when there's signal |
| No process pool | Single-spawn per call | Pooled / reusable sessions | NFR-2 — single-founder single-machine v1 |
| Stdlib only | `subprocess`, `platform`, `tempfile`, `pathlib`, `shlex`, `logging`, `json` | Any third-party CLI sugar | Per NFR-5 — no new dependencies |
| Test strategy | Mock subprocess for unit; manual smoke for actual spawn | Integration tests that actually spawn | CI doesn't have a desktop; manual smoke is the only realistic path |

---

## Open questions

None blocking. All design-question marks raised in the handoff are resolved either here or in ADR-001..003.

**Reserved-Vocabulary Sweep.** 11 proposed abstracts checked against the marketplace's K8s/Sulis-reserved set: `launch_change_terminal`, `_build_launch_script`, `_launch_macos`, `_launch_linux`, `_launch_headless`, `_write_session_json`, `write_change_context`, `_PRIMITIVE_NEXT_STEP_HINTS`, `_validate_pre_prompt`, `_PRE_PROMPT_HEREDOC_TAG`, `_build_change_pre_prompt`. No collisions found (no `apiVersion:` + `kind:` YAML in this repo; sulis manifests not yet shipped with reserved-noun conflicts). No renames required.

---

## ADRs

- **ADR-001** — Port shape: strip + adapt + drop matrix from ae_task_executor source
- **ADR-002** — Module placement convention (`_terminal_launcher.py` underscore-prefixed lib alongside `_wpxlib.py`)
- **ADR-003** — Pre-prompt delivery mechanism (quoted HERE-DOC into `claude`'s positional argument)

---

## What's NOT in this WP set (Phase 6 deferrals)

- `/sulis:change start` slash command — founder-facing wrapper around `sulis-change start --spawn`
- `/sulis:changes` smartlog / dashboard view — needs Phase 5 #4 SQLite (deferred)
- `/sulis:change focus CH-NNN` reattach to a spawned terminal — needs `session.json.pid` + os-specific window-focus
- Heartbeat / session liveness — Phase 5 #4
- Committed copy of `CONTEXT.md` at `.architecture/{project}/changes/{ulid}/CONTEXT.md` — local-only is sufficient for v0.43.0; commit-path is a Phase 5.x follow-up

After WPs 001..007 ship at v0.43.0, founders running `sulis-change start --slug X --primitive Y --spawn` get the design-doc UX end-to-end: new terminal in the change worktree, focused Sulis session aware of the change, recon already on disk for the agent to read.

---

## Sizing Report

See `SIZING.md` for the full sFPC + ASR breakdown. Highlights:

- Tier: **S** — computed (sFPC=2, ASR=6); user-accepted; 7-WP set fits the tier-S 3-8 WP target
- TDD length: ~315 lines (above the original 100–200 line target — at 1.5× the tier-S ceiling). **Why is this big?** The TDD covers two cohesive concerns (launcher mechanism + session integration) that must ship together. The pillar sections do not restate authoritative sources; the trade-offs table is dense, not decorative. Folding the integration into Form/Armor/Proof rather than a tacked-on prose paragraph cost ~70 lines but produced a structurally consistent document. Acceptable at 1.5× tier-S ceiling with this rationale; the alternative (two separate TDDs for launcher + integration) would force readers to reconcile by hand.
- ADRs produced: **3** (target tier-S: 1–2). **ADR rationale.** ADR-001 (port shape) and ADR-002 (module placement) are foundational and were locked at the original design. ADR-003 (pre-prompt delivery) crosses two systems — the bash launch-script generator and the `claude` CLI's argument contract — and is exactly the shape of decision the ADR format exists for. Burying it in WP-006 Notes would have hidden the rationale from the next reader who has to revisit the delivery choice.
- WPs produced: **7** (target tier-S: 3–8) ✓
- Pillar coverage applied: Form gap-filled, Armor gap-filled, Proof gap-filled
- Authoritative sources referenced: 0 (no context index for this project; port draws from `ae_task_executor` reference + stdlib conventions + the change-as-primitive design doc)
- Sections that referenced rather than restated: ADR-003 referenced (not restated) in Armor § "Pre-prompt delivery" and Trade-offs row
- Circuit breakers triggered: TDD-length 1.5× — addressed with the "Why is this big?" paragraph; ADR-count 1.5× — addressed with the "ADR rationale" paragraph
- Reserved-Vocabulary Sweep: 11 abstracts checked / 0 collisions / 0 renames / 0 shared-dispatch ADRs
