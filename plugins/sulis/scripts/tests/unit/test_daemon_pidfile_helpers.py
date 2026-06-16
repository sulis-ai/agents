"""WP-001 (harden-daemon-wedge-self-heal) — the daemon's pidfile helper
functions: best-effort write + a PID start-token source.

Contract: ``WP-001-daemon-writes-identity-pidfile.md`` Definition of Done > Red
(``tests/unit/test_daemon_pidfile_helpers.py``) + spec §Constraints (best-
effort, never crash on recovery I/O) + ADR-003 (stdlib-only). HD-001.

Verification posture (MEA-09, deterministic): the helpers are small stdlib-only
functions on the daemon module. ``_write_pidfile`` is exercised against an
**unwritable path** (a real directory whose write fails) to prove the best-
effort guarantee — a failed write degrades, never raises. ``_process_start_token``
is exercised against a **dead PID** to prove it returns ``None`` rather than
raising when ``ps`` cannot read the process. No real daemon process, no mocks.

Tests (RED first, per the WP Definition of Done):
    test_daemon_pidfile_helpers.py::test_write_pidfile_best_effort_does_not_crash_on_unwritable_path
    test_daemon_pidfile_helpers.py::test_process_start_token_returns_none_for_dead_pid
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

# The helpers live on the daemon module (the daemon's own identity, not the
# engine's). Importing them is the first thing that fails before WP-001.
_SCRIPTS_DIR = Path(__file__).resolve().parents[2]
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import session_manager_daemon  # noqa: E402


def _spawn_then_reap_pid() -> int:
    """Spawn a trivial child, wait for it to exit, and return its now-dead PID.

    The PID is guaranteed dead (we reaped it) so ``ps`` cannot read it — the
    deterministic substrate for the start-token-on-dead-pid case without racing
    a live process."""
    proc = subprocess.Popen([sys.executable, "-c", "pass"])
    proc.wait()
    return proc.pid


def test_write_pidfile_best_effort_does_not_crash_on_unwritable_path(
    tmp_path: Path,
) -> None:
    """A failed pidfile write must be caught + degrade — the daemon still boots.
    Point the write at a path **inside a non-existent, uncreatable parent** (a
    regular file used as a directory) so the atomic write fails; the helper must
    return without raising and without leaving the target behind."""
    # A regular file masquerading as the pidfile's parent directory: writing
    # `<file>/d.pid` cannot succeed (ENOTDIR), so the write is forced to fail.
    not_a_dir = tmp_path / "not_a_dir"
    not_a_dir.write_text("i am a file, not a directory\n")
    unwritable = str(not_a_dir / "d.pid")

    # MUST NOT raise — best-effort.
    session_manager_daemon._write_pidfile(unwritable, os.getpid())

    assert not os.path.exists(unwritable), (
        "the failed best-effort write must not leave a pidfile behind"
    )


def test_process_start_token_returns_none_for_dead_pid() -> None:
    """The start-token source is best-effort: for a PID that is gone (``ps``
    cannot read it) it returns ``None`` rather than raising — the caller treats
    a missing token as 'no durable identity recorded', it must never crash."""
    dead_pid = _spawn_then_reap_pid()

    token = session_manager_daemon._process_start_token(dead_pid)

    assert token is None, (
        f"_process_start_token({dead_pid}) returned {token!r}, expected None "
        "for a dead PID"
    )
