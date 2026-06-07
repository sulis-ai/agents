"""``_session_manager.socket_server`` — the §2.8 Unix-domain NDJSON socket layer.

Contract: ``SESSION_MANAGER_CONTRACT.md`` §2.8 (the cross-process cockpit binding
— a local Unix-domain socket carrying newline-delimited JSON, LSP-style; no TCP,
no network port, CP-01) and §2.8.2 (the wire protocol: one JSON object per line,
requests carry an ``id``, responses echo it, streaming responses are many lines
terminated by ``end``). The interactive-terminal extension
``SESSION_MANAGER_CONTRACT.extension.md`` §2.13 adds the cockpit *attach* wire
shape: ``attach`` (streaming ``term`` lines, snapshot phase then live),
``feed`` (fire-and-ack ``{"written":N}``), ``detach``, ``resize`` (§2.13.3,
``TIOCSWINSZ``). Raw terminal bytes are **base64-encoded** in the JSON ``term`` /
``feed`` ``data`` field (§2.13.1 — NDJSON is a text protocol, terminal bytes are
binary; base64 is the boring binary-in-JSON encoding, CP). §2.13.4 puts the
security gate at *attach authorisation*: a connection bound to change *X* may not
attach change *Y* (the binding guard, ADE ADR-004) — and the socket's own
filesystem permissions restrict it to the local user (§2.8.1, the first gate).
Errors are the three §2.15 categories.

**This is the remote adapter over the in-process manager surface.** It is
EXPAND-Create on a seam we own (ADR-003): the six chat methods dispatch to the
:class:`SessionManager` six-method surface (§2.2) and the four terminal methods
dispatch to its ``attach`` → :class:`Viewer` port (§2.12, WP-004). The manager is
the single source of truth; the socket is pure transport (it is the *only* layer
that base64-encodes — the in-process viewer speaks raw bytes; encoding is a
transport concern, not a model one, contract §2.11.1).

**Threading model (boring stdlib, CP).** One handler thread per connection
(``socketserver.ThreadingMixIn`` over ``UnixStreamServer``). A connection may
have at most one in-flight ``attach`` per ``key`` (the read side) plus any number
of fire-and-ack requests (``feed``/``detach``/``resize``/``send``/…) — mirroring
the base ``send`` vs ``read`` decoupling (§2.13.2). The ``attach`` stream runs on
its own pump thread draining the viewer's ``stream()`` and framing each chunk as
a base64 ``term`` line; the handler thread keeps reading requests concurrently.
All writes to the connection are serialised under a per-connection lock so two
producers (the attach pump + a fire-and-ack response) never interleave a line.
"""

from __future__ import annotations

import base64
import fcntl
import json
import os
import socket
import socketserver
import struct
import termios
import threading
from collections.abc import Callable
from typing import TYPE_CHECKING

from _session_manager.events import (
    NOT_AUTHORIZED,
    SessionError,
)
from _session_manager.adapter import SessionSpec

if TYPE_CHECKING:  # pragma: no cover - typing only
    from _session_manager.manager import SessionManager
    from _session_manager.viewer import Viewer

#: The terminal methods the §2.13.4 binding guard scopes to a change. Chat
#: methods (§2.2) are unguarded beyond the local-socket filesystem permission —
#: they are the existing base-contract surface; the attach/feed/detach/resize
#: quartet is what grants control of a *live shell* in the change's worktree, so
#: it is exactly these the guard fences (ADR-003 §Security).
_GUARDED_METHODS = frozenset({"attach", "feed", "detach", "resize"})

#: Wire method name → the ``_Handler`` method that services it. Defined once at
#: module load (not rebuilt per request) and resolved via ``getattr`` on the
#: handler instance — a typo here is a load-time AttributeError at dispatch, not a
#: silent miss. The six chat methods (§2.2) + the four terminal methods (§2.13).
_METHOD_HANDLERS: dict[str, str] = {
    "open": "_open",
    "send": "_send_method",
    "read": "_read",
    "health": "_health",
    "status": "_status",
    "close": "_close",
    "attach": "_attach",
    "feed": "_feed",
    "detach": "_detach",
    "resize": "_resize",
}

#: Type of the optional per-connection binding resolver (§2.13.4). Given the
#: connection's socket, return the single change ``key`` that connection is
#: authorised for — a connection bound to change X. When ``None`` (no binding
#: configured), only the local-socket filesystem gate applies and every key the
#: manager owns is reachable. The verbatim ADE ADR-004 mechanism (scope a
#: connection to one change) applied to the terminal methods — no new auth.
BoundKeyResolver = Callable[[socket.socket], "str | None"]


class _ConnectionState:
    """Per-connection bookkeeping for one handler thread.

    Owns the write lock (so the attach pump thread and fire-and-ack responses
    never interleave a line on the wire) and the registry of active attach
    streams keyed by request ``id`` (so ``detach`` / disconnect can end them —
    the §2.15 ``SOCKET_CLOSED`` teardown).
    """

    def __init__(self, sock: socket.socket) -> None:
        self.sock = sock
        self.write_lock = threading.Lock()
        #: request-id → ``(session key, live Viewer)`` for an open attach stream
        #: on this connection. Keyed by request-id (each ``attach`` has its own
        #: id) and carries the session key so ``feed`` / ``detach`` target the
        #: RIGHT session when one connection holds attachments to more than one
        #: change (§2.13.2 — attach/feed are decoupled per-id on one connection).
        self.attachments: dict[str, tuple[str, "Viewer"]] = {}
        #: attach pump threads, joined on disconnect so none outlives the conn.
        self.pumps: list[threading.Thread] = []
        self.lock = threading.Lock()


class _Handler(socketserver.BaseRequestHandler):
    """One per connection: read NDJSON request lines, dispatch, frame responses.

    The server (set on the class via :meth:`SocketServer.start`) carries the
    manager + the binding resolver. Each request line is one JSON object; the
    framing buffers partial lines until their newline (§2.8.2).
    """

    server: "_NDJSONServer"

    def handle(self) -> None:
        state = _ConnectionState(self.request)
        buf = b""
        try:
            while True:
                chunk = self.request.recv(65536)
                if not chunk:
                    break  # peer closed — normal disconnect
                buf += chunk
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    if line.strip():
                        self._dispatch(state, line)
        except OSError:
            # Transport dropped mid-read (the §2.15 SOCKET_CLOSED condition); the
            # finally below tears down any open attach streams.
            pass
        finally:
            self._teardown(state)

    # ── dispatch ────────────────────────────────────────────────────────────

    def _dispatch(self, state: _ConnectionState, line: bytes) -> None:
        """Parse one request line and route it to its handler.

        A malformed line or unknown method is answered with a framed error
        rather than dropping the connection — the wire stays in the §2.9 shape.
        """
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            self._send(
                state,
                {
                    "ok": False,
                    "error": _err("protocol", "BAD_REQUEST", "line is not valid JSON"),
                },
            )
            return
        req_id = req.get("id")
        method = req.get("method")
        params = req.get("params") or {}

        # §2.13.4 binding guard: the terminal methods are scoped to the
        # connection's bound change. Decline cross-change access deterministically
        # (Expected NOT_AUTHORIZED) before the op runs.
        if method in _GUARDED_METHODS and not self._authorised(
            state, params.get("key")
        ):
            self._send(state, _error_response(req_id, ExpectedAuthDecline()))
            return

        handler_name = _METHOD_HANDLERS.get(method)
        if handler_name is None:
            self._send(state, _error_response(req_id, ExpectedUnknownMethod(method)))
            return
        try:
            getattr(self, handler_name)(state, req_id, params)
        except SessionError as exc:
            self._send(state, _error_response(req_id, exc))
        except Exception as exc:  # noqa: BLE001 - map any bug onto Internal (§2.9)
            self._send(
                state,
                {
                    "id": req_id,
                    "ok": False,
                    "error": _err("internal", "UNEXPECTED", str(exc)),
                },
            )

    def _authorised(self, state: _ConnectionState, key: object) -> bool:
        """Whether this connection may act on ``key`` (the §2.13.4 gate).

        With no binding resolver, only the local-socket filesystem permission
        gates (every key is reachable). With a resolver, the connection is bound
        to exactly the key it returns — any other key is declined.
        """
        resolver = self.server.bound_key_for
        if resolver is None:
            return True
        bound = resolver(state.sock)
        return bound is not None and bound == key

    # ── §2.2 chat methods (dispatch to the manager surface) ──────────────────

    def _open(self, state: _ConnectionState, req_id: object, params: dict) -> None:
        key = params["key"]
        spec_d = params.get("spec") or {}
        spec = SessionSpec(
            provider=spec_d["provider"],
            cwd=spec_d["cwd"],
            resume_ref=spec_d.get("resume_ref"),
            io_mode=spec_d.get("io_mode", "pipe"),
        )
        session = self.server.manager.open(key, spec)
        self._send(
            state,
            {
                "id": req_id,
                "ok": True,
                "result": {
                    "key": session.key,
                    "pid": session.pid,
                    "provider": session.spec.provider,
                    "io_mode": session.spec.io_mode,
                    "viewer_count": self.server.manager.health(key).viewer_count,
                    "state": session.state_machine.state.value,
                },
            },
        )

    def _send_method(
        self, state: _ConnectionState, req_id: object, params: dict
    ) -> None:
        offset = self.server.manager.send(params["key"], params["command"])
        self._send(state, {"id": req_id, "ok": True, "result": {"offset": offset}})

    def _read(self, state: _ConnectionState, req_id: object, params: dict) -> None:
        events = self.server.manager.read(
            params["key"],
            since=int(params.get("since", 0)),
            follow=bool(params.get("follow", False)),
        )
        for event in events:
            self._send(
                state, {"id": req_id, "ok": True, "event": _event_to_json(event)}
            )
        self._send(state, {"id": req_id, "ok": True, "end": True})

    def _health(self, state: _ConnectionState, req_id: object, params: dict) -> None:
        health = self.server.manager.health(params["key"])
        self._send(
            state,
            {
                "id": req_id,
                "ok": True,
                "result": {
                    "alive": health.alive,
                    "state": health.state,
                    "pid": health.pid,
                    "provider": health.provider,
                    "io_mode": health.io_mode,
                    "viewer_count": health.viewer_count,
                },
            },
        )

    def _status(self, state: _ConnectionState, req_id: object, params: dict) -> None:
        snapshot = self.server.manager.status()
        self._send(
            state,
            {
                "id": req_id,
                "ok": True,
                "result": [
                    {
                        "key": s.key,
                        "state": s.state,
                        "pid": s.pid,
                        "provider": s.provider,
                        "memory_bytes": s.memory_bytes,
                        "last_activity": s.last_activity,
                        "log_len": s.log_len,
                        "io_mode": s.io_mode,
                        "viewer_count": s.viewer_count,
                    }
                    for s in snapshot
                ],
            },
        )

    def _close(self, state: _ConnectionState, req_id: object, params: dict) -> None:
        self.server.manager.close(params["key"])
        self._send(state, {"id": req_id, "ok": True, "result": {"closed": True}})

    # ── §2.13 terminal methods (dispatch to the attach/viewer port) ──────────

    def _attach(self, state: _ConnectionState, req_id: object, params: dict) -> None:
        """Open a viewer and stream its bytes as base64 ``term`` lines (§2.13.1).

        The snapshot phase (the scrollback retained at attach) comes first, then
        live PTY bytes, terminated by ``end`` on detach or session close. The
        stream runs on its own pump thread so the handler keeps reading requests
        (``feed``/``detach``) concurrently (§2.13.2 decoupling).
        """
        key = params["key"]
        viewer = self.server.manager.attach(key)
        rid = str(req_id)
        with state.lock:
            state.attachments[rid] = (key, viewer)
        pump = threading.Thread(
            target=self._attach_pump,
            args=(state, req_id, viewer),
            name=f"socket-attach-{rid}",
            daemon=True,
        )
        with state.lock:
            state.pumps.append(pump)
        pump.start()

    def _attach_pump(
        self, state: _ConnectionState, req_id: object, viewer: "Viewer"
    ) -> None:
        """Drain ``viewer.stream()`` to base64 ``term`` lines until it ends.

        The viewer yields the snapshot chunk(s) first then live bytes (§2.12.2);
        the first chunk is the snapshot phase, the rest are live. The stream ends
        (StopIteration) when the viewer detaches or the session closes; ``end``
        terminates the request id (§2.8.2 streaming terminator).
        """
        phase = "snapshot"
        try:
            for chunk in viewer.stream():
                if not chunk:
                    continue
                self._send(
                    state,
                    {
                        "id": req_id,
                        "ok": True,
                        "term": {
                            "data": base64.b64encode(chunk).decode("ascii"),
                            "encoding": "base64",
                            "phase": phase,
                        },
                    },
                )
                phase = "live"  # only the first emitted chunk is the snapshot
        except OSError:
            # The connection dropped mid-stream — Protocol SOCKET_CLOSED (§2.15).
            # Nothing to send (the wire is gone); teardown detaches the viewer.
            return
        # The stream ended cleanly (detach / session close): terminate the id. A
        # broken pipe here means the peer closed between the last term line and
        # the terminator (a benign teardown race) — SOCKET_CLOSED, nothing to do.
        try:
            self._send(state, {"id": req_id, "ok": True, "end": True})
        except OSError:
            return

    def _feed(self, state: _ConnectionState, req_id: object, params: dict) -> None:
        """Feed base64-decoded keystroke bytes to the live PTY (§2.13.1).

        Fire-and-ack: returns ``{"written":N}`` where N is the byte count fed.
        The bytes pass verbatim to the PTY master (§2.12.4; ADR-003 — the trust
        boundary is attach authorisation, not byte content). The feed is keyed to
        the connection's open attach for this key; with no open attach, the
        manager's attach (a fresh viewer) services the write best-effort.
        """
        data = (
            base64.b64decode(params["data"])
            if params.get("encoding") == "base64"
            else params["data"].encode("utf-8")
        )
        rid_viewer = self._viewer_for_key(state, params["key"])
        if rid_viewer is not None:
            rid_viewer.feed(data)
        else:
            # No open attach on this connection: obtain a transient viewer to
            # feed (attach validates NOT_PTY_SESSION / NO_SESSION the same way).
            viewer = self.server.manager.attach(params["key"])
            viewer.feed(data)
            viewer.detach()
        self._send(state, {"id": req_id, "ok": True, "result": {"written": len(data)}})

    def _detach(self, state: _ConnectionState, req_id: object, params: dict) -> None:
        """Detach this connection's viewer(s) for the requested key (§2.12.3 —
        leaves the session running). Idempotent; ends the matching attach
        stream's ``end``. Only viewers for ``params['key']`` are detached, so a
        connection holding attachments to two changes detaches the right one."""
        key = params["key"]
        with state.lock:
            viewers = [v for (k, v) in state.attachments.values() if k == key]
        for viewer in viewers:
            viewer.detach()
        self._send(state, {"id": req_id, "ok": True, "result": {"detached": True}})

    def _resize(self, state: _ConnectionState, req_id: object, params: dict) -> None:
        """Set the PTY window size (§2.13.3, TIOCSWINSZ).

        Drives ``ioctl(master_fd, TIOCSWINSZ, …)`` so xterm.js can tell the PTY
        its dimensions — without it full-screen TUIs and line-wrapping render
        wrong. NOT_PTY_SESSION / NO_SESSION via the manager's attach validation.
        """
        rows = int(params["rows"])
        cols = int(params["cols"])
        # attach() validates the session is pty + exists (NO_SESSION /
        # NOT_PTY_SESSION) and gives us the master fd seam via the manager.
        master_fd = self._master_fd_for_key(params["key"])
        winsize = struct.pack("HHHH", rows, cols, 0, 0)
        fcntl.ioctl(master_fd, termios.TIOCSWINSZ, winsize)
        self._send(
            state, {"id": req_id, "ok": True, "result": {"rows": rows, "cols": cols}}
        )

    # ── helpers ───────────────────────────────────────────────────────────--

    def _viewer_for_key(self, state: _ConnectionState, key: str) -> "Viewer | None":
        """The connection's open attach viewer for ``key`` (None if none open).

        Matches on the session key so a ``feed`` writes to the PTY of the change
        it names — not whichever attach happened to open first when a connection
        holds attachments to more than one change (§2.13.2)."""
        with state.lock:
            for k, viewer in state.attachments.values():
                if k == key:
                    return viewer
        return None

    def _master_fd_for_key(self, key: str) -> int:
        """The manager-owned PTY master fd for ``key`` (validates pty/exists).

        Goes through ``attach`` so the same NO_SESSION / NOT_PTY_SESSION
        validation the contract mandates for the terminal methods runs; the
        transient viewer is detached immediately (resize touches the fd, not the
        stream)."""
        viewer = self.server.manager.attach(key)
        try:
            session = self.server.manager._require_session(key)  # noqa: SLF001
            fd = session.pty_master_fd
            assert fd is not None  # attach() already proved this is a pty session
            return fd
        finally:
            viewer.detach()

    def _send(self, state: _ConnectionState, obj: dict) -> None:
        """Write one NDJSON line, serialised under the per-connection lock so two
        producers never interleave (the attach pump + a fire-and-ack response)."""
        line = (json.dumps(obj) + "\n").encode("utf-8")
        with state.write_lock:
            self.request.sendall(line)

    def _teardown(self, state: _ConnectionState) -> None:
        """Detach every open attach + join the pumps on disconnect — no viewer or
        thread outlives the connection (the §2.15 SOCKET_CLOSED teardown)."""
        with state.lock:
            viewers = [v for (_k, v) in state.attachments.values()]
            pumps = list(state.pumps)
            state.attachments.clear()
        for viewer in viewers:
            try:
                viewer.detach()
            except Exception:  # noqa: BLE001 - best-effort teardown
                pass
        for pump in pumps:
            pump.join(timeout=1.0)


# ── error helpers (the §2.9 three-category wire shape) ───────────────────────


class ExpectedAuthDecline(SessionError):
    """The §2.13.4 binding-guard decline as a raisable Expected error."""

    category = "expected"

    def __init__(self) -> None:
        super().__init__(
            NOT_AUTHORIZED,
            "connection is not authorised for this change's session",
        )


class ExpectedUnknownMethod(SessionError):
    """An unknown request method — declined deterministically (Expected)."""

    category = "expected"

    def __init__(self, method: object) -> None:
        super().__init__("UNKNOWN_METHOD", f"unknown method {method!r}")


def _err(category: str, code: str, message: str) -> dict:
    return {"category": category, "code": code, "message": message}


def _error_response(req_id: object, exc: SessionError) -> dict:
    return {
        "id": req_id,
        "ok": False,
        "error": _err(exc.category, exc.code, exc.message),
    }


def _event_to_json(event) -> dict:
    """Serialise an :class:`Event` to its §2.8.2 wire shape (one ``event`` line).

    The base contract's example carries ``offset``/``turn``/``kind`` plus the
    kind's payload (``text`` for chunk, ``result`` for result, …). Only the set
    payload is emitted — the others are ``None`` (the Event invariant)."""
    out: dict = {"offset": event.offset, "turn": event.turn, "kind": event.kind}
    if event.text is not None:
        out["text"] = event.text
    if event.tool is not None:
        out["tool"] = {
            "name": event.tool.name,
            "input_summary": event.tool.input_summary,
        }
    if event.result is not None:
        out["result"] = {
            "input_tokens": event.result.input_tokens,
            "output_tokens": event.result.output_tokens,
            "duration_ms": event.result.duration_ms,
            "stop_reason": event.result.stop_reason,
        }
    if event.error is not None:
        out["error"] = _err(event.error.category, event.error.code, event.error.message)
    return out


# ── the server ───────────────────────────────────────────────────────────--


class _NDJSONServer(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    """A threaded AF_UNIX server carrying the manager + the binding resolver to
    each handler. One handler thread per connection (ThreadingMixIn)."""

    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self,
        socket_path: str,
        manager: "SessionManager",
        bound_key_for: BoundKeyResolver | None,
    ) -> None:
        self.manager = manager
        self.bound_key_for = bound_key_for
        super().__init__(socket_path, _Handler)


class SocketServer:
    """The §2.8 Unix-domain NDJSON socket-serving layer (the remote adapter).

    Serves a :class:`SessionManager` over an AF_UNIX socket: the six chat methods
    (§2.2) and the four terminal methods (§2.13). Construct with the manager + a
    socket path; optionally a ``bound_key_for`` resolver implementing the §2.13.4
    binding guard (scope a connection to one change). :meth:`start` binds + serves
    on a background thread; :meth:`stop` shuts it down and unlinks the socket.

    Filesystem permission on the socket path restricts it to the local user
    (§2.8.1 / §2.13.4 first gate) — the boring, conventional local-IPC gate (CP).
    """

    def __init__(
        self,
        manager: "SessionManager",
        socket_path: str,
        *,
        bound_key_for: BoundKeyResolver | None = None,
    ) -> None:
        self._manager = manager
        self._socket_path = socket_path
        self._bound_key_for = bound_key_for
        self._server: _NDJSONServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def socket_path(self) -> str:
        return self._socket_path

    def start(self) -> None:
        """Bind the socket and serve on a background daemon thread.

        Reclaims a stale socket at the path (the conventional bind-time cleanup,
        base §2.8 Open Question #4) and chmods it to ``0o600`` so only the local
        user can connect — the §2.13.4 first gate (filesystem permission)."""
        if self._server is not None:
            raise RuntimeError("server already started")
        # Reclaim a stale socket file (a prior crash) before binding.
        try:
            os.unlink(self._socket_path)
        except FileNotFoundError:
            pass
        self._server = _NDJSONServer(
            self._socket_path, self._manager, self._bound_key_for
        )
        # Restrict the socket to the local user (§2.8.1 / §2.13.4 first gate).
        os.chmod(self._socket_path, 0o600)
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            name="session-manager-socket",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        """Shut the server down, close it, and unlink the socket. Idempotent."""
        server = self._server
        if server is not None:
            server.shutdown()
            server.server_close()
            self._server = None
        thread = self._thread
        if thread is not None:
            thread.join(timeout=2.0)
            self._thread = None
        try:
            os.unlink(self._socket_path)
        except FileNotFoundError:
            pass
