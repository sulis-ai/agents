"""Contract test for the thread/message/memory + context-payload seam
(CH-GJ9KQR WP-001).

This is the **producer↔consumer contract** test (CONTRACT_FIRST CF-01/CF-04,
lightweight internal tier). It is written **before** any producer or consumer
code and pins:

- the ADR-001 types, **field-for-field with the platform thread-sdk
  ``ONTOLOGY.jsonld``** (``Thread`` / ``ThreadParticipant`` / ``ThreadMemory``
  / ``ThreadMemoryContent`` / ``ThreadMessage`` / ``ExplorationJournalEntry``);
- the ``ContextPayload`` + tier enum (lean/standard/full) + the payload pointer
  (``thread_id`` + raw-fetch affordance, ADR-005);
- the ``ThreadStore`` port read/write operation surface (the discovery seam's
  read half + the session pump's write half, TDD §3.3);
- the three universal error categories **reused verbatim** from
  ``_session_manager.events`` (CF-03) plus the ``PermissionError`` carried for
  the future hosted binding (ADR-002, NFR-SEC05; not enforced on loopback);
- the pinned store-root path convention + on-disk record filename scheme
  (CF-11), so producer WPs reference it verbatim;
- the shared in-memory ``ThreadStore`` adapter stub — the same contract-test
  subject the real local adapter (WP-002) will also run against (CF-04 / §5).

The same test runs against the in-memory adapter today and the durable local
adapter at WP-002 (MEA-09: shared contract test, no mocks at integration).
"""

from __future__ import annotations

import dataclasses
import json
import typing
from pathlib import Path

import pytest

from _session_manager import thread_contract as tc
from _session_manager.events import (
    ExpectedError,
    InternalError,
    ProtocolError,
    SessionError,
)

_FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "thread_context"


# ── platform ONTOLOGY conformance ─────────────────────────────────────────
# The reference shape, transcribed from
# ~/dev/repos/platform/features/thread-sdk/ONTOLOGY.jsonld. The contract types
# MUST carry exactly these field names; a divergent field is a forked shape
# (ADR-001 forbids it).

_ONTOLOGY_FIELDS: dict[str, set[str]] = {
    "Thread": {
        "id",
        "platform_id",
        "topic",
        "activity_summary",
        "created_at",
        "updated_at",
        "participant_count",
    },
    "ThreadParticipant": {
        "id",
        "thread_id",
        "participant_id",
        "participant_type",
        "joined_at",
        "role",
    },
    "ThreadMemory": {"thread_id", "version", "content", "created_at", "updated_at"},
    "ThreadMemoryContent": {
        "messages",
        "exploration_journal",
        "participant_context",
    },
    "ThreadMessage": {
        "id",
        "participant_id",
        "participant_type",
        "content",
        "role",
        "created_at",
    },
    "ExplorationJournalEntry": {
        "type",
        "content",
        "created_at",
        "participant_id",
        "metadata",
    },
}


def _fields(cls: type) -> set[str]:
    return {f.name for f in dataclasses.fields(cls)}


@pytest.mark.parametrize("name", sorted(_ONTOLOGY_FIELDS))
def test_contract_types_conform_to_platform_ontology(name: str) -> None:
    """Each ADR-001 type carries the platform ONTOLOGY field set, with our two
    additive fields (Thread.resumed_from, ThreadMessage.order) the only
    permitted superset additions (TDD §3.3)."""
    cls = getattr(tc, name)
    actual = _fields(cls)
    required = _ONTOLOGY_FIELDS[name]
    missing = required - actual
    assert not missing, f"{name} missing platform fields: {missing}"
    # Only the two documented additive fields may extend the platform shape.
    additive_allowed = {
        "Thread": {"resumed_from"},
        "ThreadMessage": {"order"},
    }.get(name, set())
    extra = actual - required - additive_allowed
    assert not extra, f"{name} has un-sanctioned extra fields (fork?): {extra}"


def test_participant_type_enum_matches_platform() -> None:
    """participant_type is the platform's two values, used as-is (ADR-002)."""
    assert set(tc.PARTICIPANT_TYPES) == {"user", "studio_agent"}


def test_message_role_enum_matches_platform() -> None:
    """ThreadMessage.role ∈ platform set ∪ {None}."""
    assert set(tc.MESSAGE_ROLES) == {
        "question",
        "answer",
        "observation",
        "decision",
    }


def test_exploration_journal_entry_type_enum_matches_platform() -> None:
    assert set(tc.EXPLORATION_ENTRY_TYPES) == {
        "question",
        "answer",
        "pattern_detected",
        "decision_captured",
    }


# ── context payload shape (ADR-005) ───────────────────────────────────────


def test_context_payload_tier_enum() -> None:
    """The token-budget tiers are the three the assembler enforces (TDD §4)."""
    assert set(tc.PAYLOAD_TIERS) == {"lean", "standard", "full"}


def test_context_payload_shape() -> None:
    """ContextPayload carries the rich content inline + a pointer to the raw
    record (thread_id + the raw-fetch tool name affordance), per ADR-005."""
    fields = _fields(tc.ContextPayload)
    # Rich-by-default content + the discovery pointer.
    for required in ("thread_id", "tier", "memory", "raw_fetch_tool"):
        assert required in fields, f"ContextPayload missing {required!r}"


def test_payload_pointer_names_the_raw_fetch_tool() -> None:
    """The pointer's raw-fetch affordance names the thread_context MCP tool
    (ADR-005) — the constant lives in the contract so producer + consumer
    agree."""
    assert tc.RAW_FETCH_TOOL_NAME == "thread_context"


# ── ThreadStore port surface (TDD §3.3) ───────────────────────────────────


def test_threadstore_port_has_read_and_write_ops() -> None:
    """The port declares the write surface (session pump) + read surface
    (discovery seam). It is a runtime-checkable Protocol so adapters conform
    structurally."""
    for op in (
        "append_message",
        "put_memory",
        "get_thread",
        "get_memory",
        "get_messages",
    ):
        assert hasattr(tc.ThreadStore, op), f"ThreadStore port missing {op!r}"
    assert isinstance(tc.ThreadStore, type)
    assert issubclass(tc.ThreadStore, typing.Protocol)  # type: ignore[arg-type]


def test_get_messages_signature_carries_since_and_limit() -> None:
    """get_messages(thread_id, since?, limit?) — the slice read for discovery."""
    import inspect

    sig = inspect.signature(tc.InMemoryThreadStore.get_messages)
    params = sig.parameters
    assert "since" in params and params["since"].default is None
    assert "limit" in params and params["limit"].default is None


# ── the shared store-under-test fixture ────────────────────────────────────
# The adapter/invariant tests below construct their store from this fixture,
# not from a hard-coded ``tc.InMemoryThreadStore()``. The fixture is the single
# extension point: WP-002 adds its durable adapter as a second ``params`` entry
# (the in-memory stub takes no args; a path-backed adapter needs a tmp store
# root, so WP-002 supplies a factory here — only this fixture changes, never a
# test body). The SAME test bodies then run against both subjects under the same
# invariants (MEA-09 — the shared contract test, no mocks at integration).
# Today there is one subject: the in-memory stub.


# Each param is a builder ``tmp_path -> ThreadStore`` so the in-memory stub
# (no args) and the durable local adapter (needs a tmp store root) share one
# fixture without a per-test branch. WP-002 adds the durable adapter as the
# second builder; the SAME test bodies below run against both subjects.
def _build_in_memory(_tmp_path: Path):
    return tc.InMemoryThreadStore()


def _build_local(tmp_path: Path):
    # Import here (not at module top) so the contract module stays importable
    # even if a future refactor moves the adapter — and to keep the contract
    # test's only hard dependency the contract itself.
    from _session_manager.thread_store_local import LocalThreadStore

    # ``change_id`` is a valid store id; ``root`` isolates the durable store to
    # the test's tmp dir (the contract pins the production path to ~/.sulis).
    return LocalThreadStore(change_id="CH-GJ9KQR", root=tmp_path / "threads")


@pytest.fixture(
    params=[_build_in_memory, _build_local],
    ids=["in-memory", "local-durable"],
)
def store(request: pytest.FixtureRequest, tmp_path: Path):
    """The store-under-test. The single seam WP-002 extends to run these test
    bodies against its durable adapter as well (MEA-09: shared contract test,
    no mocks at integration)."""
    return request.param(tmp_path)


def test_store_subject_conforms_to_the_port(store) -> None:
    """The store-under-test structurally satisfies the runtime-checkable
    ``ThreadStore`` port — the load-bearing port↔adapter conformance the
    contract rests on (TDD §3.3). WP-002's durable adapter inherits this check
    via the fixture."""
    assert isinstance(store, tc.ThreadStore)


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


def _thread(tid: str, participant_count: int = 1) -> tc.Thread:
    return tc.Thread(
        id=tid,
        platform_id="local",
        topic=None,
        activity_summary=None,
        created_at="2026-06-24T00:00:00Z",
        updated_at="2026-06-24T00:00:00Z",
        participant_count=participant_count,
        resumed_from=None,
    )


def _memory(tid: str, version: int) -> tc.ThreadMemory:
    return tc.ThreadMemory(
        thread_id=tid,
        version=version,
        content=tc.ThreadMemoryContent(
            messages=[],
            exploration_journal=[],
            participant_context={"change_id": "CH-GJ9KQR"},
        ),
        created_at="2026-06-24T00:00:00Z",
        updated_at="2026-06-24T00:00:00Z",
    )


def test_adapter_happy_roundtrip(store) -> None:
    store.put_thread(_thread("t1"))
    store.append_message("t1", _msg("m0", 0))
    store.append_message("t1", _msg("m1", 1))

    assert store.get_thread("t1").id == "t1"
    msgs = store.get_messages("t1")
    assert [m.order for m in msgs] == [0, 1]

    store.put_memory("t1", _memory("t1", version=1))
    got = store.get_memory("t1")
    assert got.version == 1
    assert got.content.participant_context["change_id"] == "CH-GJ9KQR"


def test_adapter_empty_thread_messages(store) -> None:
    """An empty (but existing) thread yields no messages — the empty case
    (CF-04), not an error."""
    store.put_thread(_thread("empty", participant_count=0))
    assert store.get_messages("empty") == []


def test_get_messages_since_slices(store) -> None:
    store.append_message("t1", _msg("m0", 0))
    store.append_message("t1", _msg("m1", 1))
    store.append_message("t1", _msg("m2", 2))
    sliced = store.get_messages("t1", since=1)
    assert [m.order for m in sliced] == [1, 2]
    limited = store.get_messages("t1", limit=2)
    assert [m.order for m in limited] == [0, 1]


def test_get_messages_since_and_limit_compose(store) -> None:
    """``since`` filters first, then ``limit`` caps the window head — the
    semantics a SQL ``WHERE order >= since ... LIMIT n`` durable adapter must
    also honour. Pinned so WP-002 cannot order the two differently."""
    for i in range(5):
        store.append_message("t1", _msg(f"m{i}", i))
    windowed = store.get_messages("t1", since=2, limit=2)
    assert [m.order for m in windowed] == [2, 3]


def test_message_role_none_is_accepted(store) -> None:
    """``ThreadMessage.role`` is ``MessageRole | None``; the ``None`` arm (a
    message with no classified role) round-trips."""
    msg = tc.ThreadMessage(
        id="m0",
        participant_id="studio_agent_1",
        participant_type="studio_agent",
        content="raw chunk, no role",
        role=None,
        created_at="2026-06-24T00:00:00Z",
        order=0,
    )
    store.append_message("t1", msg)
    assert store.get_messages("t1")[0].role is None


# ── error categories (CF-03) ───────────────────────────────────────────────


def test_errors_reuse_the_three_event_categories() -> None:
    """The contract reuses events.py's three categories verbatim — no second
    error hierarchy (CF-03 / TDD §3.3). thread_contract re-exports them."""
    assert tc.ProtocolError is ProtocolError
    assert tc.ExpectedError is ExpectedError
    assert tc.InternalError is InternalError
    assert issubclass(tc.ProtocolError, SessionError)


def test_permission_error_is_carried_for_hosted_binding() -> None:
    """PermissionError (NFR-SEC05) exists in the contract for the future hosted
    binding; it is an ExpectedError-category deterministic refusal (ADR-002).
    Not enforced on the loopback path."""
    assert issubclass(tc.PermissionError, SessionError)
    err = tc.PermissionError(tc.NOT_A_PARTICIPANT, "not a participant")
    assert err.category == "expected"
    assert err.code == tc.NOT_A_PARTICIPANT


def test_get_memory_missing_raises_memory_not_found(store) -> None:
    """A thread may exist with no memory checkpoint yet; the miss is
    MEMORY_NOT_FOUND, distinct from THREAD_NOT_FOUND (the contract advertises
    both — CF-03)."""
    store.put_thread(_thread("t1"))  # thread exists; memory does not
    with pytest.raises(ExpectedError) as exc:
        store.get_memory("t1")
    assert exc.value.code == tc.MEMORY_NOT_FOUND


def test_get_thread_missing_raises_thread_not_found(store) -> None:
    with pytest.raises(ExpectedError) as exc:
        store.get_thread("nope")
    assert exc.value.code == tc.THREAD_NOT_FOUND


# ── append-only invariant (TDD §4) ─────────────────────────────────────────


def test_append_only_rejects_out_of_order_write(store) -> None:
    """The log is offset-ordered and monotonic; an out-of-order append is a
    deterministic refusal (ExpectedError), not a silent overwrite."""
    store.append_message("t1", _msg("m0", 0))
    store.append_message("t1", _msg("m1", 1))
    with pytest.raises(ExpectedError) as exc:
        store.append_message("t1", _msg("stale", 1))  # order not > last
    assert exc.value.code == tc.OUT_OF_ORDER_WRITE


def test_append_only_rejects_id_rewrite(store) -> None:
    """Re-appending an already-stored message id is a rewrite — rejected
    (append-only invariant)."""
    store.append_message("t1", _msg("m0", 0))
    with pytest.raises(ExpectedError) as exc:
        store.append_message("t1", _msg("m0", 1))  # duplicate id
    assert exc.value.code == tc.DUPLICATE_MESSAGE


def test_put_memory_rejects_stale_version(store) -> None:
    """ThreadMemory.version is monotonic (ADR-001 — incremented per checkpoint);
    a put with a stale or equal version is a deterministic refusal, the
    memory-record analogue of the message log's monotonic-order guard. The
    rejected put must leave the stored version unchanged (the guard validates
    before mutating) — pinned so a durable WP-002 adapter cannot pass by
    comparing against last-written rather than stored, or by mutating early."""
    store.put_memory("t1", _memory("t1", version=5))
    # Equal version rejected.
    with pytest.raises(ExpectedError) as exc:
        store.put_memory("t1", _memory("t1", version=5))
    assert exc.value.code == tc.STALE_MEMORY_VERSION
    # Strictly-lower version rejected.
    with pytest.raises(ExpectedError) as exc:
        store.put_memory("t1", _memory("t1", version=3))
    assert exc.value.code == tc.STALE_MEMORY_VERSION
    # The stored version is unchanged after the rejected puts.
    assert store.get_memory("t1").version == 5
    # A forward version is accepted.
    store.put_memory("t1", _memory("t1", version=6))
    assert store.get_memory("t1").version == 6


# ── pinned store-root path convention (CF-11) ──────────────────────────────


def test_store_root_path_convention() -> None:
    """The store root + record filename scheme are pinned here so producer WPs
    reference them verbatim (CF-11)."""
    root = tc.store_root_for_change("CH-GJ9KQR")
    assert root.parts[-2:] == ("CH-GJ9KQR", "threads")
    assert str(root).endswith("/.sulis/changes/CH-GJ9KQR/threads")
    # Record filename scheme: per-thread record file.
    assert tc.thread_record_filename("t1") == "t1.thread.json"
    assert tc.memory_record_filename("t1") == "t1.memory.json"
    assert tc.messages_record_filename("t1") == "t1.messages.jsonl"


@pytest.mark.parametrize(
    "bad_id",
    ["../../etc", "a/b", "..", ".", "with space", "semi;colon", ""],
)
def test_store_id_validation_rejects_traversal(bad_id: str) -> None:
    """The path/filename convention validates its id so a traversing or
    separator-bearing id can never escape the threads dir (CF-11). The guard
    lives in the convention, so every producer WP inherits it."""
    with pytest.raises(ExpectedError) as exc:
        tc.store_root_for_change(bad_id)
    assert exc.value.code == tc.INVALID_ID
    # The filename helpers carry the same guard.
    with pytest.raises(ExpectedError):
        tc.thread_record_filename(bad_id)


def test_store_id_validation_accepts_real_ids() -> None:
    """Real change/thread ids (alphanumerics, '-', '_') pass."""
    assert tc.validate_store_id("CH-GJ9KQR") == "CH-GJ9KQR"
    assert tc.validate_store_id("thr_01KVX26BDX") == "thr_01KVX26BDX"


@pytest.mark.parametrize("bad_id", ["abc\n", "abc\nrm -rf", "\nabc", "abc\r"])
def test_store_id_validation_rejects_trailing_newline(bad_id: str) -> None:
    """WP-001 security advisory fold-in (WP-002): the id guard must use a
    full-string anchor (``re.fullmatch`` / ``\\Z``), not ``$`` — which in
    Python matches just before a trailing ``\\n``, so ``"abc\\n"`` slipped
    through. This durable on-disk adapter builds paths/filenames on the guard,
    so an id with an embedded/trailing newline is a deterministic refusal
    (INVALID_ID), the same as a traversal-shaped id."""
    with pytest.raises(ExpectedError) as exc:
        tc.validate_store_id(bad_id)
    assert exc.value.code == tc.INVALID_ID
    # The path/filename helpers inherit the tightened guard.
    with pytest.raises(ExpectedError):
        tc.store_root_for_change(bad_id)


# ── context payload pointer wiring (ADR-005) ───────────────────────────────


def test_context_payload_default_pointer_wires_to_tool_name() -> None:
    """A ContextPayload built without an explicit raw_fetch_tool defaults to the
    pinned RAW_FETCH_TOOL_NAME — the rich-by-default pointer (ADR-005)."""
    payload = tc.ContextPayload(
        thread_id="t1",
        tier="standard",
        memory=tc.ThreadMemoryContent(),
    )
    assert payload.raw_fetch_tool == tc.RAW_FETCH_TOOL_NAME == "thread_context"


# ── fixtures (CF-04) ───────────────────────────────────────────────────────


def test_sample_thread_fixture_parses_into_contract() -> None:
    raw = json.loads((_FIXTURES / "sample_thread.json").read_text())
    thread = tc.Thread(**raw)
    assert thread.platform_id == "local"
    assert thread.id


def test_sample_memory_fixture_parses_into_contract() -> None:
    raw = json.loads((_FIXTURES / "sample_memory.json").read_text())
    memory = tc.thread_memory_from_dict(raw)
    assert memory.thread_id
    assert isinstance(memory.content, tc.ThreadMemoryContent)
    assert all(isinstance(m, tc.ThreadMessage) for m in memory.content.messages)
    assert all(
        isinstance(e, tc.ExplorationJournalEntry)
        for e in memory.content.exploration_journal
    )
