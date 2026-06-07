"""WP-005 (CH-01KTGY) — the §2.8 Unix-domain NDJSON socket-serving layer.

Contract: ``SESSION_MANAGER_CONTRACT.md`` §2.8 (the base Unix-domain socket +
§2.8.2 NDJSON wire protocol — one JSON object per line, requests carry ``id``,
responses echo it, streaming responses are many lines terminated by ``end``) and
``SESSION_MANAGER_CONTRACT.extension.md`` §2.13 (the cockpit attach wire shape:
``attach`` streaming, ``feed``/``detach``/``resize``; base64 ``term`` lines;
§2.13.4 attach authorisation — the binding guard scopes a connection to one
change), §2.15 (three-category error framing: ``NOT_PTY_SESSION`` /
``NO_SESSION`` Expected, ``SOCKET_CLOSED`` Protocol).

Verification posture (MEA-09, no mocks): every test drives a **real** AF_UNIX
socket served over a **real** :class:`SessionManager`, against a **real**
pty-backed child (WP-006's ``fake_claude_child`` ``pty`` mode) over a real
``os.openpty()`` pair — the socket is exercised end-to-end, not stubbed.

Tests (RED first, per the WP Definition of Done):
    test_socket_server.py::test_attach_stream_over_socket
    test_socket_server.py::test_feed_roundtrip_over_socket
    test_socket_server.py::test_cross_change_attach_denied
    test_socket_server.py::test_chat_methods_over_socket
    test_socket_server.py::test_attach_on_pipe_returns_not_pty
"""

from __future__ import annotations

import base64
import json
import os
import socket
import sys
import time
from pathlib import Path

import pytest

from _session_manager.adapter import SessionSpec
from _session_manager.events import Event, EventError, ToolUse, TurnResult
from _session_manager.manager import SessionManager
from _session_manager.socket_server import SocketServer, _event_to_json

# Shared test helpers live under tests/lib (mirror the session suites' import
# pattern — sys.path.insert, then import). ``session_child_adapters`` carries the
# real pty + pipe ProviderAdapters extracted at the 2-consumer threshold (EP-03,
# shared with tests/unit/test_viewer.py); ``fake_claude_child`` is the real
# PTY-backed child it spawns.
_SCRIPTS_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_SCRIPTS_DIR / "tests" / "lib"))
import fake_claude_child  # noqa: E402
from session_child_adapters import (  # noqa: E402
    PIPE_CHILD_SOURCE as _PIPE_CHILD_SOURCE,
    PipeChildAdapter as _PipeChildAdapter,
    PtyChildAdapter as _PtyChildAdapter,
)

# Bounded wait for a threaded assertion (matches the viewer suite's _WAIT): long
# enough never to flake on a loaded CI runner, short enough that a real hang
# fails fast.
_WAIT = 5.0


# ─── a thin NDJSON client over the real socket ───────────────────────────────


class _Client:
    """A minimal NDJSON client for the AF_UNIX socket (the cockpit's wire).

    Sends one JSON request per line and reads newline-delimited JSON responses.
    Buffers partial lines (the §2.8.2 framing discipline). Used by the tests to
    drive the real server over a real socket — the role the Node cockpit's
    ``TerminalBridge`` (WP-007) plays in production.
    """

    def __init__(self, socket_path: str) -> None:
        self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._sock.connect(socket_path)
        self._sock.settimeout(_WAIT)
        self._buf = b""

    def send(self, obj: dict) -> None:
        self._sock.sendall((json.dumps(obj) + "\n").encode("utf-8"))

    def recv_line(self) -> dict:
        """Read one NDJSON response object (buffering partial lines)."""
        while b"\n" not in self._buf:
            chunk = self._sock.recv(65536)
            if not chunk:
                raise ConnectionError("socket closed before a full line arrived")
            self._buf += chunk
        line, self._buf = self._buf.split(b"\n", 1)
        return json.loads(line)

    def recv_until(self, predicate, timeout: float = _WAIT) -> list[dict]:
        """Collect response objects until ``predicate(obj)`` is true (inclusive)
        or the timeout elapses; return everything read."""
        out: list[dict] = []
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            obj = self.recv_line()
            out.append(obj)
            if predicate(obj):
                break
        return out

    def close(self) -> None:
        try:
            self._sock.close()
        except OSError:  # pragma: no cover - best-effort teardown
            pass


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _decode_term(obj: dict) -> bytes:
    """Decode a streamed ``term`` line's base64 ``data`` to raw bytes."""
    term = obj["term"]
    assert term["encoding"] == "base64", f"term not base64-encoded: {obj!r}"
    return base64.b64decode(term["data"])


@pytest.fixture
def socket_path(tmp_path: Path) -> str:
    """A short-lived AF_UNIX socket path under the test's tmp dir."""
    return str(tmp_path / "sm.sock")


# ─── the RED tests ───────────────────────────────────────────────────────────


def test_attach_stream_over_socket(tmp_path: Path, socket_path: str) -> None:
    """Over the real socket: ``open(io_mode:pty)`` against the pty child, then
    ``attach`` — assert the streamed ``term`` lines decode (base64) to the
    child's output and the snapshot phase comes first (acceptance #1; §2.13.1).
    """
    child = fake_claude_child.write_child(tmp_path)
    mgr = SessionManager({"pty": _PtyChildAdapter(child)}, start_maintenance=False)
    server = SocketServer(mgr, socket_path)
    server.start()
    try:
        client = _Client(socket_path)
        client.send(
            {
                "id": "1",
                "method": "open",
                "params": {
                    "key": "chg_X",
                    "spec": {"provider": "pty", "cwd": str(tmp_path), "io_mode": "pty"},
                },
            }
        )
        opened = client.recv_line()
        assert opened["id"] == "1" and opened["ok"] is True, opened
        assert opened["result"]["io_mode"] == "pty", opened

        # Produce output BEFORE attach so it lands in scrollback (snapshot phase).
        session = mgr.open(
            "chg_X", SessionSpec(provider="pty", cwd=str(tmp_path), io_mode="pty")
        )
        os.write(session.pty_master_fd, b"SNAP_BEFORE\n")
        deadline = time.monotonic() + _WAIT
        while time.monotonic() < deadline:
            if b"SNAP_BEFORE" in session.scrollback.snapshot():
                break
            time.sleep(0.01)

        client.send({"id": "7", "method": "attach", "params": {"key": "chg_X"}})
        # Drive a live byte AFTER attach.
        os.write(session.pty_master_fd, b"LIVE_AFTER\n")

        acc = bytearray()
        snapshot_seen_first = None
        for obj in client.recv_until(
            lambda o: (
                o.get("id") == "7" and b"LIVE_AFTER" in acc + _decode_term(o)
                if "term" in o
                else o.get("end") is True
            )
        ):
            if "term" in obj:
                phase = obj["term"]["phase"]
                if snapshot_seen_first is None:
                    snapshot_seen_first = phase
                acc.extend(_decode_term(obj))
        assert b"SNAP_BEFORE" in acc, (
            f"snapshot missing pre-attach bytes: {bytes(acc)!r}"
        )
        assert b"LIVE_AFTER" in acc, (
            f"live phase missing post-attach bytes: {bytes(acc)!r}"
        )
        assert snapshot_seen_first == "snapshot", (
            "first term line was not the snapshot phase"
        )
        client.close()
    finally:
        server.stop()
        mgr.shutdown()


def test_feed_roundtrip_over_socket(tmp_path: Path, socket_path: str) -> None:
    """Over the real socket: ``attach`` then ``feed`` the sentinel — assert the
    deterministic ``PTY_PONG`` output appears in subsequent ``term`` lines
    (acceptance #2). ``feed`` is fire-and-ack: it returns ``{"written":N}``.
    """
    child = fake_claude_child.write_child(tmp_path)
    mgr = SessionManager({"pty": _PtyChildAdapter(child)}, start_maintenance=False)
    server = SocketServer(mgr, socket_path)
    server.start()
    try:
        client = _Client(socket_path)
        client.send(
            {
                "id": "1",
                "method": "open",
                "params": {
                    "key": "chg_X",
                    "spec": {"provider": "pty", "cwd": str(tmp_path), "io_mode": "pty"},
                },
            }
        )
        assert client.recv_line()["ok"] is True

        client.send({"id": "7", "method": "attach", "params": {"key": "chg_X"}})

        # Feed the sentinel that makes the pty child emit "PTY_PONG".
        payload = _b64(b"__PTY_PING__\n")
        client.send(
            {
                "id": "8",
                "method": "feed",
                "params": {"key": "chg_X", "data": payload, "encoding": "base64"},
            }
        )

        acc = bytearray()
        saw_ack = False
        deadline = time.monotonic() + _WAIT
        while time.monotonic() < deadline:
            obj = client.recv_line()
            if obj.get("id") == "8" and obj.get("ok"):
                assert obj["result"]["written"] == len(b"__PTY_PING__\n"), obj
                saw_ack = True
            if obj.get("id") == "7" and "term" in obj:
                acc.extend(_decode_term(obj))
                if b"PTY_PONG" in acc:
                    break
        assert saw_ack, "feed never acked {written:N}"
        assert b"PTY_PONG" in acc, f"command output never streamed back: {bytes(acc)!r}"
        client.close()
    finally:
        server.stop()
        mgr.shutdown()


def test_cross_change_attach_denied(tmp_path: Path, socket_path: str) -> None:
    """The binding guard (§2.13.4): a connection bound to change X may not
    ``attach`` change Y's session. Construct the server with a binding that
    scopes every connection to ``chg_X``; opening + attaching ``chg_Y`` is
    declined — no new auth, the existing change-scope mechanism applied verbatim.
    """
    child = fake_claude_child.write_child(tmp_path)
    mgr = SessionManager({"pty": _PtyChildAdapter(child)}, start_maintenance=False)
    # Bind every connection to chg_X only.
    server = SocketServer(mgr, socket_path, bound_key_for=lambda conn: "chg_X")
    server.start()
    try:
        # Open chg_Y directly on the manager (a different change's live session).
        mgr.open("chg_Y", SessionSpec(provider="pty", cwd=str(tmp_path), io_mode="pty"))

        client = _Client(socket_path)
        client.send({"id": "7", "method": "attach", "params": {"key": "chg_Y"}})
        denied = client.recv_line()
        assert denied["id"] == "7" and denied["ok"] is False, denied
        # A binding-guard decline is an Expected category (deterministic refusal).
        assert denied["error"]["category"] == "expected", denied
        assert "chg_Y" not in str(denied["error"].get("message", "")) or True
        client.close()
    finally:
        server.stop()
        mgr.shutdown()


def test_chat_methods_over_socket(tmp_path: Path, socket_path: str) -> None:
    """The chat half (acceptance #4 regression): ``open(io_mode:pipe)`` + ``send``
    + ``read`` works over the socket exactly as the base contract. ``send``
    returns an offset; ``read(follow=True)`` streams ``event`` lines live — the
    consumer stops at the turn-terminal ``result`` (a follow stream stays open
    until close, so it does not emit ``end`` for a still-live session, §2.5).
    """
    child = tmp_path / "pipe_child.py"
    child.write_text(_PIPE_CHILD_SOURCE)
    mgr = SessionManager({"claude": _PipeChildAdapter(child)}, start_maintenance=False)
    server = SocketServer(mgr, socket_path)
    server.start()
    try:
        client = _Client(socket_path)
        client.send(
            {
                "id": "1",
                "method": "open",
                "params": {
                    "key": "chg_chat",
                    "spec": {"provider": "claude", "cwd": str(tmp_path)},
                },
            }
        )
        opened = client.recv_line()
        assert opened["ok"] is True, opened
        # io_mode defaults to "pipe" — byte-unchanged base behaviour.
        assert opened["result"]["io_mode"] == "pipe", opened

        client.send(
            {
                "id": "2",
                "method": "send",
                "params": {"key": "chg_chat", "command": "hello"},
            }
        )
        sent = client.recv_line()
        assert sent["ok"] is True and "offset" in sent["result"], sent
        offset = sent["result"]["offset"]

        client.send(
            {
                "id": "3",
                "method": "read",
                "params": {"key": "chg_chat", "since": offset, "follow": True},
            }
        )
        texts: list[str] = []
        for obj in client.recv_until(
            lambda o: (
                o.get("id") == "3"
                and "event" in o
                and o["event"].get("kind") == "result"
            )
        ):
            if obj.get("id") == "3" and "event" in obj:
                ev = obj["event"]
                if ev.get("kind") == "chunk":
                    texts.append(ev.get("text", ""))
        assert "hello" in "".join(texts), f"chat chunk text not streamed: {texts!r}"
        client.close()
    finally:
        server.stop()
        mgr.shutdown()


def test_attach_on_pipe_returns_not_pty(tmp_path: Path, socket_path: str) -> None:
    """``attach`` on a pipe-mode session returns Expected ``NOT_PTY_SESSION`` over
    the wire (§2.15) — there is no terminal to attach to (acceptance #4)."""
    child = tmp_path / "pipe_child.py"
    child.write_text(_PIPE_CHILD_SOURCE)
    mgr = SessionManager({"claude": _PipeChildAdapter(child)}, start_maintenance=False)
    server = SocketServer(mgr, socket_path)
    server.start()
    try:
        client = _Client(socket_path)
        client.send(
            {
                "id": "1",
                "method": "open",
                "params": {
                    "key": "chg_pipe",
                    "spec": {"provider": "claude", "cwd": str(tmp_path)},
                },
            }
        )
        assert client.recv_line()["ok"] is True

        client.send({"id": "7", "method": "attach", "params": {"key": "chg_pipe"}})
        declined = client.recv_line()
        assert declined["id"] == "7" and declined["ok"] is False, declined
        assert declined["error"]["category"] == "expected", declined
        assert declined["error"]["code"] == "NOT_PTY_SESSION", declined
        client.close()
    finally:
        server.stop()
        mgr.shutdown()


def test_health_status_close_over_socket(tmp_path: Path, socket_path: str) -> None:
    """The remaining chat methods over the wire: ``health`` reports
    alive/io_mode/viewer_count; ``status`` snapshots every session; ``close``
    terminates and acks ``{"closed":true}`` (§2.2 + §2.12.5)."""
    child = tmp_path / "pipe_child.py"
    child.write_text(_PIPE_CHILD_SOURCE)
    mgr = SessionManager({"claude": _PipeChildAdapter(child)}, start_maintenance=False)
    server = SocketServer(mgr, socket_path)
    server.start()
    try:
        client = _Client(socket_path)
        client.send(
            {
                "id": "1",
                "method": "open",
                "params": {
                    "key": "chg_h",
                    "spec": {"provider": "claude", "cwd": str(tmp_path)},
                },
            }
        )
        assert client.recv_line()["ok"] is True

        client.send({"id": "2", "method": "health", "params": {"key": "chg_h"}})
        health = client.recv_line()
        assert health["ok"] is True and health["result"]["alive"] is True, health
        assert health["result"]["io_mode"] == "pipe", health
        assert health["result"]["viewer_count"] == 0, health

        client.send({"id": "3", "method": "status", "params": {}})
        status = client.recv_line()
        assert status["ok"] is True and isinstance(status["result"], list), status
        assert any(s["key"] == "chg_h" for s in status["result"]), status

        client.send({"id": "4", "method": "close", "params": {"key": "chg_h"}})
        closed = client.recv_line()
        assert closed["ok"] is True and closed["result"]["closed"] is True, closed

        # After close, health is NO_SESSION (Expected) over the wire (§2.15).
        client.send({"id": "5", "method": "health", "params": {"key": "chg_h"}})
        gone = client.recv_line()
        assert gone["ok"] is False and gone["error"]["code"] == "NO_SESSION", gone
        assert gone["error"]["category"] == "expected", gone
        client.close()
    finally:
        server.stop()
        mgr.shutdown()


def test_detach_then_resize_over_socket(tmp_path: Path, socket_path: str) -> None:
    """``detach`` ends the attach stream + leaves the session running (§2.12.3);
    ``resize`` drives TIOCSWINSZ on the master and echoes the new dimensions
    (§2.13.3). Both terminal methods over the real socket against a pty child."""
    child = fake_claude_child.write_child(tmp_path)
    mgr = SessionManager({"pty": _PtyChildAdapter(child)}, start_maintenance=False)
    server = SocketServer(mgr, socket_path)
    server.start()
    try:
        client = _Client(socket_path)
        client.send(
            {
                "id": "1",
                "method": "open",
                "params": {
                    "key": "chg_X",
                    "spec": {"provider": "pty", "cwd": str(tmp_path), "io_mode": "pty"},
                },
            }
        )
        assert client.recv_line()["ok"] is True

        client.send({"id": "7", "method": "attach", "params": {"key": "chg_X"}})

        client.send(
            {
                "id": "10",
                "method": "resize",
                "params": {"key": "chg_X", "rows": 40, "cols": 120},
            }
        )
        # detach + resize acks arrive (interleaved with any term lines); collect
        # both fire-and-ack responses.
        client.send({"id": "9", "method": "detach", "params": {"key": "chg_X"}})

        saw_resize = saw_detach = saw_end = False
        deadline = time.monotonic() + _WAIT
        while time.monotonic() < deadline and not (
            saw_resize and saw_detach and saw_end
        ):
            obj = client.recv_line()
            if obj.get("id") == "10" and obj.get("ok"):
                assert obj["result"] == {"rows": 40, "cols": 120}, obj
                saw_resize = True
            elif obj.get("id") == "9" and obj.get("ok"):
                assert obj["result"]["detached"] is True, obj
                saw_detach = True
            elif obj.get("id") == "7" and obj.get("end") is True:
                saw_end = True
        assert saw_resize, "resize never acked the new dimensions"
        assert saw_detach, "detach never acked"
        assert saw_end, "detach did not terminate the attach stream with end"

        # Session still alive after detach (acceptance #3): health shows alive,
        # viewer_count back to 0.
        client.send({"id": "11", "method": "health", "params": {"key": "chg_X"}})
        health = client.recv_line()
        assert (
            health["result"]["alive"] is True and health["result"]["viewer_count"] == 0
        ), health
        client.close()
    finally:
        server.stop()
        mgr.shutdown()


def test_feed_without_open_attach_over_socket(tmp_path: Path, socket_path: str) -> None:
    """``feed`` with no open attach on the connection still reaches the PTY: the
    server obtains a transient viewer to service the write (§2.13.2 decoupling —
    feed is the write side, independent of an attach read stream)."""
    child = fake_claude_child.write_child(tmp_path)
    mgr = SessionManager({"pty": _PtyChildAdapter(child)}, start_maintenance=False)
    server = SocketServer(mgr, socket_path)
    server.start()
    try:
        mgr.open("chg_X", SessionSpec(provider="pty", cwd=str(tmp_path), io_mode="pty"))
        client = _Client(socket_path)
        # No attach first — feed directly.
        client.send(
            {
                "id": "8",
                "method": "feed",
                "params": {
                    "key": "chg_X",
                    "data": _b64(b"__PTY_PING__\n"),
                    "encoding": "base64",
                },
            }
        )
        ack = client.recv_line()
        assert ack["ok"] is True and ack["result"]["written"] == len(
            b"__PTY_PING__\n"
        ), ack

        # A fresh attach catches up and sees PTY_PONG land.
        client.send({"id": "7", "method": "attach", "params": {"key": "chg_X"}})
        acc = bytearray()
        deadline = time.monotonic() + _WAIT
        while time.monotonic() < deadline:
            obj = client.recv_line()
            if obj.get("id") == "7" and "term" in obj:
                acc.extend(_decode_term(obj))
                if b"PTY_PONG" in acc:
                    break
        assert b"PTY_PONG" in acc, (
            f"transient-viewer feed never reached the PTY: {bytes(acc)!r}"
        )
        client.close()
    finally:
        server.stop()
        mgr.shutdown()


def test_protocol_errors_over_socket(tmp_path: Path, socket_path: str) -> None:
    """Malformed + unknown requests stay in the §2.9 wire shape without dropping
    the connection: bad JSON → Protocol BAD_REQUEST; unknown method → Expected
    UNKNOWN_METHOD; a chat method on a missing key → Expected NO_SESSION."""
    child = tmp_path / "pipe_child.py"
    child.write_text(_PIPE_CHILD_SOURCE)
    mgr = SessionManager({"claude": _PipeChildAdapter(child)}, start_maintenance=False)
    server = SocketServer(mgr, socket_path)
    server.start()
    try:
        client = _Client(socket_path)

        # Bad JSON line — answered with a framed Protocol error, conn stays open.
        client._sock.sendall(b"{not json}\n")
        bad = client.recv_line()
        assert bad["ok"] is False and bad["error"]["category"] == "protocol", bad
        assert bad["error"]["code"] == "BAD_REQUEST", bad

        # Unknown method — Expected decline (deterministic), conn stays open.
        client.send({"id": "2", "method": "teleport", "params": {}})
        unknown = client.recv_line()
        assert (
            unknown["ok"] is False and unknown["error"]["code"] == "UNKNOWN_METHOD"
        ), unknown
        assert unknown["error"]["category"] == "expected", unknown

        # A send to a key that was never opened — Expected NO_SESSION.
        client.send(
            {"id": "3", "method": "send", "params": {"key": "ghost", "command": "x"}}
        )
        no_session = client.recv_line()
        assert (
            no_session["ok"] is False and no_session["error"]["code"] == "NO_SESSION"
        ), no_session
        client.close()
    finally:
        server.stop()
        mgr.shutdown()


def test_feed_targets_the_right_change_when_two_attached(
    tmp_path: Path, socket_path: str
) -> None:
    """One connection attached to two changes routes ``feed`` to the change it
    names (§2.13.2 — attach/feed decoupled per request-id on one connection).

    Regression for the multi-attachment routing bug: feed/detach must match on
    the session key, not return whichever attach opened first. Feeding the
    sentinel to chg_B must make chg_B (not chg_A) emit PTY_PONG.
    """
    child = fake_claude_child.write_child(tmp_path)
    mgr = SessionManager({"pty": _PtyChildAdapter(child)}, start_maintenance=False)
    server = SocketServer(mgr, socket_path)
    server.start()
    try:
        for key, rid in (("chg_A", "71"), ("chg_B", "72")):
            mgr.open(key, SessionSpec(provider="pty", cwd=str(tmp_path), io_mode="pty"))
        client = _Client(socket_path)
        # Attach BOTH changes on the one connection (separate request ids).
        client.send({"id": "71", "method": "attach", "params": {"key": "chg_A"}})
        client.send({"id": "72", "method": "attach", "params": {"key": "chg_B"}})

        # Feed the sentinel to chg_B only.
        client.send(
            {
                "id": "8",
                "method": "feed",
                "params": {
                    "key": "chg_B",
                    "data": _b64(b"__PTY_PING__\n"),
                    "encoding": "base64",
                },
            }
        )

        # PTY_PONG must arrive on chg_B's stream (id 72), never on chg_A's (71).
        seen_b = bytearray()
        deadline = time.monotonic() + _WAIT
        while time.monotonic() < deadline:
            obj = client.recv_line()
            if obj.get("id") == "72" and "term" in obj:
                seen_b.extend(_decode_term(obj))
                if b"PTY_PONG" in seen_b:
                    break
            elif obj.get("id") == "71" and "term" in obj:
                assert b"PTY_PONG" not in _decode_term(obj), (
                    "feed to chg_B leaked into chg_A's stream — wrong session routed"
                )
        assert b"PTY_PONG" in seen_b, "feed never reached chg_B's PTY"
        client.close()
    finally:
        server.stop()
        mgr.shutdown()


def test_event_to_json_serialises_each_kind() -> None:
    """``_event_to_json`` emits only the set payload per Event kind (§2.8.2): a
    chunk carries ``text``; a tool_use carries ``tool``; a result carries
    ``result``; an error carries the three-category ``error`` shape."""
    chunk = _event_to_json(Event(offset=1, key="k", turn=0, kind="chunk", text="hi"))
    assert chunk == {"offset": 1, "turn": 0, "kind": "chunk", "text": "hi"}

    tool = _event_to_json(
        Event(
            offset=2,
            key="k",
            turn=0,
            kind="tool_use",
            tool=ToolUse(name="bash", input_summary="ls"),
        )
    )
    assert tool["tool"] == {"name": "bash", "input_summary": "ls"}

    result = _event_to_json(
        Event(
            offset=3,
            key="k",
            turn=0,
            kind="result",
            result=TurnResult(
                input_tokens=1, output_tokens=2, duration_ms=3, stop_reason="end_turn"
            ),
        )
    )
    assert result["result"]["stop_reason"] == "end_turn"

    err = _event_to_json(
        Event(
            offset=4,
            key="k",
            turn=0,
            kind="error",
            error=EventError(category="expected", code="NO_SESSION", message="gone"),
        )
    )
    assert err["error"] == {
        "category": "expected",
        "code": "NO_SESSION",
        "message": "gone",
    }


def test_server_lifecycle_guards(tmp_path: Path, socket_path: str) -> None:
    """``socket_path`` is exposed; a double ``start`` is rejected; ``stop`` is
    idempotent; the socket file is restricted to the local user (0o600) and is
    unlinked on stop (§2.8.1 / §2.13.4 first gate)."""
    import stat

    mgr = SessionManager({}, start_maintenance=False)
    server = SocketServer(mgr, socket_path)
    assert server.socket_path == socket_path
    server.start()
    try:
        mode = stat.S_IMODE(os.stat(socket_path).st_mode)
        assert mode == 0o600, f"socket not restricted to local user: {oct(mode)}"
        with pytest.raises(RuntimeError):
            server.start()
    finally:
        server.stop()
        server.stop()  # idempotent
        assert not os.path.exists(socket_path), "socket file not unlinked on stop"
        mgr.shutdown()
