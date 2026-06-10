"""``_session_manager.session`` — one warm, long-lived agent session.

Contract: SESSION_MANAGER_CONTRACT.md §2.2 (a ``Session`` holds the process +
log + per-key queue), §2.5 (the log it appends to), §2.6 (one-in-flight per
key: a FIFO queue drained one turn at a time, the slot freed by the adapter's
``turn_complete``).

A :class:`Session` is the unit the :class:`~_session_manager.manager.Session\
Manager` owns one of per caller key. It composes the merged foundation:

- a WP-001 :class:`~_session_manager.event_log.EventLog` — the append-only,
  offset-addressed record stream readers follow;
- a WP-003 :class:`~_session_manager.adapter.ProviderAdapter` — the only
  agent-specific surface (how to spawn / encode / decode / detect turn-done);
- a real subprocess + **three pump threads** adapted from the AE terminal-pool
  I/O-thread shape (``stdin_writer`` / ``stdout_reader`` / ``stderr_reader``),
  re-shaped so the stdout reader **decodes each line via the adapter and
  appends the resulting Event to the log**.

**The decoupling invariant (§2.2, load-bearing).** :meth:`submit` returns the
log offset where the turn's first event will land and enqueues the command — it
does NOT wait for any reply event. Reading content is the log's job
(``EventLog.read``); the session never bundles send with read.

**One-in-flight per key (§2.6).** A single FIFO ``queue.Queue`` holds pending
commands; the stdin pump pulls **one** command, writes it, and then blocks until
the stdout pump signals the in-flight turn finished (the adapter's
``turn_complete`` fired) before pulling the next. So at most one turn is in
flight for this session; different sessions (different keys) run in parallel
because each owns its own threads, queue, and lock.

**Liveness is the manager's** (§ WP-004 ownership): the session exposes its
process handle; :meth:`SessionManager.is_alive` is the single liveness check.
The session does not re-implement it.

**Restart-on-death (WP-005, §2.7).** The session carries its own
:class:`~_session_manager.state.StateMachine` (the manager owns it, consumers
never touch it) and an ``on_death`` callback the manager registers. When the
stdout pump reaches EOF on a process that was *not* deliberately closed, it
fires ``on_death`` once — an event-driven death signal that lets the manager's
restart-on-death logic (WP-005's :class:`~_session_manager.lifecycle.\
LifecycleManager`) run. Restart **reuses the same log + same key**
(:meth:`replace_process`): the conversation survives the crash (§2.7
restart-is-not-a-new-key). Death *detection* still consumes WP-004's
``is_alive``; this signal is just the prompt to check.
"""

from __future__ import annotations

import dataclasses
import os
import queue
import subprocess
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from _session_manager.adapter import ProviderAdapter, SessionSpec
from _session_manager.event_log import EventLog
from _session_manager.events import STDIN_BROKEN, Event, EventError
from _session_manager.scrollback import ScrollbackBuffer
from _session_manager.state import SessionState, StateMachine

# Sentinel pushed onto the command queue to tell the stdin pump to stop. A
# distinct object (not None / not a str) so it can never collide with a real
# command (which is always a str).
_STOP = object()

# Sentinel pushed by :meth:`Session.replace_process` to UNBLOCK a stale stdin
# pump parked on the command queue, so it can notice the generation bump and
# exit. Unlike _STOP, a _WAKE never terminates the *current* pump: a current-gen
# pump that pulls a leftover _WAKE simply discards it and loops. This keeps a
# restart's wake-up from accidentally stopping the fresh pump (which _STOP
# would).
_WAKE = object()

# How long close() waits for the child to exit after SIGTERM before SIGKILL.
_TERM_GRACE_SECONDS = 2.0
# How long close() waits to join each pump thread before giving up (pumps exit
# promptly once the streams close; the bound stops a wedged pump hanging close).
_JOIN_TIMEOUT_SECONDS = 2.0


@dataclass
class Session:
    """One warm session: process + pumps + log + per-key in-flight queue.

    Constructed via :meth:`SessionManager.open`; not instantiated directly by
    consumers. The dataclass holds the durable per-session state the contract
    enumerates (key, spec, log, process, queue, lock, ``resumed``, ``turn``);
    the threads and synchronisation live here too but are private.
    """

    key: str
    spec: SessionSpec
    adapter: ProviderAdapter
    log: EventLog
    process: subprocess.Popen
    #: PTY io-model (contract §2.12.1, ADR-001), set by the manager at spawn for a
    #: ``pty``-mode session and ``None`` for the default pipe model. When set, the
    #: session runs ONE master-reader pump (in place of the three pipe pumps) that
    #: reads the master fd and appends raw bytes into ``scrollback`` — the
    #: terminal content model (§2.11), distinct from the decoded ``log`` (§2.5).
    #: ``pty_master_fd`` is the manager-owned master end of the ``os.openpty()``
    #: pair (the child holds the slave end as its controlling tty); ``scrollback``
    #: is the bounded byte ring a viewer (WP-004) later snapshots. Both are
    #: re-created together on restart (:meth:`replace_process`), keeping the
    #: scrollback across the restart (§2.12.3 restart-is-not-a-new-key).
    pty_master_fd: int | None = None
    scrollback: ScrollbackBuffer | None = None
    resumed: bool = False
    #: Monotonic per-key turn counter — incremented as each submitted turn
    #: starts so every appended Event carries which turn produced it (§2.3).
    turn: int = 0
    #: When the session was last active (a send arrived or an event appended) —
    #: monotonic clock, feeds SessionStatus.last_activity (§2.3).
    last_activity: float = field(default_factory=time.monotonic)
    #: The manager-owned lifecycle state machine (§2.7). One per session;
    #: consumers never touch it. The manager walks it INITIALIZING → READY as
    #: ``open`` finishes, READY ↔ EXECUTING per turn, and through the
    #: DEAD/restart path on death (WP-005).
    state_machine: StateMachine = field(default_factory=StateMachine, repr=False)
    #: How many consecutive restarts this session has used — the recovery-budget
    #: counter WP-005's lifecycle increments per restart; exhaustion disables the
    #: session (§2.7).
    recovery_used: int = 0
    #: Registered by the manager: ``on_death(session)`` is fired once by the
    #: stdout pump when it reaches EOF on a process that was not deliberately
    #: closed (the event-driven death signal, §2.7). ``None`` until registered.
    on_death: "Callable[[Session], None] | None" = field(default=None, repr=False)
    #: Registered by the manager (WP-007 guards): ``on_turn_start(session)`` is
    #: fired by the stdin pump the instant a turn enters EXECUTING — the seam the
    #: per-turn watchdog arms on (§2.7). Mirrors ``on_death``; ``None`` until
    #: registered, so WP-004's core flow is untouched when no guard is attached.
    on_turn_start: "Callable[[Session], None] | None" = field(default=None, repr=False)
    #: Registered by the manager (WP-007 guards): ``on_event(session, event)`` is
    #: fired by the stdout pump for every event it appends — the seam the runaway
    #: counter + the watchdog-cancel observe (§2.7). Mirrors ``on_death``;
    #: ``None`` until registered.
    on_event: "Callable[[Session, Event], None] | None" = field(
        default=None, repr=False
    )
    #: Registered by the manager (WP-004 viewers): ``on_pty_output(data)`` is
    #: fired by the master-reader pump for every raw byte chunk it appends to
    #: ``scrollback`` — the live-feed broadcast seam the per-session viewer
    #: registry subscribes to so each attached viewer's ``stream`` receives live
    #: PTY output (contract §2.12.2; acceptance #1). Mirrors ``on_event``:
    #: ``None`` until registered, so a pty session with no viewers (headless) is
    #: untouched — the pump still fills the scrollback ring, it just broadcasts to
    #: nobody. Carried across restart on the same Session (the registry is wired
    #: once at spawn; §2.12.3).
    on_pty_output: "Callable[[bytes], None] | None" = field(default=None, repr=False)

    # ── private synchronisation + threads (not part of the value surface) ──
    _commands: "queue.Queue" = field(default_factory=queue.Queue, repr=False)
    #: Set by the stdout pump when the in-flight turn's terminal event arrived;
    #: the stdin pump waits on it before pulling the next queued command (§2.6).
    _turn_done: threading.Event = field(default_factory=threading.Event, repr=False)
    #: Set by the stdout pump the instant its process's stdout reaches EOF (the
    #: process ended — normal exit, unexpected death, or a guard kill). The stdin
    #: pump, woken from its in-flight wait, checks this BEFORE pulling/writing the
    #: next command: a reliable "the process is gone" signal that does NOT race
    #: ``process.poll()`` (which can still read ``None`` for a beat after a kill
    #: while the OS reaps). On a set flag the stdin pump exits without writing, so
    #: a queued command is never written into a corpse — the restart's fresh pump
    #: owns the queue (§2.6/§2.7). Cleared on :meth:`replace_process`.
    _process_ended: threading.Event = field(default_factory=threading.Event, repr=False)
    #: Guards turn/last_activity mutation shared between submit (caller thread)
    #: and the pumps.
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _threads: list = field(default_factory=list, repr=False)
    _closing: bool = field(default=False, repr=False)
    #: Set once the stdout pump has fired ``on_death`` for the *current*
    #: process, so a single EOF cannot trigger two restart signals. Cleared on
    #: :meth:`replace_process` when a fresh process + fresh pumps take over.
    _death_signalled: bool = field(default=False, repr=False)
    #: Monotonic pump generation. Each spawn (initial + every restart) bumps it;
    #: a pump bound to a stale generation exits rather than touching the new
    #: process — the clean handoff that makes restart-on-death race-free (§2.7).
    _generation: int = field(default=0, repr=False)
    #: Snapshotted by the stdout pump at EOF — whether a turn was in flight when
    #: the process died. Captured BEFORE the pump frees the in-flight slot, so
    #: the lifecycle can still tell a mid-turn death (which needs an ``error``
    #: event, §2.10 #6) from an idle-between-turns death (which does not).
    _died_mid_turn: bool = field(default=False, repr=False)

    def __post_init__(self) -> None:
        # An idle session has no turn in flight: set the turn-done event so
        # ``turn_in_flight()`` reads False until the first turn actually starts
        # (the stdin pump clears it). Without this a death detected before any
        # send would spuriously surface a mid-turn error (§2.10 #6).
        self._turn_done.set()

    # ── lifecycle: start / stop the pumps ──────────────────────────────────

    def start_pumps(self) -> None:
        """Launch the I/O pump threads for the current process (§2.6).

        Daemon threads so a hard interpreter exit never hangs on a wedged pump;
        :meth:`close` joins them cleanly in the normal path. Each pump is bound
        to the process + generation live at launch, so after a restart the old
        pumps drain their dead streams and exit while the new pumps own the new
        process.

        Branches on the io-model (contract §2.12.1, ADR-001): a ``pty`` session
        (``pty_master_fd`` set) runs the single generation-bound master-reader
        pump that appends raw terminal bytes to ``scrollback``; the default pipe
        session runs today's three pipe pumps (stdin / stdout / stderr) unchanged.
        """
        if self.pty_master_fd is not None:
            self._start_pty_pumps()
            return
        process = self.process
        generation = self._generation
        self._threads = [
            threading.Thread(
                target=self._stdin_pump,
                args=(process, generation),
                name=f"session-{self.key}-stdin-{generation}",
                daemon=True,
            ),
            threading.Thread(
                target=self._stdout_pump,
                args=(process, generation),
                name=f"session-{self.key}-stdout-{generation}",
                daemon=True,
            ),
            threading.Thread(
                target=self._stderr_pump,
                args=(process,),
                name=f"session-{self.key}-stderr-{generation}",
                daemon=True,
            ),
        ]
        for t in self._threads:
            t.start()

    def _start_pty_pumps(self) -> None:
        """Launch the single master-reader pump for a ``pty`` session (§2.12.1).

        A PTY multiplexes the child's stdin/stdout/stderr onto one master fd, so
        the pipe model's three pumps collapse into one generation-bound reader.
        It mirrors the stdout pump's generation discipline (a stale-generation
        pump exits rather than touching the new process) so restart-on-death
        (§2.7/§2.12.3) is race-free for pty sessions too. Daemon so a hard exit
        never hangs on it.
        """
        master_fd = self.pty_master_fd
        assert master_fd is not None  # only called for a pty session
        process = self.process
        generation = self._generation
        self._threads = [
            threading.Thread(
                target=self._pty_master_pump,
                args=(process, master_fd, generation),
                name=f"session-{self.key}-pty-{generation}",
                daemon=True,
            ),
        ]
        for t in self._threads:
            t.start()

    @property
    def pid(self) -> int | None:
        """The child process id, or ``None`` once it is gone."""
        return self.process.pid if self.process else None

    # ── restart-on-death support (WP-005, §2.7) ────────────────────────────

    def turn_in_flight(self) -> bool:
        """Whether a turn is currently executing (no terminal event has freed
        the one-in-flight slot). A set ``_turn_done`` means idle / between
        turns."""
        return not self._turn_done.is_set()

    def died_mid_turn(self) -> bool:
        """Whether the last process death happened mid-turn — snapshotted by the
        stdout pump at EOF before the slot was freed. Used by WP-005's lifecycle
        to decide whether to surface an ``error`` event (§2.10 #6). Reset on the
        next restart so a later idle death is not mis-reported."""
        return self._died_mid_turn

    def mark_dead(self) -> None:
        """Move the state machine to ``DEAD`` from whatever live state it is in
        (READY / EXECUTING / INITIALIZING). Idempotent if already DEAD. Used by
        WP-005's lifecycle the instant a death is confirmed (§2.7). Guarded by
        the session lock so it serialises with the pumps' cycle transitions."""
        with self._lock:
            if self.state_machine.state is SessionState.DEAD:
                return
            self.state_machine.transition(SessionState.DEAD)

    def to_state(self, target: SessionState) -> None:
        """Mandatory state transition under the session lock (§2.7).

        Used by WP-005's lifecycle for the recovery transitions that MUST be
        legal (DEAD → INITIALIZING → READY, DEAD → PERMANENTLY_DISABLED); an
        illegal one raises (it is a programming error). Serialises with the
        pumps' best-effort cycle transitions via the session lock."""
        with self._lock:
            self.state_machine.transition(target)

    def _try_transition(self, target: SessionState) -> None:
        """Best-effort state transition from a pump thread (§2.7).

        The normal turn cycle (READY ↔ EXECUTING) is driven from the pumps; a
        racing death may already have moved the machine to DEAD, making the
        cycle transition illegal. A pump must never crash on that race, so an
        illegal transition here is a no-op (the death path owns the state).
        Guarded by the session lock so it does not race the lifecycle's own
        transitions."""
        with self._lock:
            if self.state_machine.can_transition(target):
                self.state_machine.transition(target)

    # ── per-turn guard support (WP-007, §2.7) ──────────────────────────────

    @staticmethod
    def _fire_guard_hook(hook: "Callable[..., None] | None", *args: object) -> None:
        """Invoke an optional guard callback, isolated from the pump (§2.7).

        The single place the WP-007 guard seams fire: a no-op when no guard is
        attached (so WP-004's core flow is untouched), and a swallowed exception
        otherwise — a guard fault must never crash the pump thread that fires it
        (which would wedge the one-in-flight queue or the stdout reader). Shared
        by both turn-lifecycle seams (:meth:`_fire_turn_start` /
        :meth:`_fire_event`) so the "fire-if-registered, never-let-it-crash-the-
        pump" rule lives in exactly one place (Blue: one method, two callers)."""
        if hook is None:
            return
        try:
            hook(*args)
        except Exception:  # noqa: BLE001 — a guard fault must not kill the pump
            pass

    def _fire_turn_start(self) -> None:
        """Fire the ``on_turn_start`` guard seam (the stdin pump's turn-start
        point), if a guard is registered (§2.7). The watchdog arms here."""
        self._fire_guard_hook(self.on_turn_start, self)

    def _fire_event(self, event: Event) -> None:
        """Fire the ``on_event`` guard seam for one appended event (the stdout
        pump's per-event point), if a guard is registered (§2.7). The runaway
        counter + the watchdog-cancel observe here."""
        self._fire_guard_hook(self.on_event, self, event)

    def _fire_pty_output(self, data: bytes) -> None:
        """Fire the ``on_pty_output`` broadcast seam for one raw master-read
        chunk (the pty pump's per-chunk point), if a viewer registry is wired
        (WP-004, §2.12.2). Reuses :meth:`_fire_guard_hook`'s fire-if-registered,
        never-crash-the-pump discipline (Blue: one method, now three callers) — a
        viewer-fanout fault must never kill the master-reader pump (which would
        stop the scrollback ring filling). No-op for a headless pty session."""
        self._fire_guard_hook(self.on_pty_output, data)

    def force_terminate_turn(self, *, terminal: SessionState, error: Event) -> None:
        """End the in-flight turn on a guard trip: surface ``error`` then move to
        ``terminal`` (WP-007, §2.7).

        Order is the contract: the ``error`` Event is appended to the log
        **first** (so a ``read(follow=True)`` observer sees the cause), then the
        state machine moves ``EXECUTING → terminal``. The transition is
        best-effort under the session lock: a racing death (the process already
        gone) owns the state, so an illegal ``→ terminal`` is a no-op rather than
        a crash. Best-effort on the append too: a closed log (the session is
        terminating) is ignored.

        **The one-in-flight slot is deliberately NOT freed here.** Freeing it
        inline would wake the parked stdin pump, which would then pull the queued
        command and write it to the about-to-be-killed child — losing that turn
        to a broken pipe (§2.6 wedge). Instead the guard's :meth:`kill_process`
        drives WP-005 restart-on-death, and :meth:`replace_process` frees the
        slot through the **same** ``_turn_done.set()`` the normal completion path
        uses (§2.6 — one free-the-slot, not a forked one; Blue) *with fresh
        pumps*, so the queued send runs on the restarted process rather than
        racing the kill. The slot release is thus the existing one, sequenced
        after the restart so the queue drains correctly."""
        try:
            self.log.append(error)
        except RuntimeError:
            pass  # log closed (session terminating) — nothing to surface
        with self._lock:
            if self.state_machine.can_transition(terminal):
                self.state_machine.transition(terminal)

    def release_turn_for_retry(self) -> None:
        """Free the one-in-flight slot for a turn that ended in a **retryable**
        ``error`` — on the SAME live process, WITHOUT terminating it (recovery
        slot-release seam).

        The retry sibling of :meth:`force_terminate_turn`. An ``error`` Event
        does not satisfy the adapter's ``turn_complete`` (only a ``result``
        does), so the stdout pump never frees the slot for an errored turn — the
        stdin pump stays parked on ``_turn_done.wait()`` (§2.6). When the
        manager routes a transient-blip ``error`` to the recovery driver, the
        driver re-submits the stopped turn through the manager's FIFO; that
        re-submit can only promote once the held slot is freed. This method frees
        it through the **same** ``_turn_done.set()`` the normal completion path
        uses (§2.6 — one free-the-slot, not a forked one), so the parked stdin
        pump wakes and the replay promotes onto the still-live process.

        **Distinct from :meth:`force_terminate_turn`.** A transient blip is an
        API-level failure, not a dead process: the process, its pumps, and its
        log are all kept. So this does *not* SIGKILL the child, does *not* bump
        the pump generation, and does *not* drive restart-on-death; it only ends
        the *turn* (EXECUTING → READY, best-effort under the session lock — a
        racing death owns the state, so an illegal transition is a no-op) and
        frees the slot. The one-in-flight invariant is preserved: the errored
        turn is logically handed back, and the driver's replay re-acquires the
        slot as just-another-turn — at no point are two turns genuinely in
        flight on the same process.

        **``_process_ended`` is deliberately NOT set.** Unlike the EOF death
        path, the process is alive, so the stdin pump woken by the
        ``_turn_done.set()`` below must NOT see a "process gone" flag — it pulls
        the replayed command and writes it to the live child. (The guard-kill /
        mid-turn-death path sets ``_process_ended`` to *stop* a write into a
        corpse; here the opposite is required — the replayed write must land.)

        Safe from the short-lived recovery daemon thread the manager's
        ``_on_error_event`` dispatches on: it touches only the threading-primitive
        slot + the lock-guarded state machine, never the process or the pumps.

        End the turn (EXECUTING → READY) via the shared best-effort
        :meth:`_try_transition` — the same racing-death-safe, lock-guarded
        transition the normal turn cycle uses (Blue: one transition helper, not a
        re-spelled lock block) — then free the slot through the existing
        ``_turn_done.set()`` seam."""
        self._try_transition(SessionState.READY)
        self._turn_done.set()

    def kill_process(self) -> None:
        """Hard-kill the child so a hung / runaway turn actually stops, then reap
        it (WP-007).

        SIGKILL (not SIGTERM): a runaway/hung child is already misbehaving, so go
        straight to the forceful stop. The resulting stdout EOF drives WP-005's
        restart-on-death (the manager's ``on_death`` path), making a guard
        terminal a *recoverable* one within the recovery budget (§2.7).

        **``wait()`` after ``kill()`` is load-bearing.** Restart-on-death's first
        step confirms the death via ``is_alive`` (``process.poll()``). Right after
        a ``kill()`` the OS may not have reaped the child yet, so ``poll()`` can
        still read ``None`` for a beat — and the lifecycle, seeing a "live"
        process, would decline the restart, stranding the session in
        ``TERMINATED_*`` (a 1-in-N flake the recoverable-timeout path exposed).
        Reaping here makes ``poll()`` deterministically report the death before
        ``on_death`` runs, so the restart always fires. Bounded so a wedged kill
        cannot hang the guard's timer thread. Best-effort: a process already gone
        is ignored."""
        proc = self.process
        if proc is None:
            return
        try:
            if proc.poll() is None:
                proc.kill()
                # Reap so poll() reliably reports the death before the lifecycle
                # confirms it (see the docstring's load-bearing note).
                proc.wait(timeout=_TERM_GRACE_SECONDS)
        except subprocess.TimeoutExpired:
            pass  # extremely rare; on_death's own poll will catch up
        except (OSError, ValueError):
            pass

    def replace_process(
        self, process: subprocess.Popen, pty_master_fd: int | None = None
    ) -> None:
        """Swap in a freshly-spawned ``process`` and restart the pumps, keeping
        the SAME key + SAME log (§2.7 restart-is-not-a-new-key).

        Bumps the pump generation so the old (dead-process) pumps exit, unblocks
        and joins the old stdin/stderr pumps (the caller runs on the old stdout
        pump thread, which is itself returning — never self-joined), then resets
        the per-process flags and launches new pumps on the new process. The log
        is untouched, so its offsets keep climbing and every prior event stays
        readable — the conversation survives the crash.

        **PTY restart (§2.12.3).** For a pty session the manager passes the fresh
        ``os.openpty()`` master fd; the old master is closed here (so the stale
        master-reader pump's ``os.read`` returns EOF and it exits), and the new
        master is swapped in. The :class:`ScrollbackBuffer` is **kept** across the
        restart (restart-is-not-a-new-key applied to the scrollback model) — only
        the master fd is re-created, exactly as the log survives a pipe restart.
        """
        old_threads = self._threads
        old_master_fd = self.pty_master_fd
        current = threading.current_thread()
        # Invalidate the old generation so any still-running old pump exits.
        self._generation += 1
        # For a pty session, close the OLD master fd before joining so the stale
        # master-reader pump (parked in os.read) gets EOF and returns; then point
        # the session at the fresh master. The scrollback ring is untouched — it
        # carries across the restart (§2.12.3).
        if old_master_fd is not None and pty_master_fd is not None:
            try:
                os.close(old_master_fd)
            except OSError:
                pass
            self.pty_master_fd = pty_master_fd
        # Release the in-flight wait FIRST, then unblock the command queue —
        # both BEFORE joining the old pumps. An old stdin pump can be parked in
        # either place: on ``_turn_done.wait()`` (a turn was in flight when the
        # process died — e.g. a guard-killed runaway / timeout, §2.7), or on
        # ``_commands.get()`` (idle between turns). Signalling both before the
        # join means the old pump can promptly observe the generation bump and
        # exit, so the join actually completes instead of timing out and leaving
        # a stale gen-0 pump overlapping the fresh gen-1 pump (which raced the
        # fresh pump for a queued command and wrote it to the wrong process —
        # the WP-007 guard's queued-send-after-kill path surfaced this). _WAKE
        # (not _STOP) so a leftover wake-up the fresh pump pulls is discarded,
        # and a real command the stale pump pulled is re-queued, never dropped.
        self._turn_done.set()
        self._commands.put(_WAKE)
        for t in old_threads:
            if t is current:
                continue  # never join the thread we are running on
            t.join(timeout=_JOIN_TIMEOUT_SECONDS)
        # Fresh process + fresh per-process state for the new pump set.
        self.process = process
        self._turn_done.set()  # idle: no turn in flight on the new process yet
        self._process_ended.clear()  # the fresh process has not ended
        self._death_signalled = False
        self._died_mid_turn = False
        with self._lock:
            self.last_activity = time.monotonic()
        self.start_pumps()

    def mark_active(self) -> None:
        """Bump ``last_activity`` to now under the session lock (§2.3).

        The single, lock-guarded place a non-output activity signal touches the
        idle clock. ``last_activity`` is otherwise bumped only when the manager
        *submits* a turn or a pump *appends output* — but a pty session bumps it
        purely on output bytes, so a turn that produces no output for longer than
        the idle timeout (claude thinking, a long quiet tool) looks idle even
        though work is in flight (#108). Keystroke feed and the periodic liveness
        signal call this so genuine in-use activity that the output clock misses
        still resets the idle timer — without forking a second activity field."""
        with self._lock:
            self.last_activity = time.monotonic()

    # ── submit side: the decoupling invariant (§2.2) ───────────────────────

    def submit(self, command: str) -> int:
        """Enqueue ``command`` and return the offset its first event will land
        at (§2.2 forward reference, §2.5).

        **Never waits for this turn's reply** (the decoupling invariant): the
        returned offset is a *bookmark*, not a result, and content is obtained
        only via the log's ``read`` — ``submit`` returns before any chunk of
        *this* turn is produced.

        The bookmark is resolved at the moment the command reaches the head of
        the one-in-flight queue and the stdin pump is about to write it — that
        is the instant ``log.next_offset()`` equals exactly where this turn's
        first event lands, because all earlier turns (strictly FIFO,
        one-in-flight) have by then appended their events. For an idle session
        the command is at the head immediately, so the bookmark resolves with no
        wait; for a *queued* send the bookmark resolves once the prior turn has
        finished writing (admission to the writer), which is required for the
        offset to be its true eventual landing offset rather than a guess at a
        provider-dependent per-turn event count. This is admission ordering, not
        waiting on *this* turn's reply.
        """
        with self._lock:
            self.last_activity = time.monotonic()
        # A one-slot mailbox the stdin pump fills with this command's resolved
        # landing offset when it promotes the command to the writer.
        landing_box: "queue.Queue[int]" = queue.Queue(maxsize=1)
        self._commands.put((command, landing_box))
        return landing_box.get()

    # ── the three pumps (AE terminal-pool I/O-thread shape, re-shaped) ─────

    def _stdin_pump(self, process: subprocess.Popen, generation: int) -> None:
        """Drain the command queue one turn at a time (§2.6 one-in-flight).

        Pull the head command, resolve its landing bookmark (``next_offset()``
        at this instant — all earlier turns have appended, so this is exactly
        where the turn's first event lands), mark a new turn, encode + write it
        to ``process``'s stdin, then **block until the stdout pump signals the
        turn finished** before pulling the next. The ``_STOP`` sentinel ends the
        loop, and a generation mismatch (this pump was superseded by a restart)
        also ends it — without writing the pulled command to the dead process.
        """
        stdin = process.stdin
        assert stdin is not None  # spawned with stdin=PIPE (§2.8 transport)
        while True:
            item = self._commands.get()
            if item is _STOP:
                break
            if item is _WAKE:
                # A restart's wake-up. If this pump is now stale, exit; if it is
                # the current pump (a leftover _WAKE), discard and keep going.
                if generation != self._generation:
                    break
                continue
            if generation != self._generation:
                # A restart superseded this pump; the new pump owns the queue.
                # Do not write the pulled command to the dead process — but a
                # real command pulled here still has a caller blocked on its
                # landing box, so RE-QUEUE it for the new pump to handle rather
                # than dropping it (which would hang the caller's submit()).
                self._commands.put(item)
                break
            if self._process_ended.is_set():
                # This pump's process has ended (the stdout pump set this at EOF —
                # e.g. the prior turn was killed by the WP-007 runaway / timeout
                # guard, or died mid-turn). The stdout pump sets ``_turn_done`` on
                # EOF to unpark us, but the restart that bumps the generation has
                # not run yet, so the generation guard above did not catch it.
                # Writing this command now would hit a broken pipe and lose the
                # turn. ``_process_ended`` is the *reliable* signal here —
                # ``process.poll()`` can still read ``None`` for a beat after a
                # kill while the OS reaps, which raced and let the write through.
                # Re-queue the command (the caller is still blocked on its landing
                # box) and exit; the restart's fresh pump owns the queue and runs
                # it on the live process. This closes the death-vs-next-write race
                # the WP-007 queued-send-after-kill path exposed (the slot is freed
                # by the restart, not by writing into a corpse — §2.6).
                self._commands.put(item)
                break
            command, landing_box = item
            self._turn_done.clear()
            # A turn is now starting: READY → EXECUTING (best-effort — a racing
            # death owns the state if it already fired). §2.7 normal turn cycle.
            self._try_transition(SessionState.EXECUTING)
            with self._lock:
                self.turn += 1
                self.last_activity = time.monotonic()
                # The command is now at the writer's head: next_offset() is its
                # true landing offset (§2.5). Resolve the caller's bookmark.
                landing_box.put(self.log.next_offset())
            # The turn has entered EXECUTING: arm the WP-007 per-turn guard
            # (watchdog + tool counter), if one is registered. Fired here — after
            # the bookmark resolves, before the write — so the time budget covers
            # the whole turn. No-op when no guard is attached (WP-004 untouched).
            self._fire_turn_start()
            try:
                stdin.write(self.adapter.encode(command))
                stdin.flush()
            except (BrokenPipeError, ValueError, OSError):
                # stdin pipe broke: the process died in the window between the
                # caller's send and this write (§2.9 STDIN_BROKEN). The caller
                # already holds this turn's landing offset, so a follower from it
                # would hang forever waiting for output that can never come.
                # Surface a turn-terminal ``error`` event at that offset so the
                # follower sees the failure and can re-send; the stdout pump's
                # EOF then drives restart-on-death (WP-005) for the next turn.
                self._append_stdin_broken_error()
                break
            # Wait for this turn's terminal event before the next command runs.
            self._turn_done.wait()

    def _append_stdin_broken_error(self) -> None:
        """Append a ``STDIN_BROKEN`` error Event for the current turn so a
        follower of a turn whose write failed (process died in the send→write
        window) sees a terminal failure instead of hanging (§2.9). Best-effort:
        a closed log (the session is terminating) is ignored."""
        try:
            self.log.append(
                Event(
                    offset=-1,
                    key=self.key,
                    turn=self.turn,
                    kind="error",
                    error=EventError(
                        category="protocol",
                        code=STDIN_BROKEN,
                        message="session process died before the turn was written",
                    ),
                )
            )
        except RuntimeError:
            pass  # log closed (session terminating) — nothing to surface

    def _stdout_pump(self, process: subprocess.Popen, generation: int) -> None:
        """Read ``process``'s stdout line by line; decode each via the adapter;
        append every decoded Event to the log with this session's coordinates;
        release the in-flight slot when the adapter reports the turn complete.

        On EOF (the process closed its stdout — normal exit or unexpected
        death), release any waiting stdin pump and, if this was an *unexpected*
        death (not a deliberate close, and this pump is still the current
        generation), fire the registered ``on_death`` callback exactly once so
        the manager's restart-on-death logic (WP-005) can run (§2.7).
        """
        stdout = process.stdout
        assert stdout is not None  # spawned with stdout=PIPE (§2.8 transport)
        for raw in stdout:
            event = self.adapter.decode(raw)
            if event is None:
                continue  # bookkeeping/init line — no founder-facing event
            with self._lock:
                current_turn = self.turn
                self.last_activity = time.monotonic()
            # The adapter returns a partial Event (placeholder offset/key/turn);
            # stamp this session's key + current turn, then the log assigns the
            # real offset on append (§2.4 decode seam, §2.5 offset assignment).
            stamped = dataclasses.replace(event, key=self.key, turn=current_turn)
            self.log.append(stamped)
            # Let the WP-007 guard observe this event (count tool_use; cancel the
            # watchdog on the terminal result/error), if one is registered. Fired
            # AFTER the append so the guard's view matches the durable log, and
            # BEFORE the slot is freed so a runaway trip wins the race to end the
            # turn. No-op when no guard is attached (WP-004 untouched).
            self._fire_event(stamped)
            if self.adapter.turn_complete(stamped):
                # Turn finished: EXECUTING → READY (best-effort) then free the
                # one-in-flight slot. §2.7 normal turn cycle.
                self._try_transition(SessionState.READY)
                self._turn_done.set()
        # stdout closed (EOF / process gone) — run the shared EOF death discipline.
        self._handle_eof_death(process, generation)

    def _handle_eof_death(self, process: subprocess.Popen, generation: int) -> None:
        """The shared EOF → death discipline both output pumps run at end-of-
        stream (§2.7/§2.12.3).

        Extracted at the 2-consumer threshold (EP-03): the pipe stdout pump and
        the pty master-reader pump reach EOF identically — the only difference is
        WHAT they read (decoded lines vs raw bytes), not how a death is handled.
        In order:

        1. **Snapshot mid-turn-ness BEFORE freeing the slot** so the lifecycle can
           tell a mid-turn death (needs an ``error`` event, §2.10 #6) from an idle
           one (current generation only — a superseded pump must not clobber the
           restarted session's flag).
        2. **Reap the now-exited child** so ``process.poll()`` deterministically
           reports the death before restart-on-death's ``is_alive`` confirm runs
           — otherwise a not-yet-reaped corpse reads "alive", the EOF looks
           spurious, and the restart is wrongly declined (a 1-in-N flake; see
           :meth:`kill_process`'s note). Bounded + best-effort.
        3. **Mark ``_process_ended`` BEFORE releasing the in-flight wait** so a
           stdin pump woken by the ``_turn_done.set()`` below sees the reliable
           "process gone" flag and exits without writing the next command into the
           corpse (the guard-kill / mid-turn-death race, §2.6/§2.7).
        4. Release any waiting stdin pump, then fire ``on_death`` once (an
           unexpected death drives WP-005 restart-on-death).

        Each generation-guarded step is skipped for a superseded (stale) pump."""
        if generation == self._generation:
            self._died_mid_turn = self.turn_in_flight()
        if generation == self._generation:
            try:
                process.wait(timeout=_TERM_GRACE_SECONDS)
            except (subprocess.TimeoutExpired, OSError, ValueError):
                pass  # on_death's own poll will catch up if reaping stalls
        if generation == self._generation:
            self._process_ended.set()
        # Release any waiting stdin pump so it does not hang.
        self._turn_done.set()
        self._maybe_signal_death(generation)

    def _maybe_signal_death(self, generation: int) -> None:
        """Fire ``on_death`` once for an *unexpected* stdout EOF (§2.7).

        Skipped when the session is deliberately closing, when this pump has
        been superseded by a restart (stale generation), when no callback is
        registered, or when death was already signalled for this process — so a
        single death triggers at most one restart attempt.
        """
        if self._closing or generation != self._generation:
            return
        if self.on_death is None or self._death_signalled:
            return
        self._death_signalled = True
        self.on_death(self)

    def _pty_master_pump(
        self, process: subprocess.Popen, master_fd: int, generation: int
    ) -> None:
        """Read the PTY master end raw and append every byte to ``scrollback``
        (contract §2.11 / §2.12.1, ADR-001).

        The pty analogue of :meth:`_stdout_pump`: where the pipe stdout pump
        *decodes* each line into the structured event log, the pty pump appends
        the **raw** terminal bytes (escape codes, cursor moves — the literal
        stream xterm.js renders) into the bounded scrollback ring. There is no
        decode and no per-turn slot on the terminal path (a pty session is a
        terminal view, not a structured-chat stream, §2.11.1).

        On EOF (the master read returns empty / errors — the child closed its
        controlling tty, i.e. it exited) it runs the SAME death discipline as the
        stdout pump so restart-on-death (§2.7/§2.12.3) fires for pty sessions:
        snapshot whether a turn was in flight, reap the child so ``poll()``
        reports the death deterministically, mark ``_process_ended``, release any
        waiter, and fire ``on_death`` once (current generation only). Bound to
        the generation live at launch so a stale pump (superseded by a restart's
        fresh master fd) exits without clobbering the restarted session's state.
        """
        scrollback = self.scrollback
        assert scrollback is not None  # a pty session always has a scrollback
        while True:
            try:
                data = os.read(master_fd, 65536)
            except OSError:
                # The master end was closed/torn down (EOF on a pty surfaces as
                # an OSError EIO on some platforms) — treat as end-of-stream.
                break
            if not data:
                break
            with self._lock:
                self.last_activity = time.monotonic()
            scrollback.append(data)
            # Broadcast the live chunk to any attached viewers (WP-004), AFTER
            # the scrollback append so a viewer attaching at this instant takes a
            # snapshot that already includes ``data`` (the registry registers
            # before snapshotting, so a small overlap is harmless; a gap is not).
            # No-op when no registry is wired (a headless pty session, §2.12.5).
            self._fire_pty_output(data)
        # EOF / master gone — run the SAME EOF death discipline as the stdout pump
        # so a pty child that dies is restarted like a pipe child (§2.7/§2.12.3).
        # Pass the pump's OWN captured process (not self.process) so a stale pump
        # never touches the restarted session's fresh process — parity with the
        # stdout pump's generation discipline.
        self._handle_eof_death(process, generation)

    def _stderr_pump(self, process: subprocess.Popen) -> None:
        """Drain ``process``'s stderr so the pipe never fills and blocks the
        child. Captured for diagnostics; not turned into log events here (a
        failed turn surfaces as an ``error`` *event* via the adapter's decode,
        §2.9). WP-005/007 may consume this stream later."""
        stderr = process.stderr
        if stderr is None:
            return
        for _ in stderr:
            # Drain only; structured stderr handling is a later concern.
            pass

    # ── teardown ────────────────────────────────────────────────────────────

    def terminate(self) -> None:
        """SIGTERM then SIGKILL the child, stop the pumps, close the log (§2.2).

        Idempotent at the session level: the manager guarantees one call, but a
        second call is harmless (the process is already gone, the queue already
        carries a stop sentinel, the log close is idempotent).
        """
        if self._closing:
            return
        self._closing = True
        # 1. Tell the stdin pump to stop and release any in-flight wait.
        self._commands.put(_STOP)
        self._turn_done.set()
        # 2. SIGTERM, then SIGKILL if it does not exit in the grace window.
        proc = self.process
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=_TERM_GRACE_SECONDS)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
        # 3. Closing the streams unblocks the stdout/stderr readers on EOF.
        for stream in (proc.stdin, proc.stdout, proc.stderr):
            if stream is not None:
                try:
                    stream.close()
                except (OSError, ValueError):
                    pass
        # 3b. For a pty session, close the master fd so the master-reader pump's
        #     os.read returns EOF and the pump exits before the join (the slave
        #     end was already closed by the manager right after spawn).
        if self.pty_master_fd is not None:
            try:
                os.close(self.pty_master_fd)
            except OSError:
                pass
        # 4. Join the pumps (bounded so a wedged pump cannot hang close).
        #    A restart (replace_process) may have just swapped the thread set;
        #    snapshot it and skip any thread not yet started — joining an
        #    unstarted Thread raises, and a concurrent restart can momentarily
        #    expose one.
        for t in list(self._threads):
            if t.is_alive() or t.ident is not None:
                t.join(timeout=_JOIN_TIMEOUT_SECONDS)
        # 5. End the log's followers cleanly.
        self.log.close()
