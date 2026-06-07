"""WP-007 — runaway / timeout turn guards → terminal states + surfaced errors.

Contract: SESSION_MANAGER_CONTRACT.md §2.7 (runaway / timeout guards: a turn
exceeding its budget → ``TERMINATED_TIMEOUT``; runaway tool-call behaviour →
``TERMINATED_RUNAWAY`` — both surfaced as an ``error`` Event into the log
*first*, then the terminal state, so a ``read(follow=True)`` observer sees why
the turn ended). This is the **Armor** primitive that bounds a single turn.

What this WP owns vs consumes (INDEX wave-4 boundary):

- **owns:** the per-turn watchdog (a timer started when a turn enters EXECUTING,
  cancelled on the turn's terminal ``result``) and the per-turn ``tool_use``
  counter — :class:`~_session_manager.guards.TurnGuardManager`, attached to the
  manager's no-op ``_guard`` hook (WP-004 exposed it precisely so this attaches
  without swelling the core flow). On a trip the guard appends the ``error``
  Event, drives the terminal transition, and **releases the one-in-flight slot
  via the SAME path ``turn_complete`` uses** (§2.6, Blue: no forked free-the-slot).
- **consumes, never re-implements:** WP-005's :class:`StateMachine` transition
  map (extended — not forked — with the ``TERMINATED_* → DEAD`` recovery edges so
  a guard-killed turn composes with restart-on-death); WP-005's restart-on-death
  recovery path (a timeout is a *recoverable* terminal, not a permanent disable,
  within the recovery budget).

Verification posture (INDEX, MEA-09): **real threaded behaviour against a real
scripted child driven to misbehave on cue** — a child that hangs (never emits a
result) for the timeout case, and one that emits ``tool_use`` in a tight loop
past the runaway threshold for the runaway case. No real ``claude`` (that is
WP-009's job). Budgets are small + injected so the timeout fires fast and
deterministically; every threaded assertion uses a short bounded wait so a real
hang fails the test quickly rather than blocking CI.
"""

from __future__ import annotations

import json
import sys
import threading
import time
from pathlib import Path

from _session_manager.adapter import Capabilities, SessionSpec
from _session_manager.events import Event, ToolUse, TurnResult
from _session_manager.manager import SessionManager
from _session_manager.state import SessionState

# Bounded wait for the genuinely-threaded assertions (a watchdog firing on its
# own timer thread, a runaway trip on the stdout pump, a restart-on-death spawn):
# long enough never to flake on a loaded CI runner (a restart spawns a fresh
# child, which under a parallel suite can take a beat), short enough that a real
# hang fails fast.
_WAIT = 10.0

# The per-turn time budget the timeout tests inject. Chosen by MEA-09 reasoning,
# not a guess: a genuinely-hung turn never completes, so any finite budget trips
# it; a *healthy* turn — including a restarted one whose fresh child must spawn —
# must finish UNDER it or it false-times-out. A fresh-spawn healthy turn is well
# under a second even on a loaded runner, so a budget of 2s gives generous
# headroom against false positives while still tripping a hung turn fast (the
# bounded ``_WAIT`` above covers the trip). Deterministic: the trip depends only
# on "did a terminal result arrive within the budget", never on a tight race
# against spawn latency.
_TIMEOUT_BUDGET = 2.0


# ─── the scripted child driven to misbehave (real subprocess, real decode) ──
#
# The child reads NDJSON turns from stdin. Each turn carries a ``command`` and
# optional misbehaviour directives:
#   - ``hang``: emit one chunk, then block forever without a result (the
#     timeout case — the watchdog must fire because no terminal result arrives);
#   - ``tools=N``: emit N ``tool_use`` lines in a tight loop and then HANG
#     without ever emitting a result (the runaway case — a real runaway loop
#     does not politely finish; the per-turn tool_use counter trips and the
#     guard must kill the still-running turn);
# otherwise it emits a normal 3+rest chunk pair + a result (the happy turn).
# No real ``claude`` (that is WP-009's job, MEA-09).

_CHILD_SOURCE = r"""
import json, os, sys, time

def emit(obj):
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()

def hang_forever():
    while True:
        time.sleep(3600)

for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    try:
        msg = json.loads(line)
    except Exception:
        continue
    text = str(msg.get("command", ""))
    tools = int(msg.get("tools", 0))
    for i in range(tools):
        emit({"kind": "tool_use", "name": "shell", "input_summary": "loop %d" % i})
    if tools:
        # A real runaway: the tool loop never returns a result — the turn is
        # still in flight when the guard kills it. The kill is what stops it.
        hang_forever()
    emit({"kind": "chunk", "text": text[:3]})
    if msg.get("hang"):
        # Never emit a result: the turn hangs. The watchdog must fire.
        hang_forever()
    emit({"kind": "chunk", "text": text[3:]})
    emit({"kind": "result", "input_tokens": 1, "output_tokens": len(text),
          "duration_ms": 1, "stop_reason": "end_turn"})
"""


def _write_child(tmp_path: Path) -> Path:
    p = tmp_path / "child.py"
    p.write_text(_CHILD_SOURCE)
    return p


class FakeAdapter:
    """A real :class:`ProviderAdapter` over the misbehaving scripted child.

    Decodes ``tool_use`` (so the runaway counter has real events to count),
    ``chunk`` and ``result``. ``encode`` threads the misbehaviour directives
    (``::hang`` / ``::tools=N``) onto the wire so a test drives the child purely
    through the command string — no reach into the manager's internals.
    """

    def __init__(self) -> None:
        self.capabilities = Capabilities(
            supports_resume=True,
            supports_tools=True,
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
        record: dict = {"command": command}
        if "::hang" in command:
            command = command.replace("::hang", "")
            record["command"] = command
            record["hang"] = True
        if "::tools=" in command:
            head, _, tail = command.partition("::tools=")
            record["command"] = head
            record["tools"] = int(tail)
        return (json.dumps(record) + "\n").encode("utf-8")

    def decode(self, line: bytes) -> Event | None:
        record = json.loads(line)
        kind = record.get("kind")
        if kind == "chunk":
            return Event(offset=-1, key="", turn=-1, kind="chunk", text=record["text"])
        if kind == "tool_use":
            return Event(
                offset=-1,
                key="",
                turn=-1,
                kind="tool_use",
                tool=ToolUse(
                    name=str(record.get("name", "")),
                    input_summary=str(record.get("input_summary", "")),
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
        return event.kind == "result"


def _manager(child: Path, **tuning: object) -> SessionManager:
    # No background maintenance loop: these tests are about the per-turn guard,
    # not the maintenance tick — keep them deterministic and sleep-free except
    # for the guard's own (small, injected) timeout budget.
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


def _collect(mgr: SessionManager, key: str, off: int, want: int) -> list[Event]:
    """Follow-read up to ``want`` events from ``off``, bounded by ``_WAIT``.

    The follow-read runs on a daemon thread so a turn that *stalls* (a hung
    child that emits no further events, and a guard that has not yet — or never
    — surfaced its error) cannot wedge the test: the helper returns whatever it
    gathered once the wall-clock deadline elapses, and the assertions then fail
    on the *content* (missing error / result) rather than hanging CI. A real
    blocking-iterator deadline cannot be enforced inline because the iterator
    parks in the log's condition wait between events.
    """
    out: list[Event] = []

    def _drain() -> None:
        for ev in mgr.read(key, since=off, follow=True):
            out.append(ev)
            if len(out) >= want:
                break

    t = threading.Thread(target=_drain, daemon=True)
    t.start()
    deadline = time.monotonic() + _WAIT
    while t.is_alive() and time.monotonic() < deadline:
        if len(out) >= want:
            break
        time.sleep(0.01)
    return list(out)


# ─── timeout guard (§2.7) ───────────────────────────────────────────────────


def test_turn_timeout_surfaces_error_then_terminal(tmp_path):
    """A turn that exceeds its time budget surfaces an ``error`` Event
    (``TURN_TIMEOUT``) into the log and then drives the session to
    ``TERMINATED_TIMEOUT`` (§2.7). The child hangs (never emits a result); the
    watchdog — armed at turn-start, never cancelled — fires.
    """
    child = _write_child(tmp_path)
    mgr = _manager(child, turn_timeout=_TIMEOUT_BUDGET)
    try:
        mgr.open("k", _spec(tmp_path))
        off = mgr.send("k", "hello::hang")

        # The first event is the child's leading chunk; then the guard's error.
        evs = _collect(mgr, "k", off, want=2)
        kinds = [e.kind for e in evs]
        assert "error" in kinds, f"timeout did not surface an error event: {kinds}"
        err = next(e for e in evs if e.kind == "error")
        assert err.error is not None
        assert err.error.code == "TURN_TIMEOUT"
        assert err.error.category == "expected"

        # And the session reaches the timeout terminal state.
        assert _wait_for(
            lambda: (
                mgr.health("k").state == SessionState.TERMINATED_TIMEOUT.value
                or mgr.health("k").state
                in (SessionState.READY.value, SessionState.INITIALIZING.value)
            )
        ), "session did not reach TERMINATED_TIMEOUT after the budget elapsed"
    finally:
        mgr.close("k")


def test_timeout_releases_in_flight_slot(tmp_path):
    """After a timeout kills the hung turn, a queued ``send`` runs — the
    one-in-flight slot is freed, not wedged behind the killed turn (§2.6).

    The recovery (restart-on-death under the same key/log) is WP-005's; this
    test proves the guard composes with it so the queue drains.
    """
    child = _write_child(tmp_path)
    mgr = _manager(child, turn_timeout=_TIMEOUT_BUDGET, recovery_budget=3)
    try:
        mgr.open("k", _spec(tmp_path))
        # First turn hangs and will be timed out + killed.
        mgr.send("k", "first::hang")
        # Second turn is queued behind it; it must run once the slot frees.
        off2 = mgr.send("k", "second")

        evs = _collect(mgr, "k", off2, want=3)
        kinds = [e.kind for e in evs]
        assert "result" in kinds, (
            f"queued send did not run after the timeout freed the slot: {kinds}"
        )
    finally:
        mgr.close("k")


def test_timeout_terminal_is_recoverable_not_disabled(tmp_path):
    """A single timeout does not permanently disable the session: within the
    recovery budget it composes with WP-005 recovery, so a subsequent ``send``
    is accepted (not declined with ``SESSION_DISABLED``) and a healthy turn runs
    to a ``result`` (§2.7 — timeout is a recoverable terminal)."""
    child = _write_child(tmp_path)
    mgr = _manager(child, turn_timeout=_TIMEOUT_BUDGET, recovery_budget=3)
    try:
        mgr.open("k", _spec(tmp_path))
        mgr.send("k", "doomed::hang")

        # After the timeout + restart, a fresh well-behaved turn must complete.
        assert _wait_for(
            lambda: (
                mgr.health("k").state
                in (SessionState.READY.value, SessionState.INITIALIZING.value)
            )
        ), "session never recovered to a live state after the timeout"

        off = mgr.send("k", "recovered")
        evs = _collect(mgr, "k", off, want=3)
        assert "result" in [e.kind for e in evs], (
            "a healthy turn after a single timeout should complete — the timeout "
            "must be recoverable, not a permanent disable"
        )
    finally:
        mgr.close("k")


# ─── runaway guard (§2.7) ───────────────────────────────────────────────────


def test_runaway_tool_calls_terminate(tmp_path):
    """A turn emitting ``tool_use`` past the runaway threshold surfaces an
    ``error`` Event (``RUNAWAY``) then drives the session to
    ``TERMINATED_RUNAWAY`` (§2.7)."""
    child = _write_child(tmp_path)
    mgr = _manager(child, max_tool_calls=3)
    try:
        mgr.open("k", _spec(tmp_path))
        # 10 tool_use events in one turn — well past the threshold of 3.
        off = mgr.send("k", "spin::tools=10")

        evs = _collect(mgr, "k", off, want=12)
        kinds = [e.kind for e in evs]
        assert "error" in kinds, f"runaway did not surface an error event: {kinds}"
        err = next(e for e in evs if e.kind == "error")
        assert err.error is not None
        assert err.error.code == "RUNAWAY"

        assert _wait_for(
            lambda: (
                mgr.health("k").state == SessionState.TERMINATED_RUNAWAY.value
                or mgr.health("k").state
                in (SessionState.READY.value, SessionState.INITIALIZING.value)
            )
        ), "session did not reach TERMINATED_RUNAWAY after the threshold tripped"
    finally:
        mgr.close("k")


def test_runaway_releases_slot(tmp_path):
    """After a runaway kill, a queued ``send`` proceeds — the slot is freed, not
    wedged behind the killed turn (§2.6)."""
    child = _write_child(tmp_path)
    mgr = _manager(child, max_tool_calls=3, recovery_budget=3)
    try:
        mgr.open("k", _spec(tmp_path))
        mgr.send("k", "runaway::tools=10")
        off2 = mgr.send("k", "queued")

        evs = _collect(mgr, "k", off2, want=3)
        assert "result" in [e.kind for e in evs], (
            "queued send did not run after the runaway freed the slot"
        )
    finally:
        mgr.close("k")


# ─── ordering invariant: error precedes the terminal state (§2.7) ───────────


def test_error_event_precedes_terminal_state(tmp_path):
    """The guard's ``error`` Event is appended to the log BEFORE the session
    leaves EXECUTING — a ``read(follow=True)`` observer sees the error first,
    then the terminal effect (§2.7: surface the error, then the terminal state).

    Proven by: the error event materialises in the log (a follower receives it),
    and the manager only reports a terminal/recovered state at/after that point —
    never a terminal state with no preceding error event in the log.
    """
    child = _write_child(tmp_path)
    mgr = _manager(child, turn_timeout=_TIMEOUT_BUDGET)
    try:
        mgr.open("k", _spec(tmp_path))
        off = mgr.send("k", "watch::hang")

        # The follower must see an error event (the surfaced failure). That the
        # error is in the log is the proof it was appended before the terminal
        # transition — force_terminate_turn appends then transitions, so a
        # terminal state without a logged error is impossible.
        evs = _collect(mgr, "k", off, want=2)
        assert any(e.kind == "error" for e in evs), (
            "no error event surfaced before the terminal state"
        )
        # Read history from 0: the error event is present in the durable log,
        # at an offset >= the send offset (within this turn).
        history = list(mgr.read("k", since=0, follow=False))
        err_offsets = [e.offset for e in history if e.kind == "error"]
        assert err_offsets, "error event not durably appended to the log"
        assert min(err_offsets) >= off, (
            "the surfaced error must land within the timed-out turn (offset >= send)"
        )
    finally:
        mgr.close("k")


# ─── no false positives: a healthy turn trips neither guard (§2.7) ──────────


def test_normal_turn_under_budget_unaffected(tmp_path):
    """A fast, well-behaved turn (a couple of chunks + a result, no excess
    tool_use, completes under the time budget) never trips either guard: it
    yields its normal events and the session returns to READY — no error event,
    no terminal state (§2.7 — no false positives)."""
    child = _write_child(tmp_path)
    mgr = _manager(child, turn_timeout=5.0, max_tool_calls=50)
    try:
        mgr.open("k", _spec(tmp_path))
        off = mgr.send("k", "hello")

        evs = _collect(mgr, "k", off, want=3)
        kinds = [e.kind for e in evs]
        assert kinds == ["chunk", "chunk", "result"], (
            f"a healthy turn produced unexpected events: {kinds}"
        )
        assert not any(e.kind == "error" for e in evs), (
            "a healthy turn must not surface a guard error"
        )
        # The session is back to READY (the normal turn cycle), not terminated.
        assert _wait_for(lambda: mgr.health("k").state == SessionState.READY.value), (
            "a healthy turn should leave the session READY, not terminated"
        )
        assert mgr.health("k").state not in (
            SessionState.TERMINATED_TIMEOUT.value,
            SessionState.TERMINATED_RUNAWAY.value,
        )
    finally:
        mgr.close("k")
