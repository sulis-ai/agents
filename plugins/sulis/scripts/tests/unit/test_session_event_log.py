"""WP-001 — tests for the append-only, offset-addressed per-session event log.

Contract: SESSION_MANAGER_CONTRACT.md §2.5 (log/cursor semantics) and §2.1
(session = ordered, offset-addressed, append-only event log). This is the Form
spine of the persistent-chat-sessions capability — the single ``read()``
mechanism that serves live-tail, reconnect catch-up, multi-viewer, and history
(§2.2 decoupling invariant).

Verification posture (INDEX, MEA-09): real threaded in-process behaviour — no
mocks of the log's own state. ``read(follow=True)`` runs on a separate thread
from ``append`` (the contract's stdout-pump-vs-reader split, §2.6); these tests
exercise that for real with short, bounded timeouts so a hang fails loudly
instead of blocking CI.

``Event`` comes from WP-002 (parallel peer); until it merges these tests use
the package's locally-defined ``Event`` against the locked §2.3 shape.
"""

from __future__ import annotations

import threading
import time

import pytest

from _session_manager.event_log import (
    EventLog,
    OffsetEvictedError,
    OffsetOutOfRangeError,
)
from _session_manager.events import Event

# Bounded wait used by every threaded assertion: long enough to never flake on
# a loaded CI runner, short enough that a genuine hang fails the test quickly.
_WAIT = 2.0


def _chunk(key: str = "k", turn: int = 0, text: str = "x") -> Event:
    """A minimal valid ``chunk`` event. ``offset`` is assigned by the log on
    append, so the caller leaves it at its placeholder default."""
    return Event(offset=-1, key=key, turn=turn, kind="chunk", text=text)


# ─── append + offset assignment ────────────────────────────────────────────


def test_append_returns_monotonic_offsets():
    """Offsets start at 0 and increase by 1, unique and stable."""
    log = EventLog()
    offsets = [log.append(_chunk(text=str(i))) for i in range(5)]
    assert offsets == [0, 1, 2, 3, 4]
    # Offsets are stable: replaying history reports the same offsets.
    replayed = [ev.offset for ev in log.read(since=0, follow=False)]
    assert replayed == [0, 1, 2, 3, 4]
    # And the stored event carries the assigned offset (the placeholder is gone).
    assert all(ev.offset == i for i, ev in enumerate(log.read()))


def test_next_offset_is_forward_reference():
    """``next_offset()`` equals the offset the next ``append`` will return,
    and holds under concurrent appends (the send() bookmark, §2.2)."""
    log = EventLog()
    assert log.next_offset() == 0
    assert log.append(_chunk()) == 0
    assert log.next_offset() == 1

    # Concurrency: the forward reference is consistent under parallel appends —
    # every offset that comes back is unique and contiguous, and next_offset()
    # afterwards is exactly the count appended.
    n = 50
    seen: list[int] = []
    lock = threading.Lock()

    def worker() -> None:
        off = log.append(_chunk())
        with lock:
            seen.append(off)

    threads = [threading.Thread(target=worker) for _ in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(_WAIT)
    assert all(not t.is_alive() for t in threads)
    # 1 pre-existing append + n concurrent = contiguous 1..n, no dupes.
    assert sorted(seen) == list(range(1, n + 1))
    assert log.next_offset() == n + 1


# ─── read history (follow=False) ───────────────────────────────────────────


def test_read_history_then_stops():
    """``read(since=0, follow=False)`` yields all present events then stops
    (the iterator is exhausted — history, not a live tail)."""
    log = EventLog()
    for i in range(3):
        log.append(_chunk(text=str(i)))
    it = log.read(since=0, follow=False)
    got = list(it)
    assert [ev.text for ev in got] == ["0", "1", "2"]
    # Exhausted: next() raises StopIteration (the generator is done).
    with pytest.raises(StopIteration):
        next(it)


def test_read_since_offset_history():
    """``read(since=N)`` skips events with offset < N."""
    log = EventLog()
    for i in range(5):
        log.append(_chunk(text=str(i)))
    got = list(log.read(since=2, follow=False))
    assert [ev.offset for ev in got] == [2, 3, 4]


def test_read_history_past_max_is_expected_error():
    """``read(since=max+1, follow=False)`` is an Expected error: there is
    nothing at or after that offset and the caller did not ask to wait."""
    log = EventLog()
    log.append(_chunk())  # offset 0; next_offset == 1
    with pytest.raises(OffsetOutOfRangeError):
        list(log.read(since=1, follow=False))


# ─── read live tail (follow=True) ──────────────────────────────────────────


def test_read_follow_yields_live_appends():
    """A follower started before any append receives appends as they arrive,
    in order (§2.5 live tail). append() happens on a different thread."""
    log = EventLog()
    received: list[str] = []
    ready = threading.Event()
    done = threading.Event()

    def follower() -> None:
        ready.set()
        for ev in log.read(since=0, follow=True):
            received.append(ev.text)
            if len(received) == 3:
                break
        done.set()

    t = threading.Thread(target=follower)
    t.start()
    assert ready.wait(_WAIT)
    for i in range(3):
        log.append(_chunk(text=str(i)))
    assert done.wait(_WAIT), "follower did not receive 3 live appends"
    t.join(_WAIT)
    assert received == ["0", "1", "2"]


def test_read_follow_from_future_offset_waits():
    """``read(since=max+1, follow=True)`` blocks (does not error) and yields
    the event once that offset materialises — the forward-ref bookmark a
    queued send() hands back (§2.2/§2.5)."""
    log = EventLog()
    log.append(_chunk(text="present"))  # offset 0
    future = log.next_offset()  # offset 1 — not yet appended
    received: list[str] = []
    got_one = threading.Event()

    def follower() -> None:
        for ev in log.read(since=future, follow=True):
            received.append(ev.text)
            got_one.set()
            break

    t = threading.Thread(target=follower)
    t.start()
    # Give the follower a moment to start and block on the not-yet-present
    # offset; it must NOT have yielded the already-present offset-0 event.
    time.sleep(0.1)
    assert received == []
    log.append(_chunk(text="future"))  # offset 1 materialises
    assert got_one.wait(_WAIT), "follower never woke for the forward-ref offset"
    t.join(_WAIT)
    assert received == ["future"]


def test_two_followers_independent_cursors():
    """Two followers with different ``since`` both get the full tail from
    their own cursor, with no interference (§2.5 multi-viewer)."""
    log = EventLog()
    log.append(_chunk(text="0"))  # offset 0
    log.append(_chunk(text="1"))  # offset 1

    a_got: list[int] = []
    b_got: list[int] = []
    a_done = threading.Event()
    b_done = threading.Event()

    def follower(since: int, sink: list[int], done: threading.Event, want: int) -> None:
        for ev in log.read(since=since, follow=True):
            sink.append(ev.offset)
            if len(sink) == want:
                break
        done.set()

    # A reads from 0 (wants offsets 0,1,2,3 → 4 events).
    # B reads from 2 (wants offsets 2,3 → 2 events).
    ta = threading.Thread(target=follower, args=(0, a_got, a_done, 4))
    tb = threading.Thread(target=follower, args=(2, b_got, b_done, 2))
    ta.start()
    tb.start()
    time.sleep(0.1)
    log.append(_chunk(text="2"))  # offset 2
    log.append(_chunk(text="3"))  # offset 3
    assert a_done.wait(_WAIT)
    assert b_done.wait(_WAIT)
    ta.join(_WAIT)
    tb.join(_WAIT)
    assert a_got == [0, 1, 2, 3]
    assert b_got == [2, 3]


# ─── retention / eviction ──────────────────────────────────────────────────


def test_offset_evicted_when_since_predates_cap():
    """With a forced small cap, appends evict the oldest events; a reader whose
    ``since`` predates the oldest retained offset gets OFFSET_EVICTED (Expected)
    rather than silently skipping (§2.5 retention)."""
    log = EventLog(max_events=3)
    for i in range(5):
        log.append(_chunk(text=str(i)))  # offsets 0..4; only 2,3,4 retained
    # Offsets 0 and 1 were evicted; reading from 0 must raise, not skip to 2.
    with pytest.raises(OffsetEvictedError):
        list(log.read(since=0, follow=False))
    # Reading from the oldest retained offset still works and loses nothing.
    got = list(log.read(since=2, follow=False))
    assert [ev.offset for ev in got] == [2, 3, 4]


def test_default_retention_keeps_whole_session():
    """The decided default (INDEX): retain the whole live session — no eviction
    under the default cap. OFFSET_EVICTED exists but is not hit by default."""
    log = EventLog()  # default = unbounded
    for i in range(1000):
        log.append(_chunk(text=str(i)))
    got = list(log.read(since=0, follow=False))
    assert len(got) == 1000
    assert got[0].offset == 0
    assert got[-1].offset == 999


# ─── hardening / invalid input ─────────────────────────────────────────────


def test_invalid_max_events_rejected():
    """A non-positive cap is a programming error, rejected at construction."""
    with pytest.raises(ValueError):
        EventLog(max_events=0)
    with pytest.raises(ValueError):
        EventLog(max_events=-1)


def test_negative_since_rejected():
    """``since`` must be a non-negative offset."""
    log = EventLog()
    log.append(_chunk())
    with pytest.raises(ValueError):
        list(log.read(since=-1, follow=False))


def test_append_after_close_is_error():
    """Appending to a closed log is a programming error, not a silent no-op."""
    log = EventLog()
    log.close()
    with pytest.raises(RuntimeError):
        log.append(_chunk())


def test_close_is_idempotent():
    """Closing an already-closed log is a no-op (no raise)."""
    log = EventLog()
    log.close()
    log.close()  # must not raise


# ─── close ─────────────────────────────────────────────────────────────────


def test_close_releases_followers():
    """``close()`` ends every live ``read(follow=True)`` iterator without a
    hang — the follower's loop terminates cleanly."""
    log = EventLog()
    log.append(_chunk(text="0"))
    received: list[int] = []
    stopped = threading.Event()
    started = threading.Event()

    def follower() -> None:
        started.set()
        for ev in log.read(since=0, follow=True):
            received.append(ev.offset)
        # Loop exits (StopIteration) when the log closes — no hang.
        stopped.set()

    t = threading.Thread(target=follower)
    t.start()
    assert started.wait(_WAIT)
    time.sleep(0.1)  # let it drain offset 0 and block awaiting more
    log.close()
    assert stopped.wait(_WAIT), "close() did not release the follower"
    t.join(_WAIT)
    assert received == [0]
