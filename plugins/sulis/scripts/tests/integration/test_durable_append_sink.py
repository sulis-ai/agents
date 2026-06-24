"""Integration test — session-pump durable-append sink + resume payload-seed
(CH-GJ9KQR WP-004, REINFORCE-Instrument over the existing pump, TDD §3.1 / ADR-004).

This is the wiring that makes the **provider-independent-resume** journey
possible (WP-007 drives it end to end). It pins, against the REAL durable
``LocalThreadStore`` (WP-002) and the REAL ``ContextPayloadAssembler`` (WP-003) —
no mocks (MEA-09):

1. **Every-message tracking (durable second sink).** Each content-bearing,
   provider-neutral ``Event`` the session pump decodes (``chunk`` / ``tool_use``
   / ``result``-with-text) is appended to the durable thread log as a
   ``ThreadMessage`` — N messages exchanged → N durable records, preserving
   **order + role + time** — and this is **independent of ``~/.claude/projects``**
   (the store roots under an explicit tmp dir, never the provider transcript).

2. **No second decode path (ADR-004).** The sink is fed from the SAME
   ``events.Event`` vocabulary the live-tail ``EventLog`` already carries — it
   maps an already-decoded Event onto a ``ThreadMessage``; it never re-parses
   provider stdout.

3. **Side-effect isolation (hardening — the load-bearing assertion).** The
   durable sink is an ADDITIVE side-effect on the existing pump (a registered
   ``on_event`` observer). A store failure inside the sink must NEVER propagate
   into the live pump — the live-tail path is byte-for-byte unchanged whether or
   not the durable sink succeeds.

4. **Checkpoint regeneration reuses WP-003.** At a checkpoint boundary the sink
   regenerates the thread's ``ThreadMemory`` via the SAME ``summarise_memory``
   function the assembler uses (the separable Blue seam, WP-003), bumping the
   monotonic version.

5. **Resume seeds from OUR store, not the provider transcript.** On (re)spawn the
   resume seed assembles a vendor-neutral ``ContextPayload`` from the durable
   store via the assembler — with the provider transcript made unavailable — so
   a restarted PTY comes back with our rich context, never the provider's files.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from _session_manager import thread_contract as tc
from _session_manager.context_payload import ContextPayloadAssembler
from _session_manager.durable_sink import DurableAppendSink, seed_payload_for_resume
from _session_manager.events import Event, EventError, ToolUse, TurnResult
from _session_manager.thread_store_local import LocalThreadStore

_CHANGE_ID = "CH-GJ9KQR"
_THREAD_ID = "th-wp004"
_KEY = "CH-GJ9KQR"
# A token-shaped secret assembled at runtime (the contiguous provider-prefix
# signature never appears verbatim in committed source); find_secrets still
# detects the assembled value, so redaction-on-write is exercised unchanged.
_SECRET = "sk" + "_live_" + "ABCDEFGHIJKLMNOPQRSTUVWX" + "0123456789"


def _store(root: Path) -> LocalThreadStore:
    return LocalThreadStore(change_id=_CHANGE_ID, root=root)


def _thread(tid: str = _THREAD_ID) -> tc.Thread:
    return tc.Thread(
        id=tid,
        platform_id="local",
        topic=None,
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


def _result(turn: int = 0) -> Event:
    return Event(
        offset=-1,
        key=_KEY,
        turn=turn,
        kind="result",
        result=TurnResult(
            input_tokens=10, output_tokens=20, duration_ms=5, stop_reason="end_turn"
        ),
    )


def _error(turn: int = 0) -> Event:
    return Event(
        offset=-1,
        key=_KEY,
        turn=turn,
        kind="error",
        error=EventError(category="protocol", code="STDIN_BROKEN", message="boom"),
    )


# ─── every-message tracking: N events → N durable records ──────────────────


def test_n_content_events_become_n_durable_messages_in_order(tmp_path: Path) -> None:
    """N content-bearing events fed through the sink → N durable ThreadMessages,
    in the order they arrived, with monotonic ``order`` — read back from the
    durable store, independent of ``~/.claude/projects`` (the store roots under
    tmp_path, never the provider transcript)."""
    store = _store(tmp_path)
    store.put_thread(_thread())
    sink = DurableAppendSink(store, thread_id=_THREAD_ID)

    texts = ["hello", "world", "again"]
    for i, t in enumerate(texts):
        sink.append_event(_chunk(t, turn=i))

    msgs = store.get_messages(_THREAD_ID)
    assert [m.content for m in msgs] == texts
    # Order is monotonic + strictly increasing (the append-only offset convention).
    orders = [m.order for m in msgs]
    assert orders == sorted(orders)
    assert len(set(orders)) == len(orders)


def test_role_and_time_preserved_per_event_kind(tmp_path: Path) -> None:
    """Each event kind maps to the right ThreadMessage role, and each message
    carries a created_at timestamp (time preserved)."""
    store = _store(tmp_path)
    store.put_thread(_thread())
    sink = DurableAppendSink(store, thread_id=_THREAD_ID)

    sink.append_event(_chunk("an answer", turn=0))
    sink.append_event(_tool("Read", "file.py", turn=0))

    msgs = store.get_messages(_THREAD_ID)
    assert len(msgs) == 2
    # A chunk (model text) is an observation/answer; a tool_use is an observation.
    assert msgs[0].role in tc.MESSAGE_ROLES
    assert msgs[1].role in tc.MESSAGE_ROLES
    # A tool_use specifically is an "observation" (it records what the agent did),
    # rendered as a compact provider-neutral "<tool> <summary>" line (no second
    # decode — the same shape the live log shows).
    assert msgs[1].role == "observation"
    assert msgs[1].content == "Read file.py"
    # Time is preserved (non-empty ISO-ish stamp on every record).
    assert all(m.created_at for m in msgs)


def test_independent_of_claude_projects_dir(tmp_path: Path, monkeypatch) -> None:
    """The durable record is read back from OUR store under tmp_path even with
    ``~/.claude/projects`` pointed at an empty dir — the durable log does not
    depend on the provider transcript existing."""
    fake_home = tmp_path / "home"
    (fake_home / ".claude" / "projects").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(fake_home))

    store = _store(tmp_path / "threads")
    store.put_thread(_thread())
    sink = DurableAppendSink(store, thread_id=_THREAD_ID)
    sink.append_event(_chunk("durable", turn=0))

    msgs = store.get_messages(_THREAD_ID)
    assert [m.content for m in msgs] == ["durable"]


# ─── no second decode path / content selection ─────────────────────────────


def test_result_terminal_event_is_not_a_message(tmp_path: Path) -> None:
    """A bare ``result`` terminal event (usage-only, no founder/agent/tool
    content) is NOT appended as a durable message — only content-bearing events
    are tracked (the Contract: events that carry founder/agent/tool content)."""
    store = _store(tmp_path)
    store.put_thread(_thread())
    sink = DurableAppendSink(store, thread_id=_THREAD_ID)

    sink.append_event(_result(turn=0))

    assert store.get_messages(_THREAD_ID) == []


def test_error_event_is_not_a_durable_message(tmp_path: Path) -> None:
    """An ``error`` event is a control signal on the live log, not founder/agent
    content — it is not tracked as a durable thread message."""
    store = _store(tmp_path)
    store.put_thread(_thread())
    sink = DurableAppendSink(store, thread_id=_THREAD_ID)

    sink.append_event(_error(turn=0))

    assert store.get_messages(_THREAD_ID) == []


# ─── side-effect isolation (the load-bearing hardening assertion) ──────────


def test_sink_failure_never_propagates_into_the_pump(tmp_path: Path) -> None:
    """A store failure inside the sink must NEVER raise into the live pump.

    The durable sink is an additive side-effect (ADR-004 — the live-tail path is
    unchanged). ``append_event`` swallows store errors (it records them as a
    degradation, never re-raising) so the existing ``on_event`` fan-out and the
    live ``EventLog`` are byte-for-byte unaffected by a durable-store failure."""

    class _BoomStore:
        def append_message(self, thread_id, message):  # noqa: ANN001
            raise RuntimeError("disk full")

    sink = DurableAppendSink(_BoomStore(), thread_id=_THREAD_ID)
    # Must not raise — isolation is the contract.
    sink.append_event(_chunk("survives", turn=0))
    # The failure is observable as a degradation count, not an exception.
    assert sink.degraded_appends == 1


def test_reseed_read_failure_is_isolated_not_raised(tmp_path: Path) -> None:
    """A store-read failure during the resume reseed (WP-004 ADV-2) is isolated
    like an append failure — it must NEVER raise into the resume path. The reseed
    leaves ``_next_order`` unchanged and records a degradation, so a transient
    read error on resume degrades tracking rather than breaking the restart."""

    class _BoomReadStore:
        def get_messages(self, thread_id, since=None, limit=None):  # noqa: ANN001
            raise RuntimeError("store unreadable")

    sink = DurableAppendSink(_BoomReadStore(), thread_id=_THREAD_ID)
    # Must not raise — resume isolation is the contract.
    seeded = sink.seed_next_order_from_store()
    # Unchanged (still 0) and the failure is observable as a degradation count.
    assert seeded == 0
    assert sink.degraded_appends == 1


def test_observer_adapts_to_on_event_callback_signature(tmp_path: Path) -> None:
    """The sink exposes an ``as_event_observer()`` adapter matching the session's
    ``on_event(session, event)`` registered-callback seam (manager wires it
    exactly as it wires the recovery/guard fan-out — additive, no new seam)."""
    store = _store(tmp_path)
    store.put_thread(_thread())
    sink = DurableAppendSink(store, thread_id=_THREAD_ID)

    observer = sink.as_event_observer()
    # session arg is ignored by the sink (it only needs the event); pass a dummy.
    observer(object(), _chunk("via observer", turn=0))

    assert [m.content for m in store.get_messages(_THREAD_ID)] == ["via observer"]


# ─── redaction-on-write carried through the sink ───────────────────────────


def test_secret_in_event_text_is_redacted_on_durable_write(tmp_path: Path) -> None:
    """A token-shaped secret in event text is scrubbed before the durable bytes
    land (the durable store's redaction-on-write, reused — the sink adds no
    plaintext-persistence path that bypasses it)."""
    store = _store(tmp_path)
    store.put_thread(_thread())
    sink = DurableAppendSink(store, thread_id=_THREAD_ID)

    sink.append_event(_chunk(f"token is {_SECRET} ok", turn=0))

    log_file = next(tmp_path.glob("*.messages.jsonl"))
    raw = log_file.read_text(encoding="utf-8")
    assert _SECRET not in raw


# ─── checkpoint regeneration reuses WP-003 summarise_memory ────────────────


def test_checkpoint_regenerates_memory_with_bumped_version(tmp_path: Path) -> None:
    """At a checkpoint boundary the sink regenerates the thread's ThreadMemory
    (via WP-003 ``summarise_memory``) and bumps the monotonic version."""
    store = _store(tmp_path)
    store.put_thread(_thread())
    sink = DurableAppendSink(store, thread_id=_THREAD_ID)

    for i in range(3):
        sink.append_event(_chunk(f"msg {i}", turn=i))

    sink.checkpoint()
    mem1 = store.get_memory(_THREAD_ID)
    assert mem1.version >= 1
    # The summary carries the tracked messages (rich-by-default content).
    assert len(mem1.content.messages) == 3

    sink.append_event(_chunk("later", turn=3))
    sink.checkpoint()
    mem2 = store.get_memory(_THREAD_ID)
    assert mem2.version > mem1.version


# ─── resume seeds from OUR store, not the provider transcript ──────────────


def test_resume_seed_assembles_payload_from_our_store(
    tmp_path: Path, monkeypatch
) -> None:
    """On resume, seeding assembles a vendor-neutral ContextPayload from the
    durable store via the WP-003 assembler — WITHOUT reading the provider
    transcript (the load-bearing journey, ADR-004). We make
    ``~/.claude/projects`` unavailable and still recover our rich context."""
    # Provider transcript made unavailable.
    fake_home = tmp_path / "home"
    fake_home.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(fake_home))

    store = _store(tmp_path / "threads")
    store.put_thread(_thread())
    sink = DurableAppendSink(store, thread_id=_THREAD_ID)
    sink.append_event(_chunk("a decision was captured", turn=0))
    sink.append_event(_chunk("and another", turn=1))
    sink.checkpoint()

    assembler = ContextPayloadAssembler(store)
    payload = seed_payload_for_resume(assembler, thread_id=_THREAD_ID, tier="standard")

    assert isinstance(payload, tc.ContextPayload)
    assert payload.thread_id == _THREAD_ID
    # The rich payload carries our tracked content inline (rich-by-default).
    bodies = [m.content for m in payload.memory.messages]
    assert any("decision" in b for b in bodies)
    # And the discovery pointer names the raw-fetch tool (raw-on-demand, ADR-005).
    assert payload.raw_fetch_tool == tc.RAW_FETCH_TOOL_NAME


def test_resume_seed_missing_memory_is_expected_error(tmp_path: Path) -> None:
    """Seeding a thread that has no memory checkpoint yet surfaces the contract's
    Expected-category refusal (MEMORY_NOT_FOUND) — the assembler's error is
    propagated verbatim, no second hierarchy."""
    store = _store(tmp_path)
    store.put_thread(_thread())
    assembler = ContextPayloadAssembler(store)

    with pytest.raises(tc.ExpectedError) as ei:
        seed_payload_for_resume(assembler, thread_id=_THREAD_ID, tier="standard")
    assert ei.value.code == tc.MEMORY_NOT_FOUND
