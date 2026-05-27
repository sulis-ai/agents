---
id: ADR-001
title: Port shape — strip + adapt + drop matrix from ae_task_executor
status: accepted
date: 2026-05-25
deciders: [iain]
---

## Context

`ae_task_executor/terminal_launcher.py` (504 LOC) is the proven reference for cross-platform terminal spawning. The change-as-primitive design doc (`plugins/sulis/docs/change-as-primitive-design.md`) explicitly names this file as the port source for Phase 5 #5.

Direct file read + `sulis:analyse-codebase` workspace probe identified:

- The full ae terminal stack is 5 files / ~2500 LOC (terminal_launcher + terminal_manager + terminal_pool + 2 visible-mode variants)
- Only `terminal_launcher.py`'s `launch_terminal` + 3 platform dispatchers (~150 LOC) is load-bearing for sulis's single-founder single-machine v1 use case
- The other 4 files implement session pooling + multi-session orchestration — capabilities sulis doesn't need until SaaS phase

We need to decide what to port, what to adapt, what to drop.

## Decision

Apply a strip + adapt + drop matrix to the ae source:

| ae Source | Decision | New location |
|---|---|---|
| `launch_terminal` + `_launch_macos` + `_launch_linux` + `_launch_direct` (~150 LOC) | **Adopt** verbatim (shape preserved; rename `_launch_direct` → `_launch_headless` for clarity) | `_terminal_launcher.py` private platform-dispatchers |
| `create_launch_script` (~250 LOC) | **Adapt** — same shell-script scaffolding; new body (cd to worktree + export SULIS_CHANGE_ID + exec `claude --agent sulis`) | `_terminal_launcher.py` `_build_launch_script()` |
| `wait_for_ready` + `check_completion` + `cleanup_session` (~75 LOC) | **Drop** — sulis lifecycle is "spawn and forget"; the founder closes the terminal when done. Future `/sulis:change focus` may add reattach but not session-completion polling | — |
| Task-ID parsing helpers (`_extract_story_id`, `_parse_compound_task_id`, `_parse_task_id_components`, `_validate_story_id_format` — ~75 LOC) | **Drop** — ae-specific story-ID format; sulis already has ULID + Crockford handle | — |
| `terminal_manager.py` (1012 LOC) — multi-session orchestration | **Drop entirely** — no use case in single-founder v1 | — |
| `terminal_manager_visible.py` (392 LOC) — visible-mode variant | **Drop entirely** | — |
| `terminal_pool.py` (439 LOC) + `terminal_pool_visible.py` (175 LOC) — session pooling | **Drop entirely** — pooling defers to SaaS phase | — |

Net port target: ~250 LOC in `_terminal_launcher.py` (down from 504 LOC of ae's single file, down from 2522 LOC of ae's full terminal stack).

## Options Considered

- **Full port (everything)** — rejected: ~2500 LOC for capabilities sulis doesn't need. Drags in session-management + pooling + visible-mode coupling without value.
- **Verbatim port of `terminal_launcher.py` only** — rejected: includes ~75 LOC of task-ID parsing that doesn't apply (story-IDs vs ULID). Importing dead code now means it confuses future readers.
- **Strip + adapt + drop matrix (chosen)** — port the load-bearing dispatch logic; adapt the script body to sulis vocabulary; drop the rest.

## Consequences

- **Positive:** ~250 LOC of focused, sulis-specific code. No dead surface. Faithful to ae's proven cross-platform shape on the parts that matter.
- **Negative:** When sulis eventually wants multi-session sync or reattach-window-focus, those capabilities have to be re-derived (not just imported). Documented as deferred in the handoff doc.
- **Neutral:** ae remains the canonical reference for the dispatch shape — future sulis improvements can cross-check against ae's evolution.
