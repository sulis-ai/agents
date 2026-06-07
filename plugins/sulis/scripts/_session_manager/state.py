"""``_session_manager.state`` — the manager's side-effect-free snapshot types.

Contract: SESSION_MANAGER_CONTRACT.md §2.3 (``Health`` for ``health(key)`` and
``SessionStatus`` for ``status()``). These are *observational* value objects:
small, frozen dataclasses the manager builds on demand from a session's live
state. They are deliberately separate from the event vocabulary in
``events.py`` — an :class:`~_session_manager.events.Event` is a record *in* the
log; a :class:`Health` / :class:`SessionStatus` is a *view of* a session, never
logged. Keeping them in their own module keeps ``events.py`` the pure Form
invariant (§2.3) and gives the manager's observational surface its own home
(the contract offered events.py OR a state.py; state.py is chosen so the two
concerns do not bleed into one module).

Frozen because a snapshot is a value, not a handle: the caller gets the state
as it was at the call, and a later change does not mutate a snapshot it already
holds.

**Dependency direction (WPB-01, inward-only).** This module imports nothing
from the manager, the session, or any subprocess/IO machinery — those depend on
it, never the reverse.

**The session state machine (WP-005, §2.7).** :class:`SessionState` is the full
lifecycle enum the contract's §2.7 diagram defines; :class:`StateMachine` is the
**single source of legality** — an explicit allowed-transitions map that is
*enforced*, not advisory (an illegal transition raises rather than silently
mis-stating the session's state). The manager owns one machine per session;
consumers never touch it. WP-007's terminal-state transitions (TIMEOUT /
RUNAWAY) are added to *this same map* (§ Blue), never a parallel one.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal


class SessionState(Enum):
    """The lifecycle states of one warm session (contract §2.7 diagram).

    ``INITIALIZING`` — process spawned (or re-spawned after death), not yet
    ready for a turn. ``READY`` — idle, awaiting a turn. ``EXECUTING`` — a turn
    is in flight. ``ERROR`` — a turn failed; recovery may return it to READY or
    end it in a terminal state. ``DEAD`` — the process exited unexpectedly;
    restart-on-death drives it back to INITIALIZING (or, once recovery is
    exhausted, to PERMANENTLY_DISABLED). The ``TERMINATED_*`` states are the
    turn-guard terminals WP-007 fills (declared here so the one transition map
    is complete); ``PERMANENTLY_DISABLED`` is the recovery-exhausted terminal
    this WP owns.
    """

    INITIALIZING = "initializing"
    READY = "ready"
    EXECUTING = "executing"
    ERROR = "error"
    DEAD = "dead"
    TERMINATED_TIMEOUT = "terminated_timeout"
    TERMINATED_RUNAWAY = "terminated_runaway"
    PERMANENTLY_DISABLED = "permanently_disabled"


# The single source of legality (§2.7). Each key maps to the states it may
# transition *to*. A state absent from a source's set is an illegal target and
# raises. Terminal states map to the empty set: nothing leaves them. WP-007
# adds its TERMINATED_* edges to THIS table (the Blue invariant), never a
# parallel one — so there is exactly one place the machine's legality lives.
_ALLOWED_TRANSITIONS: dict[SessionState, frozenset[SessionState]] = {
    # Spawn / re-spawn → ready; or the spawn itself died.
    SessionState.INITIALIZING: frozenset({SessionState.READY, SessionState.DEAD}),
    # Idle: a turn starts, or the process dies between turns.
    SessionState.READY: frozenset({SessionState.EXECUTING, SessionState.DEAD}),
    # A turn in flight: it completes (→READY), errors, the process dies, or a
    # turn-guard (WP-007) terminates it.
    SessionState.EXECUTING: frozenset(
        {
            SessionState.READY,
            SessionState.ERROR,
            SessionState.DEAD,
            SessionState.TERMINATED_TIMEOUT,
            SessionState.TERMINATED_RUNAWAY,
        }
    ),
    # A failed turn: recovery returns it to READY, or it ends terminally.
    SessionState.ERROR: frozenset(
        {
            SessionState.READY,
            SessionState.DEAD,
            SessionState.TERMINATED_TIMEOUT,
            SessionState.TERMINATED_RUNAWAY,
        }
    ),
    # Dead process: restart-on-death re-initialises it, or recovery is
    # exhausted and it is permanently disabled.
    SessionState.DEAD: frozenset(
        {SessionState.INITIALIZING, SessionState.PERMANENTLY_DISABLED}
    ),
    # Turn-guard terminals (WP-007) are *recoverable*: the guard kills the
    # misbehaving child to actually stop the hung / runaway turn, and the
    # resulting stdout EOF drives WP-005's restart-on-death (DEAD → restart). So
    # each turn-guard terminal may move to DEAD — a single timeout / runaway is a
    # recoverable terminal within the recovery budget, not a permanent disable
    # (§2.7; WP-007 Contract). The TERMINATED_* → DEAD edges are added to THIS
    # same map (the Blue invariant), never a parallel one. Recovery exhaustion
    # still ends at PERMANENTLY_DISABLED via the DEAD branch above.
    SessionState.TERMINATED_TIMEOUT: frozenset({SessionState.DEAD}),
    SessionState.TERMINATED_RUNAWAY: frozenset({SessionState.DEAD}),
    # PERMANENTLY_DISABLED is the one truly terminal state — nothing leaves it.
    SessionState.PERMANENTLY_DISABLED: frozenset(),
}


class StateMachine:
    """The enforced session state machine (§2.7).

    A fresh machine starts in :data:`SessionState.INITIALIZING`.
    :meth:`transition` consults :data:`_ALLOWED_TRANSITIONS` — the single
    source of legality — and either advances the state or raises
    :class:`ValueError` for an illegal move, leaving the state unchanged. The
    machine is *enforced*, not advisory: an illegal transition is a programming
    error surfaced loudly, not a silently-accepted bad state.
    """

    def __init__(self, initial: SessionState = SessionState.INITIALIZING) -> None:
        self._state = initial

    @property
    def state(self) -> SessionState:
        """The current lifecycle state."""
        return self._state

    def can_transition(self, target: SessionState) -> bool:
        """Whether moving to ``target`` from the current state is legal."""
        return target in _ALLOWED_TRANSITIONS.get(self._state, frozenset())

    def transition(self, target: SessionState) -> None:
        """Move to ``target`` if legal; otherwise raise :class:`ValueError`.

        On an illegal transition the state is left unchanged so the caller's
        view of the session does not drift from reality (§2.7 enforced)."""
        if not self.can_transition(target):
            raise ValueError(
                f"illegal session-state transition: "
                f"{self._state.value!r} → {target.value!r}"
            )
        self._state = target


@dataclass(frozen=True)
class Health:
    """Liveness + identity for one session (§2.3, returned by ``health(key)``).

    ``alive`` is the WP-004-owned ``is_alive`` verdict for the session's
    process; ``state`` is the session's lifecycle label — the
    :class:`SessionState` value the WP-005 state machine currently holds
    (``"ready"`` / ``"executing"`` / ``"dead"`` / ``"permanently_disabled"`` /
    …); ``pid`` is the OS process id (``None`` once the process is gone);
    ``provider`` is the adapter key the session was opened with.

    ``io_mode`` + ``viewer_count`` (NEW, additive, defaulted — contract §2.12.5)
    make visible/headless observable without a new method: ``io_mode`` is
    ``"pipe"`` (the chat path) or ``"pty"`` (a terminal), and ``viewer_count`` is
    the number of attached viewers — ``> 0`` ⇔ visible, ``0`` ⇔ headless. Both
    default so an existing pipe-session ``Health`` is byte-unchanged (acceptance
    #4): a pipe session reads ``io_mode="pipe"``, ``viewer_count=0``.
    """

    alive: bool
    state: str
    pid: int | None
    provider: str
    io_mode: Literal["pipe", "pty"] = "pipe"
    viewer_count: int = 0


@dataclass(frozen=True)
class SessionStatus:
    """One row of ``status()`` — a snapshot of one session (§2.3).

    ``memory_bytes`` is the session process's resident memory; it is ``0`` until
    WP-006 wires the memory-cap measurement (the field exists now so WP-006 adds
    no signature churn). ``last_activity`` is a monotonic-clock timestamp of the
    session's most recent send/append; ``log_len`` is the number of events
    retained in the session's log.

    ``io_mode`` + ``viewer_count`` (NEW, additive, defaulted — contract §2.12.5)
    mirror :class:`Health`: ``io_mode`` is the session's io-model and
    ``viewer_count`` is its attached-viewer count (``> 0`` ⇔ visible). Both
    default so an existing pipe-session ``SessionStatus`` snapshot is byte-
    unchanged (acceptance #4).
    """

    key: str
    state: str
    pid: int | None
    provider: str
    memory_bytes: int
    last_activity: float
    log_len: int
    io_mode: Literal["pipe", "pty"] = "pipe"
    viewer_count: int = 0
