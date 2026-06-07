"""``_session_manager.events`` — the shared, provider-neutral event vocabulary
and the three-category error model.

This module is the **Form invariant** of the session manager
(SESSION_MANAGER_CONTRACT §2.3 + §2.9): the four event kinds
(``chunk`` / ``tool_use`` / ``result`` / ``error``) and the three error
categories (Protocol / Expected / Internal) that *every* layer speaks. The
log (WP-001) carries these records; each provider adapter's ``decode()``
(WP-003) produces them; the manager and both consumers only ever see them.

Defining them once, frozen and validated at construction, is what keeps
providers swappable: the types are the contract, so a new adapter slots in
with no change to the manager or either consumer.

**Deliberately dependency-free.** This module imports nothing from the log or
the manager — those depend on it, never the reverse. It is the innermost
domain layer (WPB-01): pure value objects, zero infrastructure.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

# ── §2.9 error code constants ─────────────────────────────────────────────
# Module-level string constants so call sites reference a symbol instead of
# typing the literal — a typo at a call site becomes a NameError, not a
# silently-wrong code string that drifts from the contract.

# Protocol — transport/process failed before the op ran.
SPAWN_FAILED = "SPAWN_FAILED"
STDIN_BROKEN = "STDIN_BROKEN"
SOCKET_CLOSED = "SOCKET_CLOSED"

# Expected — the op ran and deterministically declined.
NO_SESSION = "NO_SESSION"
UNKNOWN_PROVIDER = "UNKNOWN_PROVIDER"
CWD_NOT_FOUND = "CWD_NOT_FOUND"
OFFSET_EVICTED = "OFFSET_EVICTED"
SESSION_DISABLED = "SESSION_DISABLED"

# Internal — an unexpected crash (a bug).
DECODE_FAILED = "DECODE_FAILED"
LOG_CORRUPT = "LOG_CORRUPT"


EventKind = Literal["chunk", "tool_use", "result", "error"]
ErrorCategory = Literal["protocol", "expected", "internal"]


# ── §2.3 event payloads ───────────────────────────────────────────────────


@dataclass(frozen=True)
class ToolUse:
    """Payload for ``kind="tool_use"`` — the agent invoked a tool."""

    name: str
    input_summary: str


@dataclass(frozen=True)
class TurnResult:
    """Payload for ``kind="result"`` — the turn finished, with usage."""

    input_tokens: int
    output_tokens: int
    duration_ms: int
    stop_reason: str


@dataclass(frozen=True)
class EventError:
    """Payload for ``kind="error"`` — a typed failure carried *in the log*.

    Mirrors the (category, code, message) shape of the raised
    :class:`SessionError` exceptions (§2.9) so an in-process failure and a
    logged failure share one shape.
    """

    category: ErrorCategory
    code: str
    message: str


# ── §2.3 the log's record type ────────────────────────────────────────────

# Which payload field each kind requires. The four kinds partition the four
# optional payloads one-to-one: the chosen kind's field must be set, and every
# other payload field must be None. This table drives the __post_init__ check
# so the rule lives in exactly one place.
_REQUIRED_PAYLOAD: dict[str, str] = {
    "chunk": "text",
    "tool_use": "tool",
    "result": "result",
    "error": "error",
}
_ALL_PAYLOAD_FIELDS: tuple[str, ...] = ("text", "tool", "result", "error")


@dataclass(frozen=True)
class Event:
    """One record in a session's append-only event log (§2.3).

    Exactly one of ``text`` / ``tool`` / ``result`` / ``error`` is set,
    selected by ``kind``; the others stay ``None``. The constructor enforces
    this so a malformed Event fails loudly here, not three layers later.
    """

    offset: int
    key: str
    turn: int
    kind: EventKind
    text: str | None = None
    tool: ToolUse | None = None
    result: TurnResult | None = None
    error: EventError | None = None

    def __post_init__(self) -> None:
        required = _REQUIRED_PAYLOAD.get(self.kind)
        if required is None:
            raise ValueError(
                f"unknown Event kind {self.kind!r}; "
                f"expected one of {tuple(_REQUIRED_PAYLOAD)}"
            )
        if getattr(self, required) is None:
            raise ValueError(
                f"Event(kind={self.kind!r}) requires the {required!r} payload"
            )
        foreign = [
            field
            for field in _ALL_PAYLOAD_FIELDS
            if field != required and getattr(self, field) is not None
        ]
        if foreign:
            raise ValueError(
                f"Event(kind={self.kind!r}) must not carry {foreign}; "
                f"only {required!r} is permitted for this kind"
            )


# ── §2.9 the three-category error model (in-process binding) ──────────────


class SessionError(Exception):
    """Base for the three error categories (§2.9).

    Concrete subclasses set the ``category`` class attribute; every instance
    carries a ``code`` (one of the module-level constants) and a message.
    """

    category: ErrorCategory

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class ProtocolError(SessionError):
    """Transport/process failed before the op ran (retry-with-backoff)."""

    category: ErrorCategory = "protocol"


class ExpectedError(SessionError):
    """The op ran and deterministically declined (adjust inputs / re-open)."""

    category: ErrorCategory = "expected"


class InternalError(SessionError):
    """An unexpected crash — a bug (log + escalate; do not retry)."""

    category: ErrorCategory = "internal"
