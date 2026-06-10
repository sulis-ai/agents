"""WP-004 (CH-01KTGY) — the attach/viewer mechanism + io-mode/viewer-count.

Contract: ``SESSION_MANAGER_CONTRACT.extension.md`` §2.12.2 (``attach(key) ->
Viewer``; the ``Viewer`` protocol ``stream``/``feed``/``detach``), §2.12.3
(detach-leaves-running invariant), §2.12.4 (keystroke bytes pass VERBATIM to the
PTY master, ADR-003 §Security), §2.12.5 (additive ``io_mode`` + ``viewer_count``
on ``Health``/``SessionStatus``; ``viewer_count > 0`` ⇔ visible), §2.15
(``NOT_PTY_SESSION`` Expected error); ADR-001, ADR-003; TDD §1.3 / §3.

Verification posture (MEA-09, no mocks): every test drives a **real**
pty-backed child (WP-006's ``fake_claude_child`` ``pty`` mode) over a **real**
``os.openpty()`` pair the manager owns from spawn. ``attach`` is exercised
directly against a WP-003 pty session — the in-process port the socket layer
(WP-005) later exposes over the wire. The pipe-mode ``NOT_PTY_SESSION`` test
drives a real pipe-backed child so the decline is observed on a real session,
not a stub.

Tests (RED first, per the WP Definition of Done):
    test_viewer.py::test_snapshot_then_live
    test_viewer.py::test_feed_reaches_master
    test_viewer.py::test_detach_idempotent_leaves_running
    test_viewer.py::test_attach_on_pipe_is_not_pty
"""

from __future__ import annotations

import os
import sys
import threading
import time
from pathlib import Path

import pytest

from _session_manager.adapter import SessionSpec
from _session_manager.events import ExpectedError
from _session_manager.manager import SessionManager

# Shared test helpers live under tests/lib (mirrors the session suites' import
# pattern — sys.path.insert, then import). ``session_child_adapters`` carries the
# real pty + pipe ProviderAdapters extracted at the 2-consumer threshold (EP-03,
# shared with tests/integration/test_socket_server.py); ``fake_claude_child`` is
# the real PTY-backed child it spawns.
_SCRIPTS_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_SCRIPTS_DIR / "tests" / "lib"))
import fake_claude_child  # noqa: E402
from session_child_adapters import (  # noqa: E402
    PIPE_CHILD_SOURCE as _PIPE_CHILD_SOURCE,
    PipeChildAdapter as _PipeChildAdapter,
    PtyChildAdapter as _PtyChildAdapter,
)

# Bounded wait for a threaded assertion: long enough never to flake on a loaded
# CI runner, short enough that a real hang fails fast. Matches the session
# suites' _WAIT.
_WAIT = 5.0


def _wait_for(predicate, timeout: float = _WAIT) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


def _read_stream_until(viewer, needle: bytes, timeout: float = _WAIT) -> bytes:
    """Pull from ``viewer.stream()`` until ``needle`` is seen in the cumulative
    bytes or the timeout elapses; return the cumulative bytes read.

    ``stream()`` yields the scrollback snapshot first then live bytes; a bounded
    deadline guards against a hang if a byte never arrives.
    """
    acc = bytearray()
    deadline = time.monotonic() + timeout
    it = viewer.stream()
    while time.monotonic() < deadline:
        try:
            chunk = next(it)
        except StopIteration:
            break
        if chunk:
            acc.extend(chunk)
            if needle in acc:
                break
    return bytes(acc)


def test_snapshot_then_live(tmp_path: Path) -> None:
    """Open a pty session, produce output, ``attach``; assert ``stream()``
    yields the scrollback snapshot first, then live bytes (§2.12.2; acceptance
    #1, the 'render existing scrollback, not a blank pane' join).

    The child echoes everything written to the master back onto the master, so
    writing ``SNAP_BEFORE`` *before* attach lands it in the scrollback (the
    snapshot phase) and writing ``LIVE_AFTER`` *after* attach arrives as live
    bytes — the two-phase join the viewer guarantees.
    """
    child = fake_claude_child.write_child(tmp_path)
    mgr = SessionManager({"pty": _PtyChildAdapter(child)}, start_maintenance=False)
    try:
        spec = SessionSpec(provider="pty", cwd=str(tmp_path), io_mode="pty")
        session = mgr.open("term", spec)

        # Produce output BEFORE attaching — this is what the snapshot must carry.
        os.write(session.pty_master_fd, b"SNAP_BEFORE\n")
        assert _wait_for(lambda: b"SNAP_BEFORE" in session.scrollback.snapshot()), (
            "pre-attach output never reached the scrollback"
        )

        viewer = mgr.attach("term")

        # Drive a live byte AFTER attach; it must arrive via the live feed.
        os.write(session.pty_master_fd, b"LIVE_AFTER\n")

        seen = _read_stream_until(viewer, b"LIVE_AFTER")
        assert b"SNAP_BEFORE" in seen, (
            f"snapshot phase missing pre-attach scrollback; saw {seen!r}"
        )
        assert b"LIVE_AFTER" in seen, (
            f"live phase missing post-attach output; saw {seen!r}"
        )
        # Snapshot precedes live: the pre-attach marker appears before the
        # post-attach one in the yielded byte order.
        assert seen.index(b"SNAP_BEFORE") < seen.index(b"LIVE_AFTER"), (
            f"snapshot did not precede live in the stream; saw {seen!r}"
        )
        viewer.detach()
    finally:
        mgr.shutdown()


def test_feed_reaches_master(tmp_path: Path) -> None:
    """``feed(bytes)`` writes to the PTY master end; assert the echoing child's
    output (read back from the master via the live stream) contains those bytes
    verbatim (§2.12.2 / §2.12.4; acceptance #2, the two-way feed).

    The pty child echoes stdin straight back to stdout, so a ``feed`` that
    reaches the master returns on the master and surfaces in the viewer's live
    stream — proving the keystrokes reached the live PTY.
    """
    child = fake_claude_child.write_child(tmp_path)
    mgr = SessionManager({"pty": _PtyChildAdapter(child)}, start_maintenance=False)
    try:
        spec = SessionSpec(provider="pty", cwd=str(tmp_path), io_mode="pty")
        mgr.open("term", spec)
        viewer = mgr.attach("term")

        viewer.feed(b"FED_KEYSTROKES\n")

        seen = _read_stream_until(viewer, b"FED_KEYSTROKES")
        assert b"FED_KEYSTROKES" in seen, (
            f"fed keystrokes never echoed back from the master; saw {seen!r}"
        )
        viewer.detach()
    finally:
        mgr.shutdown()


def test_detach_idempotent_leaves_running(tmp_path: Path) -> None:
    """``detach()`` is safe to call twice; the session stays ``alive`` and
    ``viewer_count`` returns to 0 (§2.12.3 detach-leaves-running; §2.12.5
    viewer_count source of truth; acceptance #3).

    Attaching makes the session visible (``viewer_count == 1``); detaching
    twice is idempotent and leaves the process + PTY + scrollback intact —
    headless, but alive.
    """
    child = fake_claude_child.write_child(tmp_path)
    mgr = SessionManager({"pty": _PtyChildAdapter(child)}, start_maintenance=False)
    try:
        spec = SessionSpec(provider="pty", cwd=str(tmp_path), io_mode="pty")
        mgr.open("term", spec)

        assert mgr.health("term").viewer_count == 0, "fresh session is headless"
        assert mgr.health("term").io_mode == "pty"

        viewer = mgr.attach("term")
        assert _wait_for(lambda: mgr.health("term").viewer_count == 1), (
            "attach did not make the session visible (viewer_count==1)"
        )

        viewer.detach()
        viewer.detach()  # idempotent — a second detach must not raise

        assert _wait_for(lambda: mgr.health("term").viewer_count == 0), (
            "detach did not return viewer_count to 0 (headless)"
        )
        # Detach left the session RUNNING — the process is still alive.
        assert mgr.health("term").alive, "detach must leave the session running"
    finally:
        mgr.shutdown()


def test_attach_on_pipe_is_not_pty(tmp_path: Path) -> None:
    """``attach`` on a pipe-mode (non-pty) session raises Expected
    ``NOT_PTY_SESSION`` (§2.12.2 / §2.15) — there is no terminal to attach to;
    the consumer must ``open`` with ``io_mode="pty"``.

    This is the regression gate's attach half (INDEX): a default pipe session is
    byte-for-byte the base contract's chat path, and attaching to it declines
    deterministically rather than fabricating a terminal.
    """
    pipe_child = tmp_path / "pipe_child.py"
    pipe_child.write_text(_PIPE_CHILD_SOURCE)
    mgr = SessionManager(
        {"pipe": _PipeChildAdapter(pipe_child)}, start_maintenance=False
    )
    try:
        # Default io_mode is "pipe" — the existing chat path, unchanged.
        spec = SessionSpec(provider="pipe", cwd=str(tmp_path))
        session = mgr.open("chat", spec)
        assert session.pty_master_fd is None, "pipe session must have no pty master"

        with pytest.raises(ExpectedError) as excinfo:
            mgr.attach("chat")
        assert excinfo.value.code == "NOT_PTY_SESSION", (
            f"expected NOT_PTY_SESSION, got {excinfo.value.code!r}"
        )
    finally:
        mgr.shutdown()


def test_attach_no_session_is_no_session(tmp_path: Path) -> None:
    """``attach`` on a key with no open session raises Expected ``NO_SESSION``
    (§2.12.2 / §2.15) — the same eager decline ``read``/``health`` give."""
    child = fake_claude_child.write_child(tmp_path)
    mgr = SessionManager({"pty": _PtyChildAdapter(child)}, start_maintenance=False)
    try:
        with pytest.raises(ExpectedError) as excinfo:
            mgr.attach("never-opened")
        assert excinfo.value.code == "NO_SESSION", (
            f"expected NO_SESSION, got {excinfo.value.code!r}"
        )
    finally:
        mgr.shutdown()


# ─── registry/viewer unit isolation (no subprocess) ────────────────────────
#
# These drive the ViewerRegistry + concrete viewer directly against a stub
# session that owns only the two surfaces the viewer touches (``scrollback`` for
# the snapshot, ``pty_master_fd`` for feed). They cover the multi-viewer fan-out
# and the bounded-queue backpressure drop (§2.12.4) deterministically — paths a
# subprocess-driven test cannot force without contrivance.


class _StubScrollback:
    def __init__(self, data: bytes = b"") -> None:
        self._data = data

    def snapshot(self) -> bytes:
        return self._data


class _StubSession:
    """The minimal session surface the viewer reads: a scrollback + a master
    fd. ``pty_master_fd`` is ``None`` here (feed is exercised separately via the
    real-child tests); these units cover the snapshot + broadcast + drop paths."""

    def __init__(self, scrollback_bytes: bytes = b"") -> None:
        self.scrollback = _StubScrollback(scrollback_bytes)
        self.pty_master_fd = None


def test_broadcast_fans_out_to_every_attached_viewer() -> None:
    """One ``broadcast`` reaches every attached viewer's live stream (§2.12.2 —
    multiple viewers each render the same screen)."""
    from _session_manager.viewer import ViewerRegistry

    registry = ViewerRegistry(_StubSession(scrollback_bytes=b"SNAP"))
    v1 = registry.attach()
    v2 = registry.attach()
    assert registry.count == 2

    # Consume each stream on its own thread (mirrors real usage: the consumer
    # drains concurrently while the pump broadcasts), so the close sentinel is
    # lossless. Each thread collects until the stream ends.
    results: dict[str, bytes] = {}

    def _drain(name: str, viewer) -> None:
        results[name] = b"".join(viewer.stream())

    t1 = threading.Thread(target=_drain, args=("v1", v1), daemon=True)
    t2 = threading.Thread(target=_drain, args=("v2", v2), daemon=True)
    t1.start()
    t2.start()

    registry.broadcast(b"LIVE1")
    registry.close()  # end both streams so the iterators terminate
    t1.join(timeout=_WAIT)
    t2.join(timeout=_WAIT)

    assert results["v1"] == b"SNAPLIVE1", f"viewer 1 stream wrong: {results['v1']!r}"
    assert results["v2"] == b"SNAPLIVE1", f"viewer 2 stream wrong: {results['v2']!r}"


def test_live_queue_backpressure_drops_oldest() -> None:
    """A bounded live queue drops the OLDEST chunk under backpressure so a slow
    viewer never grows memory without limit (§2.12.4 SHOULD ceiling).

    With a maxsize-2 queue, the first two broadcasts fill it and the third
    evicts the oldest (the data-path drop). The broadcasts all happen BEFORE the
    consumer starts draining (so the queue genuinely overflows), then a
    concurrent drainer + ``close`` deliver the surviving chunks + the sentinel
    losslessly — separating the backpressure drop from teardown."""
    import _session_manager.viewer as viewer_module
    from _session_manager.viewer import ViewerRegistry

    # Shrink the per-viewer queue so the overflow drop is deterministic.
    original = viewer_module._LIVE_QUEUE_MAXSIZE
    viewer_module._LIVE_QUEUE_MAXSIZE = 2
    seen = b""
    try:
        registry = ViewerRegistry(_StubSession(scrollback_bytes=b"SNAP"))
        v = registry.attach()
        # Overflow the queue BEFORE anyone drains it: the oldest live chunk is
        # dropped to bound memory (§2.12.4).
        registry.broadcast(b"DROP_ME")  # [DROP_ME]
        registry.broadcast(b"KEEP1")  # [DROP_ME, KEEP1] — full
        registry.broadcast(b"KEEP2")  # evicts oldest → [KEEP1, KEEP2]

        # Now drain concurrently; close lands the sentinel losslessly once the
        # drainer frees a slot.
        result: dict[str, bytes] = {}

        def _drain() -> None:
            result["seen"] = b"".join(v.stream())

        drainer = threading.Thread(target=_drain, daemon=True)
        drainer.start()
        registry.close()
        drainer.join(timeout=_WAIT)
        seen = result.get("seen", b"")
    finally:
        viewer_module._LIVE_QUEUE_MAXSIZE = original

    assert b"SNAP" in seen, f"snapshot missing: {seen!r}"
    assert b"KEEP1" in seen and b"KEEP2" in seen, (
        f"a surviving live chunk was wrongly dropped: {seen!r}"
    )
    assert b"DROP_ME" not in seen, f"oldest live chunk not dropped: {seen!r}"


class _WritableFdSession:
    """A stub session whose ``pty_master_fd`` is the write end of a real
    ``os.pipe`` — so ``feed`` exercises the verbatim ``os.write`` + chunk loop +
    closed-fd swallow without spawning a child. Owns both ends for cleanup."""

    def __init__(self) -> None:
        self.scrollback = _StubScrollback(b"")
        self._read_fd, self.pty_master_fd = os.pipe()
        self.mark_active_calls = 0

    def mark_active(self) -> None:
        # ``feed`` bumps the idle clock on a successful write (#108); record the
        # call so the feed test can assert keystrokes register as activity.
        self.mark_active_calls += 1

    def read_all(self) -> bytes:
        # Drain whatever feed wrote (non-blocking read of buffered bytes).
        import select

        out = bytearray()
        while True:
            r, _, _ = select.select([self._read_fd], [], [], 0)
            if not r:
                break
            chunk = os.read(self._read_fd, 65536)
            if not chunk:
                break
            out.extend(chunk)
        return bytes(out)

    def cleanup(self) -> None:
        for fd in (self._read_fd, self.pty_master_fd):
            try:
                os.close(fd)
            except OSError:
                pass


def test_feed_writes_verbatim_then_chunks_oversize() -> None:
    """``feed`` writes bytes VERBATIM to the master fd (§2.12.4; ADR-003), and
    oversize input is written in bounded slices (the SHOULD throughput bound)
    without corrupting or reordering the bytes."""
    import _session_manager.viewer as viewer_module
    from _session_manager.viewer import ViewerRegistry

    session = _WritableFdSession()
    original = viewer_module._FEED_CHUNK_BYTES
    viewer_module._FEED_CHUNK_BYTES = 4  # force the slice loop
    try:
        registry = ViewerRegistry(session)
        v = registry.attach()
        payload = b"\x1b[31mABCDEFGHIJ\x00\n"  # control chars + NUL pass verbatim
        v.feed(payload)
        got = session.read_all()
        assert got == payload, f"feed did not write verbatim: {got!r} != {payload!r}"
        # A successful keystroke feed registers as in-use activity so the idle
        # clock is bumped (#108) — a session being typed into is not "idle".
        assert session.mark_active_calls == 1, (
            "feed did not mark the session active on a successful write (#108)"
        )
    finally:
        viewer_module._FEED_CHUNK_BYTES = original
        session.cleanup()


def test_feed_after_detach_is_noop() -> None:
    """``feed`` after ``detach`` is a no-op and never raises (§2.12.2 no-op-safe;
    §2.13.2 detach drops feed authorisation)."""
    from _session_manager.viewer import ViewerRegistry

    session = _WritableFdSession()
    try:
        registry = ViewerRegistry(session)
        v = registry.attach()
        v.detach()
        v.feed(b"ignored")  # must not raise
        assert session.read_all() == b"", "detached feed wrote to the master"
        # A detached feed writes nothing, so it is not activity either — the idle
        # clock must not be bumped by a dropped-auth feed (#108).
        assert session.mark_active_calls == 0, (
            "detached feed must not register as activity"
        )
    finally:
        session.cleanup()


def test_feed_on_closed_master_swallows() -> None:
    """``feed`` on a torn-down master end swallows the ``OSError`` rather than
    raising into the caller (§2.12.2 'a closed PTY swallows the write')."""
    from _session_manager.viewer import ViewerRegistry

    session = _WritableFdSession()
    registry = ViewerRegistry(session)
    v = registry.attach()
    session.cleanup()  # close both ends — the master fd is now invalid
    v.feed(b"into the void")  # must not raise


def test_feed_with_no_master_is_noop() -> None:
    """``feed`` on a viewer whose session has no master fd is a defensive no-op
    (attach guards this in practice, but the viewer must not raise)."""
    from _session_manager.viewer import ViewerRegistry

    registry = ViewerRegistry(_StubSession())  # pty_master_fd is None
    v = registry.attach()
    v.feed(b"ignored")  # must not raise


def test_detach_after_registry_close_is_idempotent() -> None:
    """A viewer ``detach`` racing a registry ``close`` is idempotent at the
    registry level (the viewer was already removed when close cleared the set) —
    it must not raise (§2.12.3 detach safety)."""
    from _session_manager.viewer import ViewerRegistry

    registry = ViewerRegistry(_StubSession())
    v = registry.attach()
    registry.close()  # clears the viewer set + ends the stream
    v.detach()  # registry.detach hits the already-removed path — must not raise
    assert registry.count == 0
