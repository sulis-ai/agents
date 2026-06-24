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
    BRAIN_ENTITIES_CONTEXT_KEY,
    ContextPayloadAssembler,
    WORKING_SET_CONTEXT_KEY,
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


def now_iso() -> str:
    """A UTC ISO-8601 timestamp (the time the durable record was tracked).

    Stdlib, timezone-aware (``Z``-style UTC) — the same shape the contract's
    ``created_at`` fields carry elsewhere in the change. Public so the manager's
    durable-sink wiring (WP-007) stamps a created Thread record with the SAME
    timestamp shape this module stamps a message with — one definition (EP-03).
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

    def seed_next_order_from_store(self) -> int:
        """Reseed :attr:`_next_order` from the durable log's high-water mark —
        the resume fix (WP-004 ADV-2).

        A fresh sink defaults ``_next_order=0``. On **resume** over a non-empty
        thread that is wrong: the store enforces a strictly-increasing ``order``,
        so an append at 0 against a log whose last order is N≥0 is rejected
        ``OUT_OF_ORDER_WRITE`` — and the sink isolates that as a silent
        :attr:`degraded_appends`, so the resumed conversation would stop being
        tracked without ever raising. Reseeding from
        ``get_messages(...)[-1].order + 1`` makes post-resume appends land at the
        right order and continue the log.

        Idempotent + safe on an empty thread (no messages → stays 0, so the
        first append lands at order 0). Returns the seeded next order. A store
        read failure is isolated like an append failure (the resume must not be
        broken by a transient read error): it leaves ``_next_order`` unchanged
        and is recorded as a degradation rather than raised into the resume path.
        """
        try:
            messages = self._store.get_messages(self._thread_id)
        except Exception:  # noqa: BLE001  (resume read isolation — see docstring)
            self.degraded_appends += 1
            _log.warning(
                "resume reseed read failed for thread %s (next_order unchanged)",
                self._thread_id,
                exc_info=True,
            )
            return self._next_order
        if messages:
            self._next_order = messages[-1].order + 1
        return self._next_order

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
            created_at=now_iso(),
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
        now = now_iso()
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


# The brief fragment's section marker (vendor-neutral, provider-agnostic). The
# manager composes this fragment ADDITIVELY beneath the change's default brief
# (WP-009): the rich Sulis-owned context augments the default; it never replaces
# the change-binding / recon pointer the default carries. PUBLIC (no underscore)
# so the manager's idempotent compose reuses the EXACT same delimiter to strip a
# previously-composed fragment before appending a fresh one (one definition of
# "where the resumed-context block begins", EP-03) — the producer and the
# idempotency-stripper cannot drift.
BRIEF_FRAGMENT_HEADER = "── Resumed context (from your durable Sulis store) ──"


def render_payload_brief(payload: ContextPayload) -> str:
    """Render an assembled :class:`ContextPayload` into a vendor-neutral brief
    fragment — the ONE definition of "render the payload into the brief"
    (WP-009; EP-03, extracted as a named function so the manager's spawn/resume
    seam has a single render seam, and a future second call site reuses it).

    The fragment is plain, provider-agnostic text (NO Claude-JSONL structure):
    the rich Working Set crystallisation + relevant brain entities (folded into
    ``participant_context`` by the assembler), the structured message summary,
    and the exploration journal — plus the raw-on-demand discovery pointer (the
    thread id + the ``thread_context`` tool name, ADR-005) telling the agent
    where the full record lives. Within the assembler's tier budget by
    construction (the assembler already trimmed the content to fit).
    """
    content = payload.memory
    ctx = content.participant_context
    lines: list[str] = [BRIEF_FRAGMENT_HEADER]

    working_set = ctx.get(WORKING_SET_CONTEXT_KEY)
    if working_set:
        lines.append("")
        lines.append("Your live reasoning state (the Working Set):")
        lines.append(str(working_set).rstrip())

    brain_entities = ctx.get(BRAIN_ENTITIES_CONTEXT_KEY)
    if brain_entities:
        lines.append("")
        lines.append("Relevant building blocks from your brain:")
        for entity in brain_entities:
            name = _brain_entity_label(entity)
            if name:
                lines.append(f"  - {name}")

    if content.exploration_journal:
        lines.append("")
        lines.append("Decisions captured this thread:")
        for entry in content.exploration_journal:
            lines.append(f"  - {entry.content}")

    if content.messages:
        lines.append("")
        lines.append("Conversation summary (most recent):")
        for message in content.messages:
            body = message.content.strip()
            if body:
                lines.append(f"  - {body}")

    lines.append("")
    lines.append(
        f"The full, correctly-ordered record is in your durable store "
        f"(thread {payload.thread_id}); fetch the raw log on demand via the "
        f"{payload.raw_fetch_tool} tool."
    )
    return "\n".join(lines)


def _brain_entity_label(entity: object) -> str:
    """A human-readable label for a brain entity (its ``name``, else ``id``).

    A brain entity is a plain JSON-LD dict (vendor-neutral); the founder/agent-
    facing label is its ``name`` when present, falling back to its ``id``. A
    non-dict or label-less entity yields ``""`` (skipped by the caller)."""
    if isinstance(entity, dict):
        return str(entity.get("name") or entity.get("id") or "")
    return ""
