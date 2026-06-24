"""``_session_manager.durable_sink`` — the session pump's durable-append sink +
resume payload-seed (CH-GJ9KQR WP-004).

**REINFORCE-Instrument over the existing pump (ADR-004), not a rewrite.** The
per-change session (the live PTY process) already decodes provider stdout into
the provider-neutral :class:`~_session_manager.events.Event` vocabulary and
appends each one to an in-memory :class:`~_session_manager.event_log.EventLog`
for live-tail / viewer fan-out. This module adds a **second sink** alongside
that in-memory log: each content-bearing ``Event`` is mapped onto a
:class:`~_session_manager.thread_contract.ThreadMessage` and appended to the
durable :class:`~_session_manager.thread_contract.ThreadStore` (WP-002). The
in-memory live-tail path is **byte-for-byte unchanged** — the durable sink is a
clearly separated side-effect (ADR-004).

**No second decode path.** The sink consumes an already-decoded ``Event`` (the
same one the in-memory log carries); it never re-parses provider stdout. It is
wired through the session's existing ``on_event(session, event)`` registered-
callback seam (the same seam the recovery + turn-guard fan-outs use), via
:meth:`DurableAppendSink.as_event_observer` — additive, no new seam.

**Side-effect isolation (the load-bearing hardening property).** A durable-store
failure must NEVER propagate into the live pump. :meth:`DurableAppendSink.append_event`
catches store errors, records them as a degradation count, and returns — so the
existing ``on_event`` fan-out and the live ``EventLog`` are unaffected whether or
not the durable write succeeds.

**Checkpoint regeneration reuses WP-003.** :meth:`DurableAppendSink.checkpoint`
regenerates the thread's :class:`~_session_manager.thread_contract.ThreadMemory`
via the SAME :func:`~_session_manager.context_payload.summarise_memory` function
the assembler uses — one definition of "the thread's structured summary" (the
separable Blue seam from WP-003) — bumping the monotonic version.

**Resume seeds from OUR store, not the provider transcript (ADR-004).**
:func:`seed_payload_for_resume` assembles a vendor-neutral
:class:`~_session_manager.thread_contract.ContextPayload` from the durable store
via the WP-003 :class:`~_session_manager.context_payload.ContextPayloadAssembler`.
A (re)spawned agent is seeded from this payload through the existing brief argv
seam (``SessionSpec.brief_change_id``, ADR-004/005) — it reads OUR store, never
``~/.claude/projects``.

**Dependency direction (MEA-01 / WPB-01).** Depends inward only on the
provider-neutral ``events`` vocabulary, the contract types, and the assembler.
It touches no filesystem of its own (the store adapter owns IO) and no provider
or subprocess.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime, timezone

from _session_manager.context_payload import (
    ContextPayloadAssembler,
    summarise_memory,
)
from _session_manager.events import Event
from _session_manager.thread_contract import (
    ContextPayload,
    MessageRole,
    PayloadTier,
    ThreadMemory,
    ThreadMemoryContent,
    ThreadMessage,
    ThreadStore,
)

_log = logging.getLogger("sulis.session_manager.durable_sink")

# The standard tier used when regenerating a memory checkpoint: the rich,
# default payload (matches the assembler's default). Kept as a named constant so
# a future tuning is a one-symbol change.
_CHECKPOINT_TIER: PayloadTier = "standard"

# The participant identity stamped on a durable message. The session pump is the
# live writer (ADR-004); on the loopback single-founder binding the studio agent
# is the producer of decoded model/tool output. A standalone founder-prompt path
# can pass an explicit participant later; the sink defaults to the agent.
_AGENT_PARTICIPANT_ID = "studio_agent"


def _now_iso() -> str:
    """A UTC ISO-8601 timestamp (the time the durable record was tracked).

    Stdlib, timezone-aware (``Z``-style UTC) — the same shape the contract's
    ``created_at`` fields carry elsewhere in the change.
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _role_for_event(event: Event) -> MessageRole | None:
    """Map a provider-neutral ``Event`` onto the contract's ``MessageRole``.

    Only **content-bearing** events become durable messages (the Contract:
    events that carry founder/agent/tool content):

    - ``chunk`` → ``observation`` — model text the agent produced.
    - ``tool_use`` → ``observation`` — a record of what the agent did.

    A ``result`` (usage-only terminal) and an ``error`` (a control signal on the
    live log) carry no founder/agent/tool content, so they are NOT tracked —
    returning ``None`` tells the caller to skip them. Returning the role here
    (rather than a bool) keeps the kind→role decision in exactly one place.
    """
    if event.kind == "chunk":
        return "observation"
    if event.kind == "tool_use":
        return "observation"
    # result / error: not founder/agent/tool content — skip.
    return None


def _content_for_event(event: Event) -> str:
    """The durable message body for a content-bearing event.

    A ``chunk`` carries model text directly; a ``tool_use`` is rendered as a
    compact, human-readable line (``<tool> <summary>``) — the same provider-
    neutral shape the live log already shows, so the durable record needs no
    second decode.
    """
    if event.kind == "chunk":
        return event.text or ""
    if event.kind == "tool_use" and event.tool is not None:
        return f"{event.tool.name} {event.tool.input_summary}".rstrip()
    return ""


class DurableAppendSink:
    """The durable second sink wired onto the session pump's ``on_event`` seam.

    Construct it bound to a single thread (one thread per change today, ADR-004);
    feed it each decoded ``Event`` via :meth:`append_event` (or register
    :meth:`as_event_observer` on the session's ``on_event`` seam). It maps a
    content-bearing event onto a ``ThreadMessage`` with a monotonic ``order`` and
    appends it to the durable store. Store failures are isolated (never raised
    into the pump) and counted in :attr:`degraded_appends`.
    """

    def __init__(self, store: ThreadStore, *, thread_id: str) -> None:
        self._store = store
        self._thread_id = thread_id
        # Monotonic offset for the durable log. The store enforces strictly-
        # increasing order; the sink owns the next value so two appends from one
        # turn never collide. Starts at 0; each successful append bumps it.
        self._next_order = 0
        #: Count of appends that hit a store failure and were isolated (the
        #: degradation signal — the live pump is unaffected; this is the only
        #: trace a durable write was dropped).
        self.degraded_appends = 0

    def append_event(self, event: Event) -> None:
        """Map ``event`` onto a ``ThreadMessage`` and append it to the durable
        store — a non-fatal side-effect.

        Skips non-content events (``result`` / ``error``). On a store failure,
        records a degradation and returns WITHOUT raising: the durable sink must
        never break the live pump (ADR-004 — the live-tail path is unchanged
        whether or not the durable write succeeds).
        """
        role = _role_for_event(event)
        if role is None:
            return  # not founder/agent/tool content — not tracked
        order = self._next_order
        message = ThreadMessage(
            id=f"{self._thread_id}-{order}",
            participant_id=_AGENT_PARTICIPANT_ID,
            participant_type="studio_agent",
            content=_content_for_event(event),
            role=role,
            created_at=_now_iso(),
            order=order,
        )
        try:
            self._store.append_message(self._thread_id, message)
        except Exception:  # noqa: BLE001  (isolation is the contract — see docstring)
            # A durable-store failure is isolated from the live pump. We log it
            # for observability (TDD §4 observability) and count it; we do NOT
            # advance _next_order (the slot is unused) and we do NOT re-raise.
            self.degraded_appends += 1
            _log.warning(
                "durable append dropped for thread %s (isolated from live pump)",
                self._thread_id,
                exc_info=True,
            )
            return
        self._next_order = order + 1

    def as_event_observer(self) -> Callable[[object, Event], None]:
        """Return an ``on_event(session, event)``-shaped adapter.

        The session pump's registered observer seam is ``(session, event)``; the
        sink only needs the event. This adapter lets the manager wire the sink
        onto ``session.on_event`` exactly as it wires the recovery/guard fan-out
        — additive, no new seam (the session arg is ignored).
        """

        def _observer(_session: object, event: Event) -> None:
            self.append_event(event)

        return _observer

    def checkpoint(self) -> ThreadMemory:
        """Regenerate the thread's ``ThreadMemory`` from the durable log and
        persist it with a bumped, monotonic version.

        Reuses the WP-003 :func:`summarise_memory` (the separable Blue seam) so
        the checkpoint summary is the SAME definition of "the thread's structured
        summary" the assembler uses. Reads the current messages from the store,
        summarises them under the standard-tier budget, increments the version
        over any existing checkpoint, and writes it back.
        """
        messages = self._store.get_messages(self._thread_id)
        raw_content = ThreadMemoryContent(messages=list(messages))
        budget = ContextPayloadAssembler.TIER_BUDGETS[_CHECKPOINT_TIER]
        summary = summarise_memory(raw_content, max_tokens=budget)

        version = self._next_memory_version()
        now = _now_iso()
        memory = ThreadMemory(
            thread_id=self._thread_id,
            version=version,
            content=summary,
            created_at=now,
            updated_at=now,
        )
        self._store.put_memory(self._thread_id, memory)
        return memory

    def _next_memory_version(self) -> int:
        """The next monotonic memory version (1 if none exists yet).

        Propagates only the contract's read op; an absent checkpoint
        (``MEMORY_NOT_FOUND``) means "no version yet" → start at 1.
        """
        try:
            existing = self._store.get_memory(self._thread_id)
        except Exception:  # noqa: BLE001  (absent memory → version 1; see docstring)
            return 1
        return existing.version + 1


def seed_payload_for_resume(
    assembler: ContextPayloadAssembler,
    *,
    thread_id: str,
    tier: PayloadTier = "standard",
) -> ContextPayload:
    """Assemble the resume context payload from OUR durable store (ADR-004).

    On (re)spawn, the (re)spawned agent is seeded from the thread's assembled
    payload — delivered through the existing brief argv seam
    (``SessionSpec.brief_change_id``, ADR-004/005) — **without reading the
    provider's transcript**. This is a thin, named seam over the WP-003
    :class:`ContextPayloadAssembler` so the resume call site reads as intent
    ("seed for resume") and the assembler's three-category errors propagate
    verbatim (e.g. ``MEMORY_NOT_FOUND`` for a thread with no checkpoint yet) —
    no second error hierarchy.
    """
    return assembler.assemble(thread_id, tier=tier)
