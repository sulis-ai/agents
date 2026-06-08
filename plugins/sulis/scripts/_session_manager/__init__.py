"""``_session_manager`` — internal package for the provider-neutral session
manager (SESSION_MANAGER_CONTRACT, CH-01KTAD · persistent-chat-sessions).

A ``SessionManager`` owns warm, long-lived agent processes — one per
caller-supplied key — each holding an append-only, offset-addressed event log.
Submitting input and reading output are decoupled operations (§2.2). The
manager depends only on a ``ProviderAdapter`` seam, so providers are swappable
with zero change to the manager or either consumer.

Arrivals so far: WP-002 (``events.py`` — the shared event vocabulary + the
three-category error model, the Form invariant every layer speaks), WP-001
(``event_log.py`` — the append-only, offset-addressed per-session log + cursor
read, contract §2.5), WP-003 (``adapter.py`` — the ``ProviderAdapter``
seam + ``Capabilities`` / ``SessionSpec``, contract §2.4 — plus
``adapters/claude.py``, the Claude adapter #1), and WP-004 (``manager.py`` —
the ``SessionManager`` six-method surface; ``session.py`` — one warm
``Session`` with three pump threads + the one-in-flight FIFO queue;
``state.py`` — the ``Health`` / ``SessionStatus`` snapshot types), and WP-005
(``lifecycle.py`` — restart-on-death + resume-as-capability + recovery budget,
filling the manager's ``_on_process_death`` hook; ``state.py`` grows the
``SessionState`` enum + the enforced ``StateMachine`` — the §2.7 session state
machine the manager owns and consumers never touch), and WP-006
(``maintenance.py`` — idle-eviction + LRU memory-cap + dead-process detection,
filling the manager's ``_maintenance_tick`` hook; the cap default derives from
host RAM with a conservative floor via ``derive_cap`` (§2.7); ``status()`` now
reports a best-effort per-session ``memory_bytes``), and WP-007 (``guards.py`` —
per-turn runaway / timeout guards, filling the manager's last extension hook
``_guard``: a per-turn watchdog (``threading.Timer`` armed at turn-start,
cancelled on the terminal ``result``) trips ``TERMINATED_TIMEOUT`` and a per-turn
``tool_use`` counter trips ``TERMINATED_RUNAWAY``; both surface an ``error`` Event
into the log *before* the terminal state, then kill the child so WP-005's
restart-on-death recovers it — a guard terminal is recoverable within the
recovery budget, not a permanent disable. ``state.py`` grows the
``TERMINATED_* → DEAD`` recovery edges in the same transition map). All three
extension hooks the WP-004 core reserved (``_on_process_death`` / ``_maintenance_\
tick`` / ``_guard``) are now filled by delegation, so the §2.2 six-method core
flow stayed lean.

Interactive-terminal extension (CH-01KTGY, contract extension §2.11–§2.15):
WP-002 added ``scrollback.py`` (``ScrollbackBuffer`` — the bounded raw-byte ring,
the second content model, §2.11); WP-003 adds the **PTY io-model** as an additive
branch at the single spawn seam (``manager._spawn_process``): a defaulted
``SessionSpec.io_mode`` (``"pipe"`` | ``"pty"``, §2.12.1, immutable "PTY from
birth") selects it, a ``pty`` open allocates an ``os.openpty()`` pair the manager
owns, spawns the child with the slave as its controlling tty, and runs ONE
generation-bound master-reader pump (``session._pty_master_pump``) that appends
raw bytes into the session's ``ScrollbackBuffer`` — restart re-creates the PTY
while keeping the scrollback (§2.12.3). The pipe path is byte-for-byte unchanged
(``io_mode`` defaults to ``"pipe"`` — acceptance #4). New error code
``PTY_OPEN_FAILED`` (Internal, §2.15) maps ``os.openpty`` / pty-spawn failure onto
the existing three-category model. WP-004 added ``viewer.py`` (the ``attach``/
``Viewer`` port — snapshot-then-live join, verbatim keystroke ``feed``,
detach-leaves-running; §2.12) and the ``io_mode`` / ``viewer_count`` observability
on ``Health`` / ``SessionStatus`` (§2.12.5). WP-005 adds ``socket_server.py``
(``SocketServer`` — the §2.8 Unix-domain NDJSON socket-serving layer): the remote
adapter that serves BOTH the six chat methods (§2.2) and the four terminal methods
(``attach`` streaming + ``feed`` / ``detach`` / ``resize``, §2.13) over a local
``AF_UNIX`` socket so the cockpit can consume the in-process manager cross-language
(ADR-003 — one channel, one auth surface). Raw terminal bytes are base64-encoded
on the wire (§2.13.1 — the socket is the ONLY layer that encodes; the in-process
viewer speaks raw bytes). The §2.13.4 attach-authorisation gate is the
local-socket filesystem permission (``0o600``) plus an optional per-connection
binding resolver that scopes a connection to one change (a connection bound to
change X may not attach change Y) — declined as Expected ``NOT_AUTHORIZED``, no new
auth invented. The headless chat path over the socket behaves exactly as the base
contract (acceptance #4 regression gate).

Reliability layer (CH-01KTMK, automation-reliability-recovery): WP-001 lands
the shared recovery data contract — ``classifier.py`` (``RecoveryClass``, the
provider-neutral verdict vocabulary ``TRANSIENT_BLIP`` / ``DEAD_END`` /
``LOGIN_EXPIRED``, ADR-003) and ``recovery.py`` (``RetryPolicy`` frozen
dataclass + the ``DEFAULT_RETRY_POLICY`` 12-min full-jitter fallback constant,
ADR-002; ``next_delay_ceiling``, the jitter-free backoff-ceiling core, and
``next_delay`` (WP-003), the full-jitter curve — ``random_between(0, ceiling)``
with an injectable RNG, ``None`` on budget exhaustion — the driver schedules
on; and ``ReauthTicket``, the
re-login-link + completion-handle value object ``adapter.reauth()`` returns,
ADR-003/004). These are pure, frozen value objects — the producer/consumer
seam the classifier (WP-002), the policy (WP-003), and the recovery driver
(WP-005) are all built against in parallel. No new error code is introduced:
login-expiry rides the existing ``NOT_AUTHORIZED`` code. The contract's
example tables (the classification truth table + the ``next_delay`` stubs)
live as a single shared test fixture (``tests/unit/_recovery_contract_\
fixtures.py``) the downstream WP suites consume, so the verdict vocabulary is
never re-spelled on either side of the seam (CF-11). WP-002 adds the producer:
``classifier.classify(error, adapter_hint) -> RecoveryClass`` — the pure,
total neutral arbiter that maps an observed ``EventError`` to a verdict, using
the per-provider hint when present and the category default otherwise
(``protocol`` → transient-blip, ``internal`` → dead-end, ``expected`` →
dead-end except ``NOT_AUTHORIZED`` → login-expired; an unknown code with no
hint falls through to the safe dead-end rather than raising). It imports
``events.py`` only — never the provider seam (ADR-003), so a provider's raw
``"401"`` interpretation stays in that provider's ``classify_failure`` hint.
WP-005 adds the consumer: ``recovery.RecoveryDriver`` — the turn-level Armor
primitive (ADR-001), the sibling of ``LifecycleManager`` (process-death) for a
*live session's turn* that ended in an ``error`` Event. Built against injected
manager capabilities (``send`` to re-submit, ``log_append`` to surface every
action on the existing log, ``reauth`` + ``resume`` for login-expiry, the
adapter's ``classify_failure`` hint) plus an injected ``clock`` / ``sleep`` /
``rng`` so the wall-clock retry budget is exercised deterministically and
sleep-free (MEA-09). ``observe(error)`` runs the §3.1 pipeline: skip a
``STDIN_BROKEN`` process-death (the lifecycle owns it — no double-handling),
classify, then branch — **transient-blip** retries with full-jitter backoff via
the existing ``send`` until it clears or ``next_delay`` returns ``None`` (budget
exhausted → abandoned with a typed Event, never a silent hang); **dead-end**
abandons immediately without consulting the budget; **login-expired** calls
``reauth()`` once, surfaces a ``NOT_AUTHORIZED`` notification carrying the
re-login link, pauses (budget NOT burned), and on ``complete_reauth`` resumes
via the **existing** ``supports_resume`` + ``resume_ref`` path so the agent
re-runs the incomplete step (no fabricated completion, ADR-004). WP-007 wires
it to the live manager: ``manager.py`` constructs a **per-session**
``RecoveryDriver`` at the composition root (beside the ``LifecycleManager``
wiring) — its capabilities bound to that session (``send`` replays the last
recorded command through the FIFO, ``log_append`` surfaces on the existing log,
``reauth`` / ``resume`` drive login-expiry pause→resume) with the default policy
+ a monotonic clock + the neutral classifier + the adapter's ``classify_failure``
hint. The driver attaches at the manager's **error-event observation seam** —
the ``_on_error_event`` hook, a sibling of ``_on_process_death`` (ADR-001) —
which chains additively onto the existing ``on_event`` callback the per-turn
guard already owns (the guard's observation is byte-unchanged). Each live
``error`` Event that is not a process-death ``STDIN_BROKEN`` is routed to the
driver on an isolated daemon thread (so the driver's FIFO-re-entrant recovery
never blocks the pump thread that observed the error); a ``STDIN_BROKEN`` is
filtered at the seam (the lifecycle owns process death — no double-handling).
The wiring is additive: the existing turn-complete / one-in-flight / state-
machine behaviour is untouched, guarded by the session-manager unit + integration
suite staying green.

The leading underscore signals "foundation-internal" — exactly as ``_discovery``
and ``_canonical_drift`` do. The public surface is re-exported here so callers
import from the package, not its sub-modules.
"""

from __future__ import annotations

from _session_manager.adapter import (
    Capabilities,
    ProviderAdapter,
    SessionSpec,
)
from _session_manager.adapters.claude import ClaudeAdapter
from _session_manager.classifier import RecoveryClass, classify
from _session_manager.event_log import (
    EventLog,
    OffsetEvictedError,
    OffsetOutOfRangeError,
)
from _session_manager.scrollback import ScrollbackBuffer
from _session_manager.events import (
    CWD_NOT_FOUND,
    DECODE_FAILED,
    LOG_CORRUPT,
    NO_SESSION,
    NOT_AUTHORIZED,
    NOT_PTY_SESSION,
    OFFSET_EVICTED,
    PTY_OPEN_FAILED,
    SESSION_DISABLED,
    SOCKET_CLOSED,
    SPAWN_FAILED,
    STDIN_BROKEN,
    UNKNOWN_PROVIDER,
    ErrorCategory,
    Event,
    EventError,
    EventKind,
    ExpectedError,
    InternalError,
    ProtocolError,
    SessionError,
    ToolUse,
    TurnResult,
)
from _session_manager.guards import (
    DEFAULT_MAX_TOOL_CALLS,
    DEFAULT_TURN_TIMEOUT_SECONDS,
    RUNAWAY,
    TURN_TIMEOUT,
    TurnGuardManager,
)
from _session_manager.lifecycle import (
    DEFAULT_RECOVERY_BUDGET,
    LifecycleManager,
)
from _session_manager.maintenance import (
    DEFAULT_IDLE_TIMEOUT_SECONDS,
    DEFAULT_MAINTENANCE_INTERVAL_SECONDS,
    MEMORY_CAP_FLOOR,
    MaintenanceManager,
    default_cap,
    derive_cap,
)
from _session_manager.manager import SessionManager
from _session_manager.recovery import (
    DEFAULT_RETRY_POLICY,
    ReauthTicket,
    RecoveryDriver,
    RetryPolicy,
    next_delay,
    next_delay_ceiling,
)
from _session_manager.session import Session
from _session_manager.socket_server import SocketServer
from _session_manager.state import (
    Health,
    SessionState,
    SessionStatus,
    StateMachine,
)

__all__ = [
    # event vocabulary (§2.3)
    "Event",
    "EventKind",
    "ToolUse",
    "TurnResult",
    "EventError",
    # event log + cursor (§2.5)
    "EventLog",
    "OffsetEvictedError",
    "OffsetOutOfRangeError",
    # terminal-scrollback content model (§2.11) — WP-002
    "ScrollbackBuffer",
    # provider adapter seam (§2.4)
    "ProviderAdapter",
    "Capabilities",
    "SessionSpec",
    "ClaudeAdapter",
    # manager core surface (§2.2) — WP-004
    "SessionManager",
    "Session",
    "Health",
    "SessionStatus",
    # session state machine + lifecycle (§2.7) — WP-005
    "SessionState",
    "StateMachine",
    "LifecycleManager",
    "DEFAULT_RECOVERY_BUDGET",
    # maintenance: idle-eviction + LRU memory-cap + dead-detection (§2.7) — WP-006
    "MaintenanceManager",
    "derive_cap",
    "default_cap",
    "MEMORY_CAP_FLOOR",
    "DEFAULT_IDLE_TIMEOUT_SECONDS",
    "DEFAULT_MAINTENANCE_INTERVAL_SECONDS",
    # per-turn runaway / timeout guards (§2.7) — WP-007
    "TurnGuardManager",
    "TURN_TIMEOUT",
    "RUNAWAY",
    "DEFAULT_TURN_TIMEOUT_SECONDS",
    "DEFAULT_MAX_TOOL_CALLS",
    # §2.8 Unix-domain NDJSON socket-serving layer (chat + terminal) — WP-005
    "SocketServer",
    # reliability layer: recovery vocabulary + retry policy (CH-01KTMK WP-001)
    "RecoveryClass",
    # reliability layer: provider-neutral classifier (CH-01KTMK WP-002)
    "classify",
    "RetryPolicy",
    "DEFAULT_RETRY_POLICY",
    "next_delay_ceiling",
    "next_delay",
    "ReauthTicket",
    # reliability layer: the turn-level recovery driver (CH-01KTMK WP-005)
    "RecoveryDriver",
    # error model (§2.9)
    "SessionError",
    "ProtocolError",
    "ExpectedError",
    "InternalError",
    "ErrorCategory",
    # error code constants (§2.9)
    "SPAWN_FAILED",
    "STDIN_BROKEN",
    "SOCKET_CLOSED",
    "NO_SESSION",
    "UNKNOWN_PROVIDER",
    "CWD_NOT_FOUND",
    "OFFSET_EVICTED",
    "SESSION_DISABLED",
    "DECODE_FAILED",
    "LOG_CORRUPT",
    # pty io-model spawn failure (§2.15) — CH-01KTGY WP-003
    "PTY_OPEN_FAILED",
    # attach on a pipe session (§2.15) — CH-01KTGY WP-004/005
    "NOT_PTY_SESSION",
    # §2.13.4 attach-authorisation decline (the binding guard) — CH-01KTGY WP-005
    "NOT_AUTHORIZED",
]
