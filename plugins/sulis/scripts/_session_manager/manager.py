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

import logging
import os
import subprocess
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Iterator

from _session_manager.adapter import ProviderAdapter, SessionSpec
from _session_manager.classifier import RecoveryClass, classify
from _session_manager.event_log import EventLog
from _session_manager.events import (
    CWD_NOT_FOUND,
    NO_SESSION,
    NOT_PTY_SESSION,
    PTY_OPEN_FAILED,
    SESSION_DISABLED,
    SPAWN_FAILED,
    STDIN_BROKEN,
    UNKNOWN_PROVIDER,
    Event,
    EventError,
    ExpectedError,
    InternalError,
    ProtocolError,
)
from _session_manager.guards import (
    DEFAULT_MAX_TOOL_CALLS,
    DEFAULT_TURN_TIMEOUT_SECONDS,
    TurnGuardManager,
)
from _session_manager.lifecycle import DEFAULT_RECOVERY_BUDGET, LifecycleManager
from _session_manager.scrollback import ScrollbackBuffer
from _session_manager.maintenance import (
    DEFAULT_MAINTENANCE_INTERVAL_SECONDS,
    MaintenanceManager,
    memory_bytes_for_pids,
)
from _session_manager.recovery import (
    DEFAULT_RETRY_POLICY,
    ReauthTicket,
    RecoveryDriver,
)
from _session_manager.context_payload import ContextPayloadAssembler
from _session_manager.durable_sink import (
    BRIEF_FRAGMENT_HEADER,
    DurableAppendSink,
    now_iso,
    render_payload_brief,
    seed_payload_for_resume,
)
from _session_manager.resume_readers import (
    make_brain_reader,
    make_working_set_reader,
)
from _session_manager.session import Session
from _session_manager.spawn_env import PROXY_ENDPOINT_ENV, child_spawn_env
from _session_manager.thread_contract import (
    THREAD_NOT_FOUND,
    Thread,
    ThreadMemory,
    ThreadStore,
)
from _session_manager.state import Health, SessionState, SessionStatus
from _session_manager.viewer import Viewer, ViewerRegistry

# The sanctioned safe-fetch proxy endpoint a spawned agent session is pointed at
# (WP-003 / SPEC §L1(d)). The agent-facing ``_safe_fetch.tool`` reads
# ``PROXY_ENDPOINT_ENV`` to find this door. A deployment that runs the proxy on a
# non-default port exports ``SULIS_SAFE_FETCH_PROXY`` in the manager's own
# environment and it is honoured; otherwise the conventional loopback default is
# used. Loopback by design: the proxy is co-located, and the test-harness
# no-egress shim (ADR-005) — and, in production, the L3 sandbox — allow loopback
# as the single sanctioned egress.
DEFAULT_SAFE_FETCH_PROXY_ENDPOINT = "http://127.0.0.1:8080"

_log = logging.getLogger("sulis.session_manager.manager")

# Default per-session scrollback ceiling for a pty session (contract §2.11.3,
# the Armor ceiling — bounded memory is a MUST): 1 MiB is generous for a terminal
# screen + deep scrollback; appending past it drops oldest bytes. Overridable via
# the ``scrollback_capacity_bytes`` tuning kwarg.
DEFAULT_SCROLLBACK_CAPACITY_BYTES = 1024 * 1024


def _default_recovery_driver_factory(**kwargs: object) -> RecoveryDriver:
    """Build the real WP-005 :class:`RecoveryDriver` for one session (ADR-001).

    The default the manager uses when no ``recovery_driver_factory`` tuning
    kwarg is injected. Kept module-level (not a literal in ``__init__``) so the
    injectable seam — the ``timer_factory`` precedent — has a named, boring
    default a test can compare against, and so the manager body reads as a
    single wiring line. The keyword capabilities are the ones
    :meth:`SessionManager._make_recovery_driver` binds per session."""
    return RecoveryDriver(**kwargs)  # type: ignore[arg-type]


def _default_thread_store_factory(change_id: str) -> ThreadStore:
    """Build the durable local :class:`ThreadStore` for ``change_id`` (ADR-002 /
    ADR-004) — the default binding the durable sink writes into.

    The default the manager uses when no ``thread_store_factory`` tuning kwarg is
    injected, mirroring ``_default_recovery_driver_factory``. The
    :class:`~_session_manager.thread_store_local.LocalThreadStore` import is
    deferred to call time so the manager module carries no filesystem dependency
    at import time and codes against the ``ThreadStore`` Protocol, not the
    concrete adapter (the binding swaps to the hosted transport later behind the
    same port, ADR-002). A test injects an in-memory contract store instead —
    still a real ``ThreadStore`` (MEA-09)."""
    from _session_manager.thread_store_local import LocalThreadStore

    return LocalThreadStore(change_id)


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
        # WP-004 attach/viewer: one ViewerRegistry per pty session, keyed by
        # session key. Wired to the session's ``on_pty_output`` broadcast seam at
        # spawn (so live master reads fan out to attached viewers) and torn down
        # at ``close``. A pipe session has no entry (there is no terminal to
        # attach to; attach on it declines NOT_PTY_SESSION). Guarded by the same
        # registry lock as ``_sessions`` since the two are mutated together.
        self._viewer_registries: dict[str, ViewerRegistry] = {}
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
        # CH-01KTMK WP-007 turn-level recovery (ADR-001). The error-observation
        # hook (``_on_error_event``, sibling of ``_on_process_death``) routes a
        # live turn's ``error`` Event to a per-session RecoveryDriver — the
        # turn-level Armor primitive that sits *around* the lifecycle, never
        # inside it. The driver is per-session (it holds at most one pending
        # re-auth ticket), so the manager keeps one per open key, built by a
        # factory at ``open`` time with the capabilities bound to that session
        # (``send`` / ``log_append`` / ``reauth`` / ``resume``) plus the default
        # policy + clock + classifier + the adapter's ``classify_failure`` hint.
        # The factory is injectable — the ``timer_factory`` precedent — so a
        # test substitutes a recording/synchronous driver without a real
        # retry/backoff loop. Default builds the real WP-005 ``RecoveryDriver``.
        self._recovery_driver_factory: Callable[..., RecoveryDriver] = self._tuning.get(  # type: ignore[assignment]
            "recovery_driver_factory", _default_recovery_driver_factory
        )
        self._recovery_drivers: dict[str, RecoveryDriver] = {}
        # CH-GJ9KQR WP-007 durable second sink (ADR-004). The session pump's
        # in-memory ``EventLog`` stays the live-tail log; this adds a SECOND
        # sink that appends each content-bearing Event to the durable thread
        # store (the authoritative persisted record). The store binding is an
        # injectable factory — the ``recovery_driver_factory`` precedent — so a
        # test drives the real sink against an in-memory contract store without
        # touching the founder's filesystem. The default builds the durable
        # local adapter (WP-002) for the session's bound change. One sink per
        # open key; built at ``open``, reseeded on ``_respawn`` (resume,
        # WP-004 ADV-2), torn down at ``close``.
        self._thread_store_factory: Callable[[str], ThreadStore] = self._tuning.get(  # type: ignore[assignment]
            "thread_store_factory", _default_thread_store_factory
        )
        self._durable_sinks: dict[str, DurableAppendSink] = {}
        # The last command submitted per key — captured by ``send`` so the
        # recovery driver's ``send`` capability can re-submit *the stopped turn*
        # (not an empty turn) on a transient-blip retry. Additive read-only
        # bookkeeping: it never changes the FIFO / one-in-flight semantics, it
        # only records what was last enqueued so a retry replays it.
        self._last_command: dict[str, str] = {}
        # The background maintenance loop: a daemon timer thread that runs the
        # tick every ``maintenance_interval`` seconds. Disabled with
        # ``start_maintenance=False`` so tests drive ``_maintenance_tick``
        # synchronously (MEA-09 determinism — no sleep-based flakiness).
        self._maintenance_interval = float(
            self._tuning.get(
                "maintenance_interval", DEFAULT_MAINTENANCE_INTERVAL_SECONDS
            )
        )
        # Per-session scrollback ceiling for pty sessions (§2.11.3, the Armor
        # ceiling). Defaults to 1 MiB; overridable via the tuning kwarg so a host
        # under memory pressure can shrink it without a signature change.
        self._scrollback_capacity = int(
            self._tuning.get(
                "scrollback_capacity_bytes", DEFAULT_SCROLLBACK_CAPACITY_BYTES
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
            process, master_fd = self._spawn_process(adapter, spec)

            # A pty session owns a ScrollbackBuffer (§2.11) alongside its log; the
            # master-reader pump appends raw terminal bytes to it. A pipe session
            # leaves both pty fields None (byte-for-byte unchanged, acceptance #4).
            scrollback = (
                ScrollbackBuffer(capacity_bytes=self._scrollback_capacity)
                if master_fd is not None
                else None
            )
            session = Session(
                key=key,
                spec=spec,
                adapter=adapter,
                log=EventLog(),
                process=process,
                pty_master_fd=master_fd,
                scrollback=scrollback,
                resumed=resume,
            )
            # WP-004 attach/viewer: a pty session gets a ViewerRegistry wired to
            # its ``on_pty_output`` broadcast seam BEFORE the pumps run, so the
            # very first live master read fans out to any viewer that attaches.
            # The registry carries across restart on the same Session (the seam
            # survives ``replace_process``, §2.12.3). A pipe session gets none.
            if master_fd is not None:
                registry = ViewerRegistry(session)
                session.on_pty_output = registry.broadcast
                self._viewer_registries[key] = registry
            # Register restart-on-death BEFORE the pumps run, so even a child
            # that dies instantly is recovered (§2.7). The callback routes to
            # the manager's hook, which delegates to the lifecycle.
            session.on_death = self._on_process_death
            # Register the WP-007 per-turn guard's observation callbacks BEFORE
            # the pumps run, so the very first turn is watched (§2.7). The guard
            # arms its watchdog on turn-start and counts tool_use per turn.
            self._guards.attach(session)
            # Attach the CH-01KTMK WP-007 turn-level recovery driver to the same
            # session BEFORE the pumps run — additive: it chains onto the guard's
            # ``on_event`` seam (it does not replace it) so a live turn's
            # ``error`` Event reaches both the guard and the recovery driver
            # (ADR-001 error-event seam). Done here, beside the guard attach, so
            # the very first turn is recoverable.
            self._attach_recovery(session)
            # CH-GJ9KQR WP-007: register the durable second sink on the same
            # ``on_event`` seam BEFORE the pumps run, so the very first decoded
            # Event is tracked durably (ADR-004). Additive over the guard +
            # recovery fan-out (the live-tail path is byte-for-byte unchanged).
            self._attach_durable_sink(session)
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
        # CH-01KTMK WP-007: record the last command so the recovery driver can
        # re-submit *this* turn on a transient-blip retry (the driver's ``send``
        # capability replays the stopped turn, not an empty one). Read-only
        # bookkeeping — the FIFO / one-in-flight path below is unchanged.
        self._last_command[key] = command
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
            # Visible/headless observability (§2.12.5): io-model from the spec,
            # viewer_count from the per-session registry (the single source of
            # truth — viewer_count > 0 ⇔ visible). A pipe session has no registry,
            # so its count is 0 and io_mode "pipe" (byte-unchanged, acceptance #4).
            io_mode=session.spec.io_mode,
            viewer_count=self._viewer_count(key),
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
                    # Visible/headless observability (§2.12.5), mirroring health().
                    io_mode=session.spec.io_mode,
                    viewer_count=self._viewer_count(session.key),
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
            # WP-004: drop + close the pty session's viewer registry so every
            # attached viewer's ``stream`` ends cleanly (the end sentinel) and a
            # long-lived manager accumulates no stale registries. A pipe session
            # has no entry — ``pop`` is a no-op.
            registry = self._viewer_registries.pop(key, None)
            # CH-01KTMK WP-007: drop the per-session recovery driver + last-
            # command record so a long-lived manager accumulates no stale
            # per-key recovery state (mirrors the guard detach below). A key
            # with no recovery state — ``pop`` is a no-op.
            self._recovery_drivers.pop(key, None)
            self._last_command.pop(key, None)
            # CH-GJ9KQR WP-007: drop the per-session durable sink so a long-lived
            # manager accumulates no stale sink state (mirrors the recovery
            # driver above). A key with no sink — ``pop`` is a no-op.
            self._durable_sinks.pop(key, None)
        if registry is not None:
            registry.close()
        if session is None:
            return
        # Drop the WP-007 guard's per-turn state for this session (cancel any
        # armed watchdog) so a long-lived manager does not accumulate stale
        # entries; then tear the session down.
        self._guards.detach(session)
        session.terminate()

    # ── §2.12 attach/viewer (WP-004) ───────────────────────────────────────

    def attach(self, key: str) -> Viewer:
        """Attach a viewer to the pty-mode session for ``key`` (contract
        §2.12.2). Returns a :class:`~_session_manager.viewer.Viewer` that yields
        the scrollback snapshot then live PTY bytes (acceptance #1) and feeds
        keystrokes back into the live PTY master (acceptance #2).

        Multiple viewers may attach to one session (each renders the same
        screen); attach is additive and never restarts the process (§2.12.2).
        Attaching makes the session *visible* (``viewer_count`` rises); detaching
        the last viewer leaves it *headless* but running (§2.12.3).

        Errors: Expected ``NO_SESSION`` (no session for ``key``); Expected
        ``NOT_PTY_SESSION`` (the session is pipe io-mode — there is no terminal
        to attach to; the consumer must ``open`` with ``io_mode="pty"``, §2.15);
        Internal.
        """
        session = self._require_session(key)
        # NOT_PTY_SESSION is decided by the session's io-model, not a flag: a
        # pipe session has no pty master + no scrollback, so there is no terminal
        # to attach to. The registry exists iff the session is pty (wired at open).
        with self._registry_lock:
            registry = self._viewer_registries.get(key)
        if registry is None or session.pty_master_fd is None:
            raise ExpectedError(
                NOT_PTY_SESSION,
                f"session {key!r} is pipe io-mode; open with io_mode='pty' to "
                f"get a terminal",
            )
        return registry.attach()

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

    # ── CH-01KTMK §3.1 turn-level recovery (WP-007 wires the driver) ───────

    def _attach_recovery(self, session: Session) -> None:
        """Construct the per-session recovery driver and chain its
        error-observation hook onto the session's ``on_event`` seam (ADR-001).

        Additive by construction: the per-turn guard has already claimed
        ``on_event`` (:meth:`TurnGuardManager.attach`), so this captures the
        existing observer and installs a fan-out that calls **both** — the
        guard first (its watchdog-cancel / runaway-count must keep working
        byte-unchanged), then the manager's :meth:`_on_error_event` recovery
        hook. The guard's ``on_turn_start`` seam is untouched. Idempotent on a
        restart: ``replace_process`` keeps the same session object, so a
        re-attach simply rebuilds the same chain over the (still guard-owned)
        ``on_event`` — the driver instance for the key is reused."""
        driver = self._recovery_drivers.get(session.key)
        if driver is None:
            driver = self._make_recovery_driver(session)
            self._recovery_drivers[session.key] = driver
        self._chain_on_event(session, self._on_error_event)

    @staticmethod
    def _chain_on_event(
        session: Session, observer: Callable[[object, Event], None]
    ) -> None:
        """Chain ``observer`` onto ``session.on_event`` ADDITIVELY — the one
        definition of "add a second observer to the event seam".

        Captures the existing observer (if any) and installs a fan-out that
        calls the **prior** observer first, then ``observer``. Order matters:
        the prior fan-out (guard watchdog / recovery) must keep working
        byte-unchanged before the new observer runs. The two wave-4 attach sites
        — recovery (:meth:`_attach_recovery`) and the durable sink
        (:meth:`_attach_durable_sink`) — share this exact chaining shape; it is
        extracted here at the 2-consumer threshold (EP-03 / Blue) so the
        prior-first ordering invariant lives in exactly one place.

        The ``observer`` param is typed with a ``object`` first arg (the widest
        of the two call sites: the recovery hook is ``(Session, Event)``, the
        durable sink's :meth:`DurableAppendSink.as_event_observer` is
        ``(object, Event)`` — it ignores the session). ``object`` admits both
        under a strict type-checker, so the seam type does not disagree with
        either caller.
        """
        prior = session.on_event

        def _fan_out(s: Session, event: Event) -> None:
            if prior is not None:
                prior(s, event)
            observer(s, event)

        session.on_event = _fan_out

    # ── CH-GJ9KQR WP-007 durable second sink + resume reseed (ADR-004) ──────

    def _attach_durable_sink(self, session: Session) -> None:
        """Register the durable second sink on ``session``'s ``on_event`` seam
        (ADR-004) — additive, beside the guard + recovery fan-out.

        One thread per change (ADR-004): the thread id is the session key (the
        same change-keyed identity the manager already uses). Ensures the
        thread record exists in the store, builds (or reuses, on a restart) a
        :class:`DurableAppendSink` bound to it, **reseeds its ``_next_order``
        from the store high-water mark** (WP-004 ADV-2 — so a restart that
        rebinds to a non-empty log continues the order rather than degrading
        OUT_OF_ORDER_WRITE), and chains the sink observer onto ``on_event``
        ADDITIVELY: the existing observer fires first (the live-tail path is
        byte-for-byte unchanged), then the durable append runs as an isolated
        side-effect (it never raises into the pump, ADR-004 / WP-004 ADV-1).

        Idempotent on a restart: ``replace_process`` keeps the same Session, so
        a re-attach reuses the per-key sink and re-chains over the (still
        guard/recovery-owned) ``on_event``. The reseed is what makes resume
        correct — it is run on every attach, so first-open is a no-op (empty
        log → next_order stays 0) and a restart picks up where the log left off.
        """
        thread_id = session.key
        store = self._durable_store_for(session.key)
        self._ensure_thread_record(store, thread_id)

        sink = self._durable_sinks.get(session.key)
        if sink is None:
            sink = DurableAppendSink(store, thread_id=thread_id)
            self._durable_sinks[session.key] = sink
        # Resume reseed (WP-004 ADV-2): align the next order with the durable
        # log's high-water mark on every attach (no-op on an empty thread).
        sink.seed_next_order_from_store()

        # Chain the durable observer additively — the prior fan-out (guard +
        # recovery) fires first, then the durable append runs as an isolated
        # side-effect (``append_event`` never raises into the pump, ADR-004 /
        # WP-004 ADV-1). Same chaining shape the recovery attach uses.
        self._chain_on_event(session, sink.as_event_observer())

    def _durable_store_for(self, key: str) -> ThreadStore:
        """The durable :class:`ThreadStore` binding for ``key``'s bound change,
        from the injectable factory (the default builds the local adapter)."""
        return self._thread_store_factory(key)

    def _ensure_thread_record(self, store: ThreadStore, thread_id: str) -> None:
        """Create the thread record if it does not exist yet (idempotent).

        The durable log + memory are keyed by the thread record; the append-only
        store needs the Thread to exist before checkpoint/read ops are meaningful.
        A ``get_thread`` that raises the contract's ``THREAD_NOT_FOUND`` means
        "not created yet" → put a minimal local-binding Thread (ADR-002:
        ``platform_id='local'``); any already-present record is left untouched.

        Only ``THREAD_NOT_FOUND`` is treated as "absent → create" — a genuine
        store/IO fault (any other category) is propagated, NOT silently masked
        by a ``put_thread`` (so a real read fault surfaces honestly rather than
        being papered over with a fresh record, consistent with the contract's
        three-category error model).
        """
        try:
            store.get_thread(thread_id)
            return
        except ExpectedError as exc:
            if exc.code != THREAD_NOT_FOUND:
                raise
            # absent thread → fall through and create it (see docstring)
        now = now_iso()
        store.put_thread(
            Thread(
                id=thread_id,
                platform_id="local",
                topic=None,
                activity_summary=None,
                created_at=now,
                updated_at=now,
                participant_count=1,
                resumed_from=None,
            )
        )

    def checkpoint(self, key: str) -> ThreadMemory | None:
        """Regenerate the bound thread's ``ThreadMemory`` from the durable log —
        the Working-Set-crystallisation-boundary hook (WP-004 ADV-1).

        Called OFF the live event hot path (at a crystallisation boundary, NOT
        inside the ``on_event`` fan-out) so a checkpoint error can never stall
        the live pump. Delegates to the per-key sink's
        :meth:`DurableAppendSink.checkpoint`, which reuses the WP-003
        ``summarise_memory`` (one definition of the structured summary) and
        bumps the monotonic memory version.

        Returns the regenerated :class:`ThreadMemory`, or ``None`` if no session
        (and so no sink) is open for ``key`` — a no-op rather than an error, so a
        crystallisation tick over a key whose session has since closed is safe.
        """
        sink = self._durable_sinks.get(key)
        if sink is None:
            return None
        return sink.checkpoint()

    def _make_recovery_driver(self, session: Session) -> RecoveryDriver:
        """Build the recovery driver for ``session`` via the injected factory,
        binding the WP-005 capabilities to this session (ADR-001/002).

        The capabilities are session-bound closures — the same
        inject-what-it-needs shape ``LifecycleManager`` uses: ``send`` re-submits
        the stopped turn through the manager's FIFO (a retry is just another
        turn, never a second in-flight one); ``log_append`` surfaces every
        recovery action on the **existing** log; ``reauth`` / ``resume`` drive
        the login-expiry pause→resume via the adapter + the existing same-key/
        same-log restart; ``classify_failure`` is the adapter's provider
        detection hint. The default policy + a monotonic clock + the neutral
        classifier are selected here at the composition root (never a literal in
        the driver). The factory is injectable for tests (the ``timer_factory``
        precedent)."""
        adapter = session.adapter

        def _send() -> bool:
            # Re-submit *the stopped turn* through the manager's FIFO — the last
            # command recorded for this key (never an empty turn). The queue
            # serialises it, so a retry is just another turn, never a second
            # in-flight one (§2.6). A True ack means the retry was enqueued onto
            # the live session; the driver loops on its own observation of the
            # re-submitted turn's outcome (it does not block here). A key with no
            # recorded command (a retry with nothing to replay) is a no-op ack.
            last = self._last_command.get(session.key)
            if last is None:
                return False
            self.send(session.key, last)
            return True

        def _log_append(error: EventError) -> None:
            session.log.append(
                Event(
                    offset=-1,
                    key=session.key,
                    turn=session.turn,
                    kind="error",
                    error=error,
                )
            )

        def _reauth() -> ReauthTicket:
            return adapter.reauth()

        def _resume() -> None:
            # Trigger the existing same-key/same-log restart (resume-as-
            # capability, §2.7) — the driver triggers it, it does not
            # reimplement resume.
            self._respawn(session)

        def _classify_failure(error: EventError) -> RecoveryClass | None:
            return adapter.classify_failure(error)

        return self._recovery_driver_factory(
            send=_send,
            log_append=_log_append,
            reauth=_reauth,
            resume=_resume,
            classify_failure=_classify_failure,
            classifier=classify,
            policy=DEFAULT_RETRY_POLICY,
            clock=time.monotonic,
        )

    def _on_error_event(self, session: Session, event: Event) -> None:
        """The error-observation hook (sibling of :meth:`_on_process_death`,
        ADR-001). Routes a live turn's ``error`` Event to the session's recovery
        driver — and **only** an error event that is not a process-death.

        - **Turn-cleared reset (load-bearing for the budget).** A ``result`` that
          satisfies ``adapter.turn_complete`` means the turn genuinely completed
          — the run survived. If a transient-blip retry sequence was in progress,
          it is now over, so the driver's accumulated wall-clock budget is reset
          via :meth:`RecoveryDriver.note_turn_cleared` so a LATER, unrelated blip
          gets a fresh budget. This is the counterpart to the fire-and-forget
          ``send``: because the driver no longer treats a ``send`` ack as
          "cleared", the *clear* must be signalled by the genuine ``result``
          event. The reset is a cheap, lock-guarded state mutation on the pump
          thread — it never re-enters the FIFO, so it cannot self-deadlock.
        - **Error-only routing.** Past the turn-cleared reset, only an ``error``
          kind is routed to ``observe``; other kinds (``chunk`` / ``tool_use``,
          or a ``result`` that already triggered the reset) return.
        - **No double-handling (TDD §3.1 step 1).** A process-death
          ``STDIN_BROKEN`` error is the :class:`LifecycleManager`'s seam
          (restart-on-death); the driver must never also act on it. Filtered
          here so the two seams stay siblings, not stacked. (The WP-005 driver
          also no-ops a ``STDIN_BROKEN`` itself — this is the belt to that
          braces, keeping the manager's routing honest at the seam.)

        **Off the pump thread (load-bearing).** This hook fires on the stdout
        pump thread that appended the ``error`` (the ``on_event`` seam). The
        driver's recovery, though, re-enters the manager's FIFO — its ``send``
        capability re-submits the stopped turn via :meth:`send`/``submit``,
        which blocks until the stdin pump promotes the command; but the slot is
        only freed by *this* pump thread. Running ``observe`` inline would
        self-deadlock (the pump waits on itself). So recovery is dispatched on a
        short-lived daemon thread: the pump fans the event out and returns
        immediately, and the driver drives retry / pause→resume off-thread,
        re-entering the FIFO as just-another-turn (§2.6, one-in-flight intact).
        Daemon so a hard interpreter exit never hangs on an in-flight recovery.

        **Free the held slot before a retry replay (load-bearing).** An ``error``
        Event does not satisfy ``adapter.turn_complete`` (only a ``result``
        does), so the stdout pump never frees the one-in-flight slot for an
        errored turn — the stdin pump stays parked on ``_turn_done.wait()``
        (§2.6). For a **retryable** (transient-blip) error the driver re-submits
        the stopped turn through the FIFO, but that replay can never promote
        while the errored turn still holds the slot — the run deadlocks instead
        of recovering (BLOCKER-WP-008). So, for a transient-blip error only, the
        slot is freed here via :meth:`Session.release_turn_for_retry` (the same
        ``_turn_done.set()`` the normal completion path uses) BEFORE the driver
        is dispatched, so the parked stdin pump wakes and the replay promotes
        onto the still-live process. This runs on the **stdout** pump thread
        (which fired this event); the *stdin* pump is the one waiting, so freeing
        the slot here wakes it — no self-deadlock. A dead-end (abandoned, never
        replayed) and a login-expiry (paused, resumed via the existing same-key
        restart which frees the slot through ``replace_process``) do NOT replay
        the turn, so their held slot is harmless and is deliberately left for
        their own path — the release is surgical to the retry case, preserving
        the one-in-flight invariant (the replay re-acquires the slot as
        just-another-turn).

        Best-effort: routing must never crash the pump thread that fired the
        event (which would wedge the stdout reader), so a driver fault is
        swallowed on the recovery thread — the failure is already in the log;
        recovery is the only casualty."""
        driver = self._recovery_drivers.get(session.key)
        # Turn-cleared reset: a genuine ``result`` ends any in-progress retry
        # sequence so a later, unrelated blip gets a fresh budget (the
        # fire-and-forget ``send`` counterpart). Cheap + lock-guarded; no FIFO
        # re-entry, so it runs inline on the pump thread without deadlock risk.
        if driver is not None and session.adapter.turn_complete(event):
            driver.note_turn_cleared()
            return
        if event.kind != "error" or event.error is None:
            return
        if event.error.code == STDIN_BROKEN:
            return
        if driver is None:
            return
        error = event.error

        # Free the held one-in-flight slot for a transient-blip retry BEFORE the
        # driver replays the stopped turn, so the replay can promote (§2.6) —
        # classified with the same arbiter + adapter hint the driver uses, so the
        # manager and the driver agree on which errors are replayed. Dead-end and
        # login-expiry do not replay, so their slot is left for their own path.
        #
        # The release runs UNCONDITIONALLY for a transient-blip error (before the
        # FIX 1 coalescing gate below), even when this error is coalesced into an
        # already-in-flight sequence: the errored turn holds the slot and must
        # hand it back so SOME replay (this sequence's) can promote. The release
        # is the same idempotent ``_turn_done.set()`` the normal completion path
        # uses, so freeing an already-freed slot is harmless.
        hint = session.adapter.classify_failure(error)
        if classify(error, hint) is RecoveryClass.TRANSIENT_BLIP:
            session.release_turn_for_retry()

        # CH-01KTMK FIX 1 — one recovery thread in flight per session. Gate the
        # daemon-thread dispatch on the driver's in-flight guard: if a recovery
        # thread is already driving this session's sequence, COALESCE — the
        # existing sequence already handles the error (``observe`` serialises the
        # state under the driver's lock), so spawning a second thread would only
        # pile up sleeping recovery threads on a pathological provider's error
        # stream (thread/memory exhaustion, CONCERN-1). The slot was already freed
        # above, so the in-flight sequence's replay still promotes.
        if not driver.try_begin_recovery():
            return

        def _drive() -> None:
            try:
                driver.observe(error)
            except Exception:  # noqa: BLE001 — a recovery fault must not propagate
                pass
            finally:
                # Release the single recovery slot whatever happens (even on a
                # faulting ``observe``), so a fault never wedges recovery shut and
                # the next error is dispatched again (FIX 1).
                driver.end_recovery()

        threading.Thread(
            target=_drive,
            name=f"session-{session.key}-recovery",
            daemon=True,
        ).start()

    def _respawn(self, session: Session) -> None:
        """Spawn a fresh process for ``session``'s spec and swap it in (§2.7).

        Resume is honoured iff the adapter supports it AND a ref exists — the
        same honest rule as first ``open`` (§2.7). The fresh process replaces
        the dead one on the SAME session (same key, same log) via
        :meth:`Session.replace_process`, which restarts the pumps; the log's
        offsets keep climbing and every prior event stays readable.

        For a pty session the fresh spawn re-creates the PTY (a new
        ``os.openpty`` master, §2.12.3); the new master fd is handed to
        ``replace_process``, which closes the old master and keeps the scrollback
        across the restart (restart-is-not-a-new-key applied to scrollback)."""
        process, master_fd = self._spawn_process(session.adapter, session.spec)
        session.replace_process(process, master_fd)
        # CH-GJ9KQR WP-007 resume reseed (WP-004 ADV-2): the durable observer
        # survives ``replace_process`` (it lives on the same Session's
        # ``on_event``), but its ``_next_order`` must be realigned to the durable
        # log's high-water mark so post-restart appends continue the order rather
        # than colliding (silent OUT_OF_ORDER_WRITE degradation). Reseed off the
        # hot path here, on the restart seam — the resume is from OUR store.
        sink = self._durable_sinks.get(session.key)
        if sink is not None:
            sink.seed_next_order_from_store()

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
          (graceful: SIGTERM→SIGKILL, log closed, registry entry removed) —
          **unless it has an attached viewer**, in which case it is in-use by
          definition and exempt (#108). The in-use signal is the WP-004-owned
          :meth:`_viewer_count`, injected the same way :meth:`is_alive` is.

        Called on the background maintenance thread, and directly by tests for
        deterministic, sleep-free verification (MEA-09)."""
        with self._registry_lock:
            snapshot = list(self._sessions.items())
        self._maintenance.tick(
            snapshot,
            is_alive=self.is_alive,
            on_death=self._on_process_death,
            evict=self.close,
            viewer_count=self._viewer_count,
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

    # ── CH-GJ9KQR WP-009 live assemble→inject resume wiring (TDD §3.2) ──────

    def _compose_resume_brief(self, spec: SessionSpec) -> None:
        """Assemble the rich resume payload over OUR durable store and compose it
        into the change's brief sidecar — the live realisation of the TDD §3.2
        ``◀── assembled payload ──`` arrow (WP-009, ADR-004/005).

        The composition root (WPB-07): builds a :class:`ContextPayloadAssembler`
        bound to the change's :class:`ThreadStore` (via the same injectable
        :meth:`_durable_store_for` the durable sink uses) with the **real**
        Working Set + brain readers injected (WP-009 GAP-2 — the readers are pure
        functions of the change worktree, so the assembler still touches no
        filesystem itself, MEA-01 / WPB-01), assembles the standard-tier payload
        from OUR store (``seed_payload_for_resume``, NEVER the provider
        transcript), renders it to a vendor-neutral fragment, and composes it
        **additively** beneath the change's default brief in
        ``~/.sulis/changes/{change_id}/pre_prompt.txt`` — the EXACT sidecar the
        adapter's ``spawn_argv`` resolves at spawn.

        **Off the live event hot path + fully isolated (WP-004 ADV-1).** This
        runs at the spawn/resume seam (inside :meth:`_spawn_process`), never
        inside the ``on_event`` observer fan-out — so a payload-assembly error
        cannot stall the live pump. EVERY failure mode (no brief target, no
        checkpoint memory yet → ``MEMORY_NOT_FOUND``, a store/reader fault, a
        sidecar write error) is caught and degrades to the existing default
        brief: the rich fragment is simply absent, and the spawn proceeds
        unchanged. It NEVER raises into the spawn.
        """
        change_id = (spec.brief_change_id or "").strip()
        if not change_id:
            return  # no brief target — nothing to compose (frozen callers)
        # Defence-in-depth (path traversal): validate ``change_id`` as a real
        # change ULID BEFORE it is joined into the sidecar filesystem path — at
        # parity with the pty adapter's READ path
        # (``claude_pty._read_pre_prompt``), which gates the identical join
        # behind the same check. ``SessionSpec.__post_init__`` only rejects a
        # leading ``-`` / control chars, so ``..`` / ``/`` segments would
        # otherwise survive to a ``mkdir`` + ``write_text`` outside
        # ``~/.sulis/changes/``. A malformed id degrades (no compose) rather than
        # turning into a path — fail closed, the same isolation posture. Reuses
        # ``_wpxlib.validate_change_ulid`` (EP-03), deferred to call time so the
        # manager carries no import-time dependency on it.
        try:
            from _wpxlib import validate_change_ulid

            ok, _reason = validate_change_ulid(change_id)
        except Exception:  # noqa: BLE001 — validator unavailable → fail closed
            ok = False
        if not ok:
            _log.warning(
                "resume brief skipped: brief_change_id is not a valid change "
                "ULID (degrading to the default brief; spawn proceeds)"
            )
            return
        try:
            store = self._durable_store_for(change_id)
            assembler = ContextPayloadAssembler(
                store,
                working_set_reader=make_working_set_reader(spec.cwd, change_id),
                brain_reader=make_brain_reader(spec.cwd),
            )
            payload = seed_payload_for_resume(assembler, thread_id=change_id)
            fragment = render_payload_brief(payload)
        except Exception:  # noqa: BLE001 — isolation: degrade to the default brief
            _log.warning(
                "resume payload assembly failed for change %s (degrading to the "
                "default brief; spawn proceeds)",
                change_id,
                exc_info=True,
            )
            return
        self._compose_into_sidecar(change_id, fragment)

    def _compose_into_sidecar(self, change_id: str, fragment: str) -> None:
        """Compose ``fragment`` ADDITIVELY but IDEMPOTENTLY into the change's
        brief sidecar.

        The rich payload AUGMENTS the change's default brief; it never clobbers
        the change-binding / recon pointer the default carries (WP Contract:
        additive over ``_default_change_pre_prompt``). When the sidecar does not
        exist, the launcher's default brief is seeded first (reused, EP-03) and
        the fragment appended — so the spawn is never left with ONLY the rich
        fragment and no change binding.

        **Idempotent across re-spawns (load-bearing).** ``_spawn_process`` —
        and so this compose — runs on EVERY spawn, including ``_respawn``
        (restart-on-death + login-expiry resume, the very paths this WP serves).
        A naive append would stack a fresh fragment beneath the prior one on each
        resume, growing the brief without bound and defeating the assembler's
        token budget (the per-fragment cap does not bound the SUM). So before
        appending, any previously-composed fragment is stripped: the base is
        truncated at :data:`BRIEF_FRAGMENT_HEADER` (the one delimiter the
        renderer and this stripper share, EP-03), keeping only the content above
        it (the default brief / launcher binding). The result is exactly ONE
        resumed-context block, no matter how many times the session respawns.

        Isolated: a sidecar resolve/read/write fault is caught and logged — the
        spawn proceeds with whatever brief already exists (or none)."""
        try:
            sidecar = self._brief_sidecar_path(change_id)
            sidecar.parent.mkdir(parents=True, exist_ok=True)
            existing = (
                sidecar.read_text(encoding="utf-8")
                if sidecar.is_file()
                else self._default_brief(change_id)
            )
            # Idempotency: drop any prior resumed-context fragment (split at the
            # shared header) before appending the fresh one — a re-spawn replaces
            # rather than stacks.
            base = existing.split(BRIEF_FRAGMENT_HEADER, 1)[0]
            composed = base.rstrip() + "\n\n" + fragment + "\n"
            sidecar.write_text(composed, encoding="utf-8")
        except Exception:  # noqa: BLE001 — isolation: spawn proceeds regardless
            _log.warning(
                "composing resume brief into the sidecar failed for change %s "
                "(spawn proceeds with the existing brief)",
                change_id,
                exc_info=True,
            )

    @staticmethod
    def _brief_sidecar_path(change_id: str) -> Path:
        """The change's brief sidecar — the EXACT path the launcher writes and
        the pty adapter (``claude_pty._read_pre_prompt``) reads
        (``~/.sulis/changes/{change_id}/{_PRE_PROMPT_SIDECAR}``).

        Reuses the launcher's :data:`~_terminal_launcher._PRE_PROMPT_SIDECAR`
        filename constant (imported, not duplicated, EP-03) so the manager
        composes into the SAME file the adapter resolves at spawn — a re-point of
        the constant follows here for free, exactly as it does in the adapter. A
        launcher import failure degrades to the conventional filename rather than
        crashing the compose (isolation)."""
        try:
            import _terminal_launcher

            name = _terminal_launcher._PRE_PROMPT_SIDECAR
        except (ImportError, AttributeError):
            # The launcher module/constant is unavailable — degrade to the
            # conventional filename rather than crash the compose. Narrow to the
            # two failures an intra-package import can actually raise.
            name = "pre_prompt.txt"
        return Path.home() / ".sulis" / "changes" / change_id / name

    @staticmethod
    def _default_brief(change_id: str) -> str:
        """The change's default opening brief — reused from the launcher
        (``_terminal_launcher._default_change_pre_prompt``, EP-03) so a sidecar
        seeded here carries the SAME change-binding / recon pointer the launcher
        writes. Import is deferred to call time so the manager carries no
        launcher dependency at import time; a launcher import failure degrades to
        a minimal binding line rather than crashing the compose."""
        try:
            import _terminal_launcher

            return _terminal_launcher._default_change_pre_prompt(change_id)
        except (ImportError, AttributeError):
            # The launcher module/function is unavailable — degrade to a minimal
            # change-binding line rather than crash the compose.
            return (
                f"You are Sulis, focused on the change bound to this session "
                f"(id: {change_id})."
            )

    # ── internal helpers ────────────────────────────────────────────────────

    def _child_env(self, spec: SessionSpec) -> dict[str, str]:
        """The environment a spawned agent session is launched with (WP-003).

        Applies the Rule-of-Two credential exclusion (SPEC §L1(d), ADR-001):
        the child inherits the manager's environment **minus** every
        credential-bearing variable, **plus** the sanctioned safe-fetch proxy
        endpoint the agent-facing tool reads. The exclusion is the *primary*
        control — the credential is not in the fetch path's scope — and WP-002's
        outbound scrub is defence-in-depth on top.

        Honoured override: a deployment that exports ``SULIS_SAFE_FETCH_PROXY``
        in the manager's own environment points sessions at that endpoint;
        otherwise the conventional loopback default is used. (Reading it before
        the exclusion is fine — the endpoint var is not credential-named, and it
        is re-set explicitly afterwards regardless.)

        Per-session change binding (this change's ADR-001): ``spec.brief_change_id``
        is stamped onto the child as ``SULIS_CHANGE_ID``, overriding the daemon's
        inherited launch-time value; a spec with no target change yields no
        ``SULIS_CHANGE_ID`` in the child (no stale inheritance).

        Previously ``Popen`` was called with no ``env=`` and inherited the full
        parent environment; this makes the child environment explicit so the
        exclusion is enforced. The pipe/pty branch logic is untouched."""
        endpoint = os.environ.get(PROXY_ENDPOINT_ENV, DEFAULT_SAFE_FETCH_PROXY_ENDPOINT)
        return child_spawn_env(
            os.environ, proxy_endpoint=endpoint, change_id=spec.brief_change_id
        )

    def _spawn_process(
        self, adapter: ProviderAdapter, spec: SessionSpec
    ) -> tuple[subprocess.Popen, int | None]:
        """Launch one child process for ``spec`` via ``adapter.spawn_argv``.

        The single spawn path shared by first ``open`` and restart-on-death
        ``_respawn`` (§2.7) — and the **single seam** the io-model branches at
        (contract §2.12.1, ADR-001; WPB-07 composition root). Returns
        ``(process, master_fd)``: ``master_fd`` is ``None`` for the default pipe
        io-model and the manager-owned PTY master end for the pty io-model.
        Extracted so the resume-flag decision and the spawn error mapping live in
        exactly one place.

        - **pipe** (default): today's ``subprocess.Popen`` with stdin/stdout/
          stderr all PIPEs (§2.8 transport) — byte-for-byte unchanged.
        - **pty** (§2.12.1): ``os.openpty()`` allocates a master/slave pair
          (stdlib, ADR-001 alt #4 rejection — no third-party pty lib); the child
          is spawned with the slave fd as stdin/stdout/stderr (its controlling
          terminal), the slave is closed in the parent (the child holds it), and
          the master fd is returned for the session's master-reader pump.

        Errors: Protocol ``SPAWN_FAILED`` (the pipe spawn failed); Internal
        ``PTY_OPEN_FAILED`` (``os.openpty`` / the pty spawn failed, §2.15)."""
        # CH-GJ9KQR WP-009: ASSEMBLE the rich resume payload from OUR durable
        # store and COMPOSE it into the change's brief sidecar BEFORE the adapter
        # resolves the brief (``spawn_argv`` reads ``pre_prompt.txt``, ADR-004/
        # 005). This is the live realisation of the TDD §3.2 brief-injection
        # arrow. Fully isolated: any failure degrades to the existing default
        # brief — it never raises into the spawn (WP-004 ADV-1, applied at the
        # spawn/resume seam, OFF the live event hot path).
        self._compose_resume_brief(spec)
        argv = adapter.spawn_argv(spec)
        if spec.io_mode == "pty":
            return self._spawn_pty_process(argv, spec)
        try:
            process = subprocess.Popen(
                argv,
                cwd=spec.cwd,
                env=self._child_env(spec),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except (OSError, ValueError) as exc:
            raise ProtocolError(
                SPAWN_FAILED,
                f"could not spawn {spec.provider!r}: {exc}",
            ) from exc
        return process, None

    def _spawn_pty_process(
        self, argv: list[str], spec: SessionSpec
    ) -> tuple[subprocess.Popen, int]:
        """Spawn ``argv`` on a fresh PTY the manager owns from birth (§2.12.1).

        Allocates the master/slave pair with ``os.openpty()`` (stdlib, ADR-001),
        launches the child with the slave end as its controlling terminal
        (stdin/stdout/stderr → slave), closes the slave in the parent (the child
        holds it; the parent keeps only the master), and returns
        ``(process, master_fd)``. The manager **owns its own PTY** — it spawns
        its own child onto it, exactly as it owns its pipe-backed child today; it
        never drives a terminal it did not spawn (ADR-001, foundation alt #4
        rejection).

        Any failure — ``os.openpty`` (fd exhaustion / kernel pty limit) or the
        spawn-with-slave — maps to Internal ``PTY_OPEN_FAILED`` (§2.15): a
        resource/bug condition to log + escalate, not a retry-with-backoff
        transport decline. Both fds are closed on a spawn failure so a failed
        open leaks no fd."""
        try:
            master_fd, slave_fd = os.openpty()
        except OSError as exc:
            raise InternalError(
                PTY_OPEN_FAILED,
                f"os.openpty() failed for {spec.provider!r}: {exc}",
            ) from exc
        try:
            process = subprocess.Popen(
                argv,
                cwd=spec.cwd,
                env=self._child_env(spec),
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                close_fds=True,
            )
        except (OSError, ValueError) as exc:
            for fd in (slave_fd, master_fd):
                try:
                    os.close(fd)
                except OSError:
                    pass
            raise InternalError(
                PTY_OPEN_FAILED,
                f"could not spawn {spec.provider!r} on a pty: {exc}",
            ) from exc
        # The child now holds the slave end as its controlling tty; the parent
        # keeps only the master. Close the parent's slave copy.
        try:
            os.close(slave_fd)
        except OSError:
            pass
        return process, master_fd

    def _viewer_count(self, key: str) -> int:
        """The attached-viewer count for ``key`` — ``viewer_count`` (§2.12.5).

        Reads the per-session :class:`ViewerRegistry`'s live count (the single
        source of truth for visible/headless); a session with no registry (a pipe
        session, or one already closed) is headless: ``0``. Cheap + side-effect-
        free, as the §2.3 observational surface requires."""
        with self._registry_lock:
            registry = self._viewer_registries.get(key)
        return registry.count if registry is not None else 0

    def _require_session(self, key: str) -> Session:
        """Return the live session for ``key`` or raise Expected
        ``NO_SESSION``. The single place the absence-of-session decline is
        raised, so every method speaks the same §2.9 code."""
        with self._registry_lock:
            session = self._sessions.get(key)
        if session is None:
            raise ExpectedError(NO_SESSION, f"no open session for key {key!r}")
        return session
