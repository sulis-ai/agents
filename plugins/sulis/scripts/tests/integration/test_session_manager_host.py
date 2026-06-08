"""WP-001 (production-terminal-sidecar) — the production session-manager HOST.

Contract: ``WP-001-session-manager-host.md`` + terminal contract §2.13.4 +
ADR-010 (terminal is an attach-authorised write path, binding guard ON) +
ADR-011 (the cockpit owns the engine via a spawned Python host process).

This is the production sibling of ``apps/cockpit/e2e/terminal-backend.py``:
a long-lived process the cockpit spawns at boot that owns the shipped
:class:`SessionManager` + :class:`SocketServer` over a 0o600 AF_UNIX socket,
with the per-change binding guard **ON** — and, unlike the e2e backend, with
**no** scrollback banner seeded (that is harness-only).

Verification posture (MEA-09, no mocks): every test boots the **real** host
process via ``subprocess``, waits for its ``READY`` line, and drives it over a
**real** AF_UNIX socket served by a **real** :class:`SessionManager` against a
**real** pty-backed child — the exact path the cockpit's Node bridge (WP-002)
walks in production.

Tests (RED first, per the WP Definition of Done):
    test_session_manager_host.py::test_host_serves_real_socket
    test_session_manager_host.py::test_guard_on_refuses_cross_change
    test_session_manager_host.py::test_no_seeded_scrollback
"""

from __future__ import annotations

import base64
import json
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

# The host module + the shared test child live under plugins/sulis/scripts.
_SCRIPTS_DIR = Path(__file__).resolve().parents[2]
_HOST_SCRIPT = _SCRIPTS_DIR / "session_manager_host.py"

# Bounded wait for a threaded/process assertion (matches the socket suite's
# _WAIT): long enough never to flake on a loaded CI runner, short enough that a
# real hang fails fast.
_WAIT = 8.0


# ─── a thin NDJSON client over the real socket (the cockpit bridge's role) ────


class _Client:
    """A minimal NDJSON client for the AF_UNIX socket (the cockpit's wire).

    One JSON request per line; newline-delimited JSON responses, with partial
    lines buffered (the §2.8.2 framing discipline). This is the role the Node
    cockpit's terminal sidecar bridge (WP-002) plays in production.
    """

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

    def close(self) -> None:
        try:
            self._sock.close()
        except OSError:  # pragma: no cover - best-effort teardown
            pass


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _decode_term(obj: dict) -> bytes:
    term = obj["term"]
    assert term["encoding"] == "base64", f"term not base64-encoded: {obj!r}"
    return base64.b64decode(term["data"])


def _boot_host(socket_path: str) -> subprocess.Popen:
    """Spawn the real host process and block until it prints ``READY <socket>``.

    Mirrors how ``terminal-proxy.ts`` (e2e) and the cockpit server (production)
    wait for readiness before connecting.
    """
    proc = subprocess.Popen(
        [sys.executable, str(_HOST_SCRIPT), "--socket", socket_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=str(_SCRIPTS_DIR),
    )
    deadline = time.monotonic() + _WAIT
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            err = proc.stderr.read() if proc.stderr else ""
            raise AssertionError(
                f"host exited before READY (rc={proc.returncode}): {err}"
            )
        line = proc.stdout.readline() if proc.stdout else ""
        if line.startswith("READY"):
            assert socket_path in line, f"READY line did not name the socket: {line!r}"
            return proc
    proc.kill()
    raise AssertionError("host never printed READY within the deadline")


def _stop_host(proc: subprocess.Popen) -> None:
    proc.terminate()
    try:
        proc.wait(timeout=_WAIT)
    except subprocess.TimeoutExpired:  # pragma: no cover - defensive
        proc.kill()
        proc.wait(timeout=_WAIT)


@pytest.fixture
def socket_path(tmp_path: Path) -> str:
    return str(tmp_path / "host.sock")


# ─── the RED tests ───────────────────────────────────────────────────────────


def test_host_serves_real_socket(socket_path: str, tmp_path: Path) -> None:
    """Boot the real host; over its real AF_UNIX socket ``open`` a pty session,
    ``attach``, then ``feed`` the sentinel — observe the deterministic
    ``PTY_PONG`` stream back as a ``term`` line. Real engine, real socket, real
    pty (MEA-09). Fails before the host exists."""
    proc = _boot_host(socket_path)
    try:
        client = _Client(socket_path)
        client.send(
            {
                "id": "1",
                "method": "open",
                "params": {
                    "key": "chg_A",
                    "spec": {"provider": "pty", "cwd": str(tmp_path), "io_mode": "pty"},
                },
            }
        )
        opened = client.recv_line()
        assert opened["id"] == "1" and opened["ok"] is True, opened
        assert opened["result"]["io_mode"] == "pty", opened

        client.send({"id": "7", "method": "attach", "params": {"key": "chg_A"}})
        # Drive deterministic output so a term line is guaranteed (a fresh pty
        # has no scrollback to snapshot): feed the sentinel that emits PTY_PONG.
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
        first_phase = None
        deadline = time.monotonic() + _WAIT
        while time.monotonic() < deadline:
            obj = client.recv_line()
            if obj.get("id") == "7" and "term" in obj:
                if first_phase is None:
                    first_phase = obj["term"]["phase"]
                acc.extend(_decode_term(obj))
                if b"PTY_PONG" in acc:
                    break
            if obj.get("id") == "7" and obj.get("end") is True:
                break
        assert b"PTY_PONG" in acc, (
            f"attach over the host socket never streamed the fed output: {bytes(acc)!r}"
        )
        assert first_phase == "snapshot", (
            f"first term line was not the snapshot phase: {first_phase}"
        )
        client.close()
    finally:
        _stop_host(proc)


def test_guard_on_refuses_cross_change(socket_path: str, tmp_path: Path) -> None:
    """Guard ON: a connection bound to change A (its FIRST guarded key) may not
    ``attach`` change B on the same connection → ``NOT_AUTHORIZED``, zero
    ``term`` lines. Parallels test_socket_server::test_cross_change_attach_denied.
    Fails while the guard defaults permissive."""
    proc = _boot_host(socket_path)
    try:
        client = _Client(socket_path)
        # Open BOTH changes' sessions on the manager (open is unguarded; chat).
        for key in ("chg_A", "chg_B"):
            client.send(
                {
                    "id": f"open_{key}",
                    "method": "open",
                    "params": {
                        "key": key,
                        "spec": {
                            "provider": "pty",
                            "cwd": str(tmp_path),
                            "io_mode": "pty",
                        },
                    },
                }
            )
            assert client.recv_line()["ok"] is True

        # First guarded op binds this connection to chg_A; feed proves A is
        # authorised (PTY_PONG streams back on the bound change).
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
            if obj.get("id") == "7" and obj.get("ok") is False:
                pytest.fail(f"attach to the bound change was refused: {obj}")
            if obj.get("id") == "8" and obj.get("ok") is False:
                pytest.fail(f"feed to the bound change was refused: {obj}")
            if obj.get("id") == "7" and "term" in obj:
                acc.extend(_decode_term(obj))
                if b"PTY_PONG" in acc:
                    break
        assert b"PTY_PONG" in acc, "the bound change A never streamed its fed output"

        # Now attach chg_B on the SAME connection → refused, no bytes.
        client.send({"id": "9", "method": "attach", "params": {"key": "chg_B"}})
        denied = None
        deadline = time.monotonic() + _WAIT
        while time.monotonic() < deadline:
            obj = client.recv_line()
            if obj.get("id") == "9":
                assert "term" not in obj, (
                    f"cross-change attach leaked a term line: {obj}"
                )
                denied = obj
                break
        assert denied is not None, "cross-change attach produced no response"
        assert denied["ok"] is False, denied
        assert denied["error"]["category"] == "expected", denied
        assert denied["error"]["code"] == "NOT_AUTHORIZED", denied
        client.close()
    finally:
        _stop_host(proc)


def test_no_seeded_scrollback(socket_path: str, tmp_path: Path) -> None:
    """The host seeds NO banner (unlike the e2e backend): a fresh ``attach``
    before any ``feed`` yields a clean snapshot — no ``WP010_SCROLLBACK_BANNER``.
    Fails if the e2e backend were reused."""
    proc = _boot_host(socket_path)
    try:
        client = _Client(socket_path)
        client.send(
            {
                "id": "1",
                "method": "open",
                "params": {
                    "key": "chg_A",
                    "spec": {"provider": "pty", "cwd": str(tmp_path), "io_mode": "pty"},
                },
            }
        )
        assert client.recv_line()["ok"] is True

        client.send({"id": "7", "method": "attach", "params": {"key": "chg_A"}})
        # Collect the snapshot phase bytes.
        snap = bytearray()
        deadline = time.monotonic() + 3.0
        while time.monotonic() < deadline:
            try:
                obj = client.recv_line()
            except (TimeoutError, socket.timeout):
                break
            if obj.get("id") == "7" and "term" in obj:
                if obj["term"]["phase"] == "snapshot":
                    snap.extend(_decode_term(obj))
                else:
                    # Reached the live phase — snapshot is complete.
                    break
            if obj.get("id") == "7" and obj.get("end") is True:
                break
        assert b"WP010_SCROLLBACK_BANNER" not in snap, (
            f"host seeded a banner it must not: {bytes(snap)!r}"
        )
        assert b"SCROLLBACK_BANNER" not in snap, (
            f"host seeded scrollback it must not: {bytes(snap)!r}"
        )
        client.close()
    finally:
        _stop_host(proc)
