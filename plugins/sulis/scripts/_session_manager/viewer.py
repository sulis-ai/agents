"""``_session_manager.viewer`` — the attach/viewer mechanism for a pty session.

Contract: ``SESSION_MANAGER_CONTRACT.extension.md`` §2.12.2 (the ``attach``
operation + the ``Viewer`` protocol ``stream``/``feed``/``detach``), §2.12.3
(detach-leaves-running invariant), §2.12.4 (keystroke bytes pass VERBATIM to the
PTY master; the trust boundary is *attach*, not byte content — ADR-003), §2.12.5
(``viewer_count`` is the single source of truth for visible/headless). TDD §1.3;
ADR-001, ADR-003.

This is **EXPAND-Create** on a seam we own (MEA-01 / WPB-01): the manager owns a
per-session viewer registry; attach/detach are orthogonal to the process
lifecycle (the lifecycle governs the *process*; viewers are observers of its
PTY). It is the **in-process port** the socket layer (WP-005) later exposes over
the wire — keeping it a separate module makes it unit-testable without a socket.

**The snapshot-then-live join (acceptance #1).** A newly-attached viewer first
renders the current scrollback snapshot (§2.11), then the live raw byte feed, so
it sees "what's on the terminal screen" rather than a blank pane. The two phases
join at attach: the registry records the live feed *before* taking the snapshot,
so no byte produced between the snapshot read and the live subscription is lost
(see :meth:`ViewerRegistry.attach`).

**Live delivery without a socket.** Each viewer owns a bounded queue the
session's master-reader pump fans live bytes into via the
:attr:`Session.on_pty_output` broadcast seam (mirroring the ``on_event`` guard
seam). The viewer's ``stream`` drains its own queue — it does NOT re-poll the
lossy scrollback ring (a re-poll would drop bytes the ring trimmed and double-
count bytes still in it). One registry per session multiplexes the pump's single
broadcast to every attached viewer.

**Dependency direction (WPB-01, inward-only).** This module imports only stdlib;
it is handed the ``Session`` it attaches to, never the manager. The manager wires
the registry to the session and calls ``attach``.
"""

from __future__ import annotations

import os
import queue
import threading
from collections.abc import Iterator
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:  # pragma: no cover - typing only
    from _session_manager.session import Session

# Per-viewer live-byte queue depth (§2.12.4 backpressure ceiling, SHOULD). A
# bounded queue means a pathological/slow viewer cannot grow memory without
# limit; when full, the OLDEST live chunk is dropped (ring discipline, mirroring
# the scrollback ring) so live output keeps flowing for healthy viewers rather
# than wedging the shared pump broadcast. Generous: a terminal screen's worth of
# 64 KiB master reads is a few chunks; 1024 buffers deep scroll bursts.
_LIVE_QUEUE_MAXSIZE = 1024

# Sentinel placed on a viewer's live queue to end its ``stream`` cleanly when the
# viewer detaches or the session closes — a distinct object so it can never
# collide with a real ``bytes`` chunk.
_END = object()

# Default per-feed throughput ceiling (§2.12.4, SHOULD): the largest single
# ``feed`` write passed to the PTY master in one ``os.write`` slice. A
# pathological client sending a multi-megabyte paste cannot wedge the PTY writer
# in one unbounded syscall; oversize input is written in bounded slices. 64 KiB
# matches the master-reader pump's read size (a symmetric, boring ceiling).
_FEED_CHUNK_BYTES = 65536


@runtime_checkable
class Viewer(Protocol):
    """An ephemeral attachment to a pty-mode session (§2.12.2).

    ``@runtime_checkable`` so the concrete viewer can be asserted to conform
    structurally — the same Protocol the socket layer (WP-005) consumes.
    """

    def stream(self) -> Iterator[bytes]:
        """Yield the scrollback snapshot first (oldest→newest), then live PTY
        output bytes as they arrive, until this viewer detaches or the session
        closes (§2.12.2; acceptance #1)."""
        ...

    def feed(self, keystrokes: bytes) -> None:
        """Write keystroke bytes VERBATIM to the live PTY's master end (§2.12.4;
        ADR-003). No-op-safe after detach/close."""
        ...

    def detach(self) -> None:
        """Detach this viewer. Idempotent. LEAVES THE SESSION RUNNING (§2.12.3)."""
        ...


class _Viewer:
    """The concrete viewer the manager hands out (§2.12.2).

    Holds a reference to the session it observes, the registry that owns it (for
    detach bookkeeping + viewer-count), the snapshot taken at attach, and its own
    bounded live-byte queue the session's pump fans bytes into. ``feed``
    authorisation is a simple boolean the registry flips on attach and detach
    drops (§2.13.2 decoupling) — once detached, ``feed`` is a no-op (the trust
    boundary is attach, §2.12.4).
    """

    def __init__(
        self, registry: "ViewerRegistry", session: "Session", snapshot: bytes
    ) -> None:
        self._registry = registry
        self._session = session
        self._snapshot = snapshot
        #: Live raw bytes delivered by the pump's broadcast (post-snapshot).
        self._live: "queue.Queue[object]" = queue.Queue(maxsize=_LIVE_QUEUE_MAXSIZE)
        #: Feed authorisation (§2.13.2): True while attached, dropped on detach.
        self._attached = True
        self._lock = threading.Lock()

    # ── the pump broadcast sink (called by ViewerRegistry.broadcast) ────────

    def _deliver(self, data: bytes) -> None:
        """Enqueue one live chunk from the pump broadcast (oldest dropped if the
        bounded queue is full — backpressure, §2.12.4)."""
        try:
            self._live.put_nowait(data)
        except queue.Full:
            # Drop the oldest buffered chunk to make room (ring discipline) so a
            # slow viewer never wedges the shared pump broadcast for healthy ones.
            try:
                self._live.get_nowait()
            except queue.Empty:  # pragma: no cover - Full implies non-empty
                pass
            try:
                self._live.put_nowait(data)
            except queue.Full:  # pragma: no cover - racing producers, best-effort
                pass

    def _close(self) -> None:
        """End this viewer's ``stream`` by enqueuing the end sentinel — called by
        the registry on detach or session close.

        A blocking ``put`` (not ``put_nowait``) so a full queue does NOT cost a
        buffered live chunk: the consumer's ``stream`` is draining concurrently,
        so the sentinel lands as soon as one slot frees — lossless. A bounded
        timeout guards the pathological case where the consumer abandoned the
        iterator without detaching (so nothing drains): there, fall back to
        evicting one chunk to guarantee the sentinel lands and no ``stream`` is
        stranded (teardown correctness wins over one trailing byte)."""
        try:
            self._live.put(_END, timeout=1.0)
        except queue.Full:  # pragma: no cover - abandoned-iterator teardown safety
            # The consumer is not draining (abandoned iterator). Make room for
            # the sentinel so a ``stream`` still parked on ``get`` is released.
            # Reaching this needs a full queue with no drainer for the full
            # timeout — a teardown safety net, not a behavioural path.
            try:
                self._live.get_nowait()
            except queue.Empty:
                pass
            try:
                self._live.put_nowait(_END)
            except queue.Full:
                pass

    # ── the Viewer protocol surface (§2.12.2) ───────────────────────────────

    def stream(self) -> Iterator[bytes]:
        """Yield the scrollback snapshot first, then live bytes until detach/close
        (§2.12.2; acceptance #1).

        The snapshot is emitted as one chunk (it is the bytes retained at attach,
        oldest→newest); then the viewer drains its own live queue — each chunk a
        raw master read the pump broadcast since attach — until the end sentinel
        (placed by detach or session close) ends the iterator cleanly.
        """
        if self._snapshot:
            yield self._snapshot
        while True:
            item = self._live.get()
            if item is _END:
                return
            yield item  # type: ignore[misc]  # never _END here

    def feed(self, keystrokes: bytes) -> None:
        """Write ``keystrokes`` VERBATIM to the PTY master (§2.12.4; ADR-003).

        No sanitising, no interpretation — the child's own shell is the
        interpreter, and byte-filtering a terminal is both futile (escape
        sequences are legitimate input) and wrong (it corrupts paste/IME). The
        trust boundary is *attach* authorisation, not byte content. A SHOULD
        throughput bound writes oversize input in bounded slices so a
        pathological paste cannot wedge the writer in one unbounded syscall.

        No-op-safe after detach/close (§2.12.2): a detached viewer's feed auth is
        dropped, and a closed master end (the session ended) swallows the write
        rather than raising into the caller — best-effort, mirroring the
        contract's 'closed PTY swallows the write' note.
        """
        with self._lock:
            if not self._attached:
                return  # detached: feed authorisation dropped (§2.13.2)
        master_fd = self._session.pty_master_fd
        if master_fd is None:
            return  # no terminal (defensive; attach guards this)
        view = memoryview(keystrokes)
        try:
            for start in range(0, len(view), _FEED_CHUNK_BYTES):
                os.write(master_fd, view[start : start + _FEED_CHUNK_BYTES])
        except OSError:
            # The master end is closed/torn down (the session ended) — a closed
            # PTY swallows the write rather than raising into the caller (§2.12.2).
            return
        # A keystroke fed into the session is genuine in-use activity (#108): bump
        # the idle clock so a session being actively typed into is not reaped by
        # the maintenance tick just because it produced no OUTPUT in the window.
        self._session.mark_active()

    def detach(self) -> None:
        """Detach this viewer; idempotent; LEAVES THE SESSION RUNNING (§2.12.3).

        Drops this viewer's feed authorisation (§2.13.2), removes it from the
        registry (so ``viewer_count`` drops), and ends its ``stream`` via the end
        sentinel. The process, its PTY, its scrollback, and the reused lifecycle
        are all untouched — a session with zero viewers is headless but alive. A
        second detach is a no-op (the first already dropped the registration).
        """
        with self._lock:
            if not self._attached:
                return
            self._attached = False
        self._registry.detach(self)
        self._close()


class ViewerRegistry:
    """The per-session registry of attached viewers (§2.12.2 / §2.12.5).

    One registry per pty session, owned by the manager and wired to the session
    at spawn: it is the single subscriber of the session's
    :attr:`Session.on_pty_output` broadcast and multiplexes each live master read
    to every attached viewer. :attr:`count` is the contract's single source of
    truth for visible/headless (``count > 0`` ⇔ visible, §2.12.5) — there is no
    second flag.

    Thread-safe: ``attach``/``detach`` mutate the viewer set under a lock, and
    ``broadcast`` (called from the master-reader pump thread) snapshots the set
    under the same lock before fanning out — so a concurrent attach/detach never
    corrupts the iteration.
    """

    def __init__(self, session: "Session") -> None:
        self._session = session
        self._viewers: list[_Viewer] = []
        self._lock = threading.Lock()

    @property
    def count(self) -> int:
        """The number of attached viewers — ``viewer_count`` (§2.12.5). The
        single source of truth for visible (``> 0``) vs headless (``0``)."""
        with self._lock:
            return len(self._viewers)

    def attach(self) -> _Viewer:
        """Attach a new viewer and return it (§2.12.2).

        **The snapshot-then-live join is race-free here.** The viewer is
        registered (so the pump's broadcast starts delivering to its live queue)
        *before* the scrollback snapshot is read, then any bytes the pump appended
        to the ring in that window are still delivered live — so the join never
        drops a byte produced between snapshot and subscription. A small live
        overlap with the tail of the snapshot is harmless (a terminal emulator is
        idempotent over repeated identical trailing bytes far more readily than it
        tolerates a gap), whereas a gap would corrupt the rendered screen. Attach
        is additive and never restarts the process (§2.12.2).
        """
        scrollback = self._session.scrollback
        with self._lock:
            # Register FIRST so live bytes from this instant are queued, THEN
            # snapshot — closing the join window in the safe direction (overlap,
            # never gap).
            snapshot = scrollback.snapshot() if scrollback is not None else b""
            viewer = _Viewer(self, self._session, snapshot)
            self._viewers.append(viewer)
        return viewer

    def detach(self, viewer: _Viewer) -> None:
        """Remove ``viewer`` from the registry (called by ``_Viewer.detach``).

        Idempotent at the registry level: removing a viewer already gone is a
        no-op, so a double detach (or a detach racing a session close) is safe.
        """
        with self._lock:
            try:
                self._viewers.remove(viewer)
            except ValueError:
                pass  # already removed — idempotent

    def broadcast(self, data: bytes) -> None:
        """Fan one live master read out to every attached viewer (§2.12.2).

        Called from the session's master-reader pump via the
        :attr:`Session.on_pty_output` seam. The viewer set is snapshotted under
        the lock before delivery so a concurrent attach/detach cannot corrupt the
        iteration; delivery itself is each viewer's bounded, best-effort enqueue.
        """
        with self._lock:
            viewers = list(self._viewers)
        for viewer in viewers:
            viewer._deliver(data)

    def close(self) -> None:
        """End every attached viewer's ``stream`` (called when the session
        closes). Each viewer gets the end sentinel; the set is cleared so a later
        broadcast is a no-op. Idempotent."""
        with self._lock:
            viewers = list(self._viewers)
            self._viewers.clear()
        for viewer in viewers:
            viewer._close()
