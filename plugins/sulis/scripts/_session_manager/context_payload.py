"""``_session_manager.context_payload`` — the ContextPayloadAssembler
(CH-GJ9KQR WP-003).

The assembler is the **GENERATED ARTIFACT** of TDD §3.2 / ADR-003: a pure
query/render component (no persistence of its own) that builds the contract's
vendor-neutral :class:`~_session_manager.thread_contract.ContextPayload`
(WP-001) in tiers — ``lean`` / ``standard`` / ``full`` — under a **hard token
budget** (TDD §4 armor).

**Rich-by-default, raw-on-demand (ADR-005).** The payload carries the
*structured* memory inline — the ``exploration_journal`` (the crystallised,
low-volume decision signal) plus a **summary** of the message log, never the
raw dump — together with the discovery *pointer* (the ``thread_id`` + the
``thread_context`` raw-fetch tool name) telling the agent where the full record
lives. The common path needs no round-trip; the raw log is fetched on demand
through the denyable MCP tool (WP-005).

**Tiers as token budgets.** ``lean`` < ``standard`` < ``full`` are hard caps on
the assembled content's estimated token count. The fuller a tier, the more
context (more of the message summary, the Working Set crystallisation, the
relevant brain entities) it folds in. When even the requested tier's content
would overflow its cap, the assembler **degrades to a tighter tier** rather
than ship an over-budget payload (TDD §4); the returned payload's ``tier``
field always reflects what was actually delivered.

**Dependency direction (WPB-01 / MEA-01).** The assembler depends inward only
on the contract's :class:`~_session_manager.thread_contract.ThreadStore` *read*
ops + two injected, side-effect-free readers (the Working Set crystallisation
and the relevant brain entities). It touches no filesystem, network, or
provider of its own — the store adapter (WP-002) owns IO; the readers are
injected at the composition root (WPB-07). The in-memory adapter from the
contract is a valid store, so the unit tests drive the real port, not a mock
(WPB-03).

**Separable summary (Blue / WP-004 reuse).** :func:`summarise_memory` is a
free function, not a method, so the session-pump checkpoint regeneration
(WP-004) reuses the *same* summariser the assembler uses — one definition of
"the structured summary of a thread's memory."

Stdlib only. Python 3.11-safe.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from _session_manager.thread_contract import (
    ContextPayload,
    PayloadTier,
    RAW_FETCH_TOOL_NAME,
    ThreadMemoryContent,
    ThreadMessage,
    ThreadStore,
)

# A reader is injected (WPB-07) and is a pure function of the thread id — it
# performs no IO the assembler is responsible for; the composition root decides
# what backs it. The Working Set reader returns the crystallisation text; the
# brain reader returns the relevant entities (as plain dicts/objects).
WorkingSetReader = Callable[[str], str]
BrainReader = Callable[[str], Sequence[Any]]

# The ``participant_context`` keys the assembler writes the rich resume content
# under (the Working Set crystallisation + the relevant brain entities, ADR-005).
# Pinned as named constants so the PRODUCER (this assembler) and the CONSUMER
# (the brief renderer ``durable_sink.render_payload_brief``) agree on one name and
# cannot silently drift — the same one-definition discipline ``RAW_FETCH_TOOL_NAME``
# and ``_BRIEF_FRAGMENT_HEADER`` already use (EP-03).
WORKING_SET_CONTEXT_KEY = "working_set"
BRAIN_ENTITIES_CONTEXT_KEY = "brain_entities"


def estimate_tokens(text: str) -> int:
    """A rough, deterministic token estimate: ~4 characters per token.

    This is the widely-used back-of-envelope heuristic (OpenAI's "~4 chars/token
    for English" rule of thumb). It is intentionally a cheap, dependency-free
    estimate, not a real tokenizer — the budget is a guard rail, and over-
    estimating is the safe direction (we ship *less* than the true cap, never
    more). Named so a future swap to a real tokenizer is a one-symbol change.
    """
    return len(text) // 4


def content_tokens(content: ThreadMemoryContent) -> int:
    """The estimated token cost of a :class:`ThreadMemoryContent` — the **one**
    whole-content accounting the tier budget is enforced against (messages +
    journal + participant-context values).

    Public (not underscore-private) so callers that need to *assert* a payload
    is within budget — the tests, a future caller validating an assembled
    payload — measure it the exact same way the assembler enforces it, rather
    than re-deriving (and drifting from) the accounting (EP-03 reuse-first)."""
    parts: list[str] = [m.content for m in content.messages]
    parts += [e.content for e in content.exploration_journal]
    parts += [str(v) for v in content.participant_context.values()]
    return estimate_tokens(" ".join(parts))


def _summarise_message(message: ThreadMessage, *, head_chars: int) -> ThreadMessage:
    """Return a copy of ``message`` with its body head-truncated to
    ``head_chars`` (an ellipsis marks elision). Identity + ordering fields are
    preserved so the summary stays a faithful, correctly-ordered view."""
    body = message.content
    if len(body) > head_chars:
        body = body[:head_chars].rstrip() + " …"
    # frozen dataclass → replace via the constructor.
    return ThreadMessage(
        id=message.id,
        participant_id=message.participant_id,
        participant_type=message.participant_type,
        content=body,
        role=message.role,
        created_at=message.created_at,
        order=message.order,
    )


def summarise_memory(
    content: ThreadMemoryContent, *, max_tokens: int
) -> ThreadMemoryContent:
    """Compress ``content`` into a structured summary within ``max_tokens`` —
    a **true hard cap on the whole content** (TDD §4): the returned content's
    estimated token cost is always ``<= max_tokens``.

    The compression is applied in fidelity order, dropping the lowest-signal
    content first:

    1. Every **message body is head-truncated** to a compact summary line (the
       raw bodies are reachable on demand via the discovery pointer, ADR-005).
    2. If still over budget, the **oldest messages are dropped** (most-recent-
       wins — recent context is the more useful on resume), until the messages
       fit the budget left after the journal + context.
    3. If the journal + context **alone** still exceed the budget, the
       **oldest exploration-journal entries are dropped** (most-recent-wins)
       until the whole content fits. The journal is the highest-signal content,
       so it is trimmed last and only when the budget cannot hold it all.

    A free function (not an assembler method) so the WP-004 checkpoint
    regeneration reuses the same definition of "the thread's structured
    summary" (Blue / DRY).
    """
    ctx = dict(content.participant_context)
    ctx_tokens = estimate_tokens(" ".join(str(v) for v in ctx.values()))

    # (1) Head-truncate every message body.
    head_chars = 120
    messages = [_summarise_message(m, head_chars=head_chars) for m in content.messages]
    journal = list(content.exploration_journal)

    def _tokens_of(bodies: list[str]) -> int:
        return estimate_tokens(" ".join(bodies))

    def _keep_fitting_suffix(bodies: list[str], budget: int) -> int:
        """Return the start index of the **longest suffix** of ``bodies`` whose
        joined token cost is within ``budget`` (most-recent-wins: the newest
        entries are kept). Single backward pass with a running character total
        — O(N), not the O(N²) of re-joining the whole list on every drop. The
        running total mirrors ``estimate_tokens`` exactly: joined length is the
        sum of body lengths plus one separator space between adjacent bodies,
        floor-divided by four."""
        start = len(bodies)
        chars = 0  # joined length of bodies[start:]
        for i in range(len(bodies) - 1, -1, -1):
            sep = 1 if start < len(bodies) else 0  # space joining to the suffix
            candidate_chars = chars + len(bodies[i]) + sep
            if candidate_chars // 4 > budget:
                break
            chars = candidate_chars
            start = i
        return start

    # (2) Drop oldest messages until messages fit the budget left after the
    #     journal + context (most-recent-wins).
    budget_for_messages = max(
        0, max_tokens - ctx_tokens - _tokens_of([e.content for e in journal])
    )
    msg_bodies = [m.content for m in messages]
    messages = messages[_keep_fitting_suffix(msg_bodies, budget_for_messages) :]

    # (3) If the journal + context alone still overflow, drop oldest journal
    #     entries (most-recent-wins) until the whole content fits the cap.
    journal_budget = max(0, max_tokens - ctx_tokens)
    jrnl_bodies = [e.content for e in journal]
    journal = journal[_keep_fitting_suffix(jrnl_bodies, journal_budget) :]

    return ThreadMemoryContent(
        messages=messages,
        exploration_journal=journal,
        participant_context=ctx,
    )


class ContextPayloadAssembler:
    """Assembles the vendor-neutral :class:`ContextPayload` from the durable
    sources Sulis owns, under a per-tier token budget.

    Pure query/render: depends inward only on the contract's
    :class:`ThreadStore` read ops + the injected, side-effect-free Working Set
    and brain readers (WPB-01 / WPB-07). Construct with the store; pass the
    readers at the composition root.
    """

    #: Hard token caps per tier (estimated tokens of the assembled content).
    #: ``lean`` is the recovery-floor; ``standard`` is the default rich payload;
    #: ``full`` carries the most context. Ordered tightest → loosest.
    TIER_BUDGETS: Mapping[PayloadTier, int] = {
        "lean": 400,
        "standard": 1500,
        "full": 4000,
    }

    #: Tiers ordered tightest → loosest (the degrade path walks this in reverse).
    _TIER_ORDER: tuple[PayloadTier, ...] = ("lean", "standard", "full")

    def __init__(
        self,
        store: ThreadStore,
        *,
        working_set_reader: WorkingSetReader | None = None,
        brain_reader: BrainReader | None = None,
    ) -> None:
        self._store = store
        # Default the readers to empty, side-effect-free sources so the
        # assembler is usable with just a store (e.g. in tests that don't
        # exercise the Working Set / brain folding).
        self._working_set_reader: WorkingSetReader = working_set_reader or (
            lambda _thread_id: ""
        )
        self._brain_reader: BrainReader = brain_reader or (lambda _thread_id: [])

    def assemble(
        self, thread_id: str, tier: PayloadTier = "standard"
    ) -> ContextPayload:
        """Build the :class:`ContextPayload` for ``thread_id`` at ``tier``.

        Reads the thread's memory through the store (the discovery seam's read
        op), folds in the Working Set crystallisation + relevant brain entities
        for the richer tiers, summarises the message log to fit the tier
        budget, and — if even the requested tier overflows — **degrades to the
        tightest tier that fits** (TDD §4). The returned payload's ``tier``
        reflects what was actually delivered.

        Propagates the contract's three-category errors verbatim (e.g.
        ``MEMORY_NOT_FOUND`` for an unknown thread) — the assembler adds no
        second error hierarchy.
        """
        memory = self._store.get_memory(thread_id)  # ExpectedError if absent
        enriched_context = self._participant_context_for(
            thread_id, memory.content, tier
        )
        base = ThreadMemoryContent(
            messages=memory.content.messages,
            exploration_journal=memory.content.exploration_journal,
            participant_context=enriched_context,
        )

        delivered_tier, content = self._fit_to_budget(base, tier)
        return ContextPayload(
            thread_id=thread_id,
            tier=delivered_tier,
            memory=content,
            raw_fetch_tool=RAW_FETCH_TOOL_NAME,
        )

    # ── internals ──────────────────────────────────────────────────────────

    def _participant_context_for(
        self, thread_id: str, content: ThreadMemoryContent, tier: PayloadTier
    ) -> dict[str, Any]:
        """The payload's ``participant_context``: the memory's own context,
        plus — for the richer tiers (``standard`` / ``full``) — the Working Set
        crystallisation AND the relevant brain entities (ADR-005 rich content).
        ``lean`` carries only the memory's own context (recovery floor).

        Both the Working Set and the brain entities fold in at ``standard`` (the
        default rich resume payload) — the live resume path (WP-009) seeds at
        the standard tier and the spec's load-bearing journey requires the
        resumed brief to carry REAL Working Set + REAL brain content within the
        standard budget. ``full`` carries the same rich content under the looser
        budget. The hard token cap (:meth:`_fit_to_budget`) still governs what
        actually ships, so folding brain at ``standard`` cannot overflow the
        budget — an over-budget assembly degrades to the tighter tier."""
        ctx: dict[str, Any] = dict(content.participant_context)
        if tier == "lean":
            return ctx
        working_set = self._working_set_reader(thread_id)
        if working_set:
            ctx[WORKING_SET_CONTEXT_KEY] = working_set
        brain_entities = list(self._brain_reader(thread_id))
        if brain_entities:
            ctx[BRAIN_ENTITIES_CONTEXT_KEY] = brain_entities
        return ctx

    def _fit_to_budget(
        self, base: ThreadMemoryContent, requested: PayloadTier
    ) -> tuple[PayloadTier, ThreadMemoryContent]:
        """Pick the loosest tier (≤ ``requested``) the content fits **without
        lossy dropping**, and return that tier's summary.

        The delivered tier label is honest about fidelity (TDD §4 armor): a
        tier is "delivered" only if summarising ``base`` to that tier's budget
        retained **all** messages and **all** journal entries (body truncation
        is acceptable; dropping whole messages / journal entries is not — that
        is a fidelity loss the looser label would misrepresent). When the
        requested tier needs lossy dropping to fit, the assembler **degrades to
        the tighter tier** whose budget the content fits losslessly.

        ``lean`` is the floor: :func:`summarise_memory` is a true hard cap, so
        the lean summary always fits lean's budget (dropping content if it must)
        — the payload is never over-budget, even for a pathologically large
        thread.
        """
        n_messages = len(base.messages)
        n_journal = len(base.exploration_journal)
        requested_idx = self._TIER_ORDER.index(requested)

        # Walk loosest → tightest within the allowed ceiling; deliver the first
        # tier whose summary kept all content (no lossy drop).
        for tier in reversed(self._TIER_ORDER[: requested_idx + 1]):
            summary = summarise_memory(base, max_tokens=self.TIER_BUDGETS[tier])
            lossless = (
                len(summary.messages) == n_messages
                and len(summary.exploration_journal) == n_journal
            )
            if lossless:
                return tier, summary

        # Floor: deliver lean (always within budget; may have dropped content).
        return "lean", summarise_memory(base, max_tokens=self.TIER_BUDGETS["lean"])
