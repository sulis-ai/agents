"""``_session_manager.chat_scope_store`` — per-product chat-scope thread keying
+ provider-on-open resolution (CH-G3Y4RM WP-002; ADR-002, ADR-003).

This is the **server side of the per-product chat seam** (the WP-001 contract).
It is overwhelmingly composition: it adds **only** a chat-scoped store-root
resolver and a key derivation over the SHIPPED :class:`LocalThreadStore` (whose
record shapes + append-only + redaction-on-write invariants are reused
verbatim), plus the boring one-function provider fallback ADR-003 names.

What is genuinely new here (and nothing more):

1. **Chat-scoped store root (ADR-002).** One durable thread per product scope,
   rooted at ``~/.sulis/chat/{scope-key}/threads/`` — a sibling of the existing
   change-scoped root (``~/.sulis/changes/{change_id}/threads/``). The wire
   scope (``product:{id}`` | ``product:__all__`` | ``product:__unassigned__``)
   is colon-bearing, but :func:`thread_contract.validate_store_id` (the on-disk
   guard) accepts only ``[A-Za-z0-9_-]+`` — so the scope is mapped to a safe key
   first. Histories are physically separate directories, so blending is
   impossible by construction.

2. **Provider remembered per scope (ADR-002).** The chosen agent (provider) is
   stamped on the scope's :class:`ThreadMemory` ``participant_context.provider``
   — the documented additive slot, no schema fork.

3. **Provider-on-open resolution (ADR-003).** :func:`resolve_provider` is the
   boring, explicit fallback order the picker drives: ``picked`` (if a
   registered key) → the scope's remembered choice (if a registered key) → the
   safe default ``pty``. The resolver NEVER yields a free-form string; the
   daemon's ``UNKNOWN_PROVIDER`` stays the last-resort backstop, never the
   user-facing failure path.

**Dependency direction (MEA-01 / WPB-01).** This module imports only the
thread contract + the shipped local adapter + the stdlib. No provider,
subprocess, or web import — it is a thin domain resolver over the store port.

**Wire-vs-disk guard.** The wire-level validator is ``parseChatScope``
(``apps/cockpit/shared/chatScope.ts``); THIS module is the on-disk backstop —
it re-validates the scope shape and refuses a hostile string (path traversal,
wrong prefix, empty id) before any path is keyed, so a bypass of the wire guard
still cannot traverse out of the chat root.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from .thread_contract import (
    INVALID_ID,
    MEMORY_NOT_FOUND,
    ExpectedError,
    ThreadMemory,
    ThreadMemoryContent,
    ThreadMessage,
    validate_store_id,
)
from .thread_store_local import LocalThreadStore

# The two wire roles the chat round-trip persists: the founder ("user") and the
# running agent ("assistant"). They map onto the shipped ThreadMessage
# `participant_type` union ("user" / "studio_agent"), reused verbatim (ADR-002).
ChatTurnRole = Literal["user", "assistant"]
_ROLE_TO_PARTICIPANT: dict[ChatTurnRole, str] = {
    "user": "user",
    "assistant": "studio_agent",
}

# The closed provider union — the two registered daemon keys (ADR-003;
# session_manager_daemon.py:638 registers "pty"=Claude, "agy"=Antigravity). The
# picker selects exactly one of these; the resolver never yields anything else.
ChatProvider = Literal["pty", "agy"]
REGISTERED_PROVIDERS: tuple[ChatProvider, ...] = ("pty", "agy")

# The safe default — preserves today's behaviour for a scope with no remembered
# choice, and the backstop for any unknown/absent provider (ADR-003).
DEFAULT_PROVIDER: ChatProvider = "pty"

# The wire prefix every chat scope carries (mirrors `SCOPE_PREFIX` in
# shared/chatScope.ts — one vocabulary, ADR-002).
_SCOPE_PREFIX = "product:"


def _scope_key(chat_scope: str) -> str:
    """Derive a ``validate_store_id``-safe on-disk key from a wire chat scope.

    The wire scope is colon-bearing (``product:dna:product:<ulid>`` for a real
    product, or the bare sentinels ``product:__all__`` / ``product:__unassigned__``).
    ``validate_store_id`` rejects ``:``, so each colon is mapped to ``_`` to
    produce a flat, safe path component.

    The mapping is collision-free across valid scopes: ``:`` is the ONLY
    character rewritten, and it always maps 1:1 to ``_``; the sentinels are
    fixed literals (``product:__all__`` → ``product___all__``) while a real
    product id is ``product:dna:product:<ulid>`` (→ ``product_dna_product_<ulid>``),
    which can never coincide with a sentinel's key because a real id never has
    the ``__all__`` / ``__unassigned__`` body. The derived key is then validated
    through the convention guard, so a hostile scope that slipped a separator or
    a ``..`` past the prefix check is refused before any path is keyed.
    """
    if not chat_scope.startswith(_SCOPE_PREFIX):
        raise ExpectedError(
            INVALID_ID,
            f"chat scope {chat_scope!r} must start with {_SCOPE_PREFIX!r} "
            f"(the only sanctioned wire scope prefix; ADR-002)",
        )
    body = chat_scope[len(_SCOPE_PREFIX) :]
    if body == "":
        raise ExpectedError(
            INVALID_ID, f"chat scope {chat_scope!r} has an empty id body"
        )
    # `.`/`..` traversal and path separators in the body are rejected here BEFORE
    # the colon→underscore rewrite, so a `..` can never reach the key (the
    # rewrite only touches `:`). The convention guard below is the final gate.
    if "/" in body or "\\" in body or "." in body:
        raise ExpectedError(
            INVALID_ID,
            f"chat scope {chat_scope!r} carries a path separator or '.' — "
            f"refusing to key a path that could traverse out of the chat root",
        )
    key = chat_scope.replace(":", "_")
    # Final gate: the derived key must be a safe single path component.
    return validate_store_id(key)


def chat_store_root_for_scope(chat_scope: str, chat_root: Path | None = None) -> Path:
    """The chat-scoped store root for a scope's durable thread (ADR-002).

    ``{chat_root}/{scope-key}/threads/`` — parallel to the change-scoped root
    (:func:`thread_contract.store_root_for_change`). ``chat_root`` defaults to
    ``~/.sulis/chat`` (the loopback single-founder trust boundary, same as the
    change root); tests pass an explicit ``chat_root``. The scope is validated +
    keyed (:func:`_scope_key`) so the convention cannot traverse.
    """
    base = (
        Path(chat_root) if chat_root is not None else (Path.home() / ".sulis" / "chat")
    )
    return base / _scope_key(chat_scope) / "threads"


def resolve_chat_thread(
    chat_scope: str, chat_root: Path | None = None
) -> LocalThreadStore:
    """Resolve the active scope's durable thread store (ADR-002).

    Returns a :class:`LocalThreadStore` rooted at the scope's chat root, reusing
    the shipped record shapes + append-only invariants verbatim. The store's
    ``change_id`` slot carries the scope key (it is the store's id; the chat has
    no change id), validated by the adapter's constructor.
    """
    root = chat_store_root_for_scope(chat_scope, chat_root=chat_root)
    return LocalThreadStore(change_id=_scope_key(chat_scope), root=root)


def remember_provider(
    chat_scope: str,
    provider: str,
    thread_id: str,
    chat_root: Path | None = None,
) -> None:
    """Stamp the chosen ``provider`` on the scope's thread memory
    (``participant_context.provider``) — remembered per scope, no schema fork
    (ADR-002).

    Persisted permissively: whatever value is chosen is stored as-is. Validation
    of whether it is a REGISTERED key happens at read/resolve time
    (:func:`resolve_provider`), so a corrupt/legacy value never crashes the
    write path and is simply ignored on the way out (defensive).
    """
    store = resolve_chat_thread(chat_scope, chat_root=chat_root)
    try:
        existing = store.get_memory(thread_id)
        version = existing.version + 1
        ctx = dict(existing.content.participant_context)
        content = ThreadMemoryContent(
            messages=list(existing.content.messages),
            exploration_journal=list(existing.content.exploration_journal),
            participant_context={**ctx, "provider": provider},
        )
    except ExpectedError as exc:
        if exc.code != MEMORY_NOT_FOUND:
            raise
        # First write for this scope — version 1, an otherwise-empty checkpoint
        # whose only job is to remember the provider choice.
        version = 1
        content = ThreadMemoryContent(participant_context={"provider": provider})
    # A real UTC instant, consistent with the TS adapter's `new Date().toISOString()`
    # so the two writers of this on-disk record agree on the timestamp shape.
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    store.put_memory(
        thread_id,
        ThreadMemory(
            thread_id=thread_id,
            version=version,
            content=content,
            created_at=now,
            updated_at=now,
        ),
    )


def read_remembered_provider(
    chat_scope: str, thread_id: str, chat_root: Path | None = None
) -> str | None:
    """Read the scope's remembered provider (``participant_context.provider``),
    or ``None`` when none has been remembered yet (ADR-002).

    Returns the raw stored value (not yet narrowed to a registered key) — the
    narrowing/backstop is :func:`resolve_provider`'s job, so this read is honest
    about what is on disk.
    """
    store = resolve_chat_thread(chat_scope, chat_root=chat_root)
    try:
        memory = store.get_memory(thread_id)
    except ExpectedError as exc:
        if exc.code == MEMORY_NOT_FOUND:
            return None
        raise
    value = memory.content.participant_context.get("provider")
    return value if isinstance(value, str) else None


def append_turn(
    chat_scope: str,
    role: ChatTurnRole,
    content: str,
    thread_id: str = "chat",
    chat_root: Path | None = None,
) -> None:
    """Append one chat turn to the scope's durable thread — the persistence
    round-trip (WP-004; folded CONCERN DAT-PERSIST-01).

    Today nothing appends chat turns at runtime, so ``get_messages`` is always
    empty and per-product history is not real. This closes the round-trip by
    persisting each turn through the SHIPPED ``LocalThreadStore.append_message``
    — which applies redaction-on-write (``_scrub_message``) before any byte lands
    — so (a) the scope's history actually persists and ``getThread`` returns it,
    and (b) chat content is scrubbed of secrets on the way to disk.

    The turn is appended at the next monotonic offset (the log is offset-ordered,
    append-only — both invariants reused verbatim, ADR-002). The wire ``role``
    ("user" | "assistant") maps onto the shipped ``ThreadMessage`` participant
    union ("user" | "studio_agent"). The scope is validated + keyed via
    :func:`resolve_chat_thread` (which calls :func:`_scope_key`), so a hostile
    scope is refused before any path is touched.
    """
    if role not in _ROLE_TO_PARTICIPANT:
        raise ExpectedError(
            INVALID_ID,
            f"chat turn role {role!r} must be one of {tuple(_ROLE_TO_PARTICIPANT)}",
        )
    store = resolve_chat_thread(chat_scope, chat_root=chat_root)
    # Next monotonic offset: one past the last persisted message's order (the
    # store's append guard rejects a non-increasing order, so this is the only
    # safe next value). A fresh thread starts at order 1.
    existing = store.get_messages(thread_id)
    next_order = (existing[-1].order + 1) if existing else 1
    participant = _ROLE_TO_PARTICIPANT[role]
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    store.append_message(
        thread_id,
        ThreadMessage(
            id=uuid.uuid4().hex,
            participant_id=f"chat_{participant}",
            participant_type=participant,  # type: ignore[arg-type]  # narrowed by the role map
            content=content,
            role=None,
            created_at=now,
            order=next_order,
        ),
    )


def resolve_provider(
    chat_scope: str,
    picked: str | None,
    thread_id: str = "chat",
    chat_root: Path | None = None,
) -> ChatProvider:
    """Resolve the provider to open the scope's chat session on (ADR-003).

    The explicit, boring fallback order (one function, no implicit magic —
    WP-002 Definition of Done > Blue):

    1. ``picked`` — the picker's choice, IF it is a registered key.
    2. the scope's remembered ``participant_context.provider``, IF registered.
    3. the safe default ``pty`` (Claude).

    The resolver only ever returns one of :data:`REGISTERED_PROVIDERS`; an
    unknown/absent/corrupt value at any tier is ignored in favour of the next
    tier, so the daemon's ``UNKNOWN_PROVIDER`` is a backstop that the
    user-facing path never relies on.
    """
    if picked in REGISTERED_PROVIDERS:
        return picked  # type: ignore[return-value]  # narrowed by the membership test
    remembered = read_remembered_provider(chat_scope, thread_id, chat_root=chat_root)
    if remembered in REGISTERED_PROVIDERS:
        return remembered  # type: ignore[return-value]
    return DEFAULT_PROVIDER
