"""WP-003 (change-owned-terminal-shared-session) — the shared session-manager
daemon: flock singleton + stable socket + clean signal-driven shutdown.

Contract: ``WP-003-shared-daemon-singleton.md`` Definition of Done > Red
(``tests/integration/test_daemon_singleton.py``) + TDD §2.1/§3/§4 + ADR-001
(one shared daemon at a stable socket, singleton via ``fcntl.flock``; the lock-
holder is the *sole binder* of the socket — a second daemon that loses the lock
race confirms the existing socket is live and exits 0, NOT clobbering it).

Verification posture (MEA-09, no mocks): every test boots the **real** daemon
process via ``subprocess`` against a **real** AF_UNIX socket served by a
**real** :class:`SessionManager`. The real interactive ``claude`` binary cannot
run in CI (the WP-009 ``--verbose`` lesson), so the daemon's pty provider is
pointed at the shared **fake pty child** (``fake_claude_child`` in ``pty`` mode)
via the ``SULIS_DAEMON_PTY_CHILD`` test seam — the same substrate the host
integration suite uses, real subprocess + real socket, just not the real model.

Tests (RED first, per the WP Definition of Done):
    test_daemon_singleton.py::test_first_daemon_takes_lock_serves_and_prints_ready
    test_daemon_singleton.py::test_second_daemon_loses_race_exits_zero_without_clobber
    test_daemon_singleton.py::test_sigterm_cleanly_stops_unlinks_socket_releases_lock
    test_daemon_singleton.py::test_daemon_module_is_terminal_only_no_chat_or_platform
"""

from __future__ import annotations

import ast
import base64
import fcntl
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

# The daemon entrypoint + the shared fake pty child live under
# plugins/sulis/scripts (this file's grandparent), with the fake child in
# tests/lib. Mirror the host suite's import wiring.
_SCRIPTS_DIR = Path(__file__).resolve().parents[2]
_DAEMON_SCRIPT = _SCRIPTS_DIR / "session_manager_daemon.py"

sys.path.insert(0, str(_SCRIPTS_DIR / "tests" / "lib"))
import fake_claude_child  # noqa: E402

# Bounded wait for a process/thread assertion (matches the host suite's _WAIT):
# long enough never to flake on a loaded CI runner, short enough that a real
# hang fails fast.
_WAIT = 8.0


# ─── a thin NDJSON client over the real socket (the view's role) ──────────────


class _Client:
    """A minimal NDJSON client for the AF_UNIX socket (a view's wire)."""

    def __init__(self, socket_path: str) -> None:
        self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._sock.connect(socket_path)
        self._sock.settimeout(_WAIT)
        self._buf = b""

    def send(self, obj: dict) -> None:
        self._sock.sendall((json.dumps(obj) + "\n").encode("utf-8"))

    def recv_line(self) -> dict:
        while b"\n" not in self._buf:
            chunk = self._sock.recv(65536)
            if not chunk:
                raise ConnectionError("socket closed before a full line arrived")
            self._buf += chunk
        line, self._buf = self._buf.split(b"\n", 1)
        return json.loads(line)

    def request(self, obj: dict) -> dict:
        """Send one request and return the first line whose id matches."""
        self.send(obj)
        want = obj.get("id")
        while True:
            reply = self.recv_line()
            if reply.get("id") == want:
                return reply

    def close(self) -> None:
        try:
            self._sock.close()
        except OSError:  # pragma: no cover - best-effort teardown
            pass


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


@pytest.fixture
def fake_pty_child(tmp_path: Path) -> Path:
    """The shared fake-``claude`` child in ``pty`` mode (a real subprocess that
    echoes stdin + emits PTY_PONG on the sentinel) — the MEA-09 substrate the
    daemon's pty provider is pointed at when the real binary can't run."""
    return fake_claude_child.write_child(tmp_path)


@pytest.fixture
def daemon_env(fake_pty_child: Path) -> dict:
    """A child env that points the daemon's pty provider at the fake child (the
    ``SULIS_DAEMON_PTY_CHILD`` test seam) and a short idle window so a test never
    waits on the 1800s production default."""
    env = os.environ.copy()
    env["SULIS_DAEMON_PTY_CHILD"] = str(fake_pty_child)
    env["SULIS_DAEMON_IDLE_EXIT_SECS"] = "3600"  # long: never trips mid-test
    return env


def _boot_daemon(socket_path: str, lock_path: str, env: dict) -> subprocess.Popen:
    """Spawn the real daemon process and block until it prints ``READY <socket>``.

    The lock path is injected (``--lock``) so each test gets an isolated tmp
    lock + socket pair — the singleton arbitration is real, just scoped to the
    test's tmp dir.
    """
    proc = subprocess.Popen(
        [
            sys.executable,
            str(_DAEMON_SCRIPT),
            "--socket",
            socket_path,
            "--lock",
            lock_path,
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


# ─── the RED tests ────────────────────────────────────────────────────────────


def test_first_daemon_takes_lock_serves_and_prints_ready(
    socket_path: str, lock_path: str, daemon_env: dict, tmp_path: Path
) -> None:
    """The first daemon takes the flock, binds the stable socket, prints
    ``READY <socket>``, and serves the engine: over its real socket ``open`` a
    pty session, ``attach``, ``feed`` the sentinel, observe ``PTY_PONG`` stream
    back. Real engine, real socket, real (fake) pty child. Fails before the
    daemon exists."""
    proc = _boot_daemon(socket_path, lock_path, daemon_env)
    try:
        # The lock file is held by the daemon: a non-blocking flock attempt from
        # the test must fail (the daemon owns it for its life).
        with open(lock_path, "a") as lf:
            with pytest.raises(OSError):
                fcntl.flock(lf, fcntl.LOCK_EX | fcntl.LOCK_NB)

        client = _Client(socket_path)
        opened = client.request(
            {
                "id": "1",
                "method": "open",
                "params": {
                    "key": "chg_A",
                    "spec": {"provider": "pty", "cwd": str(tmp_path), "io_mode": "pty"},
                },
            }
        )
        assert opened["ok"] is True and opened["result"]["io_mode"] == "pty", opened

        client.send({"id": "7", "method": "attach", "params": {"key": "chg_A"}})
        client.send(
            {
                "id": "8",
                "method": "feed",
                "params": {
                    "key": "chg_A",
                    "data": _b64(b"__PTY_PING__\n"),
                    "encoding": "base64",
                },
            }
        )
        acc = bytearray()
        deadline = time.monotonic() + _WAIT
        while time.monotonic() < deadline:
            obj = client.recv_line()
            if obj.get("id") == "7" and "term" in obj:
                term = obj["term"]
                assert term["encoding"] == "base64", obj
                acc.extend(base64.b64decode(term["data"]))
                if b"PTY_PONG" in acc:
                    break
            if obj.get("id") == "7" and obj.get("end") is True:
                break
        assert b"PTY_PONG" in acc, (
            f"daemon never streamed the fed pty output: {bytes(acc)!r}"
        )
        client.close()
    finally:
        _stop_daemon(proc)


def test_second_daemon_loses_race_exits_zero_without_clobber(
    socket_path: str, lock_path: str, daemon_env: dict, tmp_path: Path
) -> None:
    """A second daemon on the SAME lock + socket, while the first is serving,
    confirms the live socket and exits **0** — WITHOUT clobbering the socket.
    The first daemon's session survives the second's launch (the load-bearing
    singleton invariant, ADR-001). Fails before the flock arbitration exists."""
    first = _boot_daemon(socket_path, lock_path, daemon_env)
    try:
        # Open a session on the FIRST daemon — this is what must survive.
        client = _Client(socket_path)
        opened = client.request(
            {
                "id": "1",
                "method": "open",
                "params": {
                    "key": "chg_SURVIVOR",
                    "spec": {"provider": "pty", "cwd": str(tmp_path), "io_mode": "pty"},
                },
            }
        )
        assert opened["ok"] is True, opened

        # Launch the SECOND daemon on the same lock + socket. It must lose the
        # flock race, see the live socket, print READY (the contract's "another
        # daemon won — losing the race is normal"), and exit 0.
        second = subprocess.Popen(
            [
                sys.executable,
                str(_DAEMON_SCRIPT),
                "--socket",
                socket_path,
                "--lock",
                lock_path,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(_SCRIPTS_DIR),
            env=daemon_env,
        )
        try:
            rc = second.wait(timeout=_WAIT)
        except subprocess.TimeoutExpired:  # pragma: no cover - defensive
            second.kill()
            raise AssertionError("second daemon did not exit (it should lose + exit 0)")
        assert rc == 0, (
            f"second daemon exited {rc}, expected 0 (losing the race is normal); "
            f"stderr={second.stderr.read() if second.stderr else ''!r}"
        )

        # The FIRST daemon's session must still be there — the second did not
        # clobber the socket (no unlink+rebind by a non-lock-holder).
        status = client.request({"id": "2", "method": "status", "params": {}})
        assert status["ok"] is True, status
        keys = {row["key"] for row in status["result"]}
        assert "chg_SURVIVOR" in keys, (
            f"the first daemon's session was lost — the second clobbered the "
            f"socket: status keys = {keys!r}"
        )
        client.close()
    finally:
        _stop_daemon(first)


def test_sigterm_cleanly_stops_unlinks_socket_releases_lock(
    socket_path: str, lock_path: str, daemon_env: dict
) -> None:
    """SIGTERM drives a clean stop: the daemon shuts the server down, unlinks the
    socket, releases the flock, and exits 0. After it exits, the socket file is
    gone and the lock is acquirable by a fresh process. Fails before the signal-
    driven clean stop exists."""
    proc = _boot_daemon(socket_path, lock_path, daemon_env)
    assert os.path.exists(socket_path), "daemon did not bind the socket"

    proc.terminate()  # SIGTERM
    rc = proc.wait(timeout=_WAIT)
    assert rc == 0, f"clean SIGTERM stop exited {rc}, expected 0"

    # The socket is unlinked on a clean stop (no stale file left behind).
    assert not os.path.exists(socket_path), (
        "daemon left a stale socket file after a clean SIGTERM stop"
    )

    # The flock is released (auto-released on process death, but the clean stop
    # path must also not deadlock a fresh acquirer).
    with open(lock_path, "a") as lf:
        try:
            fcntl.flock(lf, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:  # pragma: no cover - would indicate a held lock
            pytest.fail("flock still held after the daemon exited")
        finally:
            fcntl.flock(lf, fcntl.LOCK_UN)


def test_daemon_module_is_terminal_only_no_chat_or_platform(
    socket_path: str, lock_path: str, daemon_env: dict
) -> None:
    """Independence directive (founder, MUST; ADR-003 / Blue): the daemon module
    imports nothing from the cockpit chat relay, the chat ``SessionBridge``, or
    the ``platform`` communication service — it owns the engine for the terminal
    over the socket directly. Codified as an import-graph assertion so the
    directive cannot regress silently. Fails before the module exists."""
    tree = ast.parse(_DAEMON_SCRIPT.read_text())
    imported_roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported_roots.add(node.module.split(".")[0])

    forbidden = {"chat", "platform", "sessionbridge"}
    leaked = imported_roots & forbidden
    assert not leaked, (
        f"session_manager_daemon.py imports forbidden modules {leaked!r} — the "
        "terminal daemon must be terminal-only (independence directive, ADR-003)"
    )
