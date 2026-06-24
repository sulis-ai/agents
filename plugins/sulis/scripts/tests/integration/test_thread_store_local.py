"""Integration test — ``ThreadStore`` durable LOCAL adapter (CH-GJ9KQR WP-002).

The shared ``ThreadStore`` contract test (``tests/unit/test_thread_store_contract.py``)
already runs every port invariant against this adapter via its parametrised
``store`` fixture (MEA-09 — shared contract test, no mocks). THIS file pins the
three properties the contract test cannot express because they are about the
*durable* binding specifically (TDD §3.2/§4, WP-002 Definition of Done):

1. **Durability across process restart** — bytes survive; a fresh adapter
   instance over the same store root rehydrates the thread/messages/memory.
2. **Append-only, persisted** — a rewrite / out-of-order append is a
   deterministic refusal (``ExpectedError``) *and* the on-disk log is left
   intact (the guard validates before any byte is written).
3. **Redaction-on-write** — a token-shaped secret fed through
   ``append_message`` is scrubbed *before* bytes land; the raw ``.jsonl`` file
   never contains the secret (the new persistence surface inherits the
   outbound-scrub posture — TDD §4, reusing ``_secret_patterns``).

These run with the real filesystem (a pytest ``tmp_path``), no mocks — the
adapter's IO is exercised end to end.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from _session_manager import thread_contract as tc
from _session_manager.events import ExpectedError
from _session_manager.thread_store_local import LocalThreadStore

_CHANGE_ID = "CH-GJ9KQR"
# A token-shaped secret: a bare long-token the outbound-scrub catalogue catches
# (no env-assignment glue, so we are testing redaction of the value itself).
# ASSEMBLED at runtime from parts so the contiguous provider-prefix signature
# never appears verbatim in committed source (GitHub secret-scanning push
# protection flags a literal sk_live_ string); find_secrets still detects the
# assembled value, so the redaction under test is unchanged.
_SECRET = "sk" + "_live_" + "ABCDEFGHIJKLMNOPQRSTUVWX" + "0123456789"
# A modern OpenAI project-scoped key (WP-010 — the GAP 3 blind spot). Assembled
# at runtime for the same push-safety reason; the new catalogue pattern must
# reach this persistence surface so the key never lands verbatim on disk.
_OPENAI_KEY = "sk-proj-" + "T3BlbkFJ" + "aB3dEf6hIjKlMn0pQrStUvWx" + "Yz12_3-4"


def _store(root: Path) -> LocalThreadStore:
    return LocalThreadStore(change_id=_CHANGE_ID, root=root)


def _thread(tid: str) -> tc.Thread:
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


def _msg(mid: str, order: int, content: str = "hi") -> tc.ThreadMessage:
    return tc.ThreadMessage(
        id=mid,
        participant_id="studio_agent_1",
        participant_type="studio_agent",
        content=content,
        role="observation",
        created_at="2026-06-24T00:00:00Z",
        order=order,
    )


def _memory(tid: str, version: int) -> tc.ThreadMemory:
    return tc.ThreadMemory(
        thread_id=tid,
        version=version,
        content=tc.ThreadMemoryContent(
            messages=[],
            exploration_journal=[],
            participant_context={"change_id": _CHANGE_ID},
        ),
        created_at="2026-06-24T00:00:00Z",
        updated_at="2026-06-24T00:00:00Z",
    )


# ── 1. durability across process restart ──────────────────────────────────


def test_durability_across_process_restart(tmp_path: Path) -> None:
    """A fresh adapter instance over the same store root rehydrates everything
    a prior instance wrote — the load-bearing property of the durable binding
    (provider-independent resume reads from OUR store, TDD §3.2)."""
    root = tmp_path / "threads"

    # First "process": write a thread, two messages, a memory checkpoint.
    writer = _store(root)
    writer.put_thread(_thread("t1"))
    writer.append_message("t1", _msg("m0", 0, "first"))
    writer.append_message("t1", _msg("m1", 1, "second"))
    writer.put_memory("t1", _memory("t1", version=1))

    # Second "process": a brand-new adapter over the same root, no shared state.
    reader = _store(root)
    assert reader.get_thread("t1").id == "t1"
    msgs = reader.get_messages("t1")
    assert [(m.id, m.order, m.content) for m in msgs] == [
        ("m0", 0, "first"),
        ("m1", 1, "second"),
    ]
    assert reader.get_memory("t1").version == 1
    assert (
        reader.get_memory("t1").content.participant_context["change_id"] == _CHANGE_ID
    )


def test_durability_appends_persist_across_instances(tmp_path: Path) -> None:
    """An append made through a second instance lands after the first
    instance's writes — the offset-ordered log is rehydrated, not reset."""
    root = tmp_path / "threads"
    first = _store(root)
    first.append_message("t1", _msg("m0", 0))

    second = _store(root)
    second.append_message("t1", _msg("m1", 1))

    third = _store(root)
    assert [m.order for m in third.get_messages("t1")] == [0, 1]


# ── 2. append-only invariant, persisted ────────────────────────────────────


def test_append_only_rejects_rewrite_and_leaves_log_intact(tmp_path: Path) -> None:
    """Re-appending a stored id is a rewrite — refused (``DUPLICATE_MESSAGE``),
    and the on-disk log is unchanged (the guard validates before writing)."""
    root = tmp_path / "threads"
    store = _store(root)
    store.append_message("t1", _msg("m0", 0))

    log_path = root / tc.messages_record_filename("t1")
    before = log_path.read_bytes()

    with pytest.raises(ExpectedError) as exc:
        store.append_message("t1", _msg("m0", 1))  # duplicate id
    assert exc.value.code == tc.DUPLICATE_MESSAGE
    assert log_path.read_bytes() == before, "rejected rewrite must not touch bytes"

    # The refusal also holds across a process restart (read from disk, not RAM).
    restarted = _store(root)
    with pytest.raises(ExpectedError) as exc2:
        restarted.append_message("t1", _msg("m0", 9))
    assert exc2.value.code == tc.DUPLICATE_MESSAGE


def test_append_only_rejects_out_of_order_and_leaves_log_intact(
    tmp_path: Path,
) -> None:
    """An out-of-order append (order ≤ last) is refused
    (``OUT_OF_ORDER_WRITE``) and leaves the persisted log intact."""
    root = tmp_path / "threads"
    store = _store(root)
    store.append_message("t1", _msg("m0", 0))
    store.append_message("t1", _msg("m1", 1))

    log_path = root / tc.messages_record_filename("t1")
    before = log_path.read_bytes()

    with pytest.raises(ExpectedError) as exc:
        store.append_message("t1", _msg("stale", 1))  # not > last order
    assert exc.value.code == tc.OUT_OF_ORDER_WRITE
    assert log_path.read_bytes() == before


def test_put_memory_rejects_stale_version_persisted(tmp_path: Path) -> None:
    """ThreadMemory.version is monotonic; a stale/equal version is refused and
    the stored version is unchanged — across a fresh instance too."""
    root = tmp_path / "threads"
    store = _store(root)
    store.put_memory("t1", _memory("t1", version=5))

    restarted = _store(root)
    with pytest.raises(ExpectedError) as exc:
        restarted.put_memory("t1", _memory("t1", version=5))
    assert exc.value.code == tc.STALE_MEMORY_VERSION
    assert restarted.get_memory("t1").version == 5


# ── 3. redaction-on-write (the new persistence surface) ────────────────────


def test_token_secret_scrubbed_before_bytes_land(tmp_path: Path) -> None:
    """A token-shaped secret in message content is scrubbed BEFORE it is
    written — the raw ``.messages.jsonl`` file never contains the secret
    (TDD §4: redaction-on-write, reusing ``_secret_patterns``)."""
    root = tmp_path / "threads"
    store = _store(root)
    store.append_message(
        "t1", _msg("m0", 0, content=f"my key is {_SECRET} keep it safe")
    )

    log_path = root / tc.messages_record_filename("t1")
    raw_bytes = log_path.read_bytes()
    assert _SECRET.encode() not in raw_bytes, "secret leaked to disk unredacted"
    assert b"keep it safe" in raw_bytes, "non-secret content must be preserved"

    # And the in-memory read path returns the redacted content (one scrub, on
    # write — the read does not re-scrub or expose the raw value).
    got = store.get_messages("t1")[0]
    assert _SECRET not in got.content
    assert "keep it safe" in got.content


def test_openai_key_scrubbed_before_bytes_land(tmp_path: Path) -> None:
    """A modern OpenAI key (``sk-proj-…``) in message content is scrubbed to
    ``[redacted-secret]`` BEFORE bytes land — proving the WP-010 catalogue
    pattern reaches the store's redaction-on-write surface (GAP 3 closure).

    Agent conversations routinely echo LLM API keys, so this is the
    highest-likelihood secret type for the durable thread store."""
    root = tmp_path / "threads"
    store = _store(root)
    store.append_message(
        "t1", _msg("m0", 0, content=f"my key is {_OPENAI_KEY} keep it safe")
    )

    log_path = root / tc.messages_record_filename("t1")
    raw_bytes = log_path.read_bytes()
    assert _OPENAI_KEY.encode() not in raw_bytes, "OpenAI key leaked to disk"
    assert b"[redacted-secret]" in raw_bytes, "secret span must be redacted"
    assert b"keep it safe" in raw_bytes, "non-secret content must be preserved"

    got = store.get_messages("t1")[0]
    assert _OPENAI_KEY not in got.content
    assert "keep it safe" in got.content


def test_redaction_scrubs_memory_content_before_write(tmp_path: Path) -> None:
    """The memory checkpoint is the same new persistence surface; a secret in
    an exploration-journal entry is scrubbed before the ``.memory.json`` bytes
    land."""
    root = tmp_path / "threads"
    store = _store(root)
    memory = tc.ThreadMemory(
        thread_id="t1",
        version=1,
        content=tc.ThreadMemoryContent(
            messages=[_msg("m0", 0, content=f"token {_SECRET}")],
            exploration_journal=[
                tc.ExplorationJournalEntry(
                    type="decision_captured",
                    content=f"decided to use {_SECRET}",
                    created_at="2026-06-24T00:00:00Z",
                )
            ],
            participant_context={"change_id": _CHANGE_ID},
        ),
        created_at="2026-06-24T00:00:00Z",
        updated_at="2026-06-24T00:00:00Z",
    )
    store.put_memory("t1", memory)

    mem_path = root / tc.memory_record_filename("t1")
    assert _SECRET.encode() not in mem_path.read_bytes(), "secret leaked to disk"

    hydrated = store.get_memory("t1")
    assert _SECRET not in hydrated.content.exploration_journal[0].content
    assert _SECRET not in hydrated.content.messages[0].content


def test_redaction_scrubs_thread_topic_and_summary(tmp_path: Path) -> None:
    """A token pasted into a Thread's free-text topic/activity_summary must be
    scrubbed before the ``.thread.json`` bytes land — the Thread record is the
    same new persistence surface as the message log (redaction-bypass guard)."""
    root = tmp_path / "threads"
    store = _store(root)
    thread = tc.Thread(
        id="t1",
        platform_id="local",
        topic=f"discussing {_SECRET} rotation",
        activity_summary=f"agent leaked {_SECRET} in summary",
        created_at="2026-06-24T00:00:00Z",
        updated_at="2026-06-24T00:00:00Z",
        participant_count=1,
        resumed_from=None,
    )
    store.put_thread(thread)

    raw = (root / tc.thread_record_filename("t1")).read_bytes()
    assert _SECRET.encode() not in raw, "secret leaked into thread record"
    assert b"rotation" in raw and b"summary" in raw, "non-secret text preserved"

    got = store.get_thread("t1")
    assert got.topic is not None and _SECRET not in got.topic
    assert got.activity_summary is not None and _SECRET not in got.activity_summary


def test_redaction_scrubs_participant_context_values(tmp_path: Path) -> None:
    """``participant_context`` is the contract's open-ended dict — it carries
    'provider identity', exactly the kind of value that holds a token. Its
    string values (nested too) are scrubbed before the ``.memory.json`` bytes
    land."""
    root = tmp_path / "threads"
    store = _store(root)
    memory = tc.ThreadMemory(
        thread_id="t1",
        version=1,
        content=tc.ThreadMemoryContent(
            messages=[],
            exploration_journal=[],
            participant_context={
                "change_id": _CHANGE_ID,
                "provider_token": _SECRET,
                "nested": {"deep_key": f"value with {_SECRET} inside"},
            },
        ),
        created_at="2026-06-24T00:00:00Z",
        updated_at="2026-06-24T00:00:00Z",
    )
    store.put_memory("t1", memory)

    raw = (root / tc.memory_record_filename("t1")).read_bytes()
    assert _SECRET.encode() not in raw, "secret leaked via participant_context"

    pctx = store.get_memory("t1").content.participant_context
    assert pctx["change_id"] == _CHANGE_ID, "non-secret value preserved"
    assert _SECRET not in pctx["provider_token"]
    assert _SECRET not in pctx["nested"]["deep_key"]


def test_redaction_scrubs_journal_metadata(tmp_path: Path) -> None:
    """An ExplorationJournalEntry's open-ended ``metadata`` dict is scrubbed
    before the ``.memory.json`` bytes land (the same surface as
    participant_context)."""
    root = tmp_path / "threads"
    store = _store(root)
    memory = tc.ThreadMemory(
        thread_id="t1",
        version=1,
        content=tc.ThreadMemoryContent(
            messages=[],
            exploration_journal=[
                tc.ExplorationJournalEntry(
                    type="pattern_detected",
                    content="found a pattern",
                    created_at="2026-06-24T00:00:00Z",
                    metadata={"source_token": _SECRET, "kind": "auth"},
                )
            ],
            participant_context={},
        ),
        created_at="2026-06-24T00:00:00Z",
        updated_at="2026-06-24T00:00:00Z",
    )
    store.put_memory("t1", memory)

    raw = (root / tc.memory_record_filename("t1")).read_bytes()
    assert _SECRET.encode() not in raw, "secret leaked via journal metadata"

    meta = store.get_memory("t1").content.exploration_journal[0].metadata
    assert meta is not None
    assert _SECRET not in meta["source_token"]
    assert meta["kind"] == "auth", "non-secret metadata preserved"


# ── adapter conforms to the port (belt-and-braces; the contract test owns
#    this too, but pinning it here keeps the integration file self-describing) ─


def test_local_adapter_conforms_to_port(tmp_path: Path) -> None:
    store = _store(tmp_path / "threads")
    assert isinstance(store, tc.ThreadStore)


def test_default_root_uses_contract_path_convention() -> None:
    """With no explicit ``root`` the adapter resolves the CF-11 pinned store
    root for the change — so production uses the contract path, tests override
    it. (No IO here — we only assert the resolved root, not that we write to
    the real home dir.)"""
    store = LocalThreadStore(change_id=_CHANGE_ID)
    assert store.root == tc.store_root_for_change(_CHANGE_ID)
