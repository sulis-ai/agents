"""WP-005 (CH-01KTKB) — the desktop viewer client (``session_viewer.py``).

Contract: TDD §2.3 / ADR-002. The local terminal program the launcher's window
runs: ``ensure_daemon`` → ``open`` (get-or-spawn, pty) → ``resize`` → ``attach``
(render the scrollback snapshot, then live pty bytes, to stdout) → raw-mode
stdin → ``feed`` → ``SIGWINCH`` → ``resize`` → **detach-on-exit** (the session
keeps running) with the **TTY restored on every exit path** (ASR-8, MUST). It is
the desktop sibling of ``<LiveTerminal/>`` (``apps/cockpit/.../LiveTerminal.tsx``),
speaking the engine's §2.13 NDJSON wire **directly** over AF_UNIX — no WebSocket
bridge (the bridge exists only because a browser cannot open AF_UNIX).

Verification posture (MEA-09, no mocks): every test drives a **real**
:class:`SessionManager` over a **real** :class:`SocketServer` on a **real**
AF_UNIX socket, against the **real** pty-backed fake child
(``fake_claude_child`` ``pty`` mode over a real ``os.openpty()`` pair). The
viewer itself is driven with a **real pty pair** as its stdin/stdout, so raw
mode + ``SIGWINCH`` + TTY restore exercise real ``termios`` against a real tty —
the desktop window's exact runtime, minus the human at the keyboard.

The viewer calls ``ensure_daemon`` first; the tests pass an already-live socket
(the real server they started) plus a ``spawn_command`` that must never run, so
``ensure_daemon`` takes its warm path and spawns nothing — the viewer is tested
against the real daemon contract without a second daemon process.

Tests (RED first, per the WP Definition of Done):
    test_session_viewer.py::test_attach_renders_snapshot_then_live
    test_session_viewer.py::test_feed_roundtrip_stdin_to_child
    test_session_viewer.py::test_sigwinch_triggers_resize
    test_session_viewer.py::test_exit_detaches_session_survives_and_tty_restored
"""

from __future__ import annotations

import base64
import json
import os
import signal
import socket
import sys
import termios
import threading
import time
from pathlib import Path

import pytest

from _session_manager.adapter import SessionSpec
from _session_manager.binding import BindingManager, ConnectionBindingRegistry
from _session_manager.manager import SessionManager
from _session_manager.socket_server import SocketServer

# Shared test helpers live under tests/lib (mirror the socket suite's import
# pattern). ``fake_claude_child`` is the real PTY-backed child; the
# ``PtyChildAdapter`` spawns it in ``pty`` mode (echoes stdin, emits PTY_PONG on
# the ``__PTY_PING__`` sentinel) — the same no-mocks vehicle WP-005 (socket) used.
_SCRIPTS_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_SCRIPTS_DIR / "tests" / "lib"))
import fake_claude_child  # noqa: E402
from session_child_adapters import PtyChildAdapter as _PtyChildAdapter  # noqa: E402

# The unit under test lives beside the engine package in the scripts dir.
import session_viewer  # noqa: E402

# Bounded wait for threaded assertions (matches the socket suite's _WAIT): long
# enough never to flake on a loaded CI runner, short enough that a real hang
# fails fast.
_WAIT = 5.0


# ─── harness ─────────────────────────────────────────────────────────────────


class _RawClient:
    """A minimal NDJSON client over the real AF_UNIX socket.

    The role a *second* view (or the cockpit sidecar) plays: connect, attach a
    key, drain ``term`` lines. Used to prove the session SURVIVES the viewer's
    detach (a second client can still attach the same key, acceptance #4/#5).
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


def _decode_term(obj: dict) -> bytes:
    term = obj["term"]
    assert term["encoding"] == "base64", f"term not base64-encoded: {obj!r}"
    return base64.b64decode(term["data"])


def _drain_for(master_fd: int, needle: bytes, timeout: float = _WAIT) -> bytes:
    """Read the viewer's stdout (the pty master) until ``needle`` appears."""
    acc = bytearray()
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            data = os.read(master_fd, 65536)
        except OSError:
            break
        if data:
            acc.extend(data)
            if needle in acc:
                break
        else:
            time.sleep(0.01)
    return bytes(acc)


@pytest.fixture
def running_server(tmp_path: Path):
    """A real manager (pty fake child) + real SocketServer on a real socket.

    Yields ``(socket_path, manager)``. No binding guard — the desktop viewer
    speaks the wire directly (the binding guard is the cockpit's per-connection
    scope; the viewer's own integration is the wire round-trip, MEA-09)."""
    child = fake_claude_child.write_child(tmp_path)
    mgr = SessionManager({"pty": _PtyChildAdapter(child)}, start_maintenance=False)
    socket_path = str(tmp_path / "sm.sock")
    server = SocketServer(mgr, socket_path)
    server.start()
    try:
        yield socket_path, mgr
    finally:
        server.stop()
        mgr.shutdown()


def _never_spawn() -> list[str]:
    """A spawn_command for ensure_daemon that must never run (the socket is
    already live → ensure_daemon's warm path returns without spawning). If it
    DID run it would fail loudly, surfacing a warm-path regression."""
    return ["/nonexistent/this-spawn-must-never-run-xyz", "{socket}"]


def _run_viewer_in_thread(
    *,
    change_id: str,
    worktree: str,
    socket_path: str,
    stdin_fd: int,
    stdout_fd: int,
) -> tuple[threading.Thread, dict]:
    """Run ``session_viewer.main`` on a daemon thread, driven by the given pty
    fds as its stdin/stdout. Returns ``(thread, result)`` where ``result['rc']``
    is set when main returns."""
    result: dict = {}

    def _target() -> None:
        result["rc"] = session_viewer.main(
            change_id,
            worktree,
            socket=socket_path,
            stdin_fd=stdin_fd,
            stdout_fd=stdout_fd,
            spawn_command=_never_spawn(),
        )

    thread = threading.Thread(target=_target, name="viewer-under-test", daemon=True)
    thread.start()
    return thread, result


def _spawn_viewer_subprocess(socket_path, worktree, key, slave_fd, mgr):
    """Spawn a REAL viewer subprocess on ``slave_fd`` (its controlling tty) and
    block until it has opened ``key``'s session. The subprocess is the viewer's
    true runtime (real main-thread signal handlers); shared by the two tests that
    need real signals — SIGWINCH and SIGTERM (EP-03, 2-consumer extraction)."""
    import subprocess

    proc = subprocess.Popen(
        [
            sys.executable,
            str(_SCRIPTS_DIR / "session_viewer.py"),
            "--change-id",
            key,
            "--worktree",
            str(worktree),
            "--socket",
            socket_path,
        ],
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=subprocess.DEVNULL,
        env=dict(os.environ),
        start_new_session=False,  # stay in our process group; we signal it
    )
    deadline = time.monotonic() + _WAIT
    while time.monotonic() < deadline:
        if mgr._sessions.get(key) is not None:
            break
        time.sleep(0.02)
    assert mgr._sessions.get(key) is not None, "viewer subprocess never opened"
    return proc


# ─── the RED tests ───────────────────────────────────────────────────────────


def _stop_viewer(thread: threading.Thread, master_fd: int) -> int:
    """Cleanly stop a viewer-thread: EOF its stdin (close the master end) so it
    exits its feed loop, runs the detach + tty-restore finally, and joins. Return
    the (now-closed) master fd sentinel (-1) so the caller's finally never
    double-closes. A lingering viewer would hold the connection open and stall
    the ``running_server`` teardown — closing here keeps each test self-contained."""
    os.close(master_fd)
    thread.join(_WAIT)
    return -1


def test_attach_renders_snapshot_then_live(running_server, tmp_path: Path) -> None:
    """On attach, the scrollback snapshot is rendered to stdout BEFORE live bytes
    (acceptance #2: catch-up). The viewer opens the change's pty session
    (get-or-spawn), attaches, and writes the decoded pty bytes raw to its stdout.

    Drive: open the session directly and write SNAP_BEFORE so it lands in
    scrollback BEFORE the viewer attaches; then run the viewer pointed at a pty
    pair; assert SNAP_BEFORE reaches the viewer's stdout (the snapshot), then a
    post-attach LIVE_AFTER byte reaches it too (live phase)."""
    socket_path, mgr = running_server

    # Pre-seed scrollback: open the session and emit a line before the viewer
    # attaches, so it is in the snapshot the viewer must render first.
    session = mgr.open(
        "chg_V", SessionSpec(provider="pty", cwd=str(tmp_path), io_mode="pty")
    )
    os.write(session.pty_master_fd, b"SNAP_BEFORE\n")
    deadline = time.monotonic() + _WAIT
    while time.monotonic() < deadline:
        if b"SNAP_BEFORE" in session.scrollback.snapshot():
            break
        time.sleep(0.01)

    # The viewer's stdin/stdout is a real pty pair; the test reads the master.
    master_fd, slave_fd = os.openpty()
    try:
        thread, _result = _run_viewer_in_thread(
            change_id="chg_V",
            worktree=str(tmp_path),
            socket_path=socket_path,
            stdin_fd=slave_fd,
            stdout_fd=slave_fd,
        )
        # The snapshot must reach the viewer's stdout.
        out = _drain_for(master_fd, b"SNAP_BEFORE")
        assert b"SNAP_BEFORE" in out, f"snapshot not rendered to stdout: {out!r}"

        # A live byte after attach reaches stdout too (live phase).
        os.write(session.pty_master_fd, b"LIVE_AFTER\n")
        out2 = _drain_for(master_fd, b"LIVE_AFTER")
        assert b"LIVE_AFTER" in out2, f"live bytes not rendered to stdout: {out2!r}"
        master_fd = _stop_viewer(thread, master_fd)
    finally:
        if master_fd != -1:
            os.close(master_fd)
        os.close(slave_fd)


def test_open_threads_brief_change_id(running_server, tmp_path: Path) -> None:
    """WP-002: the viewer's ``open`` routes its change id into the session's
    ``brief_change_id`` so the pty session briefs for the change it is FOR.

    The viewer already keys the session by ``change_id``; this asserts that same
    value also reaches the spec's brief target (read back from the real manager's
    session registry — the spec the server actually built from the viewer's wire
    payload, MEA-09 no-mock)."""
    socket_path, mgr = running_server

    master_fd, slave_fd = os.openpty()
    try:
        thread, _result = _run_viewer_in_thread(
            change_id="chg_VB",
            worktree=str(tmp_path),
            socket_path=socket_path,
            stdin_fd=slave_fd,
            stdout_fd=slave_fd,
        )
        # The viewer opens get-or-spawn; wait for the session to exist, then read
        # back the spec the server constructed from the viewer's open payload.
        deadline = time.monotonic() + _WAIT
        while time.monotonic() < deadline:
            if mgr._sessions.get("chg_VB") is not None:
                break
            time.sleep(0.02)
        assert mgr._sessions.get("chg_VB") is not None, "viewer never opened"
        assert mgr._sessions["chg_VB"].spec.brief_change_id == "chg_VB"
        master_fd = _stop_viewer(thread, master_fd)
    finally:
        if master_fd != -1:
            os.close(master_fd)
        os.close(slave_fd)


def test_feed_roundtrip_stdin_to_child(running_server, tmp_path: Path) -> None:
    """Bytes written to the viewer's stdin reach the child (feed round-trip,
    echoed back into the live stream). Type the ``__PTY_PING__`` sentinel on the
    viewer's stdin; the pty child echoes it and emits ``PTY_PONG`` — both must
    surface on the viewer's stdout, proving stdin → feed → child → attach."""
    socket_path, _mgr = running_server

    master_fd, slave_fd = os.openpty()
    try:
        thread, _result = _run_viewer_in_thread(
            change_id="chg_V",
            worktree=str(tmp_path),
            socket_path=socket_path,
            stdin_fd=slave_fd,
            stdout_fd=slave_fd,
        )
        # Give the viewer a moment to open + attach before typing.
        time.sleep(0.2)

        # "Type" the sentinel on the viewer's stdin (write to the master end).
        os.write(master_fd, b"__PTY_PING__\n")

        # The child echoes input + emits PTY_PONG; both reach the viewer stdout.
        out = _drain_for(master_fd, b"PTY_PONG")
        assert b"PTY_PONG" in out, f"feed did not round-trip to the child: {out!r}"
        master_fd = _stop_viewer(thread, master_fd)
    finally:
        if master_fd != -1:
            os.close(master_fd)
        os.close(slave_fd)


def test_sigwinch_triggers_resize(running_server, tmp_path: Path) -> None:
    """``SIGWINCH`` triggers a ``resize`` — the child's pty sees the new winsize.

    Signal handlers must be installed on the main thread, so this test runs the
    viewer as a **real subprocess** (``python session_viewer.py``) with the
    slave pty as its controlling stdin/stdout — the exact desktop-window runtime.
    Grow the pty (TIOCSWINSZ) then deliver SIGWINCH to the viewer process; assert
    the child's pty window size (read from the session's master via TIOCGWINSZ)
    reflects the new dimensions — proof the viewer read its terminal size and
    sent a ``resize`` over the wire on SIGWINCH."""
    import fcntl
    import struct
    import subprocess

    socket_path, mgr = running_server

    master_fd, slave_fd = os.openpty()
    # Start with a known small size on the viewer's tty.
    fcntl.ioctl(slave_fd, termios.TIOCSWINSZ, struct.pack("HHHH", 24, 80, 0, 0))
    viewer_proc: subprocess.Popen | None = None
    try:
        viewer_proc = _spawn_viewer_subprocess(
            socket_path, tmp_path, "chg_V", slave_fd, mgr
        )
        child_master = mgr._sessions["chg_V"].pty_master_fd
        # Drain startup bytes so the pty buffer never blocks the child.
        time.sleep(0.3)
        _drain_noblock(master_fd)

        # Grow the viewer's terminal then deliver SIGWINCH to the viewer process.
        fcntl.ioctl(slave_fd, termios.TIOCSWINSZ, struct.pack("HHHH", 50, 160, 0, 0))
        viewer_proc.send_signal(signal.SIGWINCH)

        # The child's pty master must reflect the resized dimensions.
        deadline = time.monotonic() + _WAIT
        seen = None
        while time.monotonic() < deadline:
            rows, cols, _x, _y = struct.unpack(
                "HHHH", fcntl.ioctl(child_master, termios.TIOCGWINSZ, b"\x00" * 8)
            )
            seen = (rows, cols)
            if seen == (50, 160):
                break
            _drain_noblock(master_fd)
            time.sleep(0.02)
        assert seen == (50, 160), f"child pty winsize not resized on SIGWINCH: {seen}"
    finally:
        if viewer_proc is not None:
            viewer_proc.terminate()
            try:
                viewer_proc.wait(timeout=_WAIT)
            except subprocess.TimeoutExpired:  # pragma: no cover - defensive
                viewer_proc.kill()
        os.close(master_fd)
        os.close(slave_fd)


def _drain_noblock(fd: int) -> None:
    """Best-effort non-blocking drain of a pty master (keep its buffer clear so
    the child never stalls writing). Used by the resize test, which does not
    assert on the bytes — only on the child's winsize."""
    import fcntl as _fcntl

    flags = _fcntl.fcntl(fd, _fcntl.F_GETFL)
    _fcntl.fcntl(fd, _fcntl.F_SETFL, flags | os.O_NONBLOCK)
    try:
        while True:
            try:
                if not os.read(fd, 65536):
                    break
            except (BlockingIOError, OSError):
                break
    finally:
        _fcntl.fcntl(fd, _fcntl.F_SETFL, flags)


def test_exit_detaches_session_survives_and_tty_restored(
    running_server, tmp_path: Path
) -> None:
    """On exit, a ``detach`` is sent, the session SURVIVES (a second client can
    still attach the same key), and the TTY attrs are restored (ASR-8 MUST).

    The real desktop exit path: the founder closes the window → the launcher
    signals the viewer → it detaches and restores the TTY, leaving the session
    running (DETACH-ONLY, founder-locked). So this drives a **real viewer
    subprocess** (``python session_viewer.py``) on the slave pty and sends it
    SIGTERM; the master end stays open so the slave's restored attrs read back
    honestly. Then: (a) the slave's post-exit attrs equal the cooked baseline
    (raw mode undone); (b) a fresh client attaches ``chg_V`` and sees its
    scrollback marker — the session kept running."""
    import subprocess

    socket_path, mgr = running_server

    master_fd, slave_fd = os.openpty()
    # The cooked baseline the viewer must restore the slave tty to.
    attrs_before = termios.tcgetattr(slave_fd)
    viewer_proc: subprocess.Popen | None = None
    try:
        viewer_proc = _spawn_viewer_subprocess(
            socket_path, tmp_path, "chg_V", slave_fd, mgr
        )
        session = mgr._sessions["chg_V"]
        time.sleep(0.3)  # let raw-mode + attach settle
        _drain_noblock(master_fd)
        # A marker the surviving client should later see in scrollback.
        os.write(session.pty_master_fd, b"SURVIVES_MARKER\n")

        # Keep the master drained in the background so the viewer's stdout (the
        # slave) never fills — a full slave would block the viewer's reader thread
        # mid-restore. A real terminal emulator drains continuously; this mimics it.
        drain_stop = threading.Event()

        def _bg_drain() -> None:
            while not drain_stop.is_set():
                _drain_noblock(master_fd)
                time.sleep(0.02)

        drainer = threading.Thread(target=_bg_drain, daemon=True)
        drainer.start()

        # The window closes → SIGTERM the viewer → detach + restore + exit 0.
        viewer_proc.send_signal(signal.SIGTERM)
        rc = viewer_proc.wait(timeout=_WAIT)
        drain_stop.set()
        drainer.join(_WAIT)
        assert rc == 0, f"viewer did not exit cleanly on SIGTERM: rc={rc}"

        # (a) TTY restored: the canonical/echo bits the viewer's raw mode CLEARED
        #     are back ON, matching the cooked baseline. (Full-array equality is
        #     unreliable here: closing the subprocess's dup of the slave flips an
        #     OS-set bit in c_lflag on teardown; the load-bearing assertion is
        #     that ICANON|ECHO — the bits raw mode strips — were restored, so the
        #     shell is usable again. ASR-8.)
        cooked_mask = termios.ICANON | termios.ECHO
        before_lflag = attrs_before[3]
        after_lflag = termios.tcgetattr(slave_fd)[3]
        assert (after_lflag & cooked_mask) == (before_lflag & cooked_mask), (
            "TTY ICANON/ECHO not restored after exit (raw mode leaked) — ASR-8 breach: "
            f"before={before_lflag & cooked_mask:#x} after={after_lflag & cooked_mask:#x}"
        )
        assert before_lflag & cooked_mask, "baseline tty was not cooked (test setup)"

        # (b) Session survives: a fresh client attaches the same key and sees the
        #     scrollback marker — detach-only, the session kept running.
        client = _RawClient(socket_path)
        try:
            client.send({"id": "S", "method": "attach", "params": {"key": "chg_V"}})
            acc = bytearray()
            deadline = time.monotonic() + _WAIT
            while time.monotonic() < deadline:
                obj = client.recv_line()
                if obj.get("id") == "S" and "term" in obj:
                    acc.extend(_decode_term(obj))
                    if b"SURVIVES_MARKER" in acc:
                        break
            assert b"SURVIVES_MARKER" in acc, (
                f"session did not survive viewer detach: {bytes(acc)!r}"
            )
        finally:
            client.close()
    finally:
        if viewer_proc is not None and viewer_proc.poll() is None:
            viewer_proc.kill()
        os.close(master_fd)
        os.close(slave_fd)


# ─── focused coverage: the CLI wiring + value-path branches ─────────────────
# WPB-09 (done-means-wired): the launcher entry point (`cli_main` / `_parse_args`)
# is the wiring that makes the viewer reachable as
# `python session_viewer.py --change-id … --worktree …`; it earns direct
# coverage. These run in-process (the subprocess tests above prove the real
# runtime; these prove the delegate's parse + dispatch + the value-returning
# branches without spawning).


def test_cli_main_parses_and_delegates_to_main(monkeypatch):
    """`cli_main` parses `--change-id`/`--worktree`/`--socket` and delegates them
    verbatim to `main` (WPB-04 thin-delegate / WPB-09 wired) — the launcher's
    exact entry point. `main` is captured so this asserts the parse + dispatch
    contract without spawning (the real runtime is proven by the subprocess
    tests above)."""
    captured: dict = {}

    def _fake_main(change_id, worktree, *, socket=None, **_kw):
        captured["change_id"] = change_id
        captured["worktree"] = worktree
        captured["socket"] = socket
        return 0

    monkeypatch.setattr(session_viewer, "main", _fake_main)
    rc = session_viewer.cli_main(
        ["--change-id", "chg_CLI", "--worktree", "/w/t", "--socket", "/tmp/x.sock"]
    )
    assert rc == 0
    assert captured == {
        "change_id": "chg_CLI",
        "worktree": "/w/t",
        "socket": "/tmp/x.sock",
    }


def test_parse_args_requires_change_id_and_worktree():
    """`_parse_args` is argparse-strict: missing required flags exit non-zero
    (SystemExit) — the launcher cannot invoke the viewer without a change."""
    with pytest.raises(SystemExit):
        session_viewer._parse_args([])
    ns = session_viewer._parse_args(
        ["--change-id", "c", "--worktree", "/w"]
    )
    assert ns.change_id == "c" and ns.worktree == "/w" and ns.socket is None


def test_terminal_size_falls_back_off_a_tty():
    """`_terminal_size` returns a sane (rows, cols) default when the fd is not a
    tty (e.g. a pipe) — the resize at startup still sends real dimensions rather
    than raising. Drive it against a plain pipe fd (never a terminal)."""
    r_fd, w_fd = os.pipe()
    try:
        rows, cols = session_viewer._terminal_size(r_fd)
        assert rows == 24 and cols == 80
    finally:
        os.close(r_fd)
        os.close(w_fd)


def test_request_raises_viewer_error_on_declined(running_server, tmp_path):
    """A declined unary request surfaces as a `ViewerError` carrying the §2.15
    code only (no payload) — e.g. `open` with an unknown provider. Proves the
    error-path of the request/ack demux (the value-returning decline branch)."""
    socket_path, _mgr = running_server
    conn = session_viewer._Connection(socket_path)
    try:
        conn.start_reader()
        with pytest.raises(session_viewer.ViewerError) as exc:
            conn.request(
                "open",
                {
                    "key": "chg_bad",
                    "spec": {
                        "provider": "no-such-provider",
                        "cwd": str(tmp_path),
                        "io_mode": "pty",
                    },
                },
                timeout=_WAIT,
            )
        # The message carries the method + code, never any byte payload.
        assert "open" in str(exc.value)
    finally:
        conn.close()


def test_viewer_exits_when_session_closes_server_side(running_server, tmp_path):
    """If the session is closed server-side while the viewer is attached, the
    attach stream's `end` terminator sets `conn.closed`; the feed pump notices
    on its next select wake and the viewer exits cleanly (rc 0) — the TTY is
    restored even when the exit is driven by the stream closing, not stdin EOF.

    This exercises the `end`-route + closed-driven exit path in-process (the
    snapshot/feed tests exit via stdin EOF; this one via the server). NOTE: a
    server-side `close` ends THIS session — distinct from the founder closing the
    window (detach-only); both must restore the TTY and exit 0."""
    socket_path, mgr = running_server
    master_fd, slave_fd = os.openpty()
    result: dict = {}

    def _target() -> None:
        result["rc"] = session_viewer.main(
            "chg_close",
            str(tmp_path),
            socket=socket_path,
            stdin_fd=slave_fd,
            stdout_fd=slave_fd,
            spawn_command=_never_spawn(),
        )

    thread = threading.Thread(target=_target, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + _WAIT
        while time.monotonic() < deadline:
            if mgr._sessions.get("chg_close") is not None:
                break
            time.sleep(0.02)
        assert mgr._sessions.get("chg_close") is not None, "viewer never opened"
        time.sleep(0.2)  # let attach settle so the stream is live

        # Close the session server-side → attach stream ends → viewer exits.
        mgr.close("chg_close")
        thread.join(_WAIT)
        assert not thread.is_alive(), "viewer did not exit on server-side close"
        assert result.get("rc") == 0, f"viewer rc not 0 on stream close: {result!r}"
    finally:
        os.close(master_fd)
        os.close(slave_fd)


# ─── the §2.13.4 binding guard ON (production wiring) — regression for the ─────
#     startup-resize crash.
#
# The production daemon builds its server WITH the binding guard
# (``session_manager_daemon._build_server`` → ``bound_key_for=registry.resolve``).
# Every OTHER viewer test above uses ``running_server``, which builds it with the
# guard OFF — so the viewer's startup ``resize`` (``main`` step 4) was never
# exercised against a server that can DECLINE it. In production a declined
# startup resize crashed the desktop window with a ``NOT_AUTHORIZED`` traceback,
# because that one call was unguarded while its SIGWINCH twin (step 7) was not.
# These two tests run the viewer behind the REAL guard: one proves the authorised
# path still renders (closing the guard-on coverage gap); one proves a DECLINED
# startup resize no longer tears the viewer down.


@pytest.fixture
def running_server_guarded(tmp_path: Path):
    """A real manager + ``SocketServer`` with the §2.13.4 binding guard ON — the
    production daemon's exact wiring (``BindingManager`` records each connection's
    first-opened change on its handler thread; ``bound_key_for`` resolves it).
    Yields ``(socket_path, manager)``."""
    child = fake_claude_child.write_child(tmp_path)
    mgr = SessionManager({"pty": _PtyChildAdapter(child)}, start_maintenance=False)
    registry = ConnectionBindingRegistry()
    socket_path = str(tmp_path / "sm-guarded.sock")
    server = SocketServer(
        BindingManager(mgr, registry), socket_path, bound_key_for=registry.resolve
    )
    server.start()
    try:
        yield socket_path, mgr
    finally:
        server.stop()
        mgr.shutdown()


def test_guarded_authorised_path_renders_snapshot(
    running_server_guarded, tmp_path: Path
) -> None:
    """With the binding guard ON (production wiring), the viewer's own ``open``
    binds its connection to its change, so the subsequent guarded ``resize`` +
    ``attach`` are authorised and the snapshot renders. This is the path the
    desktop window actually runs — previously covered only with the guard OFF."""
    socket_path, mgr = running_server_guarded

    # Pre-seed scrollback (get-or-spawn: the viewer re-opens the same key).
    session = mgr.open(
        "chg_GA", SessionSpec(provider="pty", cwd=str(tmp_path), io_mode="pty")
    )
    os.write(session.pty_master_fd, b"SNAP_GUARDED\n")
    deadline = time.monotonic() + _WAIT
    while time.monotonic() < deadline:
        if b"SNAP_GUARDED" in session.scrollback.snapshot():
            break
        time.sleep(0.01)

    master_fd, slave_fd = os.openpty()
    try:
        thread, result = _run_viewer_in_thread(
            change_id="chg_GA",
            worktree=str(tmp_path),
            socket_path=socket_path,
            stdin_fd=slave_fd,
            stdout_fd=slave_fd,
        )
        out = _drain_for(master_fd, b"SNAP_GUARDED")
        assert b"SNAP_GUARDED" in out, (
            f"guard-on snapshot not rendered (authorised attach failed?): {out!r}"
        )
        master_fd = _stop_viewer(thread, master_fd)
        assert result.get("rc") == 0
    finally:
        if master_fd != -1:
            os.close(master_fd)
        os.close(slave_fd)


def test_guarded_declined_startup_resize_does_not_crash(tmp_path: Path) -> None:
    """A DECLINED startup resize must NOT tear the viewer down (the bug: the
    desktop window crashed with a ``NOT_AUTHORIZED`` traceback). Reproduce the
    production decline by wiring a binding resolver that authorises a DIFFERENT
    change than the viewer opens (the stale / peer-daemon condition), so every
    guarded method on the viewer's key is declined ``NOT_AUTHORIZED``. Assert the
    viewer survives: it swallows the declined startup resize, runs to a clean
    detach-on-exit, and returns rc 0.

    RED before the fix: ``main`` step 4's unguarded ``conn.request("resize", …)``
    raised ``ViewerError`` out of ``main`` (only a ``finally``, no ``except``), so
    the thread died and ``result['rc']`` was never set.
    """
    child = fake_claude_child.write_child(tmp_path)
    mgr = SessionManager({"pty": _PtyChildAdapter(child)}, start_maintenance=False)
    socket_path = str(tmp_path / "sm-decline.sock")
    # Resolver authorises a DIFFERENT change than the viewer opens → the guarded
    # resize (and attach) on the viewer's own key are declined NOT_AUTHORIZED.
    # ``open`` is ungated (not in _GUARDED_METHODS), so the session still spawns.
    server = SocketServer(
        mgr, socket_path, bound_key_for=lambda _sock: "some-other-change"
    )
    server.start()
    master_fd, slave_fd = os.openpty()
    try:
        thread, result = _run_viewer_in_thread(
            change_id="chg_DECL",
            worktree=str(tmp_path),
            socket_path=socket_path,
            stdin_fd=slave_fd,
            stdout_fd=slave_fd,
        )
        # Wait until the (ungated) open created the session — we are now past the
        # startup resize. With the fix the viewer swallowed the decline and is
        # pumping; without it the thread already died at the resize.
        deadline = time.monotonic() + _WAIT
        while time.monotonic() < deadline:
            if mgr._sessions.get("chg_DECL") is not None:
                break
            time.sleep(0.02)
        assert mgr._sessions.get("chg_DECL") is not None, "viewer never opened"
        master_fd = _stop_viewer(thread, master_fd)
        assert result.get("rc") == 0, (
            "viewer did not exit cleanly — a declined startup resize crashed it "
            f"(result={result!r})"
        )
    finally:
        if master_fd != -1:
            os.close(master_fd)
        os.close(slave_fd)
    server.stop()
    mgr.shutdown()
