---
id: WP-003
title: Extend `_terminal_launcher.py` with `launch_change_terminal` public entry-point + session.json bookkeeping
status: pending
sequence_id: WP-003
dependsOn: [WP-001, WP-002]
blocks: [WP-004]
primitive: extend
group: EXPAND
kind: backend
estimated_token_cost:
  input: 6k
  output: 3k
tdd_section: "3.1 Form (public API + composition root) + 3.4 Proof (end-to-end test)"
adrs: [ADR-001]
---

## Context

Composes WP-001's validators + script-builder and WP-002's platform dispatchers into the public `launch_change_terminal` function — the single entry-point callers go through.

Also adds the session bookkeeping: persisted `launch.sh` + `session.json` under `~/.sulis/changes/{change_id}/`. The persistence rationale (debuggability over disposable tempfiles) is locked in the TDD's Trade-offs table.

This is the smallest WP — pure composition over the already-tested WP-001 + WP-002 surface. The novelty is the session.json schema + the per-platform dispatch decision based on `platform.system()`.

## Contract

```python
# Extended in this WP — added to _terminal_launcher.py:

import json
import platform
from datetime import datetime, timezone

def launch_change_terminal(
    change_id: str,
    worktree_path: Path | str,
    *,
    visible: bool = True,
    entry_command: str = "claude --agent sulis",
    extra_env: dict[str, str] | None = None,
) -> dict:
    """Spawn a new terminal in the change worktree with SULIS_CHANGE_ID set.

    Composes:
        1. Validate all inputs (raises ValueError on bad input)
        2. Build the launch.sh content via _build_launch_script
        3. Persist launch.sh at ~/.sulis/changes/{change_id}/launch.sh (chmod +x)
        4. Dispatch to _launch_{macos|linux|headless} based on platform + visible
        5. Persist session.json with {pid, terminal_app_used, spawned_at, script_path}
        6. Return the structured dict from the dispatcher + session.json path

    Returns:
        {
            "status": "spawned" | "failed",
            "pid": int | None,
            "terminal_app_used": str | None,
            "script_path": str,
            "session_json_path": str,
            "error": str | None,
        }

    Raises:
        ValueError on invalid change_id, worktree_path, entry_command, or extra_env.
    """

# Session JSON schema:
# {
#   "change_id": "01HYQC71000000000000000000",
#   "pid": 12345,
#   "terminal_app_used": "Terminal.app",
#   "script_path": "/Users/iain/.sulis/changes/01HYQC.../launch.sh",
#   "spawned_at": "2026-05-25T20:00:00Z"
# }
```

State invariants:
- `launch.sh` is written with mode 0o755 (executable for owner).
- `session.json` is written ONLY on `status="spawned"` — not on failure (no orphan records).
- `~/.sulis/changes/{change_id}/` directory is created if absent (mkdir -p).
- Visible-fallback to headless does NOT happen automatically; if `visible=True` on an unknown platform (not macOS / not Linux), return `{"status": "failed", "error": "unsupported platform: <platform.system()>; pass visible=False or run on macOS/Linux"}`.

## Definition of Done

### Red — Failing tests written

- [ ] `tests/unit/test_terminal_launcher.py::test_launch_change_terminal_validates_change_id` — bad ULID raises ValueError BEFORE any subprocess call
- [ ] `tests/unit/test_terminal_launcher.py::test_launch_change_terminal_validates_worktree_path` — nonexistent dir raises ValueError
- [ ] `tests/unit/test_terminal_launcher.py::test_launch_change_terminal_writes_executable_launch_script` (uses tmp_path for `~/.sulis`; mocks platform.system; mocks Popen)
- [ ] `tests/unit/test_terminal_launcher.py::test_launch_change_terminal_writes_session_json_on_spawn`
- [ ] `tests/unit/test_terminal_launcher.py::test_launch_change_terminal_does_not_write_session_json_on_failure`
- [ ] `tests/unit/test_terminal_launcher.py::test_launch_change_terminal_dispatches_to_macos_on_darwin` — mock `platform.system()` returns "Darwin"; assert `_launch_macos` called
- [ ] `tests/unit/test_terminal_launcher.py::test_launch_change_terminal_dispatches_to_linux_on_linux` — mock returns "Linux"
- [ ] `tests/unit/test_terminal_launcher.py::test_launch_change_terminal_fails_on_unknown_platform_visible` — mock returns "Windows" with visible=True → `{"status": "failed", "error": "unsupported platform: ..."}`
- [ ] `tests/unit/test_terminal_launcher.py::test_launch_change_terminal_uses_headless_on_unknown_platform_invisible` — mock returns "Windows" with visible=False → dispatches to `_launch_headless`

### Green — Implementation makes tests pass

- [ ] All Red tests pass
- [ ] `launch_change_terminal` ≤ 40 LOC (target — small composition)
- [ ] Module docstring + function docstring complete

### Blue — Refactor complete

- [ ] Platform dispatch logic extracted to `_dispatch_for_platform(visible, platform_name) -> Callable | None` if the if/elif tree grew past 3 branches
- [ ] Session.json write extracted to `_write_session_json(change_dir, payload) -> Path` if the inline JSON-write code is more than ~10 LOC
- [ ] No new behaviour introduced in Blue

## Sequence

- **dependsOn:** WP-001 (validators + script builder), WP-002 (platform dispatchers)
- **blocks:** WP-004 (sulis-change start uses this function)
- **Parallelisable with:** none (same file)

## Estimated Token Cost

- **Input:** ~6k (TDD § 3.1 + 3.4 + the WP-001 + WP-002 module state + session.json schema in TDD)
- **Output:** ~3k (the entry-point function + composition tests; ~80 LOC)
- **Total:** ~9k

## Notes

- `~/.sulis/changes/{change_id}/` directory creation is idempotent (`mkdir -p`). The same directory will be used by Phase 5 #4's SQLite heartbeat work (deferred) — co-tenancy works because both write distinct files.
- Tests use `monkeypatch.setenv("HOME", str(tmp_path))` to redirect the `~/.sulis/` writes — avoids polluting the actual user dir during test runs.
- The dispatcher's returned `script_path` MUST match what `launch_change_terminal` wrote to disk (round-trip checkable).
