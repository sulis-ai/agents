---
id: ADR-002
title: Module placement — `_terminal_launcher.py` underscore-prefixed lib alongside `_wpxlib.py`
status: accepted
date: 2026-05-25
deciders: [iain]
---

## Context

The port introduces a new module in `plugins/sulis/scripts/`. The directory currently contains:

- **CLI entry-points** (no underscore): `wpx`, `wpx-pipeline`, `wpx-train`, `wpx-blocker`, `wpx-findings`, `wpx-index`, `wpx-journal`, `wpx-step12`, `wpx-worktree`, `wpx-wp`, `sulis-change`
- **Shared library** (underscore-prefixed, imported by the CLIs): `_wpxlib.py`

`_wpxlib.py` (3679 LOC) holds all shared subprocess helpers, change-related helpers, ULID generation, back-integration mechanic. The underscore signals "library, not CLI."

The terminal-launcher port is a library (imported by `sulis-change`), not a CLI entry-point. We need to decide whether to follow the underscore convention.

## Decision

Place the port at `plugins/sulis/scripts/_terminal_launcher.py`. Match the underscore-prefixed library convention established by `_wpxlib.py`.

## Options Considered

- **`_terminal_launcher.py` (chosen)** — matches existing library convention; sibling-script imports look uniform (`from _terminal_launcher import launch_change_terminal`).
- **`terminal_launcher.py` (no underscore)** — rejected: would suggest it's a CLI entry-point. The directory's pattern is "underscore = library; no underscore = executable." Breaking the pattern would mislead future readers.
- **Inline into `_wpxlib.py`** — rejected: `_wpxlib.py` is already 3679 LOC and growing. The terminal launcher is a logically distinct concern (OS-spawn vs git-mechanics) that deserves its own module.
- **Create a `plugins/sulis/scripts/lib/` directory** — rejected: would require moving `_wpxlib.py` too, which means touching every sibling script's import block. Out of scope for this port.

## Consequences

- **Positive:** Uniform library convention. New readers learn one rule (`_` prefix = library) once.
- **Negative:** As the script library count grows (`_change.py` + `_session.py` + `_terminal_launcher.py` etc.), a `lib/` subdirectory may become warranted. Tracked as a future-refactor signal.
- **Neutral:** Import statements look the same: `from _terminal_launcher import launch_change_terminal` (mirrors `from _wpxlib import ...`).
