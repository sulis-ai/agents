"""The desktop viewer client — ``session_viewer.py`` (TDD §2.3, ADR-002, WP-005).

The local terminal program that runs inside the desktop launcher's window. It is
the **desktop sibling of** ``<LiveTerminal/>`` (``apps/cockpit/client/src/
components/LiveTerminal.tsx``): both attach a change's one shared session and
render it; both feed keystrokes back; both report terminal size; both
detach-on-exit leaving the session running. The difference is the transport — the
browser sibling needs a WebSocket bridge because a browser cannot open AF_UNIX;
the desktop window **is** a terminal, so it speaks the engine's §2.13 NDJSON wire
**directly** over the AF_UNIX socket (ADR-002 "reuse the wire, not the code").

Flow (TDD §2.3, the WP Contract):

1. ``ensure_daemon`` → the stable socket with a live shared daemon (WP-002).
2. ``connect`` one socket; the wire is request-id multiplexed (the
   ``socketWsTransport.ts`` shape): unary ``request`` + a streaming ``attach``.
3. ``open {key:change_id, spec:{provider:"pty", cwd:worktree, io_mode:"pty"}}`` —
   get-or-spawn (idempotent; the first view creates, later views attach).
4. ``resize {key, rows, cols}`` from ``os.get_terminal_size`` (sent at startup).
5. ``attach {key}``; for each streamed ``term`` line, base64-decode ``data`` and
   write the raw bytes to stdout. The first chunk is the scrollback snapshot
   (catch-up), the rest are live (acceptance #2).
6. Raw-mode the local TTY (``tty.setraw``, saving ``termios.tcgetattr`` first);
   read stdin bytes → ``feed {key, data:b64, encoding:"base64"}`` (verbatim — the
   engine passes them to the pty master).
7. ``SIGWINCH`` handler → ``resize`` from the current terminal size.
8. **Exit (any path — EOF, signal, socket close): send ``detach {key}``, restore
   the TTY from the saved attrs in a ``finally``, exit 0.** The session keeps
   running (acceptance #4, #5). **DETACH-ONLY** (founder decision, TDD §7 Q1):
   closing the window never sends ``close`` — ending a session stays the
   cockpit's / ``sulis-change finish``'s job.

**TTY restore on every exit path is a MUST (ASR-8):** a raw terminal left behind
is an unusable shell. The restore lives in a ``finally`` that runs however the
viewer exits.

**Independence (founder directive, MUST; ADR-003):** stdlib only. No chat relay,
no ``platform`` communication service, no cockpit code. The only project import is
``_session_manager.daemon_client`` (the WP-002 ensure-daemon binding, itself
stdlib-only). The terminal path is terminal-only.

**Bytes are never logged (NFR-SEC-03 parity):** keystrokes and pty output flow
between stdin/stdout and the socket and are never written to any log; diagnostics
carry the change id + outcome only, never payload.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import queue
import select
import signal
import socket as socketlib
import sys
import termios
import threading
import tty
from pathlib import Path

# Run from any cwd: the engine's daemon-presence binding lives under this file's
# directory (the scripts dir that hosts the daemon). Mirror the daemon's import
# wiring so the viewer resolves its one project import regardless of cwd.
_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:  # pragma: no cover - cwd-dependent import guard
    sys.path.insert(0, str(_SCRIPTS))

from _session_manager import daemon_client  # noqa: E402

#: How long to wait for a unary request (open/resize) ack before giving up. The
#: socket is local IPC — a healthy daemon answers in microseconds; this bound
#: only guards a wedged daemon so the viewer fails fast rather than hanging the
#: window forever.
_REQUEST_TIMEOUT = 30.0

#: A short bound for the best-effort ``detach`` on exit. The window must close
#: promptly even if the daemon is slow — the connection drop detaches server-side
#: anyway (the §2.15 SOCKET_CLOSED teardown), so a slow detach ack is never worth
#: holding the TTY restore for.
_DETACH_TIMEOUT = 2.0

#: Read size for the stdin keystroke pump + the socket reader. 65536 matches the
#: engine's own recv size — big enough to never fragment a paste, small enough to
#: stay responsive.
_READ_SIZE = 65536


class _Connection:
    """A request-id-multiplexed NDJSON client over the AF_UNIX socket.

    The exact ``socketWsTransport.ts`` shape (ADR-002 "same wire"): one socket
    carries a streaming ``attach`` (many ``term`` lines on one request id) plus
    any number of unary fire-and-ack requests (``open``/``resize``/``feed``/
    ``detach``) on their own ids. A single reader thread demultiplexes every
    inbound line by id: ``term`` lines for the attach id are handed to the
    ``on_term`` sink; every other line is a unary reply routed to the waiting
    caller's queue by id. All sends are serialised under a lock so two producers
    (the stdin feed pump + a SIGWINCH resize) never interleave a line — the
    client mirror of the server's per-connection write lock.
    """

    def __init__(self, socket_path: str) -> None:
        self._sock = socketlib.socket(socketlib.AF_UNIX, socketlib.SOCK_STREAM)
        self._sock.connect(socket_path)
        self._send_lock = threading.Lock()
        self._buf = b""
        #: request-id → reply queue for unary calls awaiting their ack.
        self._replies: dict[str, queue.Queue[dict]] = {}
        self._replies_lock = threading.Lock()
        self._next_id = 0
        self._id_lock = threading.Lock()
        #: the attach stream's request id + its raw-bytes sink (set by ``attach``).
        self._attach_id: str | None = None
        self._on_term = None
        self._reader: threading.Thread | None = None
        self._closed = threading.Event()

    # ── ids + framing ────────────────────────────────────────────────────────

    def _alloc_id(self) -> str:
        with self._id_lock:
            self._next_id += 1
            return f"r{self._next_id}"

    def _send(self, obj: dict) -> None:
        line = (json.dumps(obj) + "\n").encode("utf-8")
        with self._send_lock:
            self._sock.sendall(line)

    def start_reader(self) -> None:
        """Start the demux reader thread.

        MUST be called **before** the first :meth:`request` — every inbound line
        (unary acks AND ``term`` stream lines) is routed by this one thread, so a
        unary ``open``/``resize`` ack issued before the reader exists would never
        be consumed and the caller would block forever. The reader runs for the
        connection's life; the ``term`` sink is registered separately at
        :meth:`attach` time (the attach id is not known until then)."""
        self._reader = threading.Thread(
            target=self._read_loop, name="viewer-socket-reader", daemon=True
        )
        self._reader.start()

    def set_term_sink(self, on_term) -> None:
        """Register the raw-bytes sink for ``term`` lines on the attach id.
        ``on_term(bytes)`` receives the decoded bytes of each ``term`` line
        (snapshot first, then live)."""
        self._on_term = on_term

    def _read_loop(self) -> None:
        try:
            while True:
                while b"\n" not in self._buf:
                    chunk = self._sock.recv(_READ_SIZE)
                    if not chunk:  # pragma: no cover - defensive: peer-close mid-frame
                        return  # peer closed — the §2.15 SOCKET_CLOSED path
                    self._buf += chunk
                line, self._buf = self._buf.split(b"\n", 1)
                if line.strip():
                    self._route(line)
        except OSError:
            # Transport dropped mid-read — the viewer exits its read loop and the
            # main thread's finally detaches + restores the tty.
            return
        finally:
            self._closed.set()

    def _route(self, line: bytes) -> None:
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:  # pragma: no cover - defensive: malformed wire line
            return  # a malformed line cannot be routed; drop it (never logged)
        rid = obj.get("id")
        # An attach ``term`` line → the raw-bytes sink (stdout). The first chunk
        # is the snapshot phase, the rest live (the server tags ``term.phase``).
        if rid is not None and rid == self._attach_id and "term" in obj:
            term = obj["term"]
            data = (
                base64.b64decode(term["data"])
                if term.get("encoding") == "base64"
                else str(term.get("data", "")).encode("utf-8")
            )
            if self._on_term is not None and data:
                self._on_term(data)
            return
        # The attach stream's terminator (detach / session close).
        if rid is not None and rid == self._attach_id and obj.get("end") is True:
            self._closed.set()
            return
        # Otherwise a unary reply: route to the waiting caller by id.
        if rid is not None:
            with self._replies_lock:
                q = self._replies.get(str(rid))
            if q is not None:
                q.put(obj)

    # ── unary request/ack ────────────────────────────────────────────────────

    def request(self, method: str, params: dict, *, timeout: float) -> dict:
        """Send a unary request and block for its ack (by id). Returns the reply
        object; raises :class:`ViewerError` on an error reply or timeout."""
        rid = self._alloc_id()
        reply_q: queue.Queue[dict] = queue.Queue(maxsize=1)
        with self._replies_lock:
            self._replies[rid] = reply_q
        try:
            self._send({"id": rid, "method": method, "params": params})
            try:
                reply = reply_q.get(timeout=timeout)
            except queue.Empty as exc:  # pragma: no cover - defensive: wedged daemon
                raise ViewerError(
                    f"no ack for {method!r} within {timeout}s (daemon wedged?)"
                ) from exc
        finally:
            with self._replies_lock:
                self._replies.pop(rid, None)
        if reply.get("ok") is not True:
            err = reply.get("error", {})
            raise ViewerError(
                f"{method} declined: {err.get('code', '?')} ({err.get('category', '?')})"
            )
        return reply

    def attach(self, key: str) -> None:
        """Begin the streaming attach for ``key``. Fire-and-stream: there is no
        ack — the ``term`` lines (snapshot then live) start flowing to the
        ``on_term`` sink, terminated by ``end`` on detach / session close."""
        rid = self._alloc_id()
        self._attach_id = rid
        self._send({"id": rid, "method": "attach", "params": {"key": key}})

    def detach(self, key: str, *, timeout: float = _DETACH_TIMEOUT) -> None:
        """Detach this connection's viewer for ``key`` (DETACH-ONLY — leaves the
        session running, acceptance #4/#5). Best-effort with a SHORT timeout: on
        exit the socket may already be gone (or the reader thread stalled writing
        to a full stdout), so a failed/slow detach is swallowed — the tty restore
        must never be held up by it (the session lifecycle is daemon-owned, and
        the connection closing also detaches server-side via the §2.15
        teardown)."""
        try:
            self.request("detach", {"key": key}, timeout=timeout)
        except (ViewerError, OSError):  # pragma: no cover - best-effort on exit
            pass

    def close(self) -> None:
        try:
            self._sock.close()
        except OSError:  # pragma: no cover - best-effort teardown
            pass

    @property
    def closed(self) -> threading.Event:
        """Set when the attach stream ends or the socket drops — the stdin pump
        watches it so a server-side close also unblocks the viewer's exit."""
        return self._closed


class ViewerError(RuntimeError):
    """A viewer-level failure (a declined request, or a wedged daemon). Carries
    no payload bytes — only the method + the §2.15 error code (NFR-SEC-03)."""


def _terminal_size(fd: int) -> tuple[int, int]:
    """``(rows, cols)`` for the tty behind ``fd``; a sane default if it is not a
    tty (e.g. a pipe in a non-interactive context). ``os.get_terminal_size``
    returns ``(columns, lines)`` — flipped here to the wire's ``(rows, cols)``."""
    try:
        size = os.get_terminal_size(fd)
        return size.lines, size.columns
    except OSError:
        return 24, 80


#: How often the stdin feed pump wakes to re-check ``stop`` / the attach stream
#: closing, when no keystroke is waiting. Small enough that a server-side close
#: ends the viewer promptly, large enough not to busy-spin.
_PUMP_POLL_SECS = 0.1


def _feed_pump(
    conn: _Connection, key: str, stdin_fd: int, stop: threading.Event
) -> None:
    """Read raw stdin bytes and ``feed`` them verbatim to the pty (TDD §2.3 step
    6). Runs until stdin EOFs, the attach stream closes, or ``stop`` is set. The
    bytes pass straight through base64 to the wire and are **never logged**.

    The read is gated by ``select`` with a short timeout so the pump also wakes to
    notice the attach stream closing (a server-side detach / session close sets
    ``conn.closed``) — without it a blocking ``os.read`` would only ever return on
    a keystroke or EOF, and a server-side close would hang the viewer."""
    while not stop.is_set() and not conn.closed.is_set():
        ready, _w, _x = select.select([stdin_fd], [], [], _PUMP_POLL_SECS)
        if not ready:
            continue  # poll timeout — re-check stop / stream-closed and loop
        try:
            data = os.read(stdin_fd, _READ_SIZE)
        except OSError:  # pragma: no cover - defensive: tty vanished mid-read
            break  # the tty went away — exit the pump; finally detaches
        if not data:
            break  # EOF on stdin — the founder closed the window
        try:
            conn.request(
                "feed",
                {
                    "key": key,
                    "data": base64.b64encode(data).decode("ascii"),
                    "encoding": "base64",
                },
                timeout=_REQUEST_TIMEOUT,
            )
        except (ViewerError, OSError):  # pragma: no cover - defensive: session gone
            break  # the session/socket is gone — exit; finally detaches


def main(
    change_id: str,
    worktree: str,
    *,
    socket: str | None = None,
    stdin_fd: int | None = None,
    stdout_fd: int | None = None,
    spawn_command: list[str] | None = None,
    ready_timeout: float = 30.0,
) -> int:
    """Attach the desktop viewer to ``change_id``'s shared session and pump it.

    ``socket`` defaults to the stable daemon socket (``ensure_daemon`` cold-starts
    the daemon if needed). ``stdin_fd`` / ``stdout_fd`` default to the real
    stdin/stdout fds; tests inject a pty pair to drive the viewer headlessly.
    ``spawn_command`` is forwarded to ``ensure_daemon`` (tests inject one that
    never runs because they pass an already-live socket — the warm path).

    Returns 0 on a clean detach-on-exit. The TTY is restored on **every** exit
    path (ASR-8, MUST) via the ``finally`` block; the session keeps running
    (DETACH-ONLY).
    """
    in_fd = stdin_fd if stdin_fd is not None else sys.stdin.fileno()
    out_fd = stdout_fd if stdout_fd is not None else sys.stdout.fileno()

    # 1. Ensure a live daemon and resolve the socket (WP-002).
    socket_path = daemon_client.ensure_daemon(
        socket if socket is not None else daemon_client.resolve_default_socket(),
        ready_timeout=ready_timeout,
        spawn_command=spawn_command,
    )

    # Save the TTY attrs BEFORE raw mode so the finally can always restore them.
    # If stdin is not a tty (a pipe), there is nothing to save/restore.
    saved_attrs = None
    try:
        saved_attrs = termios.tcgetattr(in_fd)
    except (termios.error, OSError):  # pragma: no cover - defensive: stdin not a tty
        saved_attrs = None

    conn = _Connection(socket_path)
    stop = threading.Event()
    previous_sigwinch = None
    previous_sigterm = None
    previous_sigint = None

    def _on_term(data: bytes) -> None:
        # Raw pty bytes straight to stdout (snapshot then live). Never logged.
        try:
            os.write(out_fd, data)
        except OSError:  # pragma: no cover - defensive: stdout closed mid-stream
            stop.set()

    try:
        # SIGTERM / SIGINT → a clean, detach-only exit. The real desktop path:
        # the founder closes the window → the launcher signals the viewer → it
        # detaches and restores the TTY (the finally), leaving the session
        # running (DETACH-ONLY; never ``close``). Setting ``stop`` wakes the feed
        # pump's select so the finally runs instead of the default disposition
        # (which would kill the process and leave the TTY raw — an ASR-8 breach).
        def _request_exit(_signum, _frame) -> None:  # pragma: no cover - subprocess (SIGTERM test)
            stop.set()

        try:
            previous_sigterm = signal.signal(signal.SIGTERM, _request_exit)  # pragma: no cover - main-thread only (subprocess tests)
            previous_sigint = signal.signal(signal.SIGINT, _request_exit)  # pragma: no cover - main-thread only (subprocess tests)
        except (ValueError, OSError):
            # Not on the main thread (e.g. under a test harness thread) — the
            # in-process driver triggers exit via stdin EOF / stream close instead.
            previous_sigterm = None
            previous_sigint = None
        # 2. Start the demux reader BEFORE any request — it routes every inbound
        #    line (unary acks AND term-stream lines) on the one connection; a
        #    unary ack with no reader to consume it would block the caller.
        conn.start_reader()
        # 3. open (get-or-spawn): idempotent — first view creates, later attach.
        #    brief_change_id is the SAME change_id already used as the open key —
        #    routing it onto the spec is what briefs the pty session for the
        #    change it is FOR (WP-002, ADR-001).
        conn.request(
            "open",
            {
                "key": change_id,
                "spec": {
                    "provider": "pty",
                    "cwd": worktree,
                    "io_mode": "pty",
                    "brief_change_id": change_id,
                },
            },
            timeout=_REQUEST_TIMEOUT,
        )
        # 4. resize from the current terminal size (sent once at startup).
        #    Best-effort, exactly like the SIGWINCH resize below (step 7): a
        #    declined resize MUST NOT tear the viewer down. The daemon may
        #    decline it Expected (e.g. §2.13.4 NOT_AUTHORIZED, or a stale/peer
        #    daemon) — that is benign sizing, not a fatal condition. Swallowing
        #    it here lets the attach proceed instead of crashing the window with
        #    a traceback (the unguarded call was the bug).
        rows, cols = _terminal_size(out_fd)
        try:
            conn.request(
                "resize",
                {"key": change_id, "rows": rows, "cols": cols},
                timeout=_REQUEST_TIMEOUT,
            )
        except (ViewerError, OSError):
            pass
        # 5. attach: register the term sink (snapshot then live → stdout) and
        #    begin the stream. The reader (already running) routes term lines to
        #    the sink once the attach id is set.
        conn.set_term_sink(_on_term)
        conn.attach(change_id)

        # 7. SIGWINCH → resize. Installed only when we own a real tty (the main
        #    thread; signal handlers must be set there). Best-effort: a resize
        #    failure never tears the viewer down.
        def _handle_sigwinch(_signum, _frame) -> None:  # pragma: no cover - subprocess (SIGWINCH test)
            r, c = _terminal_size(out_fd)
            try:
                conn.request(
                    "resize",
                    {"key": change_id, "rows": r, "cols": c},
                    timeout=_REQUEST_TIMEOUT,
                )
            except (ViewerError, OSError):
                pass

        try:
            previous_sigwinch = signal.signal(signal.SIGWINCH, _handle_sigwinch)  # pragma: no cover - main-thread only (subprocess tests)
        except (ValueError, OSError):
            # Not on the main thread (or no SIGWINCH on this platform) — resize on
            # startup still happened; live resize is best-effort.
            previous_sigwinch = None

        # 6. raw-mode the TTY then pump stdin → feed until EOF / stream close.
        if saved_attrs is not None:
            tty.setraw(in_fd)
        _feed_pump(conn, change_id, in_fd, stop)

        return 0
    finally:
        # 8. DETACH-ONLY + restore the TTY on EVERY exit path (ASR-8, MUST).
        stop.set()
        # Restore the signal dispositions we installed so we leak no handlers.
        for signum, prev in (
            (signal.SIGWINCH, previous_sigwinch),
            (signal.SIGTERM, previous_sigterm),
            (signal.SIGINT, previous_sigint),
        ):
            if prev is not None:  # pragma: no cover - main-thread only (subprocess tests)
                try:
                    signal.signal(signum, prev)
                except (ValueError, OSError):  # pragma: no cover - best-effort
                    pass
        conn.detach(change_id)
        conn.close()
        # The tty restore is LAST and unconditional — a raw terminal left behind
        # is an unusable shell. Restore even if every step above raised.
        if saved_attrs is not None:
            try:
                termios.tcsetattr(in_fd, termios.TCSADRAIN, saved_attrs)
            except (termios.error, OSError):  # pragma: no cover - best-effort
                pass


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "The desktop viewer: attach a change's shared session over the "
            "stable daemon socket and run it in this terminal window."
        )
    )
    parser.add_argument(
        "--change-id",
        required=True,
        help="the change id whose session to attach (the session key)",
    )
    parser.add_argument(
        "--worktree",
        required=True,
        help="the change's worktree (the pty session's cwd on get-or-spawn)",
    )
    parser.add_argument(
        "--socket",
        default=None,
        help="override the daemon socket path (default: the stable socket)",
    )
    return parser.parse_args(argv)


def cli_main(argv: list[str] | None = None) -> int:
    """The launcher entry point: ``python session_viewer.py --change-id … --worktree …``.

    The thin CLI delegate (WPB-04 / WPB-09 done-means-wired) — it parses argv and
    calls :func:`main`, which owns the behaviour. The launcher (WP-006) invokes
    this in the desktop Terminal window in place of a raw ``claude``.
    """
    args = _parse_args(argv)
    return main(args.change_id, args.worktree, socket=args.socket)


if __name__ == "__main__":  # pragma: no cover - module entry point
    raise SystemExit(cli_main())
