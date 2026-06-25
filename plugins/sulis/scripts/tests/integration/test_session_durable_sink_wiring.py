"""Integration — the manager wires the durable sink onto the live session
(CH-GJ9KQR WP-007, ADR-004 + WP-004 ADV-1, seam-close).

This pins the LIVE wiring the integration WP closes (the merged WP-004 sink is
built but not yet registered on a live session):

  1. **Second sink on ``on_event``.** :meth:`SessionManager.open` registers a
     :class:`DurableAppendSink` as a SECOND observer on the session's
     ``on_event`` seam, ADDITIVELY — the existing guard/recovery fan-out still
     fires byte-for-byte (ADR-004: the live-tail path is unchanged). A
     content-bearing ``Event`` reaching the seam lands in the durable store.

  2. **checkpoint() OFF the live event hot path (WP-004 ADV-1).** The manager
     exposes :meth:`checkpoint` as the Working-Set-crystallisation-boundary
     hook. It is NOT called inside the ``on_event`` fan-out — a checkpoint error
     must never stall the live pump. Firing ``on_event`` never regenerates the
     memory; only an explicit :meth:`checkpoint` call does.

  3. **Resume reseed (WP-004 ADV-2).** On restart (``_respawn``) the sink's
     ``_next_order`` is reseeded from the store high-water mark so post-restart
     appends continue the order rather than degrading OUT_OF_ORDER_WRITE.

  4. **Injectable store factory.** The store binding is an injectable tuning
     kwarg (the ``recovery_driver_factory`` / ``timer_factory`` precedent), so
     the test drives the REAL sink against an in-memory contract store (a valid
     ``ThreadStore``, MEA-09 — no mock) without touching the founder's
     filesystem.
"""

from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

import pytest

from _session_manager import thread_contract as tc
from _session_manager.adapter import SessionSpec
from _session_manager.events import Event
from _session_manager.manager import SessionManager
from _session_manager.thread_contract import InMemoryThreadStore

_KEY = "CH-GJ9KQR"


class _AliveChildAdapter:
    """A minimal real ``ProviderAdapter`` whose child just blocks on stdin so
    the spawned process stays alive (``is_alive`` True) for the wiring assertions
    — no provider output needed; the test fires ``on_event`` directly."""

    class _Caps:
        supports_resume = True

    def __init__(self) -> None:
        self.capabilities = _AliveChildAdapter._Caps()

    def spawn_argv(self, spec: SessionSpec) -> list[str]:
        return [sys.executable, "-c", "import sys; sys.stdin.read()"]

    def encode(self, command: str) -> bytes:
        return command.encode() + b"\n"

    def decode(self, line: bytes) -> Event | None:
        return None

    def turn_complete(self, event: Event) -> bool:
        return False


def _chunk(text: str, turn: int = 0) -> Event:
    return Event(offset=-1, key=_KEY, turn=turn, kind="chunk", text=text)


def _manager(store: InMemoryThreadStore) -> SessionManager:
    """A manager whose only provider keeps its child alive and whose durable
    store binding is the injected in-memory contract store (a valid
    ``ThreadStore`` — MEA-09). Maintenance off so the background loop never
    races the assertions."""
    return SessionManager(
        {"claude": _AliveChildAdapter()},
        start_maintenance=False,
        thread_store_factory=lambda change_id: store,
    )


def _spec(tmp_path: Path) -> SessionSpec:
    return SessionSpec(provider="claude", cwd=str(tmp_path), brief_change_id=_KEY)


def test_open_registers_durable_sink_on_on_event(tmp_path: Path) -> None:
    """A content-bearing event reaching the live session's ``on_event`` seam is
    appended to the durable store — the manager registered the second sink."""
    store = InMemoryThreadStore()
    mgr = _manager(store)
    try:
        session = mgr.open(_KEY, _spec(tmp_path))
        # Fire the seam exactly as the live pump does.
        assert session.on_event is not None
        session.on_event(session, _chunk("a durable line", turn=0))

        msgs = store.get_messages(_KEY)
        assert [m.content for m in msgs] == ["a durable line"]
    finally:
        mgr.shutdown()


def test_durable_sink_is_additive_existing_fanout_still_fires(
    tmp_path: Path,
) -> None:
    """The durable sink chains ADDITIVELY: an observer registered before the
    durable sink still receives the event (the guard/recovery fan-out is
    byte-for-byte unaffected, ADR-004)."""
    store = InMemoryThreadStore()
    mgr = _manager(store)
    try:
        session = mgr.open(_KEY, _spec(tmp_path))
        seen: list[str] = []
        prior = session.on_event

        def _spy(s, event: Event) -> None:
            if event.kind == "chunk":
                seen.append(event.text or "")
            if prior is not None:
                prior(s, event)

        session.on_event = _spy
        session.on_event(session, _chunk("both sinks", turn=0))

        # The spy saw it AND the durable store got it.
        assert seen == ["both sinks"]
        assert [m.content for m in store.get_messages(_KEY)] == ["both sinks"]
    finally:
        mgr.shutdown()


def test_checkpoint_is_off_the_hot_path(tmp_path: Path) -> None:
    """Firing ``on_event`` never regenerates ThreadMemory (checkpoint is OFF the
    hot path, WP-004 ADV-1); only an explicit ``manager.checkpoint(key)`` does."""
    store = InMemoryThreadStore()
    mgr = _manager(store)
    try:
        session = mgr.open(_KEY, _spec(tmp_path))
        session.on_event(session, _chunk("hot path event", turn=0))

        # No memory checkpoint yet — the hot path did not regenerate it.
        with pytest.raises(tc.ExpectedError) as ei:
            store.get_memory(_KEY)
        assert ei.value.code == tc.MEMORY_NOT_FOUND

        # The crystallisation-boundary hook regenerates it explicitly.
        memory = mgr.checkpoint(_KEY)
        assert memory.version >= 1
        assert store.get_memory(_KEY).version == memory.version
    finally:
        mgr.shutdown()


def test_checkpoint_error_does_not_propagate(tmp_path: Path) -> None:
    """A checkpoint of an unknown key surfaces honestly but the manager's
    ``checkpoint`` for a live key is a normal call — the off-hot-path placement
    means a checkpoint failure can never stall a live turn (it is not in the
    fan-out). Here: checkpoint a key with no open session is a no-op (returns
    None) rather than raising into a caller's path."""
    store = InMemoryThreadStore()
    mgr = _manager(store)
    try:
        # No session open for this key → no sink → checkpoint is a no-op.
        assert mgr.checkpoint("CH-UNKNOWN") is None
    finally:
        mgr.shutdown()


def test_respawn_reseeds_next_order_so_appends_continue(tmp_path: Path) -> None:
    """After a restart the manager reseeds the sink's ``_next_order`` from the
    store high-water mark (WP-004 ADV-2), so post-restart appends continue the
    order — not silently rejected OUT_OF_ORDER_WRITE."""
    store = InMemoryThreadStore()
    mgr = _manager(store)
    try:
        session = mgr.open(_KEY, _spec(tmp_path))
        session.on_event(session, _chunk("pre 0", turn=0))
        session.on_event(session, _chunk("pre 1", turn=1))
        assert [m.order for m in store.get_messages(_KEY)] == [0, 1]

        # Simulate a restart: the manager re-spawns the same session/key.
        mgr._respawn(session)  # noqa: SLF001 — drive the restart seam directly

        # Post-restart appends continue at the right order (reseed happened).
        session.on_event(session, _chunk("post 2", turn=2))
        msgs = store.get_messages(_KEY)
        assert [m.order for m in msgs] == [0, 1, 2]
        assert [m.content for m in msgs] == ["pre 0", "pre 1", "post 2"]
    finally:
        mgr.shutdown()


# ── REGRESSION (CH-GJ9KQR hotfix) — the durable side-channel must NEVER stall
# or break the live open/attach/feed round-trip, whether the durable store
# RAISES, HANGS, or hits a restricted filesystem (full WP-004 ADV-1 isolation,
# extended from exceptions-only to also cover hangs/blocking).
#
# The regression: ``SessionManager.open`` ran ``_attach_durable_sink`` (which
# does real store I/O — get/put the thread record, reseed from the log) and the
# ``_respawn`` reseed synchronously on the open/restart path, under the registry
# lock, BEFORE ``start_pumps`` and before the open result is returned — with NO
# isolation. On a runner where ``~/.sulis`` is restricted, slow, or contended
# (the cockpit-e2e environment, where the daemon writes the REAL ~/.sulis, not
# the test's isolated temp dir), the durable attach RAISED (daemon errored, never
# replied) or BLOCKED (open never returned) → the WS `open` round-trip timed out.
#
# The contract these pin: a live session opens, its event seam fires, and the
# live-tail path is byte-for-byte unaffected, regardless of the durable store's
# fate. The durable capability degrades (no second sink for that session); the
# live session never does.


class _RaisingStore:
    """A valid ``ThreadStore`` shape whose every op raises an UNEXPECTED
    (non-``ExpectedError``) error — the restricted-/broken-filesystem analogue
    (e.g. ``PermissionError`` / ``OSError`` from a ``mkdir`` into a read-only
    ``~/.sulis``). The attach-time wiring must isolate this so ``open`` still
    returns a live session."""

    def get_thread(self, thread_id: str):  # noqa: ANN201
        raise OSError("read-only filesystem: cannot stat ~/.sulis/changes/.../threads")

    def put_thread(self, thread) -> None:  # noqa: ANN001
        raise OSError("read-only filesystem: cannot mkdir ~/.sulis/changes/.../threads")

    def get_messages(self, thread_id: str, since=None, limit=None):  # noqa: ANN001,ANN201
        raise OSError("read-only filesystem")

    def append_message(self, thread_id: str, message) -> None:  # noqa: ANN001
        raise OSError("read-only filesystem")

    def get_memory(self, thread_id: str):  # noqa: ANN201
        raise OSError("read-only filesystem")

    def put_memory(self, thread_id: str, memory) -> None:  # noqa: ANN001
        raise OSError("read-only filesystem")


class _HangingStore:
    """A valid ``ThreadStore`` shape whose reads/writes BLOCK (the slow/contended
    or stuck-FS analogue). Each op waits on an event that the test never sets, so
    a synchronous, unbounded call would hang forever. The attach-time wiring must
    bound this so ``open`` still returns within a small budget."""

    def __init__(self) -> None:
        self._never = threading.Event()
        #: True once at least one op started blocking — proves the hang path ran.
        self.blocked = False

    def _block(self):  # noqa: ANN202
        self.blocked = True
        # Wait on an event that is never set → blocks until the (daemon) worker
        # thread is abandoned. A generous cap keeps a wedged test from hanging CI
        # forever, but it is far longer than the attach budget so the bound — not
        # this cap — is what releases ``open``.
        self._never.wait(timeout=30.0)
        raise OSError("filesystem call never completed (test hang)")

    def get_thread(self, thread_id: str):  # noqa: ANN201
        return self._block()

    def put_thread(self, thread) -> None:  # noqa: ANN001
        self._block()

    def get_messages(self, thread_id: str, since=None, limit=None):  # noqa: ANN001,ANN201
        return self._block()

    def append_message(self, thread_id: str, message) -> None:  # noqa: ANN001
        self._block()

    def get_memory(self, thread_id: str):  # noqa: ANN201
        return self._block()

    def put_memory(self, thread_id: str, memory) -> None:  # noqa: ANN001
        self._block()


def _manager_with_store_factory(factory) -> SessionManager:  # noqa: ANN001
    """A manager bound to an arbitrary durable-store ``factory`` (the failing /
    hanging fakes below), maintenance off. A short attach timeout so the
    hang-isolation test asserts quickly without waiting on the production
    default."""
    return SessionManager(
        {"claude": _AliveChildAdapter()},
        start_maintenance=False,
        thread_store_factory=factory,
        durable_attach_timeout=1.0,
    )


def test_open_completes_when_durable_store_attach_raises(tmp_path: Path) -> None:
    """When the durable store RAISES at attach time (restricted/broken FS), the
    live session still opens — the durable wiring is isolated; the live-tail path
    is unaffected. The session is alive and its event seam fires."""
    mgr = _manager_with_store_factory(lambda change_id: _RaisingStore())
    try:
        session = mgr.open(_KEY, _spec(tmp_path))
        # The open returned a live session despite the store raising.
        assert mgr.is_alive(session)
        assert session.on_event is not None

        # The live event seam still works (firing it does not raise — the durable
        # observer either was never attached, or is itself isolated).
        seen: list[str] = []
        prior = session.on_event

        def _spy(s, event: Event) -> None:
            if event.kind == "chunk":
                seen.append(event.text or "")
            if prior is not None:
                prior(s, event)

        session.on_event = _spy
        session.on_event(session, _chunk("live line", turn=0))
        assert seen == ["live line"]
    finally:
        mgr.shutdown()


def test_open_completes_when_durable_store_attach_hangs(tmp_path: Path) -> None:
    """When the durable store HANGS at attach time (slow/contended/stuck FS), the
    live open still returns WITHIN A BOUND — it does not block on the durable
    side-channel. This is the byte-for-byte regression: the cockpit-e2e `open`
    round-trip timed out because the attach blocked the open path."""
    store = _HangingStore()
    mgr = _manager_with_store_factory(lambda change_id: store)
    try:
        started = time.monotonic()
        session = mgr.open(_KEY, _spec(tmp_path))
        elapsed = time.monotonic() - started

        # Open returned a LIVE session well inside the round-trip budget — it was
        # not blocked on the hanging store (attach timeout is 1.0s; allow margin).
        assert mgr.is_alive(session)
        assert elapsed < 5.0, (
            f"open blocked on the hanging durable store ({elapsed:.1f}s)"
        )

        # The live seam still fires (the hang did not break the live pump).
        session.on_event(session, _chunk("after a hang", turn=0))
    finally:
        mgr.shutdown()


def test_live_event_seam_unaffected_when_durable_sink_degraded(
    tmp_path: Path,
) -> None:
    """When the durable attach degrades (store raises), a content event reaching
    the live seam is delivered to the existing fan-out byte-for-byte — the
    live-tail path never depends on the durable second sink succeeding."""
    mgr = _manager_with_store_factory(lambda change_id: _RaisingStore())
    try:
        session = mgr.open(_KEY, _spec(tmp_path))
        delivered: list[str] = []
        prior = session.on_event

        def _spy(s, event: Event) -> None:
            if event.kind == "chunk":
                delivered.append(event.text or "")
            if prior is not None:
                prior(s, event)

        session.on_event = _spy
        # Fire several events as the live pump would — none raise into the pump,
        # and every one reaches the live observer.
        session.on_event(session, _chunk("one", turn=0))
        session.on_event(session, _chunk("two", turn=1))
        assert delivered == ["one", "two"]
    finally:
        mgr.shutdown()


def test_respawn_reseed_isolated_against_store_failure(tmp_path: Path) -> None:
    """A restart whose durable reseed RAISES (broken FS at restart time) must not
    break the respawn — the live session is replaced and stays alive; the durable
    reseed failure is isolated (WP-004 ADV-1, applied to the restart seam too)."""
    mgr = _manager_with_store_factory(lambda change_id: _RaisingStore())
    try:
        session = mgr.open(_KEY, _spec(tmp_path))
        assert mgr.is_alive(session)
        # Drive the restart seam directly — the reseed inside it must be isolated.
        mgr._respawn(session)  # noqa: SLF001
        assert mgr.is_alive(session)
        # The live seam still fires after the restart.
        session.on_event(session, _chunk("after restart", turn=0))
    finally:
        mgr.shutdown()
