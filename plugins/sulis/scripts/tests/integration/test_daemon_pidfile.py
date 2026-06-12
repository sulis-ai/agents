"""WP-001 (harden-daemon-wedge-self-heal) — the daemon writes and removes an
**identity pidfile** at boot / clean shutdown.

Contract: ``WP-001-daemon-writes-identity-pidfile.md`` Definition of Done > Red
(``tests/integration/test_daemon_pidfile.py``) + spec §Scope.1 + ADR-001 /
ADR-003 (stdlib-only, terminal-only, beside the lock + socket). HD-001.

The daemon must record a durable, on-disk identity of its own process — its
**PID**, a process **start-token** (the OS process start-time, which a recycled
PID cannot reproduce), and a **cmdline marker** — so a later reclaim (WP-002)
can verify a kill target PID-reuse-safely. The pidfile lives beside the lock +
socket (``~/.sulis/session-manager.pid``), env/flag-overridable (``--pidfile``)
to mirror the existing ``--lock`` / ``--socket`` test-isolation seams.

Verification posture (MEA-09, no mocks): each test boots the **real** daemon
process via ``subprocess`` against a **real** AF_UNIX socket, reusing the
``test_daemon_singleton`` harness (``_boot_daemon``, ``daemon_env``, the fake
pty child, isolated ``--lock`` / ``--socket``) extended with ``--pidfile``.

Tests (RED first, per the WP Definition of Done):
    test_daemon_pidfile.py::test_daemon_writes_pidfile_with_pid_and_start_token_at_boot
    test_daemon_pidfile.py::test_daemon_removes_pidfile_on_clean_sigterm
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

# The daemon entrypoint + the shared fake pty child live under
# plugins/sulis/scripts (this file's grandparent), with the fake child in
# tests/lib. Mirror the singleton suite's import wiring.
_SCRIPTS_DIR = Path(__file__).resolve().parents[2]
_DAEMON_SCRIPT = _SCRIPTS_DIR / "session_manager_daemon.py"

sys.path.insert(0, str(_SCRIPTS_DIR / "tests" / "lib"))
import fake_claude_child  # noqa: E402

# Bounded wait for a process/thread assertion (matches the singleton suite's
# _WAIT): long enough never to flake on a loaded CI runner, short enough that a
# real hang fails fast.
_WAIT = 8.0

# The cmdline marker the daemon records (the constant from the WP Contract,
# matched against a live process's cmdline in WP-002).
_CMDLINE_MARKER = "session_manager_daemon.py"


@pytest.fixture
def fake_pty_child(tmp_path: Path) -> Path:
    """The shared fake-``claude`` child in ``pty`` mode (a real subprocess) — the
    MEA-09 substrate the daemon's pty provider is pointed at when the real binary
    can't run."""
    return fake_claude_child.write_child(tmp_path)


@pytest.fixture
def daemon_env(fake_pty_child: Path) -> dict:
    """A child env that points the daemon's pty provider at the fake child (the
    ``SULIS_DAEMON_PTY_CHILD`` test seam) and a long idle window so a test never
    waits on the 1800s production default and never trips mid-test."""
    env = os.environ.copy()
    env["SULIS_DAEMON_PTY_CHILD"] = str(fake_pty_child)
    env["SULIS_DAEMON_IDLE_EXIT_SECS"] = "3600"
    return env


def _boot_daemon(
    socket_path: str, lock_path: str, pidfile_path: str, env: dict
) -> subprocess.Popen:
    """Spawn the real daemon process (with an injected ``--pidfile``) and block
    until it prints ``READY <socket>``. The lock + socket + pidfile are all
    injected so each test gets an isolated tmp triple."""
    proc = subprocess.Popen(
        [
            sys.executable,
            str(_DAEMON_SCRIPT),
            "--socket",
            socket_path,
            "--lock",
            lock_path,
            "--pidfile",
            pidfile_path,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=str(_SCRIPTS_DIR),
        env=env,
    )
    deadline = time.monotonic() + _WAIT
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            err = proc.stderr.read() if proc.stderr else ""
            raise AssertionError(
                f"daemon exited before READY (rc={proc.returncode}): {err}"
            )
        line = proc.stdout.readline() if proc.stdout else ""
        if line.startswith("READY"):
            assert socket_path in line, f"READY did not name the socket: {line!r}"
            return proc
    proc.kill()
    raise AssertionError("daemon never printed READY within the deadline")


def _stop_daemon(proc: subprocess.Popen) -> None:
    if proc.poll() is None:
        proc.terminate()
    try:
        proc.wait(timeout=_WAIT)
    except subprocess.TimeoutExpired:  # pragma: no cover - defensive
        proc.kill()
        proc.wait(timeout=_WAIT)


@pytest.fixture
def socket_path(tmp_path: Path) -> str:
    # Kept short — AF_UNIX path length is bounded (~104 bytes on macOS).
    return str(tmp_path / "d.sock")


@pytest.fixture
def lock_path(tmp_path: Path) -> str:
    return str(tmp_path / "d.lock")


@pytest.fixture
def pidfile_path(tmp_path: Path) -> str:
    return str(tmp_path / "d.pid")


# ─── the RED tests ────────────────────────────────────────────────────────────


def test_daemon_writes_pidfile_with_pid_and_start_token_at_boot(
    socket_path: str, lock_path: str, pidfile_path: str, daemon_env: dict
) -> None:
    """The daemon writes an identity pidfile once it is genuinely bound + holds
    the lock. After READY the pidfile exists; its ``pid`` is the daemon's PID;
    its ``start_token`` is non-empty; its ``cmdline_marker`` names the daemon
    entrypoint. Fails today — the daemon writes no pidfile."""
    proc = _boot_daemon(socket_path, lock_path, pidfile_path, daemon_env)
    try:
        assert os.path.exists(pidfile_path), (
            "daemon did not write the identity pidfile after READY"
        )
        record = json.loads(Path(pidfile_path).read_text())
        assert record["pid"] == proc.pid, (
            f"pidfile pid {record.get('pid')!r} != daemon pid {proc.pid}"
        )
        assert record.get("start_token"), f"pidfile start_token is empty: {record!r}"
        assert _CMDLINE_MARKER in record.get("cmdline_marker", ""), (
            f"pidfile cmdline_marker does not name the entrypoint: {record!r}"
        )
    finally:
        _stop_daemon(proc)


def test_daemon_removes_pidfile_on_clean_sigterm(
    socket_path: str, lock_path: str, pidfile_path: str, daemon_env: dict
) -> None:
    """A clean SIGTERM stop removes the pidfile: after the daemon exits 0 the
    pidfile is gone (it records a *live* identity only). Fails today — the
    daemon neither writes nor removes a pidfile."""
    proc = _boot_daemon(socket_path, lock_path, pidfile_path, daemon_env)
    assert os.path.exists(pidfile_path), "daemon did not write the pidfile"

    proc.terminate()  # SIGTERM
    rc = proc.wait(timeout=_WAIT)
    assert rc == 0, f"clean SIGTERM stop exited {rc}, expected 0"

    assert not os.path.exists(pidfile_path), (
        "daemon left a stale identity pidfile after a clean SIGTERM stop"
    )
