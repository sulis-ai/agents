"""WP-006 (CH-01KTGY) — proves the fake-claude child's ``pty`` reply mode
echoes input when run under a real controlling PTY.

This is the leaf test-infra dependency of the PTY round-trip WPs
(WP-003 master-read, WP-004 viewer, WP-005 socket, WP-010 end-to-end): those
integration tests need a **real** PTY-backed child to drive — MEA-09 forbids
mocking the terminal in integration. This unit proves the child, when spawned
with the slave end of an ``os.openpty()`` pair as its controlling terminal,
echoes the bytes written to the master (the defining behaviour of a tty in
cooked mode), so the round-trip tests have a real adapter to bind to.

Test (RED first, per the WP Definition of Done):
    test_fake_child_pty_mode.py::test_pty_child_echoes_input
"""

from __future__ import annotations

import contextlib
import os
import select
import subprocess
import sys
import termios
from collections.abc import Iterator
from pathlib import Path

# The shared fake-claude child helper lives under tests/lib (mirrors the
# integration suites' import pattern — sys.path.insert, then import).
_SCRIPTS_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_SCRIPTS_DIR / "tests" / "lib"))
import fake_claude_child  # noqa: E402


def _read_until(master_fd: int, needle: bytes, timeout_s: float = 5.0) -> bytes:
    """Read from ``master_fd`` until ``needle`` appears or ``timeout_s`` elapses.

    Returns everything read so far (whether or not the needle was found) — the
    caller asserts on the accumulated buffer.
    """
    buf = b""
    deadline = timeout_s
    while needle not in buf:
        ready, _, _ = select.select([master_fd], [], [], deadline)
        if not ready:
            break
        try:
            chunk = os.read(master_fd, 1024)
        except OSError:
            break
        if not chunk:
            break
        buf += chunk
    return buf


def _disable_tty_echo(slave_fd: int) -> None:
    """Turn off the slave tty's own cooked-mode echo (ECHO) so the only way
    ``ping`` returns on the master is if the **child** echoes it.

    Without this the kernel's line discipline echoes input verbatim regardless
    of what the child does — which would make the test pass even with no ``pty``
    mode (it would assert a property of the PTY, not of the child). Disabling
    ECHO pins the assertion to the child's behaviour.
    """
    attrs = termios.tcgetattr(slave_fd)
    attrs[3] &= ~termios.ECHO  # lflags
    termios.tcsetattr(slave_fd, termios.TCSANOW, attrs)


@contextlib.contextmanager
def _spawned_pty_child(tmp_path: Path) -> Iterator[int]:
    """Spawn the fake child in ``pty`` mode under a fresh ``os.openpty()`` pair
    with the slave tty's ECHO disabled, and yield the master fd.

    Centralises the spawn + guaranteed teardown (terminate → wait → kill on
    timeout, close both fds) shared by every pty-mode test, so each test body
    is just write-then-assert. Disabling ECHO pins assertions to the child's
    behaviour rather than the kernel line discipline (see ``_disable_tty_echo``).
    """
    child = fake_claude_child.write_child(tmp_path)
    argv = fake_claude_child.child_argv(child, mode="pty")

    master_fd, slave_fd = os.openpty()
    _disable_tty_echo(slave_fd)
    proc = subprocess.Popen(
        argv,
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        close_fds=True,
    )
    try:
        os.close(slave_fd)  # parent keeps only the master end
        yield master_fd
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
        os.close(master_fd)


def test_pty_child_echoes_input(tmp_path: Path) -> None:
    """Spawn the child in ``pty`` mode under ``os.openpty()``; write ``b"ping\\n"``
    to the master; assert the master read-back contains ``b"ping"`` (echo).

    The slave tty's own ECHO is disabled first, so the only source of ``ping``
    on the master is the child's ``pty``-mode echo of stdin → stdout. This is
    the guarantee the round-trip WPs (WP-003/004/005/010) rely on.
    """
    with _spawned_pty_child(tmp_path) as master_fd:
        os.write(master_fd, b"ping\n")
        readback = _read_until(master_fd, b"ping")
        assert b"ping" in readback, (
            f"pty child did not echo input; read-back was {readback!r}"
        )


def test_pty_child_emits_pong_on_sentinel(tmp_path: Path) -> None:
    """Write the sentinel line ``__PTY_PING__`` and assert the child writes its
    deterministic ``PTY_PONG`` reply to the master.

    This pins the second half of the ``pty`` mode contract — a known output line
    on a sentinel command — which gives the round-trip WPs a stable token to
    assert against (the two-way feed proof, contract §2.14 case #2). ECHO is
    disabled so ``PTY_PONG`` can only come from the child, not the tty.
    """
    with _spawned_pty_child(tmp_path) as master_fd:
        os.write(master_fd, b"__PTY_PING__\n")
        readback = _read_until(master_fd, b"PTY_PONG")
        assert b"PTY_PONG" in readback, (
            f"pty child did not emit PTY_PONG on sentinel; read-back was {readback!r}"
        )
