"""WP-003 (CH-01KTGY) — the PTY io-model at the single spawn seam.

Contract: ``SESSION_MANAGER_CONTRACT.extension.md`` §2.12.1 (io-mode fixed at
``open``, additive ``SessionSpec.io_mode`` defaulted ``"pipe"``), §2.11
(scrollback content model), §2.15 (``PTY_OPEN_FAILED`` Internal error); ADR-001
(a pty io-model alongside pipes, ``os.openpty`` stdlib-only); TDD §1.1.

Verification posture (MEA-09, no mocks in the master-read proof): the
master-read unit drives a **real** pty-backed child (WP-006's ``fake_claude_child``
``pty`` mode) over a **real** ``os.openpty()`` pair the manager owns from spawn.
The manager spawns the child with the slave end as its controlling terminal and
reads the master end into the session's :class:`ScrollbackBuffer`; the test
writes a known line to the master and asserts the child's echo lands in the
scrollback snapshot. Only ``os.openpty`` is monkeypatched in the failure unit —
to force the spawn-time ``PTY_OPEN_FAILED`` path that has no other deterministic
trigger.

Tests (RED first, per the WP Definition of Done):
    test_pty_session.py::test_master_read_appends_scrollback
    test_pty_session.py::test_pty_open_failed_maps_internal
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import pytest

from _session_manager.adapter import Capabilities, SessionSpec
from _session_manager.events import InternalError
from _session_manager import manager as manager_module
from _session_manager.manager import SessionManager

# The shared fake-claude child helper lives under tests/lib (mirrors the
# integration suites' import pattern — sys.path.insert, then import).
_SCRIPTS_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_SCRIPTS_DIR / "tests" / "lib"))
import fake_claude_child  # noqa: E402

# Bounded wait for the master-reader pump to surface bytes: long enough never to
# flake on a loaded CI runner, short enough that a real hang fails fast. Matches
# the session suites' _WAIT.
_WAIT = 5.0


class _PtyChildAdapter:
    """A real :class:`ProviderAdapter` whose child runs as a raw PTY terminal.

    ``spawn_argv`` starts WP-006's ``fake_claude_child`` in ``pty`` mode (it
    echoes stdin to stdout and emits ``PTY_PONG`` on the ``__PTY_PING__``
    sentinel). ``encode`` / ``decode`` / ``turn_complete`` are unused on the pty
    path (a pty session is a terminal view, not a structured-chat stream — the
    master-reader pump appends raw bytes to scrollback rather than decoding into
    the event log), but the Protocol shape is honoured so the manager treats it
    like any other adapter."""

    capabilities = Capabilities(
        supports_resume=False,
        supports_tools=False,
        supports_partial_streaming=False,
    )

    def __init__(self, child: Path) -> None:
        self._child = child

    def spawn_argv(self, spec: SessionSpec) -> list[str]:
        return fake_claude_child.child_argv(self._child, mode="pty")

    def encode(self, command: str) -> bytes:  # pragma: no cover - unused on pty
        return command.encode("utf-8")

    def decode(self, line: bytes):  # pragma: no cover - unused on pty
        return None

    def turn_complete(self, event) -> bool:  # pragma: no cover - unused on pty
        return False


def _wait_for(predicate, timeout: float = _WAIT) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


def test_master_read_appends_scrollback(tmp_path: Path) -> None:
    """Open a ``pty``-mode session backed by WP-006's pty fake child; write a
    known line to the PTY master; assert the session's
    ``ScrollbackBuffer.snapshot()`` contains the child's echoed bytes (§2.11 /
    §2.12.1, ADR-001).

    The child echoes stdin straight back to stdout under the controlling tty, so
    a line written to the master returns on the master — and the manager's
    master-reader pump appends it to the session's scrollback. This is the
    master-read → scrollback append loop the viewer (WP-004) later snapshots.
    """
    child = fake_claude_child.write_child(tmp_path)
    adapter = _PtyChildAdapter(child)
    mgr = SessionManager({"pty": adapter}, start_maintenance=False)
    try:
        spec = SessionSpec(provider="pty", cwd=str(tmp_path), io_mode="pty")
        session = mgr.open("term", spec)

        # Drive the child: a line written to the PTY master is echoed back by the
        # child (pty mode), so it returns on the master and the pump appends it.
        os.write(session.pty_master_fd, b"hello\n")

        assert _wait_for(lambda: b"hello" in session.scrollback.snapshot()), (
            "master-reader pump did not append the child's echoed bytes to "
            f"scrollback; snapshot was {session.scrollback.snapshot()!r}"
        )
    finally:
        mgr.shutdown()


def test_pty_open_failed_maps_internal(tmp_path: Path, monkeypatch) -> None:
    """Force ``os.openpty`` to fail on a ``pty``-mode open; assert the manager
    raises an Internal ``PTY_OPEN_FAILED`` error (§2.15, ADR-001).

    ``os.openpty`` failure (fd exhaustion, kernel pty limit) is the spawn-time
    failure mode unique to the pty branch; it maps onto the existing
    three-category model as Internal (a bug / resource exhaustion — log +
    escalate, do not retry blindly), not a new category.
    """
    child = fake_claude_child.write_child(tmp_path)
    adapter = _PtyChildAdapter(child)
    mgr = SessionManager({"pty": adapter}, start_maintenance=False)

    def _boom() -> tuple[int, int]:
        raise OSError("out of ptys")

    monkeypatch.setattr(os, "openpty", _boom)
    try:
        spec = SessionSpec(provider="pty", cwd=str(tmp_path), io_mode="pty")
        with pytest.raises(InternalError) as excinfo:
            mgr.open("term", spec)
        assert excinfo.value.code == "PTY_OPEN_FAILED", (
            f"expected PTY_OPEN_FAILED, got {excinfo.value.code!r}"
        )
    finally:
        mgr.shutdown()


def test_pty_spawn_failure_maps_internal_and_closes_fds(
    tmp_path: Path, monkeypatch
) -> None:
    """Force the pty-mode ``subprocess.Popen`` to fail AFTER ``os.openpty``
    succeeds; assert ``PTY_OPEN_FAILED`` Internal AND that both pty fds were
    closed (no fd leak on a failed open) (§2.15, Armor).

    The two fds ``os.openpty`` allocated are the manager's until the child owns
    the slave; a spawn failure must release both so a flapping pty open cannot
    exhaust the process's fd table. This pins the spawn-with-slave failure branch
    of ``_spawn_pty_process`` (distinct from the ``os.openpty`` failure above).
    """
    child = fake_claude_child.write_child(tmp_path)
    adapter = _PtyChildAdapter(child)
    mgr = SessionManager({"pty": adapter}, start_maintenance=False)

    real_openpty = os.openpty
    opened: list[int] = []

    def _tracking_openpty() -> tuple[int, int]:
        master_fd, slave_fd = real_openpty()
        opened.extend((master_fd, slave_fd))
        return master_fd, slave_fd

    def _popen_boom(*args, **kwargs):
        raise OSError("spawn refused")

    monkeypatch.setattr(os, "openpty", _tracking_openpty)
    monkeypatch.setattr(manager_module.subprocess, "Popen", _popen_boom)
    try:
        spec = SessionSpec(provider="pty", cwd=str(tmp_path), io_mode="pty")
        with pytest.raises(InternalError) as excinfo:
            mgr.open("term", spec)
        assert excinfo.value.code == "PTY_OPEN_FAILED"
        # Both fds the failed open allocated must now be closed — os.fstat on a
        # closed fd raises EBADF.
        assert opened, "openpty was never called"
        for fd in opened:
            with pytest.raises(OSError):
                os.fstat(fd)
    finally:
        mgr.shutdown()
