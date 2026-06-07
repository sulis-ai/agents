"""Append-only, offset-addressed per-session event log (the Form spine).

Contract: ``SESSION_MANAGER_CONTRACT.md`` §2.5 (log/cursor semantics) and §2.1
(a session is an ordered, offset-addressed, append-only event log). This single
:meth:`EventLog.read` mechanism serves all four content use cases — live-tail,
reconnect catch-up, multi-viewer, and full history — so they are one mechanism
rather than four special cases (§2.2 decoupling invariant).

Concurrency model (§2.6): appends and ``read(follow=True)`` run on **different
threads** (the stdout pump appends; readers follow). The log is guarded by a
single lock and a condition variable; a follower blocks on the condition and is
woken on every append or on :meth:`close` — never busy-polling.

Retention (§2.5): the log retains the whole live session by default
(``max_events=None``; the decided-by-default per the change INDEX). A finite cap
evicts oldest events; a reader whose ``since`` predates the oldest retained
offset receives :class:`OffsetEvictedError` so it can restart from a valid
offset rather than silently skipping.

Dependency direction (MEA-01): this module imports only the provider-neutral
:class:`~_session_manager.events.Event` — never any provider/process code. The
dependency points inward.
"""

from __future__ import annotations

import dataclasses
import itertools
import threading
from collections import deque
from typing import Iterator

from _session_manager.events import Event


class OffsetOutOfRangeError(Exception):
    """Expected error (§2.9): ``read(since, follow=False)`` was asked for an
    offset at or beyond ``next_offset`` — there is nothing present there and
    the caller did not ask to wait (``follow=False``). Under ``follow=True`` a
    future offset is waited for instead of raising."""


class OffsetEvictedError(Exception):
    """Expected error (§2.9, ``OFFSET_EVICTED``): ``read(since, …)`` was asked
    for an offset older than the oldest retained event (retention cap evicted
    it). The caller should restart from the oldest available offset rather than
    silently skip."""


class EventLog:
    """A thread-safe, append-only, offset-addressed event log for one session.

    Offsets are monotonic integers starting at 0, unique and stable for the
    life of the session (Kafka-offset / ``tail -f --since`` convention, CP-01).

    Args:
        max_events: retention cap (number of events). ``None`` (default) retains
            the whole live session — the decided default per the change INDEX;
            eviction never fires. A positive integer caps retention: appending
            past the cap evicts the oldest event and advances the oldest
            retained offset.
    """

    def __init__(self, max_events: int | None = None) -> None:
        if max_events is not None and max_events <= 0:
            raise ValueError("max_events must be a positive integer or None")
        self._max_events = max_events
        # Guards every field below + backs the follower wake-up condition.
        self._cond = threading.Condition()
        # Retained events in offset order. With a finite cap this is bounded;
        # otherwise it grows with the session.
        self._events: deque[Event] = deque()
        # The offset the NEXT appended event will receive (§2.2 forward ref).
        self._next_offset = 0
        # The oldest offset still retained (advances as eviction occurs). Equals
        # _next_offset when the log is empty.
        self._oldest_offset = 0
        self._closed = False

    # ── append side (the producer thread) ──────────────────────────────────

    def append(self, event: Event) -> int:
        """Append ``event``; assign it the next monotonic offset; return that
        offset. Wakes every blocked follower (§2.6).

        The assigned offset overwrites any placeholder ``event.offset`` (the
        event is frozen, so a new instance is stored via
        :func:`dataclasses.replace`)."""
        with self._cond:
            if self._closed:
                raise RuntimeError("cannot append to a closed EventLog")
            offset = self._next_offset
            self._events.append(dataclasses.replace(event, offset=offset))
            self._next_offset += 1
            self._evict_if_needed()
            self._cond.notify_all()
            return offset

    def _evict_if_needed(self) -> None:
        """Drop oldest events past the retention cap, advancing the oldest
        retained offset. Caller holds the condition lock."""
        if self._max_events is None:
            return
        while len(self._events) > self._max_events:
            self._events.popleft()
            self._oldest_offset += 1

    # ── read side (any number of consumer threads) ─────────────────────────

    def read(self, since: int = 0, follow: bool = False) -> Iterator[Event]:
        """Yield events with ``offset >= since``, in order (contract §2.5).

        ``follow=False`` (history): yield what is present now from ``since``,
        then stop. ``since`` at/after ``next_offset`` with nothing present
        raises :class:`OffsetOutOfRangeError`.

        ``follow=True`` (live tail): yield existing events from ``since``, then
        block-yield new appends as they arrive, until the log is
        :meth:`close`-d. A ``since`` at/beyond ``next_offset`` is a forward
        reference — the follower waits for it to materialise (§2.2/§2.5).

        Either mode: a ``since`` older than the oldest retained offset raises
        :class:`OffsetEvictedError` (``OFFSET_EVICTED``).

        The returned iterator holds no lock while the caller consumes it; it
        re-acquires the lock only to read newly-available events or to wait.
        """
        if since < 0:
            raise ValueError("since must be >= 0")
        if follow:
            return self._read_follow(since)
        return self._read_history(since)

    def _check_not_evicted(self, since: int) -> None:
        """Raise OffsetEvictedError if ``since`` predates retained data. Caller
        holds the condition lock."""
        # Nothing is evicted until eviction has actually advanced the oldest
        # offset; only then can a `since` fall below it.
        if since < self._oldest_offset:
            raise OffsetEvictedError(
                f"since={since} predates oldest retained offset "
                f"{self._oldest_offset}"
            )

    def _slice_from(self, offset: int) -> list[Event]:
        """Return retained events with ``offset >= offset``, in order.

        Offsets are contiguous within the retained window, so the start index
        into the deque is ``offset - oldest_offset`` directly — an O(k) slice
        (k = events returned) rather than an O(n) scan of the whole log on
        every call. This matters for a long-lived ``follow`` reader, which
        would otherwise re-scan the entire retained log on every append
        (O(n) per chunk → O(n²) over a turn).

        Precondition (caller's responsibility): ``offset >= oldest_offset`` —
        every caller runs :meth:`_check_not_evicted` first, so ``start`` is
        always non-negative here. Caller holds the condition lock.
        """
        start = offset - self._oldest_offset
        return list(itertools.islice(self._events, start, None))

    def _read_history(self, since: int) -> Iterator[Event]:
        """Snapshot the present events from ``since`` and yield them, then stop."""
        with self._cond:
            self._check_not_evicted(since)
            if since >= self._next_offset:
                raise OffsetOutOfRangeError(
                    f"since={since} is at/beyond next_offset="
                    f"{self._next_offset} (nothing present; follow=False)"
                )
            snapshot = self._slice_from(since)
        yield from snapshot

    def _read_follow(self, since: int) -> Iterator[Event]:
        """Yield from ``since`` then block-yield live appends until close.

        Validation (eviction) happens eagerly so a bad ``since`` raises on first
        iteration rather than being deferred. A future ``since`` is waited for,
        not rejected.
        """
        with self._cond:
            self._check_not_evicted(since)
        cursor = since
        while True:
            with self._cond:
                # Eviction may have advanced past the cursor since we last held
                # the lock — surface it rather than skip silently.
                self._check_not_evicted(cursor)
                # Wait until there is an event at or after the cursor, or close.
                while cursor >= self._next_offset and not self._closed:
                    self._cond.wait()
                if cursor >= self._next_offset and self._closed:
                    return
                # Collect everything available from the cursor under the lock.
                ready = self._slice_from(cursor)
                if ready:
                    cursor = ready[-1].offset + 1
            yield from ready

    # ── cursor / lifecycle queries ─────────────────────────────────────────

    def next_offset(self) -> int:
        """The offset the NEXT appended event will receive — the forward
        bookmark ``send()`` returns (§2.2)."""
        with self._cond:
            return self._next_offset

    def close(self) -> None:
        """Release any ``follow()`` waiters cleanly (their iterators end).

        Idempotent: closing an already-closed log is a no-op."""
        with self._cond:
            self._closed = True
            self._cond.notify_all()
