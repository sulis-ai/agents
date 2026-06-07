"""``_session_manager.manager`` — the ``SessionManager`` core surface.

Contract: SESSION_MANAGER_CONTRACT.md §2.2 (the six consumer methods
open/send/read/health/status/close), §2.5 (offset/cursor read delegated to the
log), §2.6 (one-in-flight per key; different keys parallel), §2.9 (the
three-category error model).

The manager is the **composition root** (WPB-07) for the persistent-chat
capability: it owns the keyed registry of warm :class:`~_session_manager.\
session.Session` objects, each composing a WP-001 log + a WP-003 adapter + a
real subprocess with three pump threads. The manager depends on providers
**only through the WP-003 ``ProviderAdapter`` Protocol** — adapters are injected
as a ``{provider_name: adapter}`` dict at construction, so a new provider is one
new adapter with zero change here (§2.4, MEA-01 dependency-inward).

**The decoupling invariant (§2.2, load-bearing).** :meth:`send` returns the log
offset the turn's first event will land at and never blocks on a reply;
:meth:`read` is the only content path. A consumer composes them for
request/response convenience; the manager never bundles them.

**Liveness is owned here.** :meth:`is_alive` is the single liveness check
(``process.poll()``-style) that backs :meth:`health` and :meth:`status`. WP-005
(restart-on-death) and WP-006 (dead-process detection) consume it unchanged —
there is no separate liveness primitive.

**Three extension points** are defined here so the wave-4 Armor WPs attach
without editing the core flow, each in its own module:
:meth:`_on_process_death` (WP-005 — restart-on-death, delegates to
``lifecycle.py``), :meth:`_maintenance_tick` (WP-006 — idle-eviction / LRU
memory-cap / dead-process detection, delegates to ``maintenance.py``), and
:meth:`_guard` (WP-007 — the per-turn runaway/timeout guard, still a no-op
seam). Defining them up front is what keeps WP-005/006/007 parallelisable and
conflict-free; WP-005 + WP-006 now fill theirs by delegation, so the core flow
stayed lean.
"""

from __future__ import annotations

import os
import subprocess
import threading
from typing import Iterator

from _session_manager.adapter import ProviderAdapter, SessionSpec
from _session_manager.event_log import EventLog
from _session_manager.events import (
    CWD_NOT_FOUND,
    NO_SESSION,
    SESSION_DISABLED,
    SPAWN_FAILED,
    UNKNOWN_PROVIDER,
    Event,
    ExpectedError,
    ProtocolError,
)
from _session_manager.guards import (
    DEFAULT_MAX_TOOL_CALLS,
    DEFAULT_TURN_TIMEOUT_SECONDS,
    TurnGuardManager,
)
from _session_manager.lifecycle import DEFAULT_RECOVERY_BUDGET, LifecycleManager
from _session_manager.maintenance import (
    DEFAULT_MAINTENANCE_INTERVAL_SECONDS,
    MaintenanceManager,
    memory_bytes_for_pids,
)
from _session_manager.session import Session
from _session_manager.state import Health, SessionState, SessionStatus


class SessionManager:
    """Owns warm, long-lived agent sessions — one per caller-supplied key.

    Args:
        adapters: the provider registry — ``{provider_name: ProviderAdapter}``.
            ``SessionSpec.provider`` selects which adapter starts a session; an
            unknown name is an Expected ``UNKNOWN_PROVIDER`` error (§2.9). The
            manager touches providers *only* through this dict (MEA-01).
        **tuning: forward-compatible tuning kwargs. Recognised:
            ``recovery_budget`` (WP-005 restart budget), ``idle_timeout`` +
            ``memory_cap`` (WP-006 idle-eviction + LRU cap; ``memory_cap``
            defaults to a host-RAM-derived value with a conservative floor),
            ``maintenance_interval`` (the background tick period, seconds), and
            ``start_maintenance`` (bool, default ``True`` — set ``False`` to
            drive the tick synchronously in tests). Stored as a dict so adding a
            tuning knob is no signature churn (§ Notes).
    """

    def __init__(self, adapters: dict[str, ProviderAdapter], **tuning: object) -> None:
        self._adapters = dict(adapters)
        self._tuning = dict(tuning)
        self._sessions: dict[str, Session] = {}
        # Guards the registry; per-session concurrency lives on each Session.
        self._registry_lock = threading.Lock()
        # WP-005 restart-on-death + resume + recovery budget. The ``_on_process_\
        # death`` hook (no-op in WP-004) now delegates here. The recovery budget
        # comes from the ``recovery_budget`` tuning kwarg (default boring small
        # integer) so a poison spec is taken out of rotation, not restart-looped.
        recovery_budget = int(
            self._tuning.get("recovery_budget", DEFAULT_RECOVERY_BUDGET)
        )
        self._lifecycle = LifecycleManager(recovery_budget=recovery_budget)
        # WP-006 idle-eviction + LRU memory-cap + dead-process detection. The
        # ``_maintenance_tick`` hook (no-op in WP-004) now delegates here, and
        # ``open`` consults the cap before admitting a new session. ``memory_cap``
        # defaults to a host-RAM-derived value (conservative floor) when not
        # given (§2.7 decided default).
        maintenance_kwargs: dict[str, object] = {}
        if "idle_timeout" in self._tuning:
            maintenance_kwargs["idle_timeout"] = float(self._tuning["idle_timeout"])
        if "memory_cap" in self._tuning:
            maintenance_kwargs["memory_cap"] = int(self._tuning["memory_cap"])
        self._maintenance = MaintenanceManager(**maintenance_kwargs)
        # WP-007 per-turn runaway / timeout guards. The ``_guard`` hook (no-op in
        # WP-004) now delegates here, and ``open`` / ``_respawn`` register the
        # guard's per-turn observation callbacks on each session. ``turn_timeout``
        # + ``max_tool_calls`` default to generous boring values (a healthy turn
        # never trips); both overridable via tuning kwargs (§2.7).
        self._guards = TurnGuardManager(
            turn_timeout=float(
                self._tuning.get("turn_timeout", DEFAULT_TURN_TIMEOUT_SECONDS)
            ),
            max_tool_calls=int(
                self._tuning.get("max_tool_calls", DEFAULT_MAX_TOOL_CALLS)
            ),
        )
        # The background maintenance loop: a daemon timer thread that runs the
        # tick every ``maintenance_interval`` seconds. Disabled with
        # ``start_maintenance=False`` so tests drive ``_maintenance_tick``
        # synchronously (MEA-09 determinism — no sleep-based flakiness).
        self._maintenance_interval = float(
            self._tuning.get(
                "maintenance_interval", DEFAULT_MAINTENANCE_INTERVAL_SECONDS
            )
        )
        self._maintenance_stop = threading.Event()
        self._maintenance_thread: threading.Thread | None = None
        if bool(self._tuning.get("start_maintenance", True)):
            self._start_maintenance_loop()

    # ── §2.2 the six-method surface ────────────────────────────────────────

    def open(self, key: str, spec: SessionSpec) -> Session:
        """Get-or-spawn the warm session for ``key``; idempotent (§2.2).

        A live session for ``key`` is returned as-is, spawning nothing. On
        first spawn, the adapter is selected by ``spec.provider`` and the child
        is launched in ``spec.cwd``. Resume (§2.7) is honoured only if the
        adapter's ``capabilities.supports_resume`` is true; otherwise the
        session starts fresh and ``resumed`` is ``False`` — honestly.

        **Memory cap (§2.7).** When admitting a *new* session would exceed the
        configured cap, the least-recently-used session(s) are evicted first
        (by ``last_activity``) before the new one is spawned — so the cap is a
        hard bound on warm sessions. An idempotent re-``open`` of a live key
        never triggers eviction (it admits nothing new).

        Errors: Expected ``UNKNOWN_PROVIDER`` / ``CWD_NOT_FOUND``; Protocol
        ``SPAWN_FAILED`` (the spawn itself failed).
        """
        # Idempotent fast-path: a live session for ``key`` is returned as-is and
        # admits nothing new, so the cap is not consulted.
        with self._registry_lock:
            existing = self._sessions.get(key)
            if existing is not None and self.is_alive(existing):
                return existing

        # Admitting a new session: enforce the LRU memory cap BEFORE spawning, so
        # the cap is never momentarily exceeded. Victims are evicted gracefully
        # via ``close`` (SIGTERM→SIGKILL, log closed, registry entry removed).
        self._enforce_cap_for_new(key)

        with self._registry_lock:
            existing = self._sessions.get(key)
            if existing is not None and self.is_alive(existing):
                return existing

            adapter = self._adapters.get(spec.provider)
            if adapter is None:
                raise ExpectedError(
                    UNKNOWN_PROVIDER,
                    f"no adapter registered for provider {spec.provider!r}",
                )
            if not os.path.isdir(spec.cwd):
                raise ExpectedError(
                    CWD_NOT_FOUND,
                    f"cwd does not exist: {spec.cwd}",
                )

            resume = bool(spec.resume_ref) and adapter.capabilities.supports_resume
            process = self._spawn_process(adapter, spec)

            session = Session(
                key=key,
                spec=spec,
                adapter=adapter,
                log=EventLog(),
                process=process,
                resumed=resume,
            )
            # Register restart-on-death BEFORE the pumps run, so even a child
            # that dies instantly is recovered (§2.7). The callback routes to
            # the manager's hook, which delegates to the lifecycle.
            session.on_death = self._on_process_death
            # Register the WP-007 per-turn guard's observation callbacks BEFORE
            # the pumps run, so the very first turn is watched (§2.7). The guard
            # arms its watchdog on turn-start and counts tool_use per turn.
            self._guards.attach(session)
            session.start_pumps()
            # The spawn succeeded: INITIALIZING → READY (§2.7 normal entry).
            session.to_state(SessionState.READY)
            self._sessions[key] = session
            return session

    def send(self, key: str, command: str) -> int:
        """Submit ``command`` for ``key``; return the landing offset (§2.2).

        Returns immediately — never waits for the turn or any reply (decoupling
        invariant). One turn in flight per key (§2.6): a send while a turn runs
        is queued and the returned offset is its eventual landing offset.

        Errors: Expected ``NO_SESSION`` (no open session for ``key``); Expected
        ``SESSION_DISABLED`` (the session exhausted its recovery budget and is
        permanently disabled, §2.7).
        """
        session = self._require_session(key)
        if session.state_machine.state is SessionState.PERMANENTLY_DISABLED:
            raise ExpectedError(
                SESSION_DISABLED,
                f"session {key!r} is permanently disabled (recovery budget "
                f"exhausted); re-open to start a fresh session",
            )
        # WP-007 per-turn guard: ensure the session is armed before the turn is
        # enqueued. Registration happens at ``open`` / restart; this is the §2.6
        # send-path seam WP-004 reserved, kept so a guard can also veto a send
        # synchronously in future without touching the core flow.
        self._guard(session, command)
        return session.submit(command)

    def read(self, key: str, since: int = 0, follow: bool = False) -> Iterator[Event]:
        """Yield the key's events with ``offset >= since`` (§2.2/§2.5).

        Delegates entirely to the session's log: ``follow=False`` yields history
        then stops; ``follow=True`` yields from ``since`` then live until the
        session closes. ``since`` semantics (forward reference, eviction) are
        the log's (§2.5).

        Errors: Expected ``NO_SESSION`` (no open session for ``key``) — raised
        eagerly at call time, since the absence of a session is knowable
        immediately and a consumer should not have to start iterating to learn
        the key was never opened.
        """
        session = self._require_session(key)
        return session.log.read(since=since, follow=follow)

    def health(self, key: str) -> Health:
        """Liveness + identity for one session, side-effect-free (§2.2/§2.3).

        Errors: Expected ``NO_SESSION`` (no session for ``key``).
        """
        session = self._require_session(key)
        alive = self.is_alive(session)
        return Health(
            alive=alive,
            # The honest lifecycle state (§2.7): the state machine's current
            # label (ready / executing / dead / permanently_disabled / …),
            # which WP-005 now drives — no longer the WP-004 ready/closed stub.
            state=session.state_machine.state.value,
            pid=session.pid,
            provider=session.spec.provider,
        )

    def status(self) -> list[SessionStatus]:
        """Snapshot every session the manager owns, side-effect-free (§2.3)."""
        with self._registry_lock:
            sessions = list(self._sessions.values())
        # WP-006 wires the best-effort resident-memory reading (was 0 in WP-004).
        # Read every session's RSS in ONE ``ps`` call (not one per session) so a
        # snapshot at the RAM-derived cap stays a single fork — the method is
        # documented cheap/side-effect-free (§2.3). Observational only: the cap is
        # a count derived from host RAM, not a live RSS sum (§2.7).
        pids = [s.pid for s in sessions if s.pid is not None]
        rss_by_pid = memory_bytes_for_pids(pids)
        snapshot: list[SessionStatus] = []
        for session in sessions:
            snapshot.append(
                SessionStatus(
                    key=session.key,
                    # The honest lifecycle state (§2.7), driven by WP-005.
                    state=session.state_machine.state.value,
                    pid=session.pid,
                    provider=session.spec.provider,
                    memory_bytes=rss_by_pid.get(session.pid, 0),
                    last_activity=session.last_activity,
                    log_len=session.log.next_offset(),
                )
            )
        return snapshot

    def status_keys(self) -> set[str]:
        """The set of keys the manager currently owns, side-effect-free.

        A cheaper sibling of :meth:`status` for callers (and tests) that only
        need membership — e.g. asserting an evicted key is gone — without paying
        the per-session memory reading :meth:`status` does."""
        with self._registry_lock:
            return set(self._sessions.keys())

    def close(self, key: str) -> None:
        """Terminate the session for ``key`` and release it; idempotent (§2.2).

        SIGTERM then SIGKILL, join the pumps, close the log. Closing an
        already-closed or unknown key is a no-op.
        """
        with self._registry_lock:
            session = self._sessions.pop(key, None)
        if session is None:
            return
        # Drop the WP-007 guard's per-turn state for this session (cancel any
        # armed watchdog) so a long-lived manager does not accumulate stale
        # entries; then tear the session down.
        self._guards.detach(session)
        session.terminate()

    # ── §2.2 the WP-004-owned liveness primitive ───────────────────────────

    def is_alive(self, session: Session) -> bool:
        """The single liveness check (``process.poll()``-style), owned here and
        consumed unchanged by WP-005/006 (§ Liveness ownership).

        ``True`` while the session's child process is running; ``False`` once it
        has exited (poll returns its exit code) or there is no process.
        """
        process = session.process
        if process is None:
            return False
        return process.poll() is None

    # ── §2.7 restart-on-death (WP-005 fills the hook) ──────────────────────

    def _on_process_death(self, session: Session) -> None:
        """Called when a session's process is detected dead — delegates to the
        WP-005 lifecycle for restart-on-death + resume + recovery budget (§2.7).

        Death *detection* consumes the WP-004-owned :meth:`is_alive`; *recovery*
        (DEAD → restart → resume → READY, or DEAD → PERMANENTLY_DISABLED on
        budget exhaustion) is the lifecycle's. The actual spawn is the manager's
        (:meth:`_respawn`, which owns ``Popen`` + the resume-flag decision); the
        lifecycle orchestrates around it. The restart reuses the same key + same
        log, so the conversation survives the crash."""
        self._lifecycle.on_process_death(
            session,
            is_alive=self.is_alive,
            respawn=self._respawn,
        )

    def _respawn(self, session: Session) -> None:
        """Spawn a fresh process for ``session``'s spec and swap it in (§2.7).

        Resume is honoured iff the adapter supports it AND a ref exists — the
        same honest rule as first ``open`` (§2.7). The fresh process replaces
        the dead one on the SAME session (same key, same log) via
        :meth:`Session.replace_process`, which restarts the pumps; the log's
        offsets keep climbing and every prior event stays readable."""
        process = self._spawn_process(session.adapter, session.spec)
        session.replace_process(process)

    def _maintenance_tick(self) -> None:
        """One pass of the periodic maintenance loop (§2.7), filled by WP-006.

        Delegates to :class:`~_session_manager.maintenance.MaintenanceManager`
        over a *snapshot* of the live registry (taken under the registry lock,
        then released — so the tick's own evictions, which re-acquire the lock
        via :meth:`close`, never deadlock). Per session the tick:

        - **detects a dead process** via the WP-004-owned :meth:`is_alive` and
          routes it through :meth:`_on_process_death` (recovery is WP-005's —
          this WP only *detects in the tick*); else
        - **idle-evicts** a session idle past the timeout via :meth:`close`
          (graceful: SIGTERM→SIGKILL, log closed, registry entry removed).

        Called on the background maintenance thread, and directly by tests for
        deterministic, sleep-free verification (MEA-09)."""
        with self._registry_lock:
            snapshot = list(self._sessions.items())
        self._maintenance.tick(
            snapshot,
            is_alive=self.is_alive,
            on_death=self._on_process_death,
            evict=self.close,
        )

    def _enforce_cap_for_new(self, key: str) -> None:
        """Evict least-recently-used session(s) so admitting one new session for
        ``key`` keeps the warm-session count at or below the cap (§2.7).

        The victim selection (LRU by ``last_activity``) is the maintenance
        seam's (:meth:`MaintenanceManager.over_cap_victims`); the manager owns
        the graceful eviction (:meth:`close`). ``key`` itself is excluded from
        the victim pool — re-opening a key never evicts that same key."""
        with self._registry_lock:
            candidates = [(k, s) for k, s in self._sessions.items() if k != key]
        victims = self._maintenance.over_cap_victims(candidates, admitting=1)
        for victim_key in victims:
            self.close(victim_key)

    def _start_maintenance_loop(self) -> None:
        """Launch the background maintenance thread (daemon) that runs the tick
        every ``maintenance_interval`` seconds until :meth:`shutdown` (§2.7).

        Daemon so a hard interpreter exit never hangs on it; the loop waits on a
        stop :class:`~threading.Event` (interruptible, not a bare sleep) so
        shutdown is prompt. Exceptions in a single tick are swallowed so one bad
        pass never kills the loop — the next interval retries."""

        def _loop() -> None:
            while not self._maintenance_stop.wait(self._maintenance_interval):
                try:
                    self._maintenance_tick()
                except Exception:  # noqa: BLE001 — one bad pass must not kill the loop
                    pass

        thread = threading.Thread(
            target=_loop, name="session-manager-maintenance", daemon=True
        )
        self._maintenance_thread = thread
        thread.start()

    def shutdown(self) -> None:
        """Stop the background maintenance loop and close every owned session.

        Manager-level teardown (distinct from per-key :meth:`close`): signals
        the maintenance thread to stop, joins it (bounded), then closes all
        remaining sessions. Idempotent."""
        self._maintenance_stop.set()
        thread = self._maintenance_thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=self._maintenance_interval + 1.0)
        for key in self.status_keys():
            self.close(key)

    def _guard(self, session: Session, command: str) -> None:
        """Hook: per-turn guard, called by :meth:`send` before a turn is
        enqueued (§2.7), filled by WP-007.

        The runaway / timeout guards are driven by the per-turn observation
        callbacks the :class:`~_session_manager.guards.TurnGuardManager`
        registered on the session at ``open`` (and which survive a restart): the
        watchdog arms on turn-start, the tool counter increments per ``tool_use``,
        and a trip surfaces an ``error`` Event then drives the terminal state +
        frees the slot. This send-path seam is retained (WP-004 reserved it) so a
        guard can additionally veto a send synchronously here without touching the
        core flow; today the guard is event-driven, so this is the registration
        point and a no-op per-send. Kept rather than inlined so the guard stays
        behind the hook (Blue: WP-004 core flow untouched)."""
        return None

    # ── internal helpers ────────────────────────────────────────────────────

    def _spawn_process(
        self, adapter: ProviderAdapter, spec: SessionSpec
    ) -> subprocess.Popen:
        """Launch one child process for ``spec`` via ``adapter.spawn_argv``.

        The single spawn path shared by first ``open`` and restart-on-death
        ``_respawn`` (§2.7) — extracted so the resume-flag decision (the adapter
        appends ``--resume`` iff ``spec.resume_ref`` is set, and the manager
        only passes a ref when the adapter supports resume) and the
        ``SPAWN_FAILED`` mapping live in exactly one place. The streams are all
        PIPEs (§2.8 transport).

        Errors: Protocol ``SPAWN_FAILED`` (the spawn itself failed)."""
        argv = adapter.spawn_argv(spec)
        try:
            return subprocess.Popen(
                argv,
                cwd=spec.cwd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except (OSError, ValueError) as exc:
            raise ProtocolError(
                SPAWN_FAILED,
                f"could not spawn {spec.provider!r}: {exc}",
            ) from exc

    def _require_session(self, key: str) -> Session:
        """Return the live session for ``key`` or raise Expected
        ``NO_SESSION``. The single place the absence-of-session decline is
        raised, so every method speaks the same §2.9 code."""
        with self._registry_lock:
            session = self._sessions.get(key)
        if session is None:
            raise ExpectedError(NO_SESSION, f"no open session for key {key!r}")
        return session
