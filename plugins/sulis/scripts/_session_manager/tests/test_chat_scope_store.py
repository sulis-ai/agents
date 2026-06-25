"""Per-product chat-scope thread keying (CH-G3Y4RM WP-002, ADR-002).

The PRIMARY verification artifact for WP-002 (frontmatter + INDEX):
``test_two_scopes_two_threads``. The spec requires one durable conversation
**per product**, persisted, never blended; switching products swaps the thread.
ADR-002 keys the durable thread by a stable ``chat_scope`` and roots one
``LocalThreadStore`` per scope at a chat-scoped store root parallel to the
existing change-scoped root — ``~/.sulis/chat/{scope-key}/threads/`` — reusing
the shipped record shapes + append-only invariants VERBATIM. Only the root
resolver and the key are new.

These run against the REAL filesystem (a pytest ``tmp_path``), no mocks — the
``LocalThreadStore`` IO is exercised end to end, exactly as the existing
durable-adapter integration suite does.

What this pins (WP-002 Definition of Done > Red):
1. ``test_two_scopes_two_threads`` — two scopes write to two thread directories;
   ``get_messages`` returns each scope's OWN history; histories never blend. A
   characterisation test on the new root resolver; fails before it exists.
2. The chosen agent (provider) is remembered PER scope by stamping
   ``participant_context.provider`` on the scope's ``ThreadMemory`` — no contract
   fork (ADR-002 "the documented additive slot").
3. The chat-store root is chat-scoped (``.../chat/...``), physically separate
   from the change-scoped root, so blending is impossible by construction.
4. A hostile scope (path traversal) is refused before any path is keyed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from _session_manager import thread_contract as tc
from _session_manager.chat_scope_store import (
    append_turn,
    chat_store_root_for_scope,
    read_remembered_provider,
    remember_provider,
    resolve_chat_thread,
)
from _session_manager.thread_contract import ExpectedError

# A real product scope is colon-bearing (`product:dna:product:<ulid>`); the two
# synthetic scopes use the bare sentinels behind the `product:` prefix (ADR-002).
_SCOPE_A = "product:dna:product:01HZX9"
_SCOPE_B = "product:dna:product:01HZY0"
_SCOPE_ALL = "product:__all__"

# A stable thread id within a scope. The store is keyed by scope on disk; the
# thread id is the per-scope conversation handle (the chat has one thread).
_THREAD = "chat"


def _thread(tid: str) -> tc.Thread:
    return tc.Thread(
        id=tid,
        platform_id="local",
        topic=None,
        activity_summary=None,
        created_at="2026-06-25T00:00:00Z",
        updated_at="2026-06-25T00:00:00Z",
        participant_count=1,
        resumed_from=None,
    )


def _msg(mid: str, order: int, content: str) -> tc.ThreadMessage:
    return tc.ThreadMessage(
        id=mid,
        participant_id="studio_agent_1",
        participant_type="studio_agent",
        content=content,
        role="observation",
        created_at="2026-06-25T00:00:00Z",
        order=order,
    )


def test_two_scopes_two_threads(tmp_path: Path) -> None:
    """Two scopes -> two thread directories; each scope's history is its OWN and
    never blends (the PRIMARY WP-002 artifact, ADR-002)."""
    store_a = resolve_chat_thread(_SCOPE_A, chat_root=tmp_path)
    store_b = resolve_chat_thread(_SCOPE_B, chat_root=tmp_path)

    store_a.put_thread(_thread(_THREAD))
    store_b.put_thread(_thread(_THREAD))

    store_a.append_message(_THREAD, _msg("a1", 1, "hello from A"))
    store_b.append_message(_THREAD, _msg("b1", 1, "hello from B"))

    # Each scope returns ONLY its own history — no blend.
    msgs_a = store_a.get_messages(_THREAD)
    msgs_b = store_b.get_messages(_THREAD)
    assert [m.content for m in msgs_a] == ["hello from A"]
    assert [m.content for m in msgs_b] == ["hello from B"]

    # Physically separate directories under the chat-scoped root (blending is
    # impossible by construction, ADR-002).
    assert store_a.root != store_b.root
    assert store_a.root.exists()
    assert store_b.root.exists()
    # A fresh resolver over the same root + scope rehydrates the SAME history.
    again_a = resolve_chat_thread(_SCOPE_A, chat_root=tmp_path)
    assert [m.content for m in again_a.get_messages(_THREAD)] == ["hello from A"]


def test_chat_root_is_scoped_under_chat_not_changes(tmp_path: Path) -> None:
    """The chat-store root is chat-scoped (``.../chat/{scope-key}/threads/``),
    parallel to the change-scoped root — never under ``.../changes/`` (ADR-002)."""
    store = resolve_chat_thread(_SCOPE_A, chat_root=tmp_path)
    assert store.root.parent.parent == tmp_path
    assert store.root.name == "threads"
    # The scope key is a `validate_store_id`-safe component (no raw colon on disk).
    scope_key = store.root.parent.name
    assert ":" not in scope_key
    assert "/" not in scope_key


def test_distinct_scopes_derive_distinct_keys(tmp_path: Path) -> None:
    """Two distinct scopes never collide to the same on-disk key (ADR-002 — the
    histories must be physically separate)."""
    root_a = chat_store_root_for_scope(_SCOPE_A, chat_root=tmp_path)
    root_b = chat_store_root_for_scope(_SCOPE_B, chat_root=tmp_path)
    root_all = chat_store_root_for_scope(_SCOPE_ALL, chat_root=tmp_path)
    assert len({root_a, root_b, root_all}) == 3


def test_provider_remembered_per_scope(tmp_path: Path) -> None:
    """The chosen agent (provider) is remembered PER scope via
    ``participant_context.provider`` — no schema fork (ADR-002)."""
    remember_provider(_SCOPE_A, "agy", _THREAD, chat_root=tmp_path)
    remember_provider(_SCOPE_B, "pty", _THREAD, chat_root=tmp_path)

    assert read_remembered_provider(_SCOPE_A, _THREAD, chat_root=tmp_path) == "agy"
    assert read_remembered_provider(_SCOPE_B, _THREAD, chat_root=tmp_path) == "pty"
    # An unremembered scope returns None (the resolver applies the pty backstop).
    assert read_remembered_provider(_SCOPE_ALL, _THREAD, chat_root=tmp_path) is None


def test_hostile_scope_is_refused(tmp_path: Path) -> None:
    """A path-traversal scope is refused before any path is keyed (the on-disk
    guard backstop behind the wire-level ``parseChatScope``)."""
    for hostile in (
        "product:../../etc/passwd",
        "product:..",
        "product:a/b",
        "change:abc",  # wrong prefix
        "product:",  # empty id
    ):
        with pytest.raises(ExpectedError):
            chat_store_root_for_scope(hostile, chat_root=tmp_path)


# ── WP-004 seam-close: the persistence round-trip (folded CONCERN DAT-PERSIST-01)
# Today nothing appends chat turns to the per-product scope thread at runtime, so
# ``get_messages`` is always empty and per-product history is not real. WP-004
# closes the round-trip: ``append_turn`` persists each chat turn through the
# REDACTING store path (``LocalThreadStore.append_message`` -> ``_scrub_message``)
# so (a) history actually persists per scope and (b) redaction-on-write applies
# to chat content. Scenario 1 (switch product -> see that product's history)
# depends on this being real.


def test_append_turn_persists_and_round_trips(tmp_path: Path) -> None:
    """A user turn then an agent turn are persisted to the scope's durable thread
    and read back, in order, by the SAME scope — closing the round-trip
    ``getThread`` reads (DAT-PERSIST-01)."""
    append_turn(_SCOPE_A, "user", "what changed today?", chat_root=tmp_path)
    append_turn(_SCOPE_A, "assistant", "three changes shipped", chat_root=tmp_path)

    store = resolve_chat_thread(_SCOPE_A, chat_root=tmp_path)
    msgs = store.get_messages(_THREAD)
    # The wire roles ("user"/"assistant") map onto the shipped participant union
    # ("user"/"studio_agent"); the round-trip preserves order + content.
    assert [(m.participant_type, m.content) for m in msgs] == [
        ("user", "what changed today?"),
        ("studio_agent", "three changes shipped"),
    ]
    # Offsets are monotonic (the log is offset-ordered) so a later read is stable.
    assert [m.order for m in msgs] == sorted(m.order for m in msgs)
    assert len({m.order for m in msgs}) == len(msgs)
    assert len({m.id for m in msgs}) == len(msgs)


def test_append_turn_history_is_per_scope(tmp_path: Path) -> None:
    """Appended turns never blend across scopes — switching products returns that
    product's OWN conversation (Scenario 1)."""
    append_turn(_SCOPE_A, "user", "hello from A", chat_root=tmp_path)
    append_turn(_SCOPE_B, "user", "hello from B", chat_root=tmp_path)

    store_a = resolve_chat_thread(_SCOPE_A, chat_root=tmp_path)
    store_b = resolve_chat_thread(_SCOPE_B, chat_root=tmp_path)
    assert [m.content for m in store_a.get_messages(_THREAD)] == ["hello from A"]
    assert [m.content for m in store_b.get_messages(_THREAD)] == ["hello from B"]


def test_append_turn_redacts_secrets_on_write(tmp_path: Path) -> None:
    """Chat content passes through redaction-on-write — a secret in a turn is
    scrubbed before the bytes land on disk (DAT-PERSIST-01: the REDACTING path)."""
    secret = "sk-ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789abcdefghij"  # noqa: S105 (test fixture)
    append_turn(_SCOPE_A, "user", f"my key is {secret} keep it safe", chat_root=tmp_path)

    # The secret is gone from the read-back content...
    store = resolve_chat_thread(_SCOPE_A, chat_root=tmp_path)
    content = store.get_messages(_THREAD)[0].content
    assert secret not in content
    assert "[redacted-secret]" in content
    # ...and gone from the persisted bytes (the on-disk log), not just the read.
    # The log is `{thread_id}.messages.jsonl` under the scope's threads root.
    log_path = (
        chat_store_root_for_scope(_SCOPE_A, chat_root=tmp_path)
        / f"{_THREAD}.messages.jsonl"
    )
    assert secret not in log_path.read_text(encoding="utf-8")


def test_append_turn_rejects_hostile_scope(tmp_path: Path) -> None:
    """A hostile scope is refused before any path is keyed (the on-disk backstop
    behind the wire-level ``parseChatScope``)."""
    with pytest.raises(ExpectedError):
        append_turn("product:../../etc/passwd", "user", "x", chat_root=tmp_path)
