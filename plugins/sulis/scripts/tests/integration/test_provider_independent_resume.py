"""Seam-close drive — provider-independent resume over the REAL store
(CH-GJ9KQR WP-007, the load-bearing journey, CF-12 / TDD §5 / ADR-004).

This is the change's **verification artifact**. It closes the contract-first
seam (CF-07 + CF-12) by wiring all the merged pieces together LIVE and proving
the load-bearing journey end-to-end over the **real saved record** — no mocks
on the integration path (MEA-09):

  * the real durable :class:`LocalThreadStore` (WP-002) under an explicit tmp
    root (never ``~/.claude/projects``);
  * the real :class:`DurableAppendSink` (WP-004) as the session pump's second
    sink;
  * the real :class:`ContextPayloadAssembler` (WP-003) doing the resume seed.

The journey (spec's load-bearing scenario):

  1. **Run a session** — feed N content-bearing provider-neutral ``Event``s
     through the durable sink (every-message tracking).
  2. **Capture decisions** — checkpoint regenerates the thread's
     ``ThreadMemory`` from OUR store (the rich, vendor-neutral summary).
  3. **End it** — the live process is gone; only OUR durable record remains.
  4. **Make the provider transcript unavailable** — point ``HOME`` at an empty
     dir so ``~/.claude/projects`` carries nothing; the recovery cannot read
     the provider's files even if it tried.
  5. **Resume** — a fresh sink is reseeded from OUR store's high-water mark
     (WP-004 ADV-2) and the agent is seeded with the rich payload assembled
     from OUR store; appends after resume land at the RIGHT order (not silently
     rejected OUT_OF_ORDER_WRITE), and the raw log stays intact + correctly
     ordered.

The ADV-2 gap this drive pins (the real functional gap WP-004's review
flagged): a fresh ``DurableAppendSink`` defaults ``_next_order=0``. Over a
non-empty thread that makes EVERY post-resume append fail OUT_OF_ORDER_WRITE
(silently counted as ``degraded_appends``). The resume MUST reseed
``_next_order`` from ``get_messages(...)[-1].order + 1`` so the conversation
continues, not stalls.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from _session_manager import thread_contract as tc
from _session_manager.context_payload import ContextPayloadAssembler
from _session_manager.durable_sink import DurableAppendSink, seed_payload_for_resume
from _session_manager.events import Event, ToolUse
from _session_manager.thread_store_local import LocalThreadStore

_CHANGE_ID = "CH-GJ9KQR"
_THREAD_ID = "CH-GJ9KQR"  # one thread per change (ADR-004) — keyed by the change
_KEY = "CH-GJ9KQR"


def _store(root: Path) -> LocalThreadStore:
    return LocalThreadStore(change_id=_CHANGE_ID, root=root)


def _thread(tid: str = _THREAD_ID) -> tc.Thread:
    return tc.Thread(
        id=tid,
        platform_id="local",
        topic="portable-agent-context",
        activity_summary=None,
        created_at="2026-06-24T00:00:00Z",
        updated_at="2026-06-24T00:00:00Z",
        participant_count=1,
        resumed_from=None,
    )


def _chunk(text: str, turn: int = 0) -> Event:
    return Event(offset=-1, key=_KEY, turn=turn, kind="chunk", text=text)


def _tool(name: str, summary: str, turn: int = 0) -> Event:
    return Event(
        offset=-1,
        key=_KEY,
        turn=turn,
        kind="tool_use",
        tool=ToolUse(name=name, input_summary=summary),
    )


def _make_provider_transcript_unavailable(tmp_path: Path, monkeypatch) -> None:
    """Point ``HOME`` at an empty dir so the provider's ``~/.claude/projects``
    transcript is unavailable — resume must recover from OUR store regardless."""
    fake_home = tmp_path / "home"
    (fake_home / ".claude" / "projects").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(fake_home))


# ─── the load-bearing journey, end-to-end over the real store ──────────────


def test_resume_recovers_rich_context_from_our_store_with_transcript_gone(
    tmp_path: Path, monkeypatch
) -> None:
    """Run → capture → end → transcript unavailable → resume: the agent comes
    back with the rich payload (summary + tracked content) assembled from OUR
    durable store, never the provider transcript."""
    store_root = tmp_path / "threads"
    store = _store(store_root)
    store.put_thread(_thread())

    # (1) run a session: every message tracked durably.
    sink = DurableAppendSink(store, thread_id=_THREAD_ID)
    sink.append_event(_chunk("we decided to use the hybrid local store", turn=0))
    sink.append_event(_tool("Edit", "thread_store_local.py", turn=0))
    sink.append_event(_chunk("and the assembler stays vendor-neutral", turn=1))

    # (2) capture decisions: checkpoint regenerates ThreadMemory from OUR store.
    sink.checkpoint()

    # (3) end the live process: only OUR durable record remains (we drop the
    #     sink object — the live pump is gone).
    del sink

    # (4) make the provider transcript unavailable.
    _make_provider_transcript_unavailable(tmp_path, monkeypatch)

    # (5) resume: seed the rich payload from OUR store.
    assembler = ContextPayloadAssembler(store)
    payload = seed_payload_for_resume(assembler, thread_id=_THREAD_ID, tier="standard")

    assert isinstance(payload, tc.ContextPayload)
    assert payload.thread_id == _THREAD_ID
    # Rich-by-default: the tracked decision content is carried inline.
    bodies = [m.content for m in payload.memory.messages]
    assert any("hybrid local store" in b for b in bodies)
    assert any("vendor-neutral" in b for b in bodies)
    # The discovery pointer names the raw-fetch tool (raw-on-demand, ADR-005).
    assert payload.raw_fetch_tool == tc.RAW_FETCH_TOOL_NAME


def test_resume_reseeds_next_order_so_appends_continue_not_stall(
    tmp_path: Path, monkeypatch
) -> None:
    """WP-004 ADV-2 (the real gap): on resume a FRESH sink must reseed
    ``_next_order`` from the store high-water mark, so post-resume appends land
    at the right order — NOT silently rejected OUT_OF_ORDER_WRITE (degraded).

    Without the reseed, a fresh sink's ``_next_order=0`` collides with the
    existing log and EVERY append degrades. With it, the conversation continues
    and the raw log stays intact + correctly ordered."""
    store_root = tmp_path / "threads"
    store = _store(store_root)
    store.put_thread(_thread())

    # Pre-resume conversation: three durable messages (orders 0,1,2).
    pre = DurableAppendSink(store, thread_id=_THREAD_ID)
    for i in range(3):
        pre.append_event(_chunk(f"pre {i}", turn=i))
    assert [m.order for m in store.get_messages(_THREAD_ID)] == [0, 1, 2]
    del pre

    _make_provider_transcript_unavailable(tmp_path, monkeypatch)

    # Resume: a fresh sink reseeded from the store high-water mark.
    resumed = DurableAppendSink(store, thread_id=_THREAD_ID)
    resumed.seed_next_order_from_store()
    resumed.append_event(_chunk("post-resume one", turn=3))
    resumed.append_event(_chunk("post-resume two", turn=4))

    # The post-resume appends LANDED (not degraded) and continue the order.
    assert resumed.degraded_appends == 0
    msgs = store.get_messages(_THREAD_ID)
    assert [m.order for m in msgs] == [0, 1, 2, 3, 4]
    assert [m.content for m in msgs] == [
        "pre 0",
        "pre 1",
        "pre 2",
        "post-resume one",
        "post-resume two",
    ]


def test_reseed_on_empty_thread_starts_at_zero(tmp_path: Path) -> None:
    """Reseeding a fresh thread with no prior messages is a no-op:
    ``_next_order`` stays at 0 so the first append lands at order 0."""
    store = _store(tmp_path / "threads")
    store.put_thread(_thread())

    sink = DurableAppendSink(store, thread_id=_THREAD_ID)
    sink.seed_next_order_from_store()
    sink.append_event(_chunk("first", turn=0))

    assert sink.degraded_appends == 0
    assert [m.order for m in store.get_messages(_THREAD_ID)] == [0]


def test_raw_log_intact_and_correctly_ordered_after_resume(
    tmp_path: Path, monkeypatch
) -> None:
    """After a resume cycle the RAW message log (the discovery seam's
    ``get_messages``) is intact and correctly ordered from OUR store — the
    append-only invariant held across the resume boundary."""
    store_root = tmp_path / "threads"
    store = _store(store_root)
    store.put_thread(_thread())

    s1 = DurableAppendSink(store, thread_id=_THREAD_ID)
    s1.append_event(_chunk("alpha", turn=0))
    s1.append_event(_chunk("beta", turn=1))
    s1.checkpoint()
    del s1

    _make_provider_transcript_unavailable(tmp_path, monkeypatch)

    s2 = DurableAppendSink(store, thread_id=_THREAD_ID)
    s2.seed_next_order_from_store()
    s2.append_event(_chunk("gamma", turn=2))

    raw = store.get_messages(_THREAD_ID)
    orders = [m.order for m in raw]
    assert orders == sorted(orders)
    assert len(set(orders)) == len(orders)
    assert [m.content for m in raw] == ["alpha", "beta", "gamma"]


def test_resume_seed_without_checkpoint_regenerates_on_demand(
    tmp_path: Path, monkeypatch
) -> None:
    """A resume seed on a thread that has messages but no checkpoint yet
    regenerates the structured summary ON DEMAND from the durable messages
    (CH-GJ9KQR WP-011) — the COMMON first-resume case. Converted from the prior
    "surfaces MEMORY_NOT_FOUND" contract: before WP-011 the assembler hard-
    required a saved memory, so the first resume degraded; now it builds the
    summary from the messages so the rich path fires before any checkpoint."""
    store = _store(tmp_path / "threads")
    store.put_thread(_thread())
    sink = DurableAppendSink(store, thread_id=_THREAD_ID)
    sink.append_event(_chunk("regenerated on demand", turn=0))
    del sink

    _make_provider_transcript_unavailable(tmp_path, monkeypatch)

    assembler = ContextPayloadAssembler(store)
    payload = seed_payload_for_resume(assembler, thread_id=_THREAD_ID, tier="standard")
    # The durable message body is carried in the regenerated summary — no
    # checkpoint was ever taken.
    bodies = [m.content for m in payload.memory.messages]
    assert any("regenerated on demand" in b for b in bodies), (
        "the cold-memory resume seed did not regenerate the summary from the "
        "durable messages"
    )


def test_resume_seed_with_no_messages_and_no_memory_surfaces_expected_error(
    tmp_path: Path, monkeypatch
) -> None:
    """The genuinely-unrecoverable case — a thread with NO messages AND no
    checkpoint — still surfaces the contract's Expected-category refusal
    (MEMORY_NOT_FOUND): there is nothing to regenerate on demand, so the
    assembler propagates the three-category error verbatim and the live wiring's
    degrade-to-plain-brief isolation (WP-004) stays pinned (CH-GJ9KQR WP-011)."""
    store = _store(tmp_path / "threads")
    store.put_thread(_thread())  # thread exists, but NO messages, NO memory

    _make_provider_transcript_unavailable(tmp_path, monkeypatch)

    assembler = ContextPayloadAssembler(store)
    with pytest.raises(tc.ExpectedError) as ei:
        seed_payload_for_resume(assembler, thread_id=_THREAD_ID, tier="standard")
    assert ei.value.code == tc.MEMORY_NOT_FOUND
