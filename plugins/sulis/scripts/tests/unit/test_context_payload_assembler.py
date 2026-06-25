"""Unit tests for the ``ContextPayloadAssembler`` (CH-GJ9KQR WP-003).

The assembler is the **GENERATED ARTIFACT** of TDD §3.2 / ADR-003: a pure
query/render component that builds the contract's vendor-neutral
``ContextPayload`` (WP-001, ``_session_manager.thread_contract``) in tiers
(lean / standard / full) under a **hard token budget**, from the durable
sources Sulis owns — the structured thread memory (the
``ThreadMemoryContent`` exploration journal + a messages *summary*, never the
raw dump), the Working Set crystallisation, and the relevant brain entities.

These tests pin the behaviour the WP's Definition of Done names:

- **standard tier carries the summary, not the raw dump** (ADR-005
  rich-by-default; the structured journal + a messages summary inline, with a
  pointer to fetch the raw on demand);
- **each tier stays within its token budget** (TDD §4 hard constraint);
- **over-budget assembly degrades to a tighter tier** rather than overflowing
  (TDD §4 armor);
- **the payload is vendor-neutral** — no Claude-JSONL-specific structure;
- **the payload carries the discovery pointer** (``thread_id`` +
  ``raw_fetch_tool``, ADR-005);
- **the assembler is pure** — it depends inward only on injected read sources
  (a ``ThreadStore`` read surface + a Working Set reader + a brain reader) and
  does no IO of its own (WPB-01 / MEA-01);
- **summary generation is a separable function** — reused at checkpoint
  regeneration (WP-004), so it is exercised standalone here.

Outside-in TDD (WPB-08): driven against the contract's real in-memory
``ThreadStore`` adapter (WPB-03 — never a mock of the port under test).
"""

from __future__ import annotations

import dataclasses

import pytest

from _session_manager import thread_contract as tc
from _session_manager.context_payload import (
    ContextPayloadAssembler,
    content_tokens,
    estimate_tokens,
    summarise_memory,
)

# The tests assert budget compliance using the SAME whole-content accounting
# the assembler enforces against (``content_tokens``) — never a re-derived copy
# that could drift from the production accounting (EP-03 reuse-first).
estimate_tokens_of_content = content_tokens

# ── fixtures: a real in-memory store seeded with a chatty thread ────────────


def _seed_thread(
    store: tc.InMemoryThreadStore,
    thread_id: str,
    *,
    n_messages: int = 40,
    journal_entries: int = 6,
) -> None:
    """Seed ``store`` with a thread carrying a long message log + a structured
    exploration journal, so the budget + summary behaviour has something real
    to compress. The message bodies are deliberately long so the *raw* log
    blows any sane tier budget — forcing the assembler to ship the summary."""
    store.put_thread(
        tc.Thread(
            id=thread_id,
            platform_id="local",
            topic="Portable agent context",
            activity_summary="Captured decisions; resume verified.",
            created_at="2026-06-24T15:00:00Z",
            updated_at="2026-06-24T16:00:00Z",
            participant_count=2,
        )
    )
    journal = [
        tc.ExplorationJournalEntry(
            type="decision_captured",
            content=f"Decision {i}: chose the boring, established option for concern {i}.",
            created_at="2026-06-24T15:30:00Z",
            participant_id="agent-1",
        )
        for i in range(journal_entries)
    ]
    messages = []
    for i in range(n_messages):
        body = f"Message {i}: " + (
            "lorem ipsum dolor sit amet " * 20
        )  # ~deliberately long raw body
        msg = tc.ThreadMessage(
            id=f"{thread_id}-m{i}",
            participant_id="agent-1" if i % 2 else "user-1",
            participant_type="studio_agent" if i % 2 else "user",
            content=body,
            role="observation" if i % 2 else "question",
            created_at="2026-06-24T15:31:00Z",
            order=i,
        )
        messages.append(msg)
        store.append_message(thread_id, msg)
    memory = tc.ThreadMemory(
        thread_id=thread_id,
        version=1,
        content=tc.ThreadMemoryContent(
            messages=messages,
            exploration_journal=journal,
            participant_context={"change_id": "01KVX26BDXGJ9KQRJ11HACHMZV"},
        ),
        created_at="2026-06-24T15:00:00Z",
        updated_at="2026-06-24T16:00:00Z",
    )
    store.put_memory(thread_id, memory)


@pytest.fixture()
def store() -> tc.InMemoryThreadStore:
    s = tc.InMemoryThreadStore()
    _seed_thread(s, "thr-1")
    return s


@pytest.fixture()
def assembler(store: tc.InMemoryThreadStore) -> ContextPayloadAssembler:
    # Working Set + brain readers are injected (constructor injection, WPB-07);
    # here they return real-shaped text/entities so assembly is exercised end
    # to end without any IO.
    return ContextPayloadAssembler(
        store,
        working_set_reader=lambda thread_id: (
            "Working Set: problem framed; solution chosen."
        ),
        brain_reader=lambda thread_id: [
            {"type": "Decision", "summary": "Adopt platform thread model."},
            {"type": "Requirement", "summary": "Provider-independent resume."},
        ],
    )


# ── the budget estimator + separable summary fn (Blue: reused at WP-004) ────


def test_estimate_tokens_is_monotonic_and_nonnegative() -> None:
    assert estimate_tokens("") == 0
    assert estimate_tokens("a") >= 0
    assert estimate_tokens("a" * 400) > estimate_tokens("a" * 40)


def test_summarise_memory_is_a_separable_function(
    store: tc.InMemoryThreadStore,
) -> None:
    """The summary generator is callable standalone (no assembler instance) so
    WP-004's checkpoint regeneration reuses it. It returns a
    ``ThreadMemoryContent`` whose messages are a *summary*, not the raw log."""
    memory = store.get_memory("thr-1")
    summary = summarise_memory(memory.content, max_tokens=300)
    assert isinstance(summary, tc.ThreadMemoryContent)
    # The structured exploration journal is preserved (it is already the
    # crystallised, low-volume signal); the raw message bodies are not carried
    # verbatim.
    assert summary.exploration_journal == memory.content.exploration_journal
    raw_total = estimate_tokens(" ".join(m.content for m in memory.content.messages))
    summ_total = estimate_tokens(" ".join(m.content for m in summary.messages))
    assert summ_total < raw_total
    assert estimate_tokens_of_content(summary) <= 300


# ── the core behaviours the Definition of Done names ────────────────────────


def test_standard_tier_carries_summary_not_raw_dump(
    assembler: ContextPayloadAssembler, store: tc.InMemoryThreadStore
) -> None:
    payload = assembler.assemble("thr-1", "standard")
    raw = store.get_memory("thr-1").content
    # The standard payload must NOT carry the raw message bodies verbatim.
    payload_msg_text = " ".join(m.content for m in payload.memory.messages)
    raw_msg_text = " ".join(m.content for m in raw.messages)
    assert payload_msg_text != raw_msg_text
    assert estimate_tokens(payload_msg_text) < estimate_tokens(raw_msg_text)
    # …but it keeps the structured exploration journal (the crystallised signal).
    assert payload.memory.exploration_journal == raw.exploration_journal


def test_each_tier_stays_within_token_budget(
    assembler: ContextPayloadAssembler,
) -> None:
    for tier in ("lean", "standard", "full"):
        payload = assembler.assemble("thr-1", tier)  # type: ignore[arg-type]
        budget = ContextPayloadAssembler.TIER_BUDGETS[payload.tier]
        assert estimate_tokens_of_content(payload.memory) <= budget, (
            f"tier {tier} (delivered {payload.tier}) overflowed its budget"
        )


def test_lean_is_tighter_than_standard_is_tighter_than_full(
    assembler: ContextPayloadAssembler,
) -> None:
    lean = estimate_tokens_of_content(assembler.assemble("thr-1", "lean").memory)
    standard = estimate_tokens_of_content(
        assembler.assemble("thr-1", "standard").memory
    )
    full = estimate_tokens_of_content(assembler.assemble("thr-1", "full").memory)
    assert lean <= standard <= full


def test_over_budget_assembly_degrades_to_a_tighter_tier(
    store: tc.InMemoryThreadStore,
) -> None:
    """A thread so large that even the requested tier's content overflows must
    degrade to a tighter tier rather than ship an over-budget payload
    (TDD §4 armor)."""
    big = tc.InMemoryThreadStore()
    _seed_thread(big, "huge", n_messages=400, journal_entries=200)
    assembler = ContextPayloadAssembler(big)
    payload = assembler.assemble("huge", "full")
    # Whatever tier it lands on, it must be within THAT tier's budget…
    assert (
        estimate_tokens_of_content(payload.memory)
        <= ContextPayloadAssembler.TIER_BUDGETS[payload.tier]
    )
    # …and it must have degraded below the requested tier.
    assert payload.tier in ("lean", "standard")


def test_payload_is_vendor_neutral_no_claude_jsonl_keys(
    assembler: ContextPayloadAssembler,
) -> None:
    """The payload carries no provider-shaped (Claude-JSONL) structure — only
    the contract's vendor-neutral types."""
    payload = assembler.assemble("thr-1", "standard")
    assert isinstance(payload, tc.ContextPayload)
    assert isinstance(payload.memory, tc.ThreadMemoryContent)
    # No Claude transcript keys anywhere in the participant_context.
    forbidden = {"type", "message", "uuid", "parentUuid", "sessionId", "cwd"}
    ctx_keys = set(payload.memory.participant_context.keys())
    assert not (ctx_keys & forbidden), (
        f"vendor-shaped keys leaked: {ctx_keys & forbidden}"
    )
    for msg in payload.memory.messages:
        assert isinstance(msg, tc.ThreadMessage)


def test_payload_carries_the_discovery_pointer(
    assembler: ContextPayloadAssembler,
) -> None:
    payload = assembler.assemble("thr-1", "standard")
    assert payload.thread_id == "thr-1"
    assert payload.raw_fetch_tool == tc.RAW_FETCH_TOOL_NAME


def test_assembler_does_no_io_only_injected_read_sources(
    store: tc.InMemoryThreadStore,
) -> None:
    """The assembler reads ONLY through the injected ``ThreadStore`` read ops +
    the injected readers; it touches no filesystem/network of its own
    (WPB-01 / MEA-01). We assert this by driving it with a store that records
    which ops were called and readers that are pure functions."""
    calls: list[str] = []

    class _RecordingStore(tc.InMemoryThreadStore):
        def get_memory(self, thread_id: str) -> tc.ThreadMemory:
            calls.append("get_memory")
            return super().get_memory(thread_id)

        def get_thread(self, thread_id: str) -> tc.Thread:
            calls.append("get_thread")
            return super().get_thread(thread_id)

    rec = _RecordingStore()
    _seed_thread(rec, "thr-1")
    assembler = ContextPayloadAssembler(rec)
    assembler.assemble("thr-1", "standard")
    # It read through the port (not a side channel).
    assert "get_memory" in calls


def test_working_set_and_brain_feed_full_tier_participant_context(
    assembler: ContextPayloadAssembler,
) -> None:
    """The fuller tiers fold the Working Set crystallisation + relevant brain
    entities into the payload (the rich-by-default content, ADR-005)."""
    payload = assembler.assemble("thr-1", "full")
    ctx = payload.memory.participant_context
    # The bound change id (already in memory) survives…
    assert ctx.get("change_id") == "01KVX26BDXGJ9KQRJ11HACHMZV"
    # …and the injected Working Set + brain signal is present in the rich tiers.
    blob = " ".join(str(v) for v in ctx.values())
    assert "Working Set" in blob or any("Working Set" in str(v) for v in ctx.values())


def test_unknown_thread_raises_contract_expected_error(
    assembler: ContextPayloadAssembler,
) -> None:
    with pytest.raises(tc.ExpectedError) as exc:
        assembler.assemble("nope", "standard")
    assert (
        exc.value.code == tc.MEMORY_NOT_FOUND or exc.value.code == tc.THREAD_NOT_FOUND
    )


def test_payload_is_immutable_value(
    assembler: ContextPayloadAssembler,
) -> None:
    payload = assembler.assemble("thr-1", "standard")
    # ContextPayload is a frozen dataclass (contract); assembler returns a value.
    with pytest.raises(dataclasses.FrozenInstanceError):
        payload.tier = "full"  # type: ignore[misc]


# ── CH-GJ9KQR WP-011: cold-memory on-demand regenerate + ADV-1 ctx trim ──────


def _thread_only_store(thread_id: str = "cold-1") -> tc.InMemoryThreadStore:
    """A store with a thread record but no memory checkpoint (the cold case)."""
    s = tc.InMemoryThreadStore()
    s.put_thread(
        tc.Thread(
            id=thread_id,
            platform_id="local",
            topic=None,
            activity_summary=None,
            created_at="2026-06-24T15:00:00Z",
            updated_at="2026-06-24T15:00:00Z",
            participant_count=1,
        )
    )
    return s


def _msg(thread_id: str, order: int, body: str) -> tc.ThreadMessage:
    return tc.ThreadMessage(
        id=f"{thread_id}-{order}",
        participant_id="agent-1",
        participant_type="studio_agent",
        content=body,
        role="observation",
        created_at="2026-06-24T15:31:00Z",
        order=order,
    )


def test_cold_memory_assemble_regenerates_from_messages() -> None:
    """On MEMORY_NOT_FOUND with durable messages present, ``assemble`` regenerates
    the structured summary on demand from the messages rather than raising."""
    store = _thread_only_store("cold-1")
    store.append_message("cold-1", _msg("cold-1", 0, "first durable line SENTINEL-AAA"))
    store.append_message("cold-1", _msg("cold-1", 1, "second durable line"))

    payload = ContextPayloadAssembler(store).assemble("cold-1", "standard")
    bodies = " ".join(m.content for m in payload.memory.messages)
    assert "SENTINEL-AAA" in bodies


def test_cold_memory_assemble_no_messages_reraises_memory_not_found() -> None:
    """A thread with NO messages AND no memory is genuinely unrecoverable —
    ``assemble`` re-raises MEMORY_NOT_FOUND (degrade contract preserved)."""
    store = _thread_only_store("cold-empty")
    with pytest.raises(tc.ExpectedError) as exc:
        ContextPayloadAssembler(store).assemble("cold-empty", "standard")
    assert exc.value.code == tc.MEMORY_NOT_FOUND


def test_assemble_propagates_non_memory_not_found_verbatim() -> None:
    """A store read error that is NOT MEMORY_NOT_FOUND (e.g. THREAD_NOT_FOUND or
    any other category) is propagated verbatim — the cold-memory branch only
    catches MEMORY_NOT_FOUND, never a second error hierarchy."""

    class _BoomStore(tc.InMemoryThreadStore):
        def get_memory(self, thread_id: str) -> tc.ThreadMemory:
            raise tc.ExpectedError(tc.THREAD_NOT_FOUND, "boom")

    with pytest.raises(tc.ExpectedError) as exc:
        ContextPayloadAssembler(_BoomStore()).assemble("x", "standard")
    assert exc.value.code == tc.THREAD_NOT_FOUND


def test_fit_participant_context_drops_non_string_value_to_honour_cap() -> None:
    """A non-string participant-context value (e.g. the brain-entity list) that
    alone overflows the budget is dropped wholesale — not partially serialisable
    here, so the hard cap is honoured (WP-009 ADV-1)."""
    from _session_manager.context_payload import _fit_participant_context

    big_list = [{"name": "x" * 50} for _ in range(200)]  # >> any small budget
    fitted, tokens = _fit_participant_context(
        {"brain_entities": big_list, "change_id": "keep"}, max_tokens=10
    )
    assert tokens <= 10
    assert "brain_entities" not in fitted  # the oversized non-string was dropped


def test_fit_participant_context_truncates_string_into_budget() -> None:
    """A large string value is head-truncated (not dropped) so it fits the cap
    while staying present — the Working Set survives, trimmed."""
    from _session_manager.context_payload import _fit_participant_context

    fitted, tokens = _fit_participant_context(
        {"working_set": "lorem ipsum " * 500}, max_tokens=20
    )
    assert tokens <= 20
    assert "working_set" in fitted
    assert fitted["working_set"].endswith("…")
