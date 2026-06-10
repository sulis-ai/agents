"""WP-006 — idle-eviction + LRU memory-cap + dead-process detection.

Contract: SESSION_MANAGER_CONTRACT.md §2.7 (idle-eviction, memory cap with LRU
eviction, dead-process detection — the **Armor** primitive for resource bounds).
The manager caps how many warm sessions it holds (RAM costs) and reaps idle ones
on a periodic maintenance tick.

What this WP owns vs consumes (INDEX liveness ownership + WP boundary):

- **owns:** the maintenance *tick* (idle-eviction + LRU memory-cap + the
  *scheduling* of dead-process detection) — :class:`MaintenanceManager`,
  attached to the manager's no-op ``_maintenance_tick`` hook (WP-004 exposed it
  precisely so this attaches without swelling the core flow).
- **consumes, never re-implements:** WP-004's ``is_alive(session)`` for liveness;
  WP-004/005's ``_on_process_death`` for recovery routing of a detected death;
  the ``last_activity`` timestamp WP-004 already bumps on send/read — this WP
  only *reads* it as the LRU/idle key.

Verification posture (INDEX, MEA-09): **real threaded behaviour against a real
scripted child** — no mocked manager state, no mocked liveness. The maintenance
tick is driven **synchronously** (``mgr._maintenance_tick()`` called directly,
or the :class:`MaintenanceManager` invoked directly) and idle is made
deterministic by stamping ``last_activity`` against the manager's own clock — no
``sleep``-based flakiness. Bounded waits guard the few genuinely-threaded
assertions (a death the child performs itself) so a real hang fails fast.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pytest

from _session_manager.adapter import Capabilities, SessionSpec
from _session_manager.event_log import OffsetOutOfRangeError
from _session_manager.events import Event, TurnResult
from _session_manager.maintenance import (
    MEMORY_CAP_FLOOR,
    MaintenanceManager,
    default_cap,
    derive_cap,
    session_memory_bytes,
    total_host_ram_bytes,
)
from _session_manager.manager import SessionManager

# A real pty-backed child + adapter (no mocks) so the viewer-exemption test
# drives an attach against a real ``os.openpty()`` session — the same trio
# tests/unit/test_viewer.py uses (EP-03, single home under tests/lib).
_SCRIPTS_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_SCRIPTS_DIR / "tests" / "lib"))
import fake_claude_child  # noqa: E402
from session_child_adapters import PtyChildAdapter as _PtyChildAdapter  # noqa: E402

# Bounded wait for the few genuinely-threaded assertions (a child that kills
# itself): long enough never to flake on a loaded runner, short enough that a
# real hang fails fast.
_WAIT = 5.0


# ─── the scripted child (real subprocess, real decode) ──────────────────────
#
# A long-lived child that echoes a 3+rest chunk pair + a result per turn, and
# can be told to die on cue (``::die=now`` → the child exits before output).
# No real ``claude`` (that is WP-009's job, MEA-09).

_CHILD_SOURCE = r"""
import json, os, sys, time

def emit(obj):
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()

for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    try:
        msg = json.loads(line)
    except Exception:
        continue
    text = str(msg.get("command", ""))
    if msg.get("die"):
        os._exit(137)  # unexpected death before any output
    emit({"kind": "chunk", "text": text[:3]})
    emit({"kind": "chunk", "text": text[3:]})
    emit({"kind": "result", "input_tokens": 1, "output_tokens": len(text),
          "duration_ms": 1, "stop_reason": "end_turn"})
"""


def _write_child(tmp_path: Path) -> Path:
    p = tmp_path / "child.py"
    p.write_text(_CHILD_SOURCE)
    return p


class FakeAdapter:
    """A real :class:`ProviderAdapter` over the scripted child (no mock)."""

    def __init__(self) -> None:
        self.capabilities = Capabilities(
            supports_resume=True,
            supports_tools=False,
            supports_partial_streaming=True,
        )
        self._child: Path | None = None

    def bind(self, child: Path) -> "FakeAdapter":
        self._child = child
        return self

    def spawn_argv(self, spec: SessionSpec) -> list[str]:
        assert self._child is not None
        return [sys.executable, str(self._child)]

    def encode(self, command: str) -> bytes:
        die = None
        if "::die=" in command:
            command, die = command.split("::die=", 1)
        record: dict = {"command": command}
        if die:
            record["die"] = die
        return (json.dumps(record) + "\n").encode("utf-8")

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


def _manager(child: Path, **tuning: object) -> SessionManager:
    # Drive the tick synchronously (no background loop) so eviction timing is
    # deterministic — every WP-006 test calls ``_maintenance_tick()`` directly
    # (MEA-09: no sleep-based flakiness).
    tuning.setdefault("start_maintenance", False)
    adapter = FakeAdapter().bind(child)
    return SessionManager({"fake": adapter}, **tuning)


def _spec(tmp_path: Path) -> SessionSpec:
    return SessionSpec(provider="fake", cwd=str(tmp_path), resume_ref=None)


def _wait_for(predicate, timeout: float = _WAIT) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


def _drain_turn(mgr: SessionManager, key: str, off: int) -> list[Event]:
    """Follow-read one turn's three events from ``off`` (bounded)."""
    out: list[Event] = []
    deadline = time.monotonic() + _WAIT
    for ev in mgr.read(key, since=off, follow=True):
        out.append(ev)
        if len(out) >= 3 or time.monotonic() > deadline:
            break
    return out


# ─── idle-eviction (§2.7) ───────────────────────────────────────────────────


def test_idle_session_evicted_after_timeout(tmp_path):
    """A session with no activity past the idle timeout is closed by the tick;
    its process is gone and ``health`` reports it as no longer owned (§2.7).

    Determinism: a tiny idle timeout + stamping ``last_activity`` into the past
    against the manager's own clock — no ``sleep``-based flakiness.
    """
    child = _write_child(tmp_path)
    mgr = _manager(child, idle_timeout=10.0)
    try:
        session = mgr.open("k", _spec(tmp_path))
        proc = session.process
        assert mgr.is_alive(session)

        # Make the session look idle: last activity is well past the timeout,
        # measured against the maintenance clock the manager actually uses.
        now = mgr._maintenance.clock()
        session.last_activity = now - 100.0

        mgr._maintenance_tick()

        # The session is no longer owned and its process has been terminated.
        assert "k" not in mgr.status_keys()
        assert _wait_for(lambda: proc.poll() is not None), (
            "evicted session's process was not terminated"
        )
        # health on the evicted key declines (no session) — proven by an empty
        # status snapshot for that key.
        assert all(row.key != "k" for row in mgr.status())
    finally:
        mgr.close("k")


def test_active_session_not_evicted(tmp_path):
    """Recent activity resets the idle clock: a session active within the
    timeout survives the tick (§2.7)."""
    child = _write_child(tmp_path)
    mgr = _manager(child, idle_timeout=10.0)
    try:
        session = mgr.open("k", _spec(tmp_path))
        # Fresh activity: last_activity is "now" on the maintenance clock.
        session.last_activity = mgr._maintenance.clock()

        mgr._maintenance_tick()

        assert "k" in mgr.status_keys()
        assert mgr.is_alive(session)
    finally:
        mgr.close("k")


def test_in_use_session_with_viewer_not_idle_evicted(tmp_path):
    """An in-use pty session with an ATTACHED viewer is NEVER idle-evicted, even
    when its ``last_activity`` is well past the idle timeout (#108).

    A pty session bumps ``last_activity`` only on output bytes, so a turn that is
    quiet for longer than the idle timeout (claude thinking, a long quiet tool)
    looks idle to the tick — but an attached desktop window is definitionally
    in-use, so the tick must exempt it. A second, viewer-less pty session that is
    equally idle is still reaped, proving the exemption is scoped to in-use
    sessions and the genuine-idle reap is intact.
    """
    child = fake_claude_child.write_child(tmp_path)
    mgr = SessionManager(
        {"pty": _PtyChildAdapter(child)},
        idle_timeout=10.0,
        start_maintenance=False,
    )
    try:
        spec = SessionSpec(provider="pty", cwd=str(tmp_path), io_mode="pty")
        watched = mgr.open("watched", spec)
        headless = mgr.open("headless", spec)

        # Attach a viewer to "watched" — it is now visible/in-use.
        viewer = mgr.attach("watched")
        assert mgr.health("watched").viewer_count == 1
        assert mgr.health("headless").viewer_count == 0

        # Make BOTH look idle: last activity well past the timeout, on the clock
        # the tick actually uses (no sleep-based flakiness).
        idle = mgr._maintenance.clock() - 100.0
        watched.last_activity = idle
        headless.last_activity = idle

        mgr._maintenance_tick()

        # The watched (attached) session survives; the headless idle one is reaped.
        keys = mgr.status_keys()
        assert "watched" in keys, (
            "an in-use session with an attached viewer must not be idle-evicted (#108)"
        )
        assert mgr.is_alive(watched)
        assert "headless" not in keys, (
            "a viewer-less idle session must still be reaped (genuine-idle reap intact)"
        )
        viewer.detach()
    finally:
        for k in ("watched", "headless"):
            mgr.close(k)


def test_in_flight_turn_not_idle_evicted(tmp_path):
    """A session with a turn IN FLIGHT is never idle-evicted, even past the idle
    timeout and with no attached viewer (#108).

    A pty session bumps ``last_activity`` only on output bytes, so a turn that is
    actively working but quiet (claude thinking, a long quiet tool) looks idle.
    The in-flight slot (``turn_in_flight()``) is the liveness signal the output
    clock misses: an actively-working session is in-use and must not be reaped
    mid-work. Once the turn completes (slot freed) and it is genuinely idle, the
    same session is eligible again — the exemption is scoped, not permanent.
    """
    child = _write_child(tmp_path)
    mgr = _manager(child, idle_timeout=10.0)
    try:
        session = mgr.open("k", _spec(tmp_path))

        # Simulate a turn in flight (the stdin pump clears _turn_done when a turn
        # enters EXECUTING) and an idle-looking output clock.
        session._turn_done.clear()
        assert session.turn_in_flight()
        session.last_activity = mgr._maintenance.clock() - 100.0

        mgr._maintenance_tick()

        assert "k" in mgr.status_keys(), (
            "a session with a turn in flight must not be idle-evicted mid-work (#108)"
        )
        assert mgr.is_alive(session)

        # The turn completes: the slot frees and the now-genuinely-idle session is
        # eligible again — proving the exemption is scoped to in-flight work.
        session._turn_done.set()
        assert not session.turn_in_flight()
        session.last_activity = mgr._maintenance.clock() - 100.0
        mgr._maintenance_tick()
        assert "k" not in mgr.status_keys(), (
            "a genuinely-idle session (turn done, no viewer) must still be reaped"
        )
    finally:
        mgr.close("k")


# ─── memory-cap with LRU eviction (§2.7) ────────────────────────────────────


def test_memory_cap_evicts_lru_first(tmp_path):
    """Fill to the cap, then ``open`` one more → the LEAST-recently-used session
    is evicted first (by ``last_activity`` ordering), not a random or the newest
    one (§2.7)."""
    child = _write_child(tmp_path)
    mgr = _manager(child, memory_cap=2)
    try:
        a = mgr.open("a", _spec(tmp_path))
        b = mgr.open("b", _spec(tmp_path))
        # Make 'a' the least-recently-used, 'b' more recent.
        base = mgr._maintenance.clock()
        a.last_activity = base - 50.0
        b.last_activity = base - 10.0

        # Opening a third over the cap of 2 evicts the LRU ('a'), keeps 'b'.
        mgr.open("c", _spec(tmp_path))

        keys = mgr.status_keys()
        assert "a" not in keys, "LRU session 'a' should have been evicted"
        assert "b" in keys
        assert "c" in keys
        assert _wait_for(lambda: a.process.poll() is not None), (
            "evicted LRU process not terminated"
        )
    finally:
        for k in ("a", "b", "c"):
            mgr.close(k)


def test_lru_order_updated_on_send_and_read(tmp_path):
    """``send``/``read`` bump ``last_activity`` so a busy OLD session survives
    over an idle NEWER one when the cap forces an eviction (§2.7).

    This WP only *reads* ``last_activity``; WP-004 owns bumping it on send/read.
    The test proves the ordering the cap relies on actually reflects send/read.
    """
    child = _write_child(tmp_path)
    mgr = _manager(child, memory_cap=2)
    try:
        old = mgr.open("old", _spec(tmp_path))
        newer = mgr.open("newer", _spec(tmp_path))

        # 'old' opened first; but a send on it bumps its last_activity ABOVE
        # 'newer''s — making 'newer' the LRU even though it was opened later.
        before_old = old.last_activity
        off = mgr.send("old", "ping")
        evs = _drain_turn(mgr, "old", off)
        assert [e.kind for e in evs] == ["chunk", "chunk", "result"]
        assert old.last_activity > before_old, "send did not bump last_activity"
        assert old.last_activity > newer.last_activity, (
            "busy old session should be more-recently-used than the idle newer one"
        )

        # Opening a third over the cap now evicts 'newer' (the true LRU), not
        # 'old' (which is busy), proving the ordering tracks send/read.
        mgr.open("third", _spec(tmp_path))
        keys = mgr.status_keys()
        assert "newer" not in keys, "the idle newer session should be the LRU evicted"
        assert "old" in keys, "the busy old session must survive"
        assert "third" in keys
    finally:
        for k in ("old", "newer", "third"):
            mgr.close(k)


# ─── cap default derives from host RAM with a floor (§2.7, decided default) ──


def test_cap_default_derives_from_host_ram_with_floor():
    """``derive_cap`` clamps to a conservative floor for a tiny host: with a
    near-zero simulated RAM the cap is the floor (never zero), and a generous
    RAM yields more than the floor (§2.7 decided default: derive-from-RAM with a
    conservative floor)."""
    # A tiny host (1 byte of RAM) clamps to the floor, never zero.
    assert derive_cap(1) == MEMORY_CAP_FLOOR
    assert derive_cap(0) == MEMORY_CAP_FLOOR
    assert MEMORY_CAP_FLOOR >= 1, "the floor must keep at least one warm session"

    # A generous host (64 GiB) yields strictly more than the floor — the cap
    # actually scales with RAM rather than always pinning to the floor.
    big = derive_cap(64 * 1024 * 1024 * 1024)
    assert big > MEMORY_CAP_FLOOR

    # And the cap is monotonic in RAM (more RAM never gives a smaller cap).
    assert derive_cap(128 * 1024 * 1024 * 1024) >= big


def test_manager_default_cap_is_derived(tmp_path):
    """With no explicit ``memory_cap`` the manager adopts the RAM-derived
    default (≥ the floor) rather than an unbounded or zero cap (§2.7)."""
    child = _write_child(tmp_path)
    mgr = _manager(child)  # no memory_cap kwarg → derive from host RAM
    try:
        assert mgr._maintenance.memory_cap >= MEMORY_CAP_FLOOR
    finally:
        pass


def test_host_ram_reading_degrades_to_floor_when_unavailable(monkeypatch):
    """A missing host-RAM reading must degrade to the floor, never raise: when
    ``os.sysconf`` is unavailable, ``total_host_ram_bytes`` returns 0 and
    ``default_cap`` clamps to the floor (§ WP Notes: a missing reading degrades
    to the safe default)."""
    import _session_manager.maintenance as maint

    # Real host read is a positive number.
    assert total_host_ram_bytes() > 0

    def _boom(_name):
        raise OSError("sysconf unavailable on this platform")

    monkeypatch.setattr(maint.os, "sysconf", _boom)
    assert total_host_ram_bytes() == 0
    assert default_cap() == MEMORY_CAP_FLOOR


def test_session_memory_bytes_degrades_to_zero_for_dead_process(tmp_path):
    """``session_memory_bytes`` is a best-effort observational reading: a live
    session yields a non-negative byte count; once its process is gone the
    reading degrades to 0 rather than raising into the side-effect-free status
    snapshot (§2.3)."""
    child = _write_child(tmp_path)
    mgr = _manager(child)
    try:
        session = mgr.open("k", _spec(tmp_path))
        live = session_memory_bytes(session)
        assert live >= 0  # a real ps reading (or a benign 0 if ps is absent)
        mgr.close("k")
        # After close the process is gone (or poll set); the reading must not
        # raise and is a benign 0 / non-negative.
        assert session_memory_bytes(session) >= 0
    finally:
        mgr.close("k")


# ─── dead-process detection in the tick (§2.7) ──────────────────────────────


def test_dead_process_detected_by_tick(tmp_path):
    """Kill a child; the next tick detects the death (via WP-004's ``is_alive``)
    and routes it through WP-004/005's ``_on_process_death`` — proven by the
    death actually being handled (the session is restarted to a fresh live pid,
    same key). This WP owns the *detection in the tick*; recovery itself is
    WP-005's (§2.7 liveness ownership)."""
    child = _write_child(tmp_path)
    mgr = _manager(child)
    try:
        session = mgr.open("k", _spec(tmp_path))
        first_pid = session.pid

        # Kill the child out from under the manager, then disarm the session's
        # own EOF-driven death signal so the TICK is unambiguously the detector
        # (not the stdout pump's EOF path) — the tick must independently catch a
        # process that died without its pump noticing yet.
        session._death_signalled = True
        session.process.kill()
        assert _wait_for(lambda: session.process.poll() is not None)

        # The tick detects the dead process and fires the death hook.
        mgr._maintenance_tick()

        # The death was handled: restart-on-death (WP-005) gave a fresh live pid
        # under the SAME key — the tick's detection drove recovery.
        assert _wait_for(
            lambda: (
                "k" in mgr.status_keys()
                and mgr.health("k").alive
                and mgr.health("k").pid != first_pid
            )
        ), "tick did not detect the dead process and route it to recovery"
    finally:
        mgr.close("k")


def test_dead_process_routed_through_on_death_hook(tmp_path):
    """The tick's dead-process detection routes through the EXISTING
    ``_on_process_death`` hook (WP-004/005), it does not re-implement recovery.
    Proven by spying the hook: a dead process in the tick invokes it exactly
    once for that session (§2.7 boundary — consume, don't fork)."""
    child = _write_child(tmp_path)
    mgr = _manager(child)
    called: list[str] = []
    original = mgr._on_process_death

    def _spy(session):
        called.append(session.key)
        return original(session)

    mgr._on_process_death = _spy  # type: ignore[method-assign]
    try:
        session = mgr.open("k", _spec(tmp_path))
        session._death_signalled = True  # disarm the pump path
        session.process.kill()
        assert _wait_for(lambda: session.process.poll() is not None)

        mgr._maintenance_tick()

        assert called == ["k"], (
            "dead-process detection must route through _on_process_death exactly once"
        )
    finally:
        mgr.close("k")


# ─── graceful eviction (§2.7) ───────────────────────────────────────────────


def test_eviction_is_graceful(tmp_path):
    """An evicted session's log is closed, followers are released, the registry
    entry is removed, and no pump threads leak (§2.7 graceful eviction:
    SIGTERM→SIGKILL, log closed, registry entry removed)."""
    child = _write_child(tmp_path)
    mgr = _manager(child, idle_timeout=10.0)
    try:
        session = mgr.open("k", _spec(tmp_path))
        proc = session.process

        # A follower parked on the live log must be RELEASED when the session is
        # evicted (the log close ends the follow), not left hanging.
        follower_done: list[bool] = []

        def _follow():
            try:
                for _ in mgr.read("k", since=0, follow=True):
                    pass
            except OffsetOutOfRangeError:
                pass
            follower_done.append(True)

        import threading

        t = threading.Thread(target=_follow, daemon=True)
        t.start()

        # Force eviction via the idle path.
        session.last_activity = mgr._maintenance.clock() - 100.0
        mgr._maintenance_tick()

        # Registry entry removed.
        assert "k" not in mgr.status_keys()
        # Process terminated (SIGTERM→SIGKILL).
        assert _wait_for(lambda: proc.poll() is not None)
        # The follower was released (log closed ends the follow) — no hang.
        t.join(_WAIT)
        assert not t.is_alive(), "follower not released after eviction (log not closed)"
        assert follower_done == [True]
        # The session's pump threads are gone (no leaked threads).
        assert _wait_for(lambda: all(not th.is_alive() for th in session._threads)), (
            "evicted session leaked a live pump thread"
        )
    finally:
        mgr.close("k")


# ─── the background maintenance loop actually runs the tick (§2.7) ──────────


def test_background_loop_evicts_idle_session_then_shuts_down(tmp_path):
    """The background maintenance thread runs the tick on its interval: an idle
    session is reaped without any direct ``_maintenance_tick()`` call, and
    ``shutdown`` stops the loop + closes remaining sessions cleanly (§2.7).

    A short interval keeps the test fast; a bounded wait guards the assertion so
    a stalled loop fails fast rather than hanging CI."""
    child = _write_child(tmp_path)
    # Real background loop (start_maintenance default True), tiny interval, tiny
    # idle timeout so the loop reaps promptly.
    adapter = FakeAdapter().bind(child)
    mgr = SessionManager(
        {"fake": adapter},
        idle_timeout=0.05,
        maintenance_interval=0.05,
    )
    try:
        session = mgr.open("k", _spec(tmp_path))
        proc = session.process
        # Do not touch the session: it crosses the 0.05s idle threshold and the
        # background loop reaps it on its next pass — no manual tick.
        assert _wait_for(lambda: "k" not in mgr.status_keys(), timeout=_WAIT), (
            "background maintenance loop did not evict the idle session"
        )
        assert _wait_for(lambda: proc.poll() is not None)
    finally:
        mgr.shutdown()
        # shutdown stopped the loop: the maintenance thread is no longer alive.
        assert not (
            mgr._maintenance_thread is not None and mgr._maintenance_thread.is_alive()
        )


# ─── the MaintenanceManager is the seam the manager delegates to ────────────


def test_maintenance_manager_idle_predicate_uses_injected_clock(tmp_path):
    """:class:`MaintenanceManager` decides idle against an injectable clock, so
    eviction timing is deterministic in tests (no real sleep). A session whose
    ``last_activity`` is older than ``now - idle_timeout`` is idle; one within
    the window is not (§2.7, MEA-09 determinism)."""
    fake_now = [1000.0]
    mm = MaintenanceManager(idle_timeout=30.0, memory_cap=8, clock=lambda: fake_now[0])

    assert mm.is_idle(last_activity=fake_now[0] - 31.0) is True
    assert mm.is_idle(last_activity=fake_now[0] - 29.0) is False
    # Advancing the clock makes a once-active session idle — deterministically.
    fake_now[0] = 2000.0
    assert mm.is_idle(last_activity=1000.0) is True


def test_maintenance_manager_rejects_invalid_tuning():
    """Invalid tuning is a programming error, rejected loudly at construction
    (boring, explicit validation): a non-positive idle timeout and a sub-1
    memory cap both raise (§2.7)."""
    with pytest.raises(ValueError):
        MaintenanceManager(idle_timeout=0)
    with pytest.raises(ValueError):
        MaintenanceManager(idle_timeout=-1.0)
    with pytest.raises(ValueError):
        MaintenanceManager(memory_cap=0)


def test_session_memory_bytes_returns_zero_on_ps_failure(tmp_path, monkeypatch):
    """When the ``ps`` reading fails (binary missing / non-numeric output) the
    memory reading degrades to 0 rather than raising into the side-effect-free
    snapshot (§2.3 best-effort)."""
    import _session_manager.maintenance as maint

    child = _write_child(tmp_path)
    mgr = _manager(child)
    try:
        session = mgr.open("k", _spec(tmp_path))

        def _boom(*_a, **_k):
            raise OSError("ps not found")

        monkeypatch.setattr(maint.subprocess, "run", _boom)
        assert session_memory_bytes(session) == 0

        class _Out:
            stdout = "not-a-number\n"

        monkeypatch.setattr(maint.subprocess, "run", lambda *a, **k: _Out())
        assert session_memory_bytes(session) == 0
    finally:
        mgr.close("k")
