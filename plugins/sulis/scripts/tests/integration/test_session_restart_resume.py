"""WP-005 — session state machine + restart-on-death + resume-as-capability.

Contract: SESSION_MANAGER_CONTRACT.md §2.7 (resume-as-capability + the internal
state machine) and §2.10 #6 (death + restart → ``error`` event then
continuation). This WP is the **Armor** primitive for process lifecycle: the
manager owns the state machine (consumers never touch it), restarts a dead
process under the **same key / same log**, and resumes prior context **only
where the provider's capability allows** — with an honest ``Session.resumed``.

Verification posture (INDEX, MEA-09): **real threaded behaviour against a real
scripted child the test can kill** — no mocked death, no mocked manager state.
The child is a deterministic python program (no real ``claude`` — that is
WP-009's job) that emits recorded NDJSON and can be made to die on cue (exit
mid-turn, or be SIGKILLed by the test). Death *detection* consumes WP-004's
``is_alive``; this WP owns *recovery* (DEAD → restart → resume).

Every threaded assertion uses a short bounded wait so a genuine hang fails the
test quickly rather than blocking CI.
"""

from __future__ import annotations

import json
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from _session_manager.adapter import Capabilities, SessionSpec
from _session_manager.event_log import OffsetOutOfRangeError
from _session_manager.events import (
    SESSION_DISABLED,
    Event,
    ExpectedError,
    TurnResult,
)
from _session_manager.lifecycle import LifecycleManager
from _session_manager.manager import SessionManager
from _session_manager.state import SessionState, StateMachine

# Bounded wait for threaded assertions: long enough never to flake on a loaded
# CI runner, short enough that a real hang fails fast.
_WAIT = 5.0


# ─── the scripted child the test can kill (real subprocess, real decode) ───
#
# The child reads NDJSON turns from stdin. Each turn carries a ``command`` and
# an optional ``die`` directive that makes the child kill itself — either
# before any output (``die=before``), after one chunk but before the result
# (``die=mid``), or never (the normal happy turn). A child that dies leaves the
# manager's stdout pump at EOF with a non-zero ``poll()`` — exactly the
# real-world unexpected-exit shape restart-on-death must handle.
#
# The child writes its own resume marker to a sidecar file when spawned with a
# ``--resumed`` flag, so a test can assert the *restarted* process actually
# carried the resume flag in its argv (proving §2.7 resume-on-restart) without
# reaching into the manager's internals.

_CHILD_SOURCE = r"""
import json, os, sys, time

# argv: child.py <delay> [<resume_marker_path> if spawned with --resume]
delay = float(sys.argv[1]) if len(sys.argv) > 1 else 0.0
# The adapter appends a resume marker path as the final argv entry only when
# the spawn carried a resume ref; its presence is how the test proves the
# restarted process was spawned resume-capable.
resume_marker = None
for i, a in enumerate(sys.argv):
    if a == "--resumed" and i + 1 < len(sys.argv):
        resume_marker = sys.argv[i + 1]
if resume_marker:
    with open(resume_marker, "a") as fh:
        fh.write("spawned-with-resume\n")

def emit(obj):
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()

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
    die = msg.get("die")
    turn += 1
    time.sleep(delay)
    if die == "before":
        os._exit(137)  # unexpected death before any output
    emit({"kind": "chunk", "text": text[:3]})
    if die == "mid":
        os._exit(137)  # unexpected death mid-turn (chunk emitted, no result)
    emit({"kind": "chunk", "text": text[3:]})
    emit({"kind": "result", "input_tokens": 1, "output_tokens": len(text),
          "duration_ms": 1, "stop_reason": "end_turn"})
"""


def _write_child(tmp_path: Path) -> Path:
    p = tmp_path / "child.py"
    p.write_text(_CHILD_SOURCE)
    return p


class FakeAdapter:
    """A real :class:`ProviderAdapter` over the killable scripted child.

    ``capabilities.supports_resume`` is configurable so the same child drives
    both the resume-capable and resume-incapable §2.7 cases. When a session is
    spawned with a resume ref AND this adapter supports resume, ``spawn_argv``
    appends ``--resumed <marker>``; the child writes to that marker so a test
    can prove the (restarted) process was spawned resume-capable.
    """

    def __init__(
        self,
        child: Path,
        *,
        supports_resume: bool,
        delay: float = 0.0,
        resume_marker: Path | None = None,
    ) -> None:
        self._child = child
        self._delay = delay
        self._resume_marker = resume_marker
        self.capabilities = Capabilities(
            supports_resume=supports_resume,
            supports_tools=False,
            supports_partial_streaming=True,
        )

    def spawn_argv(self, spec: SessionSpec) -> list[str]:
        argv = [sys.executable, str(self._child), str(self._delay)]
        if spec.resume_ref and self.capabilities.supports_resume:
            marker = str(self._resume_marker) if self._resume_marker else "/dev/null"
            argv += ["--resumed", marker]
        return argv

    def encode(self, command: str) -> bytes:
        # A command may carry a ``::die=<mode>`` suffix the test uses to make
        # the child die on cue; strip it into the NDJSON ``die`` directive.
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


@pytest.fixture
def child(tmp_path) -> Path:
    return _write_child(tmp_path)


def _manager(
    child: Path,
    *,
    supports_resume: bool,
    delay: float = 0.0,
    resume_marker: Path | None = None,
    recovery_budget: int | None = None,
) -> SessionManager:
    adapter = FakeAdapter(
        child,
        supports_resume=supports_resume,
        delay=delay,
        resume_marker=resume_marker,
    )
    # No background maintenance loop: these tests exercise the EOF-driven
    # restart-on-death path, not the maintenance tick. A loop ticking on its own
    # interval adds thread-scheduling nondeterminism under a loaded suite (it
    # contends for the GIL with the pumps + the restart handoff) and can race the
    # very deaths these tests drive — so disable it, matching WP-006/007 which
    # drive the tick synchronously instead (MEA-09 determinism).
    tuning: dict = {"start_maintenance": False}
    if recovery_budget is not None:
        tuning["recovery_budget"] = recovery_budget
    return SessionManager({"fake": adapter}, **tuning)


def _spec(tmp_path: Path, resume_ref: str | None = None) -> SessionSpec:
    return SessionSpec(provider="fake", cwd=str(tmp_path), resume_ref=resume_ref)


def _wait_for(predicate, timeout: float = _WAIT) -> bool:
    """Poll ``predicate`` until true or timeout. Returns whether it became
    true. Used to wait on real threaded transitions without a fixed sleep."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


def _kill_and_reap(session) -> None:
    """Kill the session's child AND reap it before returning — the deterministic
    way for a test to take a live child out from under the manager.

    A bare ``process.kill()`` is not enough on a loaded host: right after a
    ``kill()`` the OS may not have reaped the child yet, so ``process.poll()``
    (which is what ``SessionManager.is_alive`` reads) can still report ``None``
    for a beat. The EOF-driven ``on_death`` then fires and restart-on-death's
    first step *confirms* the death via ``is_alive`` — and if it races the
    not-yet-reaped corpse it reads "alive", treats the signal as spurious, and
    declines the restart, stranding the session (the 1-in-N flake these tests
    exhibited under full-suite load).

    The product code's own guard-kill path (:meth:`Session.kill_process`) reaps
    for exactly this reason; a test that kills the child manually must do the
    same so ``poll()`` deterministically reports the death before the lifecycle
    confirms it. ``wait()`` is bounded so a wedged kill fails the test fast
    rather than hanging. This makes the death itself deterministic — it does
    **not** weaken any assertion about the restart that follows."""
    proc = session.process
    proc.kill()
    try:
        proc.wait(timeout=_WAIT)
    except subprocess.TimeoutExpired:  # pragma: no cover — a wedged kill
        pass


def _collect(mgr, key, since, *, count, timeout=_WAIT):
    """Follow-read ``count`` events (or until timeout) from ``since``."""
    out: list[Event] = []
    deadline = time.monotonic() + timeout
    for ev in mgr.read(key, since=since, follow=True):
        out.append(ev)
        if len(out) >= count or time.monotonic() > deadline:
            break
    return out


# ─── resume-as-capability at first open (§2.7 honesty) ─────────────────────


def test_open_resumes_when_capability_true(child, tmp_path):
    """Adapter ``supports_resume=True`` + a ``resume_ref`` → ``Session.resumed``
    is True and the resume flag is in the spawned argv (§2.7)."""
    marker = tmp_path / "resume_marker.txt"
    mgr = _manager(child, supports_resume=True, resume_marker=marker)
    try:
        s = mgr.open("k", _spec(tmp_path, resume_ref="prior-transcript"))
        assert s.resumed is True
        # The child wrote the resume marker → it was spawned resume-capable.
        assert _wait_for(lambda: marker.exists())
        assert "spawned-with-resume" in marker.read_text()
    finally:
        mgr.close("k")


def test_open_starts_fresh_when_capability_false(child, tmp_path):
    """Adapter ``supports_resume=False`` + a ``resume_ref`` set → starts fresh,
    ``Session.resumed`` is False (honest — never synthesise continuity a
    provider can't give, §2.7)."""
    marker = tmp_path / "resume_marker.txt"
    mgr = _manager(child, supports_resume=False, resume_marker=marker)
    try:
        s = mgr.open("k", _spec(tmp_path, resume_ref="prior-transcript"))
        assert s.resumed is False
        # Even though a ref was supplied, the incapable adapter never resumes.
        time.sleep(0.1)
        assert not marker.exists()
    finally:
        mgr.close("k")


def test_open_no_resume_ref_starts_fresh(child, tmp_path):
    """No ``resume_ref`` → fresh, ``resumed`` False even on a resume-capable
    adapter (§2.7: resume requires BOTH capability AND a ref)."""
    mgr = _manager(child, supports_resume=True)
    try:
        s = mgr.open("k", _spec(tmp_path, resume_ref=None))
        assert s.resumed is False
    finally:
        mgr.close("k")


# ─── restart-on-death: same key, same log (§2.7 restart-is-not-new-key) ─────


def test_process_death_restarts_same_key_same_log(child, tmp_path):
    """Kill the child mid-session; the manager restarts it; the log offset keeps
    CLIMBING (not reset) and a ``read(since=0)`` still has the pre-death events
    — proving the restart reuses the same key + same log (§2.7)."""
    mgr = _manager(child, supports_resume=True)
    try:
        first = mgr.open("k", _spec(tmp_path, resume_ref="t"))
        first_pid = first.pid
        # One clean turn so the log has real pre-death events.
        off = mgr.send("k", "hello")
        evs = _collect(mgr, "k", off, count=3)
        assert [e.kind for e in evs] == ["chunk", "chunk", "result"]
        pre_death_max = evs[-1].offset

        # Now kill the live child out from under the manager (kill + reap, so
        # poll() deterministically reports the death before restart-on-death
        # confirms it — see _kill_and_reap).
        _kill_and_reap(first)
        # The manager must detect death and restart (new pid, same key).
        assert _wait_for(
            lambda: mgr.health("k").alive and mgr.health("k").pid != first_pid
        )
        restarted_pid = mgr.health("k").pid
        assert restarted_pid != first_pid

        # The pre-death events are STILL readable from offset 0 (same log).
        history = list(mgr.read("k", since=0, follow=False))
        assert len(history) >= 3
        assert history[-1].offset == pre_death_max

        # A post-restart turn lands at a CLIMBING offset, not reset to 0.
        off2 = mgr.send("k", "world")
        assert off2 > pre_death_max
        evs2 = _collect(mgr, "k", off2, count=3)
        assert [e.kind for e in evs2] == ["chunk", "chunk", "result"]
    finally:
        mgr.close("k")


def test_death_mid_turn_surfaces_error_then_continues(child, tmp_path):
    """Kill mid-turn: an ``error`` Event appears in the log, THEN the restarted
    session accepts a new turn that streams to completion (§2.7 death+restart,
    contract §2.10 #6). A ``read(follow=True)`` sees the failure then the
    continuation."""
    mgr = _manager(child, supports_resume=True)
    try:
        first = mgr.open("k", _spec(tmp_path, resume_ref="t"))
        first_pid = first.pid
        # This turn emits one chunk then the child dies before the result.
        off = mgr.send("k", "abcdef::die=mid")

        # Read follow from the send offset: we must see the chunk, then an
        # ``error`` event the restart surfaced (the turn never completed).
        seen: list[Event] = []

        def _has_error() -> bool:
            try:
                events = list(mgr.read("k", since=off, follow=False))
            except OffsetOutOfRangeError:
                return False  # nothing has landed yet; keep waiting
            return any(ev.kind == "error" for ev in events)

        assert _wait_for(_has_error, timeout=_WAIT), (
            "no error event surfaced after mid-turn death"
        )
        seen = list(mgr.read("k", since=off, follow=False))
        kinds = [e.kind for e in seen]
        assert "chunk" in kinds  # the partial output before death
        assert "error" in kinds  # the surfaced failure (§2.10 #6)

        # The session restarted (new pid) and accepts a fresh turn that
        # completes — the conversation continues after the crash.
        assert _wait_for(
            lambda: mgr.health("k").alive and mgr.health("k").pid != first_pid
        )
        off2 = mgr.send("k", "ghijkl")
        evs2 = _collect(mgr, "k", off2, count=3)
        assert [e.kind for e in evs2][-1] == "result"
    finally:
        mgr.close("k")


def test_restart_resumes_context_when_capable(child, tmp_path):
    """After a restart with a resume-capable adapter, the restarted process is
    spawned WITH the resume flag (§2.7 restart resumes from transcript where
    capability allows). Proven via the child's resume marker, written only when
    the resume flag is in argv."""
    marker = tmp_path / "resume_marker.txt"
    mgr = _manager(child, supports_resume=True, resume_marker=marker)
    try:
        first = mgr.open("k", _spec(tmp_path, resume_ref="prior-transcript"))
        first_pid = first.pid
        # First spawn already carried resume → one marker line.
        assert _wait_for(
            lambda: (
                marker.exists() and marker.read_text().count("spawned-with-resume") >= 1
            )
        )

        # Kill it (kill + reap for a deterministic death); the restart must ALSO
        # be spawned resume-capable.
        _kill_and_reap(first)
        assert _wait_for(
            lambda: mgr.health("k").alive and mgr.health("k").pid != first_pid
        )
        # Two marker lines now: the original spawn + the restart spawn.
        assert _wait_for(lambda: marker.read_text().count("spawned-with-resume") >= 2)
    finally:
        mgr.close("k")


def test_send_during_death_window_never_hangs(child, tmp_path):
    """A ``send`` issued in the narrow window between a death and its detection
    must never leave a follower hanging (§2.6 + §2.9 STDIN_BROKEN).

    Regression for two restart-handoff races: (a) a dying-generation stdin pump
    that pulled the command must RE-QUEUE it rather than drop it (which would
    hang the caller's ``submit``); (b) a write that fails because the process
    already died must surface a turn-terminal ``error`` event so a follower from
    the send offset sees the failure instead of waiting forever. Either way the
    follower TERMINATES — on a ``result`` (restarted process ran it) or an
    ``error`` (the death-window turn failed).
    """
    mgr = _manager(child, supports_resume=True)
    try:
        first = mgr.open("k", _spec(tmp_path, resume_ref="t"))
        first.process.kill()
        # send() must return a landing offset within the bounded wait (the
        # command is never dropped): run it on a watchdog thread so a hang fails
        # the test fast instead of blocking CI.
        result: dict = {}

        def _do_send():
            result["offset"] = mgr.send("k", "after-kill")

        t = threading.Thread(target=_do_send, daemon=True)
        t.start()
        t.join(_WAIT)
        assert not t.is_alive(), "send() hung in the death window (command dropped)"
        assert "offset" in result

        # The follower from the send offset TERMINATES on a turn-terminal event
        # — a result (restarted process ran the turn) or an error (the
        # death-window turn failed) — never hangs.
        terminal: list[str] = []
        deadline = time.monotonic() + _WAIT
        for ev in mgr.read("k", since=result["offset"], follow=True):
            if ev.kind in ("result", "error"):
                terminal.append(ev.kind)
                break
            if time.monotonic() > deadline:
                break
        assert terminal, "follower never saw a terminal event (it hung)"
        assert terminal[0] in ("result", "error")
    finally:
        mgr.close("k")


# ─── recovery budget: exhaustion → PERMANENTLY_DISABLED (§2.7) ──────────────


def test_recovery_budget_exhaustion_disables(child, tmp_path):
    """Force consecutive deaths past the recovery budget → the session reaches
    ``PERMANENTLY_DISABLED``; a subsequent ``send`` raises Expected
    ``SESSION_DISABLED`` (§2.7 recovery budget)."""
    # Budget of 2 restarts: the 3rd death exhausts recovery.
    mgr = _manager(child, supports_resume=True, recovery_budget=2)
    try:
        sess = mgr.open("k", _spec(tmp_path, resume_ref="t"))

        def _disabled() -> bool:
            return sess.state_machine.state is SessionState.PERMANENTLY_DISABLED

        # Drive consecutive deaths deterministically: each iteration kills (and
        # REAPS) the *current* live child, then waits for the manager to settle
        # the death — either by restarting it (a fresh live pid under the same
        # key) or, once the budget is spent, by disabling it. Synchronising on
        # that settled outcome before the next kill (instead of a blind
        # ``sleep(0.15)``) removes two flakes the loaded suite exposed: killing a
        # process mid-restart, and the outer deadline expiring before the budget
        # was driven to exhaustion (restart spawn is slower under load than a
        # fixed sleep guessed).
        for _ in range(mgr._lifecycle.recovery_budget + 2):
            if _disabled():
                break
            pid_before = sess.process.pid
            _kill_and_reap(sess)
            # The death is now certain (reaped). Wait for the manager to either
            # restart onto a fresh live pid or disable the session.
            assert _wait_for(
                lambda pid=pid_before: (
                    _disabled()
                    or (mgr.health("k").alive and mgr.health("k").pid != pid)
                )
            ), "manager neither restarted nor disabled the session after a death"

        assert _disabled(), (
            "session never reached PERMANENTLY_DISABLED after budget exhaustion"
        )
        # A send on a disabled session is an Expected SESSION_DISABLED decline.
        with pytest.raises(ExpectedError) as exc:
            mgr.send("k", "after-disabled")
        assert exc.value.code == SESSION_DISABLED
    finally:
        mgr.close("k")


# ─── the state machine is ENFORCED, not advisory (§2.7) ────────────────────


def test_state_transitions_follow_machine():
    """The allowed-transitions map is the single source of legality: legal
    transitions succeed; an illegal transition is REJECTED (the machine is
    enforced, not advisory). §2.7."""
    sm = StateMachine()
    # Starts INITIALIZING.
    assert sm.state is SessionState.INITIALIZING
    # Legal normal turn cycle: INITIALIZING → READY → EXECUTING → READY.
    sm.transition(SessionState.READY)
    assert sm.state is SessionState.READY
    sm.transition(SessionState.EXECUTING)
    assert sm.state is SessionState.EXECUTING
    sm.transition(SessionState.READY)
    assert sm.state is SessionState.READY
    # Legal death path: READY → DEAD → INITIALIZING (restart).
    sm.transition(SessionState.DEAD)
    sm.transition(SessionState.INITIALIZING)
    assert sm.state is SessionState.INITIALIZING

    # Illegal: you cannot jump straight from INITIALIZING to EXECUTING.
    with pytest.raises(ValueError):
        sm.transition(SessionState.EXECUTING)
    # The rejected transition did not move the machine.
    assert sm.state is SessionState.INITIALIZING

    # Legal recovery-exhausted path: DEAD → PERMANENTLY_DISABLED is terminal.
    sm.transition(SessionState.READY)
    sm.transition(SessionState.DEAD)
    sm.transition(SessionState.PERMANENTLY_DISABLED)
    assert sm.state is SessionState.PERMANENTLY_DISABLED
    # Terminal: no transition out of PERMANENTLY_DISABLED.
    with pytest.raises(ValueError):
        sm.transition(SessionState.READY)


# ─── lifecycle guards: spurious signal no-op + budget validation (§2.7) ─────


def test_spurious_death_signal_is_noop(child, tmp_path):
    """A death signal for a still-LIVE process is a no-op (the signal was
    spurious, or a racing signal already restarted): the manager does not
    restart and the live session is untouched (§2.7 confirm-before-recover)."""
    mgr = _manager(child, supports_resume=True)
    try:
        s = mgr.open("k", _spec(tmp_path, resume_ref="t"))
        live_pid = s.pid
        assert mgr.is_alive(s)
        # Fire the hook directly while the process is still alive.
        mgr._on_process_death(s)
        # No restart happened: same pid, still READY, no recovery consumed.
        assert mgr.health("k").pid == live_pid
        assert s.recovery_used == 0
        assert s.state_machine.state is SessionState.READY
    finally:
        mgr.close("k")


def test_negative_recovery_budget_rejected():
    """A negative recovery budget is a programming error — rejected at
    construction (§2.7 boring, explicit validation)."""
    with pytest.raises(ValueError):
        LifecycleManager(recovery_budget=-1)
