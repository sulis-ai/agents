"""WP-007 (automation-reliability-recovery) — manager wiring tests for the
``RecoveryDriver`` + the error-observation hook.

Contract: ADR-001 (the classifier + recovery driver sit *around* the lifecycle,
not inside it) and TDD §2.2 / §3.1 step 1 (the no-double-handling rule —
process-death ``STDIN_BROKEN`` is the lifecycle's seam, not the driver's).

This WP attaches WP-005's :class:`~_session_manager.recovery.RecoveryDriver` at
the manager's **error-event observation seam** — the sibling of the
``_on_process_death`` death hook (ADR-001). A live turn that ends in an
``error`` Event is routed to the driver; a process-death ``STDIN_BROKEN`` error
is **not** (the lifecycle owns it). The wiring is additive: a per-session driver
constructed at the composition root + the ``_on_error_event`` hook, attached
alongside the existing ``TurnGuardManager`` ``on_event`` observer so neither
clobbers the other.

Verification posture (MEA-09, mirroring ``test_session_manager_core``): a
**real** scripted-child subprocess behind a real fake adapter drives a real
``error`` Event through the manager's pumps; no part of the manager's
threading / queue / log is mocked. The driver itself is substituted by a
recording spy via the injectable ``recovery_driver_factory`` tuning kwarg (the
same injectable-factory seam ``TurnGuardManager``'s ``timer_factory`` uses), so
the test observes routing without running a real retry/backoff loop.

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
from _session_manager.classifier import RecoveryClass
from _session_manager.events import STDIN_BROKEN, Event, EventError, TurnResult
from _session_manager.manager import SessionManager
from _session_manager.recovery import DEFAULT_RETRY_POLICY

# Bounded wait for threaded assertions: long enough never to flake on a loaded
# CI runner, short enough that a real hang fails fast.
_WAIT = 5.0


# ─── a scripted child that can emit an error turn (real subprocess) ────────
#
# The child reads one NDJSON line per turn. The command text selects the turn
# shape: a command starting with "ERR:" emits a single ``error`` line carrying
# the remainder as the raw failure code; any other command emits one ``chunk``
# then one ``result`` (the healthy turn). It is a REAL process — the manager
# spawns it, writes its stdin, reads its stdout on a pump thread, and decodes
# each line. No part of the manager is mocked.
_CHILD_SOURCE = r"""
import json, sys

def emit(obj):
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()

# A command starting with "ERR:" emits one ``error`` line carrying the
# remainder as the raw code; "ERR1:" errors only on its FIRST occurrence (the
# blip), then answers a healthy turn on the replay — so a transient-blip retry
# can be observed clearing without an unbounded re-error storm. Any other
# command emits one ``chunk`` then one ``result`` (the healthy turn).
seen = set()
for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    try:
        msg = json.loads(line)
    except Exception:
        continue
    text = str(msg.get("command", ""))
    if text.startswith("ERR1:"):
        if text not in seen:
            seen.add(text)
            emit({"kind": "error", "category": "expected", "code": text[5:],
                  "message": "scripted blip (first occurrence)"})
            continue
        # replay: answer healthily so the blip "clears"
        emit({"kind": "chunk", "text": "ok"})
        emit({"kind": "result", "input_tokens": 1, "output_tokens": 2,
              "duration_ms": 1, "stop_reason": "end_turn"})
        continue
    if text.startswith("ERR:"):
        emit({"kind": "error", "category": "expected", "code": text[4:],
              "message": "scripted failure"})
        continue
    emit({"kind": "chunk", "text": text})
    emit({"kind": "result", "input_tokens": 1, "output_tokens": len(text),
          "duration_ms": 1, "stop_reason": "end_turn"})
"""


def _write_child(tmp_path: Path) -> Path:
    p = tmp_path / "child.py"
    p.write_text(_CHILD_SOURCE)
    return p


class FakeAdapter:
    """A real :class:`ProviderAdapter` over the scripted child (no mocks).

    ``decode`` maps the child's ``error`` line into an ``error``-kind Event
    (the §2.4 partial-event seam), so a live turn can terminate in an ``error``
    the manager appends to the log — exactly the seam WP-007 routes from.
    ``classify_failure`` records nothing here; the spy driver captures routing.
    """

    def __init__(self, child: Path) -> None:
        self._child = child
        self.capabilities = Capabilities(
            supports_resume=False,
            supports_tools=False,
            supports_partial_streaming=True,
        )

    def spawn_argv(self, spec: SessionSpec) -> list[str]:
        return [sys.executable, str(self._child)]

    def encode(self, command: str) -> bytes:
        return (json.dumps({"command": command}) + "\n").encode("utf-8")

    def decode(self, line: bytes) -> Event | None:
        record = json.loads(line)
        kind = record.get("kind")
        if kind == "chunk":
            return Event(offset=-1, key="", turn=-1, kind="chunk", text=record["text"])
        if kind == "error":
            return Event(
                offset=-1,
                key="",
                turn=-1,
                kind="error",
                error=EventError(
                    category=record.get("category", "expected"),
                    code=record.get("code", "ERROR"),
                    message=record.get("message", ""),
                ),
            )
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
        # An ``error`` event does NOT free the slot via this signal (§2.6 /
        # claude adapter precedent) — only a successful ``result`` does.
        return event.kind == "result"

    def classify_failure(self, error: EventError) -> RecoveryClass | None:
        return None

    def reauth(self):  # pragma: no cover - not reached in these tests
        raise AssertionError("reauth must not be called in the wiring tests")


class _SpyDriver:
    """A recording stand-in for :class:`RecoveryDriver`.

    Captures every ``observe(error)`` call and the constructor kwargs the
    manager wired it with, so a test can assert *what was routed* and *how the
    driver was constructed* — without running a real retry/backoff loop. It
    replicates the driver's own first step (skip ``STDIN_BROKEN``) so the test
    sees exactly the contract the real driver honours."""

    instances: list["_SpyDriver"] = []

    def __init__(self, **kwargs: object) -> None:
        self.kwargs = kwargs
        self.observed: list[EventError] = []
        self.cleared_count = 0
        self._lock = threading.Lock()
        # CH-01KTMK FIX 1 — the spy honours the in-flight guard contract the
        # manager now calls (``try_begin_recovery`` / ``end_recovery``). The base
        # spy never coalesces (each observe is recorded), so it always wins the
        # slot; subclasses override to model coalescing / fault-release.
        self._in_flight = threading.Event()
        _SpyDriver.instances.append(self)

    def try_begin_recovery(self) -> bool:
        with self._lock:
            if self._in_flight.is_set():
                return False
            self._in_flight.set()
            return True

    def end_recovery(self) -> None:
        with self._lock:
            self._in_flight.clear()

    def observe(self, error: EventError) -> None:
        with self._lock:
            self.observed.append(error)

    def note_turn_cleared(self) -> None:
        # The manager fires this on a genuine ``result`` (turn_complete True) so
        # the driver can reset its accumulated retry budget. Recorded so a wiring
        # test can assert the reset hook is actually wired.
        with self._lock:
            self.cleared_count += 1


@pytest.fixture(autouse=True)
def _reset_spy() -> None:
    _SpyDriver.instances.clear()
    yield
    _SpyDriver.instances.clear()


@pytest.fixture
def child(tmp_path) -> Path:
    return _write_child(tmp_path)


def _spy_manager(child: Path) -> SessionManager:
    """A manager whose recovery driver is the recording spy (injected via the
    ``recovery_driver_factory`` tuning kwarg — the ``timer_factory`` seam
    precedent). ``start_maintenance=False`` keeps the background tick out of
    the test (MEA-09 determinism)."""
    return SessionManager(
        {"fake": FakeAdapter(child)},
        recovery_driver_factory=lambda **kw: _SpyDriver(**kw),
        start_maintenance=False,
    )


def _spec(tmp_path: Path) -> SessionSpec:
    return SessionSpec(provider="fake", cwd=str(tmp_path))


def _wait_for(predicate, timeout: float = _WAIT) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return predicate()


# ─── acceptance #1: the driver is constructed at the composition root ──────


def test_recovery_driver_constructed_at_composition_root(child, tmp_path):
    """Opening a session constructs a ``RecoveryDriver`` wired with the default
    policy + a clock + the classifier + the per-session adapter's
    ``classify_failure`` hint (ADR-001 — one wiring line beside the lifecycle).

    Proven against the spy factory: the manager hands the driver exactly the
    injected capabilities the WP-005 contract names, with the default policy."""
    mgr = _spy_manager(child)
    try:
        mgr.open("k", _spec(tmp_path))
        assert _wait_for(lambda: len(_SpyDriver.instances) >= 1)
        driver = _SpyDriver.instances[-1]
        kw = driver.kwargs
        # The injected manager capabilities (WP-005 driver contract).
        assert callable(kw["send"])
        assert callable(kw["log_append"])
        assert callable(kw["reauth"])
        assert callable(kw["resume"])
        # The default policy is selected at the composition root (ADR-002).
        assert kw["policy"] is DEFAULT_RETRY_POLICY
        # A clock is injected (the wall-clock retry budget is measured on it).
        assert callable(kw["clock"])
        # The adapter's provider-detection hint is wired through (ADR-003).
        assert callable(kw["classify_failure"])
    finally:
        mgr.close("k")


def test_default_factory_builds_real_recovery_driver(child, tmp_path):
    """With no ``recovery_driver_factory`` injected, the manager's default
    builds the real WP-005 :class:`RecoveryDriver` at the composition root
    (the boring default the injectable seam falls back to)."""
    from _session_manager.recovery import RecoveryDriver

    mgr = SessionManager({"fake": FakeAdapter(child)}, start_maintenance=False)
    try:
        mgr.open("k", _spec(tmp_path))
        assert _wait_for(lambda: "k" in mgr._recovery_drivers)
        assert isinstance(mgr._recovery_drivers["k"], RecoveryDriver)
    finally:
        mgr.close("k")


# ─── acceptance #2a: an error Event from a live session reaches the driver ──


def test_error_event_routes_to_driver(child, tmp_path):
    """A live turn ending in an ``error`` Event is routed to the driver's
    ``observe`` (the error-observation hook, ADR-001).

    The error's payload reaches the driver verbatim so the classifier can act
    on it; the routing is additive — it does not perturb the log a follower
    reads."""
    mgr = _spy_manager(child)
    try:
        mgr.open("k", _spec(tmp_path))
        off = mgr.send("k", "ERR:429")
        # The error Event lands in the log (a follower sees it).
        evs: list[Event] = []
        for ev in mgr.read("k", since=off, follow=True):
            evs.append(ev)
            if ev.kind == "error":
                break
            if len(evs) > 5:
                break
        assert evs[-1].kind == "error"
        assert evs[-1].error.code == "429"
        # …and that same error reached the driver via the observation hook.
        driver = _SpyDriver.instances[-1]
        assert _wait_for(lambda: len(driver.observed) >= 1)
        routed = driver.observed[-1]
        assert isinstance(routed, EventError)
        assert routed.code == "429"
        assert routed.category == "expected"
    finally:
        mgr.close("k")


# ─── acceptance #2b: a process-death STDIN_BROKEN error is NOT routed ───────


def test_process_death_error_not_routed_to_driver(child, tmp_path):
    """A process-death ``STDIN_BROKEN`` ``error`` Event (the lifecycle's seam)
    is NOT handed to the recovery driver — the no-double-handling rule (TDD
    §3.1 step 1).

    The lifecycle (WP-005) owns restart-on-death; the driver must never also
    act on a death. Asserted directly at the manager's error-observation hook:
    a ``STDIN_BROKEN`` error appended for a session is filtered before the
    driver sees it."""
    mgr = _spy_manager(child)
    try:
        session = mgr.open("k", _spec(tmp_path))
        assert _wait_for(lambda: len(_SpyDriver.instances) >= 1)
        driver = _SpyDriver.instances[-1]
        death_error = Event(
            offset=-1,
            key="k",
            turn=session.turn,
            kind="error",
            error=EventError(
                category="protocol",
                code=STDIN_BROKEN,
                message="session process died before the turn was written",
            ),
        )
        # Drive the error-observation hook directly with the death error.
        mgr._on_error_event(session, death_error)
        # The driver was NOT asked to observe a process-death error.
        assert all(e.code != STDIN_BROKEN for e in driver.observed)
        assert driver.observed == []
    finally:
        mgr.close("k")


# ─── acceptance: non-error events are not routed (the hook is error-only) ───


def test_non_error_events_not_routed_to_driver(child, tmp_path):
    """``chunk`` / ``result`` events from a healthy turn never reach the driver
    — the hook routes ``error``-kind events only (ADR-001 error-event seam)."""
    mgr = _spy_manager(child)
    try:
        mgr.open("k", _spec(tmp_path))
        off = mgr.send("k", "hello")
        evs: list[Event] = []
        for ev in mgr.read("k", since=off, follow=True):
            evs.append(ev)
            if ev.kind == "result":
                break
        assert [e.kind for e in evs] == ["chunk", "result"]
        driver = _SpyDriver.instances[-1]
        # Give any stray routing a beat to land, then assert nothing did.
        time.sleep(0.1)
        assert driver.observed == []
    finally:
        mgr.close("k")


# ─── the turn-cleared reset hook fires on a genuine result ──────────────────


def test_result_event_resets_retry_budget(child, tmp_path):
    """A healthy turn's ``result`` (``turn_complete`` True) fires the driver's
    ``note_turn_cleared`` reset hook — the fire-and-forget ``send`` counterpart
    that ends the accumulated retry sequence so a LATER, unrelated blip gets a
    fresh wall-clock budget (the budget-accumulation reconciliation).

    Proven against the spy: a clean turn drives ``note_turn_cleared`` exactly
    once and routes NOTHING to ``observe`` (a ``result`` is not an error)."""
    mgr = _spy_manager(child)
    try:
        mgr.open("k", _spec(tmp_path))
        off = mgr.send("k", "hello")
        for ev in mgr.read("k", since=off, follow=True):
            if ev.kind == "result":
                break
        driver = _SpyDriver.instances[-1]
        # The result fired the reset hook (the run survived → the budget resets).
        assert _wait_for(lambda: driver.cleared_count >= 1)
        # …and the result was NOT mis-routed to observe (error-only routing).
        assert driver.observed == []
    finally:
        mgr.close("k")


# ─── the guard's on_event observer is NOT clobbered (additive wiring) ───────


def test_guard_still_observes_alongside_recovery(child, tmp_path):
    """Wiring the recovery driver onto the ``on_event`` seam does NOT detach the
    per-turn guard: a healthy turn's ``result`` still completes (the guard's
    watchdog is cancelled, the one-in-flight slot frees) AND the error routing
    works on the SAME session — proving both observers coexist (Blue: the
    WP-007 wiring is additive, the guard's seam is untouched)."""
    mgr = _spy_manager(child)
    try:
        mgr.open("k", _spec(tmp_path))
        # A healthy turn completes (guard observed the result → freed the slot).
        off1 = mgr.send("k", "ok")
        first: list[Event] = []
        for ev in mgr.read("k", since=off1, follow=True):
            first.append(ev)
            if ev.kind == "result":
                break
        assert first[-1].kind == "result"
        # A second turn (the slot was freed → it runs) ends in an error that
        # routes to the driver.
        off2 = mgr.send("k", "ERR:500")
        second: list[Event] = []
        for ev in mgr.read("k", since=off2, follow=True):
            second.append(ev)
            if ev.kind == "error":
                break
        assert second[-1].kind == "error"
        driver = _SpyDriver.instances[-1]
        assert _wait_for(lambda: any(e.code == "500" for e in driver.observed))
    finally:
        mgr.close("k")


# ─── the wired capabilities fire against the REAL driver (no spy) ───────────
#
# The spy tests above prove ROUTING; these prove the manager binds the WP-005
# driver's capabilities correctly — using the *real* RecoveryDriver (default
# factory shape) with an injected no-op sleep + seeded rng so the retry loop is
# deterministic and never really sleeps (MEA-09). They exercise the
# ``send`` / ``log_append`` / ``reauth`` / ``resume`` / ``classify_failure``
# closures the manager builds in ``_make_recovery_driver``.


class _ReauthAdapter(FakeAdapter):
    """A fake adapter whose ``classify_failure`` maps a ``401`` to
    LOGIN_EXPIRED and a ``429`` to TRANSIENT_BLIP, and whose ``reauth`` returns
    a real ticket — so the real driver's login-expiry + retry branches run
    against the manager-bound capabilities."""

    def __init__(self, child: Path) -> None:
        super().__init__(child)
        self.reauth_calls = 0

    def classify_failure(self, error: EventError) -> RecoveryClass | None:
        if error.code == "401":
            return RecoveryClass.LOGIN_EXPIRED
        if error.code == "429":
            return RecoveryClass.TRANSIENT_BLIP
        return None

    def reauth(self):
        from _session_manager.recovery import ReauthTicket

        self.reauth_calls += 1
        return ReauthTicket(relogin_link="https://example/login", completion_handle="h")


def _real_driver_manager(child: Path, adapter: FakeAdapter) -> SessionManager:
    """A manager whose recovery driver is the REAL ``RecoveryDriver`` but with
    a no-op sleep + seeded rng injected, so the retry loop is sleep-free and
    deterministic. Exercises the manager-bound capabilities for real."""
    from _session_manager.recovery import RecoveryDriver

    def factory(**kw):
        kw.setdefault("sleep", lambda _seconds: None)
        kw.setdefault("rng", lambda: 0.0)
        return RecoveryDriver(**kw)

    return SessionManager(
        {"fake": adapter},
        recovery_driver_factory=factory,
        start_maintenance=False,
    )


def test_login_expired_reauth_capability_fires(child, tmp_path):
    """A ``401`` error from a live turn drives the real driver's login-expired
    branch through the manager-bound ``reauth`` capability: the adapter's
    ``reauth`` is called and a ``NOT_AUTHORIZED`` notification is surfaced on
    the existing log via the bound ``log_append`` (ADR-004)."""
    adapter = _ReauthAdapter(child)
    mgr = _real_driver_manager(child, adapter)
    try:
        mgr.open("k", _spec(tmp_path))
        off = mgr.send("k", "ERR:401")
        # Collect the original error + the driver's NOT_AUTHORIZED notification.
        seen_codes: list[str] = []
        for ev in mgr.read("k", since=off, follow=True):
            if ev.kind == "error":
                seen_codes.append(ev.error.code)
            if "NOT_AUTHORIZED" in seen_codes:
                break
            if len(seen_codes) > 4:
                break
        assert adapter.reauth_calls == 1
        assert "NOT_AUTHORIZED" in seen_codes  # surfaced via bound log_append
    finally:
        mgr.close("k")


def test_send_capability_replays_last_command(child, tmp_path):
    """The manager-bound ``send`` capability re-submits *the last recorded
    command* for the key (the stopped turn), not an empty turn — proven by
    firing the bound capability directly on an idle session and observing the
    replayed turn land on the live FIFO.

    Scope note (WP-007 = wiring): this pins that the ``send`` closure is wired
    to replay the right command and reaches the real one-in-flight queue. The
    *end-to-end* transient-blip retry-until-clear round-trip (where the held
    in-flight slot interacts with the retry) is WP-008's integration concern;
    here the capability binding is proven in isolation, with no turn in flight
    so the replayed command promotes immediately."""
    captured: dict[str, object] = {}

    def capture_factory(**kw: object) -> _SpyDriver:
        captured.update(kw)
        return _SpyDriver(**kw)

    mgr = SessionManager(
        {"fake": FakeAdapter(child)},
        recovery_driver_factory=capture_factory,
        start_maintenance=False,
    )
    try:
        mgr.open("k", _spec(tmp_path))
        # Submit a turn and let it complete so the in-flight slot is free and
        # ``_last_command`` is recorded.
        off1 = mgr.send("k", "remember-me")
        for ev in mgr.read("k", since=off1, follow=True):
            if ev.kind == "result":
                break
        assert mgr._last_command["k"] == "remember-me"
        baseline = len(list(mgr.read("k", since=0, follow=False)))
        # Fire the bound ``send`` capability: it must re-enqueue "remember-me".
        assert captured["send"]() is True
        evs: list[Event] = []
        for ev in mgr.read("k", since=baseline, follow=True):
            evs.append(ev)
            if ev.kind == "result":
                break
        text = "".join(e.text for e in evs if e.kind == "chunk")
        assert text == "remember-me"  # the recorded command was replayed verbatim
    finally:
        mgr.close("k")


def test_send_capability_noop_when_no_command_recorded(child, tmp_path):
    """The bound ``send`` capability is a no-op ``False`` ack when nothing has
    been recorded for the key (a retry with nothing to replay) — it never sends
    an empty turn."""
    captured: dict[str, object] = {}

    def capture_factory(**kw: object) -> _SpyDriver:
        captured.update(kw)
        return _SpyDriver(**kw)

    mgr = SessionManager(
        {"fake": FakeAdapter(child)},
        recovery_driver_factory=capture_factory,
        start_maintenance=False,
    )
    try:
        mgr.open("k", _spec(tmp_path))
        # No send() yet → no recorded command → the capability acks False.
        assert "k" not in mgr._last_command
        assert captured["send"]() is False
    finally:
        mgr.close("k")


def test_resume_capability_respawns_session(child, tmp_path):
    """The manager-bound ``resume`` capability triggers the existing same-key/
    same-log restart (``_respawn``) — the driver triggers resume, it does not
    reimplement it (ADR-004 / §2.7 resume-as-capability)."""
    captured: dict[str, object] = {}

    def capture_factory(**kw: object) -> _SpyDriver:
        captured.update(kw)
        return _SpyDriver(**kw)

    mgr = SessionManager(
        {"fake": FakeAdapter(child)},
        recovery_driver_factory=capture_factory,
        start_maintenance=False,
    )
    try:
        session = mgr.open("k", _spec(tmp_path))
        old_pid = session.pid
        # Fire the bound resume capability: it must respawn the SAME session
        # (same key, same log) with a fresh process.
        captured["resume"]()
        assert _wait_for(lambda: session.pid is not None and session.pid != old_pid)
        assert session.pid != old_pid  # a fresh process — the same-key restart
        assert mgr.is_alive(session)
    finally:
        mgr.close("k")


def test_routing_swallows_driver_fault(child, tmp_path):
    """A fault inside the driver's ``observe`` must NOT crash the pump thread
    that fired the event (which would wedge the stdout reader) — the routing is
    best-effort (it runs on an isolated recovery thread that swallows the
    fault). Proven with a driver whose ``observe`` raises: the error still lands
    in the log, the manager's stdout pump stays alive, and the manager remains
    responsive on its side-effect-free surface (``health``)."""

    class _BoomDriver(_SpyDriver):
        def observe(self, error: EventError) -> None:  # type: ignore[override]
            raise RuntimeError("boom in recovery")

    mgr = SessionManager(
        {"fake": FakeAdapter(child)},
        recovery_driver_factory=lambda **kw: _BoomDriver(**kw),
        start_maintenance=False,
    )
    try:
        session = mgr.open("k", _spec(tmp_path))
        # An error routes to the booming driver — the fault is swallowed on the
        # isolated recovery thread; the error itself still lands in the log.
        off1 = mgr.send("k", "ERR:500")
        saw_error = False
        for ev in mgr.read("k", since=off1, follow=True):
            if ev.kind == "error":
                saw_error = True
                break
        assert saw_error
        # Give the recovery thread a beat to raise-and-swallow, then assert the
        # manager is unharmed: the process is still alive and ``health`` (the
        # §2.3 side-effect-free surface) answers — the pump did not crash.
        time.sleep(0.1)
        assert mgr.is_alive(session)
        assert mgr.health("k").alive is True
    finally:
        mgr.close("k")


def test_on_error_event_hook_routes_directly(child, tmp_path):
    """Driving the ``_on_error_event`` hook directly with a routable (non-
    process-death) ``error`` Event hands its payload to the session's driver —
    the deterministic unit-level proof of the hook's happy path (the pump-fired
    path is proven by ``test_error_event_routes_to_driver``)."""
    mgr = _spy_manager(child)
    try:
        session = mgr.open("k", _spec(tmp_path))
        assert _wait_for(lambda: "k" in mgr._recovery_drivers)
        driver = mgr._recovery_drivers["k"]
        err = Event(
            offset=-1,
            key="k",
            turn=session.turn,
            kind="error",
            error=EventError(category="protocol", code="SOCKET_CLOSED", message="x"),
        )
        mgr._on_error_event(session, err)
        assert _wait_for(
            lambda: any(e.code == "SOCKET_CLOSED" for e in driver.observed)
        )
        # Defensive branch: with no driver registered for the key (popped), the
        # hook is a safe no-op — it never raises and routes nothing.
        mgr._recovery_drivers.pop("k", None)
        before = list(driver.observed)
        mgr._on_error_event(session, err)
        time.sleep(0.05)
        assert driver.observed == before  # nothing routed (no driver)
    finally:
        mgr.close("k")


def test_recovery_driver_dropped_on_close(child, tmp_path):
    """``close`` drops the per-session recovery driver + last-command record so
    a long-lived manager accumulates no stale per-key recovery state."""
    mgr = _spy_manager(child)
    mgr.open("k", _spec(tmp_path))
    mgr.send("k", "hello")
    assert _wait_for(lambda: "k" in mgr._recovery_drivers)
    mgr.close("k")
    assert "k" not in mgr._recovery_drivers
    assert "k" not in mgr._last_command


# ── CH-01KTMK hardening FIX 1 — one recovery thread in flight per session ──
#
# ``_on_error_event`` spawned a fresh unbounded daemon thread on EVERY routed
# error Event. A pathological provider emitting a rapid error stream piled up
# sleeping recovery threads (they sleep on the backoff curve) → thread/memory
# exhaustion. The fix gates dispatch on a per-driver in-flight guard
# (``try_begin_recovery`` / ``end_recovery``): at most ONE recovery thread drives
# a session's sequence at a time; a fresh error arriving while a recovery thread
# is already in flight is COALESCED into the existing sequence (the driver's
# ``observe`` already serialises the sequence state under its lock), not given
# its own thread.


class _BlockingDriver(_SpyDriver):
    """A spy whose ``observe`` blocks until released, so a test can hold one
    recovery thread "in flight" and prove that a flood of further errors does
    NOT spawn more threads (they coalesce). Honours the in-flight guard the
    manager calls (``try_begin_recovery`` / ``end_recovery``)."""

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.release = threading.Event()
        self.entered = threading.Event()
        self.concurrent = 0
        self.max_concurrent = 0
        self._in_flight = threading.Event()

    def try_begin_recovery(self) -> bool:
        # One-in-flight guard: the first caller wins; subsequent callers are told
        # to coalesce (return False) until ``end_recovery`` clears the flag.
        with self._lock:
            if self._in_flight.is_set():
                return False
            self._in_flight.set()
            return True

    def end_recovery(self) -> None:
        with self._lock:
            self._in_flight.clear()

    def observe(self, error: EventError) -> None:  # type: ignore[override]
        with self._lock:
            self.concurrent += 1
            self.max_concurrent = max(self.max_concurrent, self.concurrent)
            self.observed.append(error)
        self.entered.set()
        # Block here, holding the recovery thread "in flight", until released.
        self.release.wait(_WAIT)
        with self._lock:
            self.concurrent -= 1


def test_recovery_dispatch_capped_at_one_thread_per_session(child, tmp_path):
    """A flood of routed error events for one session spawns AT MOST ONE recovery
    thread at a time: while a recovery thread is in flight (blocked in
    ``observe``), further errors are COALESCED via the driver's in-flight guard
    rather than each getting its own thread (FIX 1 — bounds the pathological
    thread/memory pile-up).

    Proven against a blocking spy that records peak concurrency: even with many
    rapid ``_on_error_event`` calls, never more than one ``observe`` runs at once,
    and once the in-flight thread is released the guard re-opens for the next."""
    mgr = SessionManager(
        {"fake": FakeAdapter(child)},
        recovery_driver_factory=lambda **kw: _BlockingDriver(**kw),
        start_maintenance=False,
    )
    try:
        session = mgr.open("k", _spec(tmp_path))
        assert _wait_for(lambda: "k" in mgr._recovery_drivers)
        driver = mgr._recovery_drivers["k"]
        assert isinstance(driver, _BlockingDriver)

        err = Event(
            offset=-1,
            key="k",
            turn=session.turn,
            kind="error",
            error=EventError(category="protocol", code="SOCKET_CLOSED", message="x"),
        )
        # Flood the hook: 20 rapid routed errors for the same session.
        for _ in range(20):
            mgr._on_error_event(session, err)

        # One recovery thread entered and is blocked in observe …
        assert driver.entered.wait(_WAIT)
        # … and despite 20 routed errors, no more than one observe ran at a time
        # (the rest coalesced — the guard refused them a thread).
        time.sleep(0.1)  # let any wrongly-spawned thread reach observe
        assert driver.max_concurrent == 1, driver.max_concurrent
        # Release the in-flight thread; the guard re-opens for the next error
        # once that thread finishes and the manager's finally clears the slot.
        driver.entered.clear()
        driver.release.set()
        assert _wait_for(lambda: not driver._in_flight.is_set())
        # A subsequent error now gets a thread again (the guard is not stuck shut).
        driver.release.clear()
        mgr._on_error_event(session, err)
        assert driver.entered.wait(_WAIT)
        driver.release.set()
    finally:
        mgr.close("k")


def test_in_flight_guard_released_after_recovery_completes(child, tmp_path):
    """The in-flight guard is RELEASED when a recovery thread finishes, even if
    the driver's ``observe`` raised — so a single faulting recovery never wedges
    the session's recovery shut forever (FIX 1 — the guard's ``end_recovery``
    runs in a finally on the recovery thread)."""

    class _BoomGuardedDriver(_SpyDriver):
        def __init__(self, **kwargs: object) -> None:
            super().__init__(**kwargs)
            self._in_flight = threading.Event()
            self.ended = 0

        def try_begin_recovery(self) -> bool:
            with self._lock:
                if self._in_flight.is_set():
                    return False
                self._in_flight.set()
                return True

        def end_recovery(self) -> None:
            with self._lock:
                self._in_flight.clear()
                self.ended += 1

        def observe(self, error: EventError) -> None:  # type: ignore[override]
            with self._lock:
                self.observed.append(error)
            raise RuntimeError("boom in recovery")

    mgr = SessionManager(
        {"fake": FakeAdapter(child)},
        recovery_driver_factory=lambda **kw: _BoomGuardedDriver(**kw),
        start_maintenance=False,
    )
    try:
        session = mgr.open("k", _spec(tmp_path))
        assert _wait_for(lambda: "k" in mgr._recovery_drivers)
        driver = mgr._recovery_drivers["k"]
        err = Event(
            offset=-1,
            key="k",
            turn=session.turn,
            kind="error",
            error=EventError(category="protocol", code="SOCKET_CLOSED", message="x"),
        )
        mgr._on_error_event(session, err)
        # The faulting recovery still released the guard (end_recovery ran) …
        assert _wait_for(lambda: driver.ended >= 1)
        # … so a fresh error is dispatched again (the guard was not left shut).
        before = len(driver.observed)
        mgr._on_error_event(session, err)
        assert _wait_for(lambda: len(driver.observed) > before)
    finally:
        mgr.close("k")
