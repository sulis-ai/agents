"""``_session_manager.lifecycle`` — restart-on-death + resume + recovery budget.

Contract: SESSION_MANAGER_CONTRACT.md §2.7 (the manager-owned lifecycle:
restart-on-death, resume-as-capability, recovery budget → PERMANENTLY_DISABLED)
and §2.10 #6 (a death mid-turn surfaces an ``error`` Event into the log
before/around the restart). This is the **Armor** primitive for process
lifecycle.

**Why its own module (WPB-04/WPB-07).** The manager (WP-004) exposes a no-op
``_on_process_death`` hook precisely so this recovery logic attaches without
swelling the core flow. :class:`LifecycleManager` is that logic, injected with
the two capabilities it needs from the manager — *spawn a fresh process for a
spec* and *append an Event to a session's log* — so it owns recovery while the
manager keeps owning the registry, the six-method surface, and the
``is_alive`` liveness primitive it consumes here.

**What this owns vs consumes (§ INDEX liveness ownership).** This WP owns
*recovery* (DEAD → restart → resume → READY, or DEAD → PERMANENTLY_DISABLED).
It **consumes** WP-004's ``is_alive`` for death *detection* (it does not
re-implement the poll) and WP-003's adapter ``capabilities.supports_resume``
for the resume decision (it never assumes resume).

**The state machine is the single source of legality.** Every lifecycle step
moves the session's :class:`~_session_manager.state.StateMachine` through a
*legal* transition; an illegal one raises rather than silently corrupting the
session's state.
"""

from __future__ import annotations

import threading

from _session_manager.events import (
    STDIN_BROKEN,
    Event,
    EventError,
)
from _session_manager.session import Session
from _session_manager.state import SessionState

# The default number of consecutive restarts a session may attempt before it is
# permanently disabled. A finite budget so a child that crashes on every spawn
# (a poison spec, a broken binary) is taken out of rotation instead of
# restart-looping forever (§2.7 recovery budget). Conservative + boring: a small
# integer, overridable via the manager's ``recovery_budget`` tuning kwarg.
DEFAULT_RECOVERY_BUDGET = 3


class LifecycleManager:
    """Owns restart-on-death + resume + recovery-budget for one manager (§2.7).

    Args:
        recovery_budget: how many consecutive restarts a session may attempt
            before reaching :data:`SessionState.PERMANENTLY_DISABLED`. Defaults
            to :data:`DEFAULT_RECOVERY_BUDGET`.

    The manager constructs one :class:`LifecycleManager` and routes its
    ``_on_process_death`` hook to :meth:`on_process_death`. Per-session restart
    accounting lives on the :class:`Session` (``recovery_used``) so concurrent
    sessions never share a budget.
    """

    def __init__(self, recovery_budget: int = DEFAULT_RECOVERY_BUDGET) -> None:
        if recovery_budget < 0:
            raise ValueError("recovery_budget must be >= 0")
        self._recovery_budget = recovery_budget
        # Serialises restart handling so two death signals for the same session
        # (e.g. the stdout pump's EOF and a future WP-006 maintenance poll)
        # cannot both restart it — the second observes the already-restarted
        # live process and no-ops.
        self._lock = threading.Lock()

    @property
    def recovery_budget(self) -> int:
        """The configured per-session restart budget."""
        return self._recovery_budget

    def on_process_death(
        self,
        session: Session,
        *,
        is_alive,
        respawn,
    ) -> None:
        """Handle a detected process death for ``session`` (§2.7).

        Steps, all under the per-manager restart lock so a doubly-signalled
        death restarts at most once:

        1. **Confirm death.** Consume WP-004's ``is_alive`` — if the process is
           actually live (a spurious signal, or already restarted by a racing
           signal), do nothing.
        2. **Surface a mid-turn failure.** If a turn was in flight when the
           process died (no terminal ``result`` freed the slot), append an
           ``error`` Event so a ``read(follow=True)`` sees the failure before
           the continuation (§2.10 #6).
        3. **DEAD.** Move the state machine to ``DEAD``.
        4. **Budget check.** If the recovery budget is exhausted →
           ``PERMANENTLY_DISABLED`` and stop (a subsequent ``send`` declines
           with ``SESSION_DISABLED``). Otherwise:
        5. **Restart.** ``respawn`` a fresh process for the session's spec
           (resume-capable iff the adapter supports it AND a ref exists — the
           ``respawn`` callback owns that decision), swap it into the session
           **keeping the same key + same log**, restart the pumps, and move the
           machine ``DEAD → INITIALIZING → READY``. Increment ``recovery_used``.

        Args:
            session: the session whose process died.
            is_alive: WP-004's liveness predicate, ``is_alive(session) -> bool``.
            respawn: a callback ``respawn(session) -> None`` that spawns a fresh
                process for the session's spec and swaps it in (the manager owns
                ``Popen`` + the resume-flag decision; lifecycle orchestrates).
        """
        with self._lock:
            current = session.state_machine.state
            # Already permanently disabled — nothing to recover.
            if current is SessionState.PERMANENTLY_DISABLED:
                return
            # A guard terminal (WP-007 runaway / timeout) is an *intentional*
            # kill: the death is certain, so do NOT consult ``is_alive`` here.
            # ``process.poll()`` can still read "alive" for a beat after the
            # SIGKILL while the OS reaps, and on a loaded host that race let the
            # confirm step below bail — stranding the session in ``TERMINATED_*``
            # with no restart (the 1-in-N recoverable-timeout flake). For a guard
            # terminal we know exactly why the process is gone; proceed straight
            # to recovery (§2.7 — a guard terminal is recoverable within budget).
            guard_terminal = current in (
                SessionState.TERMINATED_TIMEOUT,
                SessionState.TERMINATED_RUNAWAY,
            )
            # 1. Confirm: outside a guard terminal, a live process means the
            #    signal was spurious or a racing signal already restarted it.
            if not guard_terminal and is_alive(session):
                return

            # 2. A turn in flight at death → surface the failure (§2.10 #6).
            self._surface_mid_turn_error(session)

            # 3. DEAD.
            session.mark_dead()

            # 4. Budget exhausted → permanently disabled, no restart.
            if session.recovery_used >= self._recovery_budget:
                session.to_state(SessionState.PERMANENTLY_DISABLED)
                return

            # 5. Restart: same key, same log; resume if capable (respawn owns
            #    the flag). The state machine walks DEAD → INITIALIZING → READY.
            session.to_state(SessionState.INITIALIZING)
            session.recovery_used += 1
            respawn(session)
            session.to_state(SessionState.READY)

    @staticmethod
    def _surface_mid_turn_error(session: Session) -> None:
        """Append an ``error`` Event iff a turn was in flight at death (§2.10 #6).

        "In flight" is the value the stdout pump snapshotted at EOF
        (:meth:`Session.died_mid_turn`) — captured *before* the slot was freed,
        so it survives the pump's own slot-release. The error is appended with
        the session's current turn so a follower from the send offset sees the
        partial output, then this failure, then (after restart) the continuation.

        **WP-007 boundary:** a turn killed by the runaway / timeout guard is
        already in a ``TERMINATED_*`` state and the guard has already surfaced the
        specific ``RUNAWAY`` / ``TURN_TIMEOUT`` error. The death this restart is
        recovering from is that guard's own kill, so a second generic
        "died mid-turn" error would be redundant — skip it (the guard's error is
        the cause; this path only adds the restart). Recovery itself still
        proceeds (mark_dead → restart) so a guard terminal is recoverable (§2.7).
        """
        if session.state_machine.state in (
            SessionState.TERMINATED_TIMEOUT,
            SessionState.TERMINATED_RUNAWAY,
        ):
            return
        if session.died_mid_turn():
            error = Event(
                offset=-1,
                key=session.key,
                turn=session.turn,
                kind="error",
                error=EventError(
                    category="protocol",
                    code=STDIN_BROKEN,
                    message="session process died mid-turn; restarting",
                ),
            )
            session.log.append(error)
