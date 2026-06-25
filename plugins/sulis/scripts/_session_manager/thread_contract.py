"""``_session_manager.thread_contract`` — the thread/message/memory +
context-payload **contract** (CH-GJ9KQR WP-001).

This is the producer↔consumer seam (CONTRACT_FIRST CF-01/CF-02, lightweight
internal tier), defined **before** any producer or consumer code. It pins, in
one place every side imports:

- the **ADR-001 types**, mirroring the platform thread-sdk ``ONTOLOGY.jsonld``
  field-for-field — ``Thread`` / ``ThreadParticipant`` / ``ThreadMemory`` /
  ``ThreadMemoryContent`` / ``ThreadMessage`` / ``ExplorationJournalEntry``.
  Our two additive fields (``Thread.resumed_from`` the resume chain, ADR-003;
  ``ThreadMessage.order`` the stable offset, TDD §3.3) are the only superset
  additions; everything else is the platform's names + enums verbatim
  (ADR-001 forbids a fork);
- the **``ContextPayload``** value + the tier enum (lean/standard/full) + the
  payload **pointer** (``thread_id`` + the raw-fetch tool affordance, ADR-005)
  — rich-by-default content inline, raw-on-demand via the ``thread_context``
  MCP tool;
- the **``ThreadStore`` port** — the write surface (the session pump's sink:
  ``append_message`` / ``put_memory``) + the read surface (the discovery seam:
  ``get_thread`` / ``get_memory`` / ``get_messages``);
- the **three universal error categories**, **reused verbatim** from
  ``_session_manager.events`` (CF-03 — no second hierarchy), plus a
  ``PermissionError`` carried for the future hosted binding (ADR-002,
  NFR-SEC05; not enforced on the loopback path);
- the **pinned store-root path convention** + on-disk record filename scheme
  (CF-11), so producer WPs reference them verbatim;
- the **in-memory ``ThreadStore`` adapter stub** — the shared contract-test
  subject the real local adapter (WP-002) will also run against (CF-04 / §5).

**Transport-agnostic (CF-02 / ADR-002 hybrid).** Nothing here touches a
network, a transport, or a provider. The same contract binds to a local
library call today and a hosted REST transport later — only the binding moves.

**Dependency direction (MEA-01 / WPB-01).** This module depends only on the
provider-neutral ``events`` error model — never on a provider, a subprocess,
or the cockpit web layer. It is a pure domain layer.

**Caution for consumers.** ``PermissionError`` here intentionally shadows the
builtin (it is the contract's NFR-SEC05 refusal type). A consumer that does
``from _session_manager.thread_contract import PermissionError`` — or a
``*`` import — rebinds the name in its namespace; code in that module that
means to catch the *OS* ``PermissionError`` (e.g. a file-perm error in the
durable adapter, WP-002) must reference ``builtins.PermissionError``
explicitly to disambiguate.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Protocol, runtime_checkable

# CF-03: the three universal error categories are reused verbatim from the
# existing session-manager error model — no second hierarchy. They are
# re-exported here so producer + consumer import the contract's errors from one
# place.
from _session_manager.events import (  # noqa: F401  (re-exported as the contract surface)
    ExpectedError,
    InternalError,
    ProtocolError,
    SessionError,
)

# ── enums (platform ONTOLOGY values, used as-is — ADR-001/ADR-002) ─────────

ParticipantType = Literal["user", "studio_agent"]
PARTICIPANT_TYPES: tuple[ParticipantType, ...] = ("user", "studio_agent")

MessageRole = Literal["question", "answer", "observation", "decision"]
MESSAGE_ROLES: tuple[MessageRole, ...] = (
    "question",
    "answer",
    "observation",
    "decision",
)

ExplorationEntryType = Literal[
    "question", "answer", "pattern_detected", "decision_captured"
]
EXPLORATION_ENTRY_TYPES: tuple[ExplorationEntryType, ...] = (
    "question",
    "answer",
    "pattern_detected",
    "decision_captured",
)

PayloadTier = Literal["lean", "standard", "full"]
PAYLOAD_TIERS: tuple[PayloadTier, ...] = ("lean", "standard", "full")


# ── error codes (the contract's Expected-category vocabulary, CF-03) ───────
# String constants so call sites reference a symbol (a typo becomes a
# NameError, not a silently-wrong code) — the same discipline as events.py.

# Expected — the op ran and deterministically declined.
THREAD_NOT_FOUND = "THREAD_NOT_FOUND"
MEMORY_NOT_FOUND = "MEMORY_NOT_FOUND"
OUT_OF_ORDER_WRITE = "OUT_OF_ORDER_WRITE"
DUPLICATE_MESSAGE = "DUPLICATE_MESSAGE"
STALE_MEMORY_VERSION = "STALE_MEMORY_VERSION"
INVALID_ID = "INVALID_ID"
# Carried for the future hosted binding (NFR-SEC05); not raised on loopback.
NOT_A_PARTICIPANT = "NOT_A_PARTICIPANT"


class PermissionError(ExpectedError):  # noqa: A001  (shadows builtin by contract design)
    """Participant-scoped authorisation refusal (NFR-SEC05, ADR-002).

    Carried in the contract so a future hosted binding enforces participant
    scoping **without a contract change**. It is an Expected-category
    deterministic refusal (the op ran and declined), not a new error category —
    it slots into the existing three-category model. **Not enforced on the
    local loopback path** (single founder, no JWT / ``platform_id``).
    """


# ── ADR-001 types (field-for-field with the platform ONTOLOGY) ─────────────


@dataclass(frozen=True)
class Thread:
    """Workspace-independent conversation unit scoped to a platform.

    Platform ONTOLOGY ``Thread`` + the one additive field ``resumed_from`` —
    our resume chain (ADR-003). ``platform_id="local"`` on the loopback binding
    (ADR-002); the field exists so the hosted binding can populate it from JWT.
    """

    id: str
    platform_id: str
    topic: str | None
    activity_summary: str | None
    created_at: str
    updated_at: str
    participant_count: int
    resumed_from: str | None = None  # additive (ADR-003): prior thread id


@dataclass(frozen=True)
class ThreadParticipant:
    """User or studio agent participating in a Thread (platform ONTOLOGY)."""

    id: str
    thread_id: str
    participant_id: str
    participant_type: ParticipantType
    joined_at: str
    role: str | None = None


@dataclass(frozen=True)
class ThreadMessage:
    """A message within thread memory.

    Platform ONTOLOGY ``ThreadMessage`` + the one additive field ``order`` —
    our stable, monotonic offset (the log is offset-ordered, TDD §3.3). ``role``
    is the platform enum or ``None``.
    """

    id: str
    participant_id: str
    participant_type: ParticipantType
    content: str
    role: MessageRole | None
    created_at: str
    order: int = 0  # additive: stable monotonic offset


@dataclass(frozen=True)
class ExplorationJournalEntry:
    """Structured exploration journal entry (platform ONTOLOGY, BR-25)."""

    type: ExplorationEntryType
    content: str
    created_at: str
    participant_id: str | None = None
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class ThreadMemoryContent:
    """The structured content of thread memory (platform ONTOLOGY).

    ``participant_context`` is the platform's open-ended object — where
    Sulis-specific context (bound ``change_id``, provider identity) lives
    without renaming a platform field (ADR-001 consequences).
    """

    messages: list[ThreadMessage] = field(default_factory=list)
    exploration_journal: list[ExplorationJournalEntry] = field(default_factory=list)
    participant_context: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ThreadMemory:
    """Structured conversation memory for a Thread, 1:1 with Thread, versioned
    (platform ONTOLOGY). ``version`` increments on each checkpoint
    regeneration."""

    thread_id: str
    version: int
    content: ThreadMemoryContent
    created_at: str
    updated_at: str


# ── the context payload (ADR-005 discovery seam) ──────────────────────────

# The raw-fetch affordance: the name of the read-only MCP tool that exposes the
# store's read ops to the agent (ADR-005). Pinned in the contract so producer
# (assembler) + consumer (the tool) agree on one name.
RAW_FETCH_TOOL_NAME = "thread_context"


@dataclass(frozen=True)
class ContextPayload:
    """The assembled, vendor-neutral context payload delivered to a (re)spawned
    agent (ADR-005).

    **Rich-by-default**: the structured ``memory`` (ADR-001 ThreadMemory.content
    — summary + exploration journal + participant context) is carried **inline**
    so the common path needs no round-trip. **Raw-on-demand**: the pointer
    (``thread_id`` + ``raw_fetch_tool``) tells the agent where the full record
    lives and which tool fetches it. ``tier`` is the token-budget the assembler
    honoured (WP-003 enforces the budget; the shape is pinned here).
    """

    thread_id: str
    tier: PayloadTier
    memory: ThreadMemoryContent
    raw_fetch_tool: str = RAW_FETCH_TOOL_NAME


# ── the ThreadStore port (TDD §3.3) ────────────────────────────────────────


@runtime_checkable
class ThreadStore(Protocol):
    """The persistence port the cockpit domain owns (EXPAND-Create, not a wrap).

    Transport-agnostic (ADR-002): the in-memory adapter (this module) and the
    durable local adapter (WP-002) both conform; the hosted REST adapter is the
    future second adapter behind the same port. The write surface is the
    session pump's sink; the read surface is the discovery seam.
    """

    # write (producer-side, session pump)
    def append_message(self, thread_id: str, message: ThreadMessage) -> None: ...

    def put_memory(self, thread_id: str, memory: ThreadMemory) -> None: ...

    # read (discovery seam)
    def get_thread(self, thread_id: str) -> Thread: ...

    def get_memory(self, thread_id: str) -> ThreadMemory: ...

    def get_messages(
        self, thread_id: str, since: int | None = None, limit: int | None = None
    ) -> list[ThreadMessage]: ...


# ── pinned store-root path convention + record filename scheme (CF-11) ─────

# A store id (change_id / thread_id) is interpolated into a filesystem path +
# a record filename. The id charset is pinned here — alphanumerics plus the
# id-shape punctuation our ids actually use (`-`, `_`) — so a traversing or
# separator-bearing id (``../..``, ``a/b``) can never escape the threads dir.
# Validated **in the convention** so every producer WP inherits the guard
# rather than each re-deriving (or forgetting) it (CF-11; security lens).
# Matched with ``re.fullmatch`` (below), NOT a ``^...$`` anchor: in Python
# ``$`` also matches just before a trailing ``\n``, so ``^[A-Za-z0-9_-]+$``
# would accept ``"abc\n"`` — an id carrying an embedded newline into a
# constructed path/filename. ``fullmatch`` requires the WHOLE string to match,
# closing that gap (WP-001 security advisory, folded in at WP-002 — the first
# durable on-disk consumer of this guard).
_ID_PATTERN = re.compile(r"[A-Za-z0-9_-]+")


def validate_store_id(store_id: str) -> str:
    """Return ``store_id`` if it is a safe path component, else raise.

    A safe id is a **full-string** match of ``[A-Za-z0-9_-]+`` — no path
    separators, no ``.``, no ``..``, **and no trailing/embedded newline** (the
    ``re.fullmatch`` anchors the whole string, unlike ``$`` which accepts a
    trailing ``\\n``). So it cannot traverse out of the threads dir when joined
    into a path or a filename, nor smuggle a newline into a constructed path.
    Raises :class:`ExpectedError` (``INVALID_ID``): a deterministic refusal,
    the op declined the input (CF-03). The path/filename helpers call this, so
    the guard is impossible to bypass via the convention.
    """
    if not _ID_PATTERN.fullmatch(store_id):
        raise ExpectedError(
            INVALID_ID,
            f"store id {store_id!r} is not a safe path component "
            f"(allowed: letters, digits, '-', '_'); refusing to build a path "
            f"that could traverse out of the threads dir",
        )
    return store_id


def store_root_for_change(change_id: str) -> Path:
    """The pinned store root for a change's threads (CF-11).

    ``~/.sulis/changes/{change_id}/threads/`` — the same trust boundary as the
    brief + Working Set (loopback, single founder, OS file perms; ADR-002 / TDD
    §4 at-rest scope). Pinned here so producer WPs reference it verbatim rather
    than re-deriving the path and drifting. ``change_id`` is validated
    (:func:`validate_store_id`) so the convention cannot traverse.
    """
    return Path.home() / ".sulis" / "changes" / validate_store_id(change_id) / "threads"


def thread_record_filename(thread_id: str) -> str:
    """On-disk filename for a Thread record (CF-11). ``thread_id`` validated."""
    return f"{validate_store_id(thread_id)}.thread.json"


def memory_record_filename(thread_id: str) -> str:
    """On-disk filename for a ThreadMemory record (CF-11). ``thread_id`` validated."""
    return f"{validate_store_id(thread_id)}.memory.json"


def messages_record_filename(thread_id: str) -> str:
    """On-disk filename for the append-only message log (CF-11).

    ``.jsonl`` — one ThreadMessage per line, append-only, the offset-ordered
    log convention (CP-01, mirrors the event log). ``thread_id`` validated.
    """
    return f"{validate_store_id(thread_id)}.messages.jsonl"


# ── fixture / dict hydration helpers (CF-04) ───────────────────────────────


def thread_message_from_dict(raw: dict[str, Any]) -> ThreadMessage:
    return ThreadMessage(**raw)


def exploration_entry_from_dict(raw: dict[str, Any]) -> ExplorationJournalEntry:
    return ExplorationJournalEntry(**raw)


def thread_memory_content_from_dict(raw: dict[str, Any]) -> ThreadMemoryContent:
    return ThreadMemoryContent(
        messages=[thread_message_from_dict(m) for m in raw.get("messages", [])],
        exploration_journal=[
            exploration_entry_from_dict(e) for e in raw.get("exploration_journal", [])
        ],
        participant_context=dict(raw.get("participant_context", {})),
    )


def thread_memory_from_dict(raw: dict[str, Any]) -> ThreadMemory:
    """Hydrate a ThreadMemory from a plain dict (the fixture / wire shape)."""
    return ThreadMemory(
        thread_id=raw["thread_id"],
        version=raw["version"],
        content=thread_memory_content_from_dict(raw["content"]),
        created_at=raw["created_at"],
        updated_at=raw["updated_at"],
    )


# ── the in-memory adapter stub (CF-04 / §5 shared contract-test subject) ───


class InMemoryThreadStore:
    """An in-memory ``ThreadStore`` adapter — the contract's reference stub.

    It is the shared contract-test subject (the real durable adapter at WP-002
    runs the same test against the same invariants, MEA-09). It enforces the
    append-only message invariant (monotonic ``order``, no id rewrite, TDD §4)
    and returns the contract's three-category errors. It holds nothing durable
    — purely in-process — so it is the cheap mock for the parallel consumer WPs
    (CF-05) and the conformance baseline for the durable one.
    """

    def __init__(self) -> None:
        self._threads: dict[str, Thread] = {}
        self._messages: dict[str, list[ThreadMessage]] = {}
        self._memory: dict[str, ThreadMemory] = {}

    # write ----------------------------------------------------------------

    def put_thread(self, thread: Thread) -> None:
        """Upsert a Thread record. (Not a contract read/write op for the agent;
        the session pump creates the thread before appending — kept on the
        in-memory stub so tests + the durable adapter share thread setup.)"""
        self._threads[thread.id] = thread

    def append_message(self, thread_id: str, message: ThreadMessage) -> None:
        log = self._messages.setdefault(thread_id, [])
        # Append-only invariant (TDD §4): no id rewrite, monotonic order. Both
        # are Expected-category deterministic refusals (the op ran, the input
        # was rejected) — not a new error category.
        if any(m.id == message.id for m in log):
            raise ExpectedError(
                DUPLICATE_MESSAGE,
                f"message {message.id!r} already appended to thread "
                f"{thread_id!r}; the log is append-only (no rewrite)",
            )
        if log and message.order <= log[-1].order:
            raise ExpectedError(
                OUT_OF_ORDER_WRITE,
                f"message order {message.order} is not greater than the last "
                f"order {log[-1].order} on thread {thread_id!r}; the log is "
                f"offset-ordered and monotonic",
            )
        log.append(message)

    def put_memory(self, thread_id: str, memory: ThreadMemory) -> None:
        # ThreadMemory is versioned, incremented on each checkpoint
        # regeneration (ADR-001). The version must move forward — a stale or
        # equal version is a deterministic refusal (ExpectedError), the
        # memory-record analogue of the message log's monotonic-order guard.
        existing = self._memory.get(thread_id)
        if existing is not None and memory.version <= existing.version:
            raise ExpectedError(
                STALE_MEMORY_VERSION,
                f"memory version {memory.version} for thread {thread_id!r} is "
                f"not greater than the stored version {existing.version}; "
                f"memory versions are monotonic",
            )
        self._memory[thread_id] = memory

    # read -----------------------------------------------------------------

    def get_thread(self, thread_id: str) -> Thread:
        try:
            return self._threads[thread_id]
        except KeyError:
            raise ExpectedError(THREAD_NOT_FOUND, f"no thread {thread_id!r}") from None

    def get_memory(self, thread_id: str) -> ThreadMemory:
        # MEMORY_NOT_FOUND, distinct from THREAD_NOT_FOUND: a thread may exist
        # (put_thread) with no memory checkpoint yet (put_memory not called).
        # The contract advertises both codes; the stub emits the one matching
        # the case it is in (CF-03).
        try:
            return self._memory[thread_id]
        except KeyError:
            raise ExpectedError(
                MEMORY_NOT_FOUND, f"no memory for thread {thread_id!r}"
            ) from None

    def get_messages(
        self, thread_id: str, since: int | None = None, limit: int | None = None
    ) -> list[ThreadMessage]:
        log = list(self._messages.get(thread_id, []))
        if since is not None:
            log = [m for m in log if m.order >= since]
        if limit is not None:
            log = log[:limit]
        return log
