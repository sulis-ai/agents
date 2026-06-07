"""``_session_manager.guards`` — per-turn runaway / timeout guards.

Contract: SESSION_MANAGER_CONTRACT.md §2.7 (runaway / timeout guards) and §2.6
(release the one-in-flight slot). This is the **Armor** primitive that bounds a
*single turn*: a turn exceeding its time budget → ``TERMINATED_TIMEOUT``;
runaway tool-call behaviour (``tool_use`` past a threshold within one turn) →
``TERMINATED_RUNAWAY``. Both surface an ``error`` Event into the log **first**,
then drive the terminal state, so a ``read(follow=True)`` observer sees *why* the
turn ended before the terminal effect. Adapted from the AE ``claude_session.py``
safety-metrics / runaway monitoring (ADR-001), given tests for the first time.

**Why its own module (WPB-04/WPB-07).** The manager (WP-004) exposes a no-op
``_guard`` hook precisely so this logic attaches without swelling the core flow.
:class:`TurnGuardManager` is that logic, injected with the one capability it
needs from the manager — *is this session's process alive?* — while the manager
keeps owning the registry, the six-method surface, and the spawn path. The guard
observes the turn lifecycle through two session callbacks it registers
(``on_turn_start`` / ``on_event``), mirroring the existing ``on_death`` callback
the manager already registers (§ session.py) — so the WP-004 core flow is
untouched: the pumps fire the callbacks they already had the seams for.

**What this owns vs consumes (§ INDEX wave-4 boundary).** This WP owns the
per-turn watchdog (a :class:`threading.Timer` armed when a turn enters EXECUTING,
cancelled on the turn's terminal ``result``) and the per-turn ``tool_use``
counter. On a trip it appends the ``error`` Event and drives the terminal
transition (:meth:`Session.force_terminate_turn`), then kills the child
(:meth:`Session.kill_process`) so the hung / runaway turn actually stops. That
kill's stdout EOF drives WP-005's restart-on-death, and **the restart is what
frees the one-in-flight slot — through the SAME ``_turn_done.set()`` the normal
completion path uses** (:meth:`Session.replace_process`, Blue: no forked
free-the-slot). Freeing the slot *via the restart* rather than inline is
deliberate: an inline free would let the parked stdin pump write the next queued
command into the about-to-be-killed child (a §2.6 wedge), so the slot is released
with fresh pumps, after the restart, so the queue drains onto the live process. A
timeout is thus a *recoverable* terminal, not a permanent disable (§2.7) —
recovery itself is **consumed** from WP-005, not re-implemented here.

**Boring, explicit threading** (§ Green): a real :class:`threading.Timer`, an
integer counter, injected thresholds. No async, no event loop, no clever
cancellation tricks beyond a per-turn generation guard so a timer that fires
after its turn already finished is a no-op.
"""

from __future__ import annotations

import threading
from collections.abc import Callable

from _session_manager.events import Event, EventError
from _session_manager.session import Session
from _session_manager.state import SessionState

# §2.9-style error codes for the two guard trips. Surfaced in the ``error`` Event
# the guard appends so a follower sees the specific cause. Both are **Expected**
# declines (§2.9): the op ran and the manager deterministically ended it for
# exceeding a budget — a consumer adjusts (shorter turn / fewer tools) and
# re-sends; it is not a transport fault (Protocol) nor a bug (Internal).
TURN_TIMEOUT = "TURN_TIMEOUT"
RUNAWAY = "RUNAWAY"

#: Default per-turn time budget, in seconds. Generous + boring: a healthy turn
#: finishes well under it; only a genuinely hung turn (no terminal ``result``)
#: crosses it. Overridable via the manager's ``turn_timeout`` tuning kwarg.
#: Five minutes — a long turn for a warm agent, short enough that a wedged child
#: does not hold the one-in-flight slot indefinitely (§2.6/§2.7).
DEFAULT_TURN_TIMEOUT_SECONDS = 300.0

#: Default per-turn ``tool_use`` ceiling. A healthy turn invokes a handful of
#: tools; a runaway loop emits them without bound. Generous so a legitimately
#: tool-heavy turn is never tripped, finite so a tight tool loop is caught
#: (§2.7). Overridable via the manager's ``max_tool_calls`` tuning kwarg.
DEFAULT_MAX_TOOL_CALLS = 100


class TurnGuardManager:
    """Owns the per-turn runaway + timeout guards for one manager (§2.7).

    Args:
        turn_timeout: per-turn time budget in seconds. A turn whose terminal
            ``result`` has not arrived within this window is timed out.
            Defaults to :data:`DEFAULT_TURN_TIMEOUT_SECONDS`.
        max_tool_calls: the per-turn ``tool_use`` ceiling. A turn emitting more
            than this many ``tool_use`` events is treated as runaway. Defaults to
            :data:`DEFAULT_MAX_TOOL_CALLS`.
        timer_factory: constructs the watchdog timer — injectable so a test can
            substitute a synchronous/controllable timer. Defaults to
            :class:`threading.Timer`. The factory is called as
            ``timer_factory(interval, function)`` and the result must support
            ``start()`` and ``cancel()`` (the :class:`threading.Timer` surface).

    The manager constructs one :class:`TurnGuardManager` and registers its
    per-turn observation callbacks on each session it opens (and re-registers
    after a restart, since ``replace_process`` keeps the same session object).
    """

    def __init__(
        self,
        *,
        turn_timeout: float = DEFAULT_TURN_TIMEOUT_SECONDS,
        max_tool_calls: int = DEFAULT_MAX_TOOL_CALLS,
        timer_factory: Callable[[float, Callable[[], None]], "threading.Timer"]
        | None = None,
    ) -> None:
        if turn_timeout <= 0:
            raise ValueError("turn_timeout must be > 0")
        if max_tool_calls < 1:
            raise ValueError("max_tool_calls must be >= 1")
        self._turn_timeout = float(turn_timeout)
        self._max_tool_calls = int(max_tool_calls)
        self._timer_factory = timer_factory or (
            lambda interval, fn: threading.Timer(interval, fn)
        )
        # Per-session guard state, keyed by the session's identity (the manager
        # holds one Session per key; the guard tracks the in-flight turn on it).
        self._lock = threading.Lock()
        self._state: dict[int, _TurnState] = {}

    @property
    def turn_timeout(self) -> float:
        """The configured per-turn time budget in seconds."""
        return self._turn_timeout

    @property
    def max_tool_calls(self) -> int:
        """The configured per-turn ``tool_use`` ceiling."""
        return self._max_tool_calls

    # ── registration (the manager calls this at open + after restart) ───────

    def attach(self, session: Session) -> None:
        """Register the per-turn observation callbacks on ``session`` (§2.7).

        Wires the guard to the turn lifecycle through the session's
        ``on_turn_start`` / ``on_event`` seams (the same callback shape as the
        existing ``on_death``), so the WP-004 pumps drive the guard without the
        core flow knowing it exists. Idempotent — safe to call again after a
        restart (``replace_process`` keeps the same session object)."""
        session.on_turn_start = self._on_turn_start
        session.on_event = self._on_event

    # ── the turn lifecycle hooks (fired by the session's pumps) ─────────────

    def _on_turn_start(self, session: Session) -> None:
        """A turn just entered EXECUTING: reset the tool counter and arm the
        watchdog timer for this turn (§2.7). A per-turn generation tag lets a
        timer that fires *after* its turn already finished recognise itself as
        stale and no-op (the cancel-vs-fire race is benign)."""
        with self._lock:
            prior = self._state.pop(id(session), None)
            if prior is not None:
                prior.timer.cancel()
            generation = (prior.generation + 1) if prior is not None else 0
            timer = self._timer_factory(
                self._turn_timeout,
                lambda: self._on_timeout(session, generation),
            )
            self._state[id(session)] = _TurnState(generation=generation, timer=timer)
        timer.start()

    def _on_event(self, session: Session, event: Event) -> None:
        """Observe one appended event for the in-flight turn (§2.7).

        - a terminal ``result`` (the turn completed normally) → cancel the
          watchdog and drop the per-turn state (no trip);
        - a ``tool_use`` → increment the per-turn counter; if it exceeds the
          ceiling, trip the runaway guard;
        - an ``error`` (the turn already failed, e.g. a mid-turn death surfaced
          by WP-005) → cancel the watchdog and drop the state (the failure path
          owns it; the guard must not also trip).
        """
        if event.kind == "result" or event.kind == "error":
            self._clear(session)
            return
        if event.kind != "tool_use":
            return
        trip = False
        with self._lock:
            state = self._state.get(id(session))
            if state is None:
                return
            state.tool_calls += 1
            if state.tool_calls > self._max_tool_calls:
                # Disarm before tripping so the watchdog can't also fire.
                state.timer.cancel()
                self._state.pop(id(session), None)
                trip = True
        if trip:
            self._trip(
                session,
                terminal=SessionState.TERMINATED_RUNAWAY,
                code=RUNAWAY,
                message=(
                    f"turn emitted more than {self._max_tool_calls} tool calls; "
                    f"terminated as runaway"
                ),
            )

    def _on_timeout(self, session: Session, generation: int) -> None:
        """The watchdog fired: the in-flight turn exceeded its time budget
        (§2.7). Trip the timeout guard — unless this is a stale timer for a turn
        that already finished (the generation no longer matches), in which case
        it is a benign no-op (the cancel-vs-fire race)."""
        with self._lock:
            state = self._state.get(id(session))
            if state is None or state.generation != generation:
                return  # stale timer for an already-finished turn — no-op
            self._state.pop(id(session), None)
        self._trip(
            session,
            terminal=SessionState.TERMINATED_TIMEOUT,
            code=TURN_TIMEOUT,
            message=(
                f"turn exceeded its {self._turn_timeout:g}s time budget; "
                f"terminated as timeout"
            ),
        )

    # ── the trip: surface the error, drive terminal state, kill → restart ───

    def _trip(
        self,
        session: Session,
        *,
        terminal: SessionState,
        code: str,
        message: str,
    ) -> None:
        """End the misbehaving turn (§2.7).

        Order matters and is the contract: append the ``error`` Event **first**
        (so a follower sees the cause), then drive ``EXECUTING → terminal`` — both
        via :meth:`Session.force_terminate_turn`, which appends-then-transitions.
        Finally kill the child (:meth:`Session.kill_process`) so the hung /
        runaway process actually stops; its stdout EOF drives WP-005's
        restart-on-death, which frees the one-in-flight slot through the **same**
        ``_turn_done.set()`` the normal completion path uses (with fresh pumps, so
        a queued send drains onto the live process — §2.6, Blue: no forked
        free-the-slot), making a timeout a *recoverable* terminal rather than a
        permanent disable (§2.7). Best-effort: a session already terminating /
        a closed log is ignored (the trip raced a deliberate close)."""
        error = Event(
            offset=-1,
            key=session.key,
            turn=session.turn,
            kind="error",
            error=EventError(category="expected", code=code, message=message),
        )
        session.force_terminate_turn(terminal=terminal, error=error)
        session.kill_process()

    def _clear(self, session: Session) -> None:
        """Cancel + drop the in-flight turn's guard state (turn finished)."""
        with self._lock:
            state = self._state.pop(id(session), None)
        if state is not None:
            state.timer.cancel()

    def detach(self, session: Session) -> None:
        """Drop any guard state for ``session`` (called when it is closed) so a
        long-lived manager does not accumulate stale per-session entries."""
        self._clear(session)


class _TurnState:
    """Mutable per-turn guard state for one session: the armed watchdog timer,
    the ``tool_use`` count so far, and a generation tag so a timer that fires
    after its turn finished recognises itself as stale (the cancel-vs-fire
    race). A plain class (not a frozen dataclass) because the counter mutates
    every ``tool_use``; tiny + private to this module."""

    __slots__ = ("generation", "timer", "tool_calls")

    def __init__(self, *, generation: int, timer: "threading.Timer") -> None:
        self.generation = generation
        self.timer = timer
        self.tool_calls = 0
