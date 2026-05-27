---
id: WP-002
title: Extend `_terminal_launcher.py` with platform dispatchers (_launch_macos / _launch_linux / _launch_headless)
status: pending
sequence_id: WP-002
dependsOn: [WP-001]
blocks: [WP-003]
primitive: extend
group: EXPAND
kind: backend
estimated_token_cost:
  input: 5k
  output: 4k
tdd_section: "3.1 Form (platform dispatchers) + 3.3 Armor (NFR-4 failure-mode honesty)"
adrs: [ADR-001]
---

## Context

Adds the cross-platform spawn dispatchers to the `_terminal_launcher.py` module created in WP-001. Each dispatcher takes a script path + change_id and returns a structured dict per the TDD § 3.1 public API contract.

The shape is a faithful port of ae_task_executor's `_launch_macos` / `_launch_linux` / `_launch_direct` methods (ADR-001), with the latter renamed `_launch_headless` for clarity.

Per TDD § Armor (NFR-4): no silent fallback to headless when visible was asked. Failure cases return `{"status": "failed", "error": "..."}` so the caller can surface honestly.

## Contract

```python
# Extended in this WP — added to _terminal_launcher.py:

import shutil
import subprocess
from pathlib import Path

def _launch_macos(
    script_path: Path,
    change_id: str,
    visible: bool,
) -> dict:
    """Spawn via `osascript -e 'tell Terminal to do script ...'`.

    Returns:
        {"status": "spawned", "pid": int, "terminal_app_used": "Terminal.app",
         "script_path": str, "error": None}

    Or on failure:
        {"status": "failed", "pid": None, "terminal_app_used": None,
         "script_path": str, "error": "<reason>"}
    """

def _launch_linux(
    script_path: Path,
    change_id: str,
    visible: bool,
) -> dict:
    """Try gnome-terminal → konsole → xterm in order via `shutil.which`.

    On none-found: returns {"status": "failed", ..., "error": "no supported
    terminal app found; install gnome-terminal, konsole, or xterm — or
    pass visible=False for headless"}

    No silent fallback to headless (NFR-4).
    """

def _launch_headless(
    script_path: Path,
    change_id: str,
) -> dict:
    """Background subprocess invocation. Used when visible=False.

    Returns:
        {"status": "spawned", "pid": int, "terminal_app_used": "headless",
         "script_path": str, "error": None}
    """
```

State invariants:
- All three dispatchers return the structured dict shape (never raise; failures go in `error`).
- `_launch_linux` MUST NOT fall back to headless when no terminal app is found (NFR-4 honesty).
- `_launch_macos` MUST set `terminal_app_used` to `"Terminal.app"` (forward-compat: future Iterm2 support is a follow-up).

## Definition of Done

### Red — Failing tests written

- [ ] `tests/unit/test_terminal_launcher.py::test_launch_macos_invokes_osascript` — mock `subprocess.Popen`; assert call args contain `osascript` + `tell Terminal to do script`
- [ ] `tests/unit/test_terminal_launcher.py::test_launch_macos_returns_spawned_dict` — assert returned dict has `status="spawned"`, `terminal_app_used="Terminal.app"`, `pid` int, `error` None
- [ ] `tests/unit/test_terminal_launcher.py::test_launch_linux_tries_gnome_first` — mock `shutil.which` to return gnome-terminal path; assert subprocess invoked with gnome-terminal
- [ ] `tests/unit/test_terminal_launcher.py::test_launch_linux_falls_back_to_konsole` — gnome-terminal unavailable, konsole available
- [ ] `tests/unit/test_terminal_launcher.py::test_launch_linux_falls_back_to_xterm` — only xterm available
- [ ] `tests/unit/test_terminal_launcher.py::test_launch_linux_fails_when_no_terminal_app` — `shutil.which` returns None for all three; assert `{"status": "failed", ...}` with NFR-4-honest error message; assert NO subprocess call made
- [ ] `tests/unit/test_terminal_launcher.py::test_launch_headless_uses_background_subprocess` — assert Popen called with stdout=DEVNULL or similar non-interactive shape
- [ ] `tests/unit/test_terminal_launcher.py::test_launch_headless_returns_spawned_dict` — assert `terminal_app_used="headless"`

### Green — Implementation makes tests pass

- [ ] All Red tests pass
- [ ] Combined dispatchers ≤ 100 LOC (target — matches ae's shape)
- [ ] Each dispatcher's error path produces an actionable founder-facing error string (per NFR-4)
- [ ] No try/except that silently swallows subprocess errors (per `references/boring-code.md`)

### Blue — Refactor complete

- [ ] Linux terminal priority list extracted to module-level constant `_LINUX_TERMINAL_APPS = ("gnome-terminal", "konsole", "xterm")` — readable + future-extension point
- [ ] Common dict-construction logic for spawned/failed deduplicated if it grew (probably a one-liner — only refactor if there's actual duplication)
- [ ] No new behaviour introduced in Blue

## Sequence

- **dependsOn:** WP-001 (module file must exist; uses validators internally for defence-in-depth)
- **blocks:** WP-003 (public entry point composes the dispatchers)
- **Parallelisable with:** none (same file as WP-001 + WP-003)

## Estimated Token Cost

- **Input:** ~5k (TDD § 3.1 + 3.3 + ae source `terminal_launcher.py` lines 275-377 for reference)
- **Output:** ~4k (the 3 dispatcher functions + tests)
- **Total:** ~9k

## Notes

- The osascript shape used by ae:
  ```python
  applescript = f'tell application "Terminal" to do script "bash {script_path}"'
  subprocess.Popen(["osascript", "-e", applescript], ...)
  ```
  This works because `do script` opens a NEW window and runs the command in it. The osascript process itself exits quickly; Terminal.app continues running.
- `_launch_linux` returning the EARLIEST available terminal app is intentional — matches ae's pattern. Future configurability via `SULIS_LINUX_TERMINAL` env-var is a follow-up if signal warrants.
- pid returned for macOS is the osascript process's pid, NOT the Terminal.app window pid (which is harder to capture cross-platform). For reattach in Phase 6, additional pid-tracking will be needed.
