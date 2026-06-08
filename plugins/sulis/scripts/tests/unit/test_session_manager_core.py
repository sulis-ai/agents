"""WP-004 — tests for the ``SessionManager`` six-method core surface.

Contract: SESSION_MANAGER_CONTRACT.md §2.2 (the six methods open/send/read/
health/status/close), §2.5 (log/cursor), §2.6 (one-in-flight per key,
different keys parallel), plus the decoupling invariant (send returns an
offset and never blocks; read is the only content path).

Verification posture (INDEX, MEA-09): **real manager state** — no mock of the
manager's own threads, queue, lock, or log. The agent process is **stubbed**
not by mocking the manager, but by driving a *real* scripted child subprocess
(``_child_script.py``-equivalent inlined here) behind a *real* fake adapter.
The manager's threading / queue / log / one-in-flight behaviour is exercised
for real against that child's recorded, delayed NDJSON output. Spawning the
real ``claude`` binary is WP-009's job; here the child is a deterministic
python script.

Every threaded assertion uses a short bounded wait so a genuine hang fails the
test quickly rather than blocking CI.
"""

from __future__ import annotations

import json
import sys
import threading
import time
from pathlib import Path

import pytest

from _session_manager.adapter import Capabilities, SessionSpec
from _session_manager.events import (
    CWD_NOT_FOUND,
    NO_SESSION,
    UNKNOWN_PROVIDER,
    Event,
    ExpectedError,
    TurnResult,
)
from _session_manager.manager import SessionManager
from _session_manager.session import Session
from _session_manager.state import Health, SessionStatus

# Bounded wait for threaded assertions: long enough never to flake on a loaded
# CI runner, short enough that a real hang fails fast.
_WAIT = 5.0


# ─── the scripted child + fake adapter (real subprocess, real decode) ──────
#
# The child is a tiny python program that, per stdin line it reads (one
# encoded turn), waits a short configurable delay then emits a recorded NDJSON
# turn: N `chunk` lines followed by one `result` line. It is a REAL process —
# the manager spawns it, writes to its stdin, reads its stdout on a pump
# thread, and decodes each line. No part of the manager is mocked.

# The child program source. Reads NDJSON turns from stdin; for each, sleeps
# `delay` seconds then writes a bookkeeping line (decoded to None), N chunk
# lines, and a terminal `result` line, plus one stderr line. Flushes after
# every stdout line so the manager's stdout pump sees them stream.
_CHILD_SOURCE = r"""
import json, sys, time

def emit(obj):
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()

delay = float(sys.argv[1]) if len(sys.argv) > 1 else 0.0
turn = 0
for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    try:
        msg = json.loads(line)
    except Exception:
        continue
    text = str(msg.get("command", ""))
    turn += 1
    time.sleep(delay)
    # a bookkeeping/init line the adapter decodes to None (skipped by the pump)
    emit({"kind": "system", "subtype": "init"})
    # a stderr diagnostic line the stderr pump must drain
    sys.stderr.write("diag: turn %d\n" % turn)
    sys.stderr.flush()
    # two chunk lines then a terminal result line
    emit({"kind": "chunk", "text": text[:3]})
    emit({"kind": "chunk", "text": text[3:]})
    emit({"kind": "result", "input_tokens": 1, "output_tokens": len(text),
          "duration_ms": 1, "stop_reason": "end_turn"})
"""


def _write_child(tmp_path: Path, name: str = "child.py") -> Path:
    p = tmp_path / name
    p.write_text(_CHILD_SOURCE)
    return p


class FakeAdapter:
    """A real :class:`ProviderAdapter` over the scripted child (no mocks).

    ``spawn_argv`` launches the scripted python child; ``encode`` frames a turn
    as a single NDJSON line carrying ``command``; ``decode`` parses one child
    output line into a partial :class:`Event` (placeholder log coordinates, as
    the §2.4 seam mandates); ``turn_complete`` fires on the ``result`` line.
    """

    def __init__(self, child: Path, delay: float = 0.0) -> None:
        self._child = child
        self._delay = delay
        self.capabilities = Capabilities(
            supports_resume=False,
            supports_tools=False,
            supports_partial_streaming=True,
        )

    def spawn_argv(self, spec: SessionSpec) -> list[str]:
        return [sys.executable, str(self._child), str(self._delay)]

    def encode(self, command: str) -> bytes:
        return (json.dumps({"command": command}) + "\n").encode("utf-8")

    def decode(self, line: bytes) -> Event | None:
        record = json.loads(line)
        kind = record.get("kind")
        if kind == "chunk":
            return Event(offset=-1, key="", turn=-1, kind="chunk", text=record["text"])
        if kind == "result":
            return Event(
                offset=-1,
                key="",
                turn=-1,
                kind="result",
                result=TurnResult(
                    input_tokens=int(record.get("input_tokens", 0)),
                    output_tokens=int(record.get("output_tokens", 0)),
                    duration_ms=int(record.get("duration_ms", 0)),
                    stop_reason=str(record.get("stop_reason", "")),
                ),
            )
        return None

    def turn_complete(self, event: Event) -> bool:
        return event.kind == "result"


@pytest.fixture
def child(tmp_path) -> Path:
    return _write_child(tmp_path)


def _manager(child: Path, *, delay: float = 0.0, extra=None) -> SessionManager:
    adapters = {"fake": FakeAdapter(child, delay=delay)}
    if extra:
        adapters.update(extra)
    return SessionManager(adapters)


def _spec(tmp_path: Path, provider: str = "fake") -> SessionSpec:
    return SessionSpec(provider=provider, cwd=str(tmp_path))


def _drain(
    mgr: SessionManager,
    key: str,
    since: int,
    *,
    until_result: bool,
    timeout: float = _WAIT,
) -> list[Event]:
    """Follow-read a key, collecting events until a ``result`` arrives (or
    timeout). Runs the follow read on this thread but stops on the terminal
    event so the test never hangs."""
    collected: list[Event] = []
    deadline = time.monotonic() + timeout
    it = mgr.read(key, since=since, follow=True)
    for ev in it:
        collected.append(ev)
        if until_result and ev.kind == "result":
            break
        if time.monotonic() > deadline:
            break
    return collected


# ─── open: get-or-spawn idempotence + expected errors ──────────────────────


def test_open_get_or_spawn_idempotent(child, tmp_path):
    """A second ``open`` on a live key returns the SAME Session and spawns
    nothing (§2.2 idempotent get-or-spawn)."""
    mgr = _manager(child)
    try:
        s1 = mgr.open("k", _spec(tmp_path))
        assert isinstance(s1, Session)
        pid1 = s1.pid
        s2 = mgr.open("k", _spec(tmp_path))
        assert s2 is s1
        assert s2.pid == pid1  # nothing re-spawned
    finally:
        mgr.close("k")


def test_open_unknown_provider_expected_error(child, tmp_path):
    """``open`` with a provider not in the adapters dict raises an Expected
    error with code ``UNKNOWN_PROVIDER`` (§2.9)."""
    mgr = _manager(child)
    with pytest.raises(ExpectedError) as exc:
        mgr.open("k", _spec(tmp_path, provider="nope"))
    assert exc.value.code == UNKNOWN_PROVIDER


def test_open_cwd_not_found_expected_error(child, tmp_path):
    """``open`` with a cwd that does not exist raises an Expected error with
    code ``CWD_NOT_FOUND`` (§2.9) — checked before spawn."""
    mgr = _manager(child)
    spec = SessionSpec(provider="fake", cwd=str(tmp_path / "does-not-exist"))
    with pytest.raises(ExpectedError) as exc:
        mgr.open("k", spec)
    assert exc.value.code == CWD_NOT_FOUND


# ─── the decoupling invariant: send returns a bookmark, never blocks ───────


def test_send_returns_landing_offset_immediately(child, tmp_path):
    """``send`` returns the landing offset BEFORE any event arrives, and that
    offset is exactly where the turn's first event lands (decoupling
    invariant + §2.5 forward reference). Proven with a slow child: send
    returns fast, the first event is not yet in the log."""
    mgr = _manager(child, delay=0.3)
    try:
        mgr.open("k", _spec(tmp_path))
        t0 = time.monotonic()
        off = mgr.send("k", "hello world")
        elapsed = time.monotonic() - t0
        # send must return well before the child's 0.3s turn delay elapses.
        assert elapsed < 0.2
        assert off == 0  # first turn lands at offset 0
        # The first event has NOT landed yet (send did not block on it).
        evs = _drain(mgr, "k", since=off, until_result=True)
        assert evs[0].offset == off
        assert evs[-1].kind == "result"
    finally:
        mgr.close("k")


def test_send_then_read_follow_streams_turn(child, tmp_path):
    """``off = send(); read(since=off, follow=True)`` yields chunk* then result
    — the request/response composition (§2.2)."""
    mgr = _manager(child)
    try:
        mgr.open("k", _spec(tmp_path))
        off = mgr.send("k", "abcdef")
        evs = _drain(mgr, "k", since=off, until_result=True)
        kinds = [e.kind for e in evs]
        assert kinds == ["chunk", "chunk", "result"]
        # The chunks reconstruct the submitted command.
        text = "".join(e.text for e in evs if e.kind == "chunk")
        assert text == "abcdef"
        # Offsets are contiguous from the send bookmark.
        assert [e.offset for e in evs] == [off, off + 1, off + 2]
    finally:
        mgr.close("k")


def test_read_no_session_expected_error(child, tmp_path):
    """``read`` on a key with no open session raises Expected ``NO_SESSION``."""
    mgr = _manager(child)
    with pytest.raises(ExpectedError) as exc:
        # read() returns an iterator; the error surfaces on first use OR on
        # call — accept either by forcing iteration.
        list(mgr.read("missing", since=0, follow=False))
    assert exc.value.code == NO_SESSION


# ─── one-in-flight per key + per-key parallelism (§2.6) ────────────────────


def test_one_in_flight_queues_second_send(child, tmp_path):
    """Two back-to-back ``send``s on one key: the second runs only AFTER the
    first's ``result``; both landing offsets are correct (§2.6 FIFO queue)."""
    mgr = _manager(child, delay=0.2)
    try:
        mgr.open("k", _spec(tmp_path))
        off1 = mgr.send("k", "one")
        off2 = mgr.send("k", "two")
        # First turn: 2 chunks + result at offsets 0,1,2 → second lands at 3.
        assert off1 == 0
        assert off2 == 3
        # Read the whole stream up to the SECOND result.
        evs: list[Event] = []
        for ev in mgr.read("k", since=0, follow=True):
            evs.append(ev)
            if ev.kind == "result" and ev.offset == off2 + 2:
                break
        # The two turns are strictly ordered: turn 1's result precedes turn 2's
        # first chunk (proves the second was queued, not run concurrently).
        offsets = [e.offset for e in evs]
        assert offsets == [0, 1, 2, 3, 4, 5]
        turns = [e.turn for e in evs]
        assert turns == [1, 1, 1, 2, 2, 2]
    finally:
        mgr.close("k")


def test_different_keys_run_in_parallel(child, tmp_path):
    """Two keys, two turns overlap in wall-clock — the one-in-flight rule is
    per-key, not global (§2.6)."""
    mgr = _manager(child, delay=0.4)
    try:
        mgr.open("a", _spec(tmp_path))
        mgr.open("b", _spec(tmp_path))
        t0 = time.monotonic()
        mgr.send("a", "aaa")
        mgr.send("b", "bbb")

        def _wait_result(key):
            for ev in mgr.read(key, since=0, follow=True):
                if ev.kind == "result":
                    return

        ta = threading.Thread(target=_wait_result, args=("a",))
        tb = threading.Thread(target=_wait_result, args=("b",))
        ta.start()
        tb.start()
        ta.join(_WAIT)
        tb.join(_WAIT)
        elapsed = time.monotonic() - t0
        assert not ta.is_alive() and not tb.is_alive()
        # If they were serialised the wall-clock would be ~0.8s (2 × 0.4).
        # Parallel keys complete in ~0.4s; allow generous headroom.
        assert elapsed < 0.7
    finally:
        mgr.close("a")
        mgr.close("b")


def test_read_never_blocked_by_send(child, tmp_path):
    """A follower reads while a turn runs; it is not serialised behind the
    in-flight lock (§2.6: read is never blocked by send)."""
    mgr = _manager(child, delay=0.3)
    try:
        mgr.open("k", _spec(tmp_path))
        off = mgr.send("k", "streamed")
        # Start following immediately; we should receive the first chunk as
        # soon as the child emits it, while the turn (and its in-flight slot)
        # is still held.
        first: list[Event] = []
        ev_seen = threading.Event()

        def _follow():
            for ev in mgr.read("k", since=off, follow=True):
                first.append(ev)
                ev_seen.set()
                if ev.kind == "result":
                    return

        t = threading.Thread(target=_follow)
        t.start()
        # The first chunk must arrive (reader not blocked by the running turn).
        assert ev_seen.wait(_WAIT)
        assert first[0].kind == "chunk"
        t.join(_WAIT)
        assert not t.is_alive()
    finally:
        mgr.close("k")


# ─── health / status (backed by the WP-004-owned is_alive primitive) ───────


def test_health_reflects_pid_and_alive(child, tmp_path):
    """``health`` returns alive/pid/provider/state for a live session and
    raises Expected ``NO_SESSION`` for an unknown key (§2.2/§2.3)."""
    mgr = _manager(child)
    try:
        s = mgr.open("k", _spec(tmp_path))
        h = mgr.health("k")
        assert isinstance(h, Health)
        assert h.alive is True
        assert h.pid == s.pid
        assert h.provider == "fake"
        assert h.state  # a non-empty state label
        with pytest.raises(ExpectedError) as exc:
            mgr.health("missing")
        assert exc.value.code == NO_SESSION
    finally:
        mgr.close("k")


def test_status_snapshots_all_sessions(child, tmp_path):
    """``status()`` lists every open key with the §2.3 SessionStatus fields
    (memory_bytes / last_activity / log_len among them)."""
    mgr = _manager(child)
    try:
        mgr.open("a", _spec(tmp_path))
        mgr.open("b", _spec(tmp_path))
        snap = mgr.status()
        assert isinstance(snap, list)
        assert all(isinstance(s, SessionStatus) for s in snap)
        keys = {s.key for s in snap}
        assert keys == {"a", "b"}
        for s in snap:
            assert s.provider == "fake"
            assert s.pid is not None
            assert s.log_len >= 0
            assert s.last_activity is not None
            # memory_bytes is present (may be 0 if unmeasured pre-WP-006).
            assert s.memory_bytes >= 0
    finally:
        mgr.close("a")
        mgr.close("b")


# ─── close: terminate + idempotent (§2.2) ──────────────────────────────────


def test_close_terminates_and_is_idempotent(child, tmp_path):
    """``close`` ends the pumps + child; a second ``close`` is a no-op; closing
    an unknown key is a no-op (§2.2)."""
    mgr = _manager(child)
    s = mgr.open("k", _spec(tmp_path))
    pid = s.pid
    mgr.close("k")
    # The child is no longer alive after close.
    assert not mgr.is_alive(s)
    # health on a closed key raises NO_SESSION (it was removed from registry).
    with pytest.raises(ExpectedError) as exc:
        mgr.health("k")
    assert exc.value.code == NO_SESSION
    # Second close: no-op (no raise).
    mgr.close("k")
    # Closing an unknown key: no-op (no raise).
    mgr.close("never-opened")
    assert pid is not None


# ─── the WP-004-owned liveness primitive (backs health/status) ─────────────


def test_is_alive_owned_liveness_primitive(child, tmp_path):
    """``is_alive(session)`` is the single liveness check owned here, consumed
    unchanged by WP-005/006. True for a live session, False after close
    (process.poll-style)."""
    mgr = _manager(child)
    s = mgr.open("k", _spec(tmp_path))
    assert mgr.is_alive(s) is True
    mgr.close("k")
    assert mgr.is_alive(s) is False


# ─── the three extension-point hooks are no-op stubs (§ Blue seams) ─────────


def test_extension_hooks_are_noop_stubs(child, tmp_path):
    """The three wave-4 extension points exist as no-op stubs so WP-005/006/007
    fill them without editing core flow: ``_on_process_death(session)``,
    ``_maintenance_tick()``, and a per-turn ``_guard(...)``. Calling each on a
    fresh manager does nothing and returns None (no exception)."""
    mgr = _manager(child)
    try:
        s = mgr.open("k", _spec(tmp_path))
        assert mgr._on_process_death(s) is None
        assert mgr._maintenance_tick() is None
        # _guard is per-turn; it accepts the session + a candidate command and
        # returns None as a no-op (WP-007 fills the guard logic).
        assert mgr._guard(s, "any command") is None
    finally:
        mgr.close("k")
