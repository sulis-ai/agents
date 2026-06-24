"""Contract test for the ``thread_context`` MCP server (``_thread_context_mcp``)
— CH-GJ9KQR WP-005, ADR-005, TDD §3.1 / §5.

The raw-on-demand half of the discovery seam: ONE parameterised, **denyable**,
**change-scoped**, **READ-ONLY** MCP tool that exposes the read side of the
WP-001 ``ThreadStore`` contract to a spawned agent. It mirrors
``test_safe_tools_mcp_contract.py`` — the established safe-tools pattern
(``_safe_tools_mcp.py``): one parameterised ``op`` tool over a wrapped library,
scope resolved server-side (never from the agent's call args), typed results
serialised to a plain dict, an unknown ``op`` fail-closed.

These are in-process contract assertions over the real ``FastMCP`` instance the
launcher would run over stdio:

  * exactly ONE tool, ``thread_context(op, thread_id, since?, limit?)``;
  * ``op`` is the closed READ enum ``{get_thread, get_memory, get_messages}`` —
    the read half of the WP-001 contract, and **only** the read half (no write
    op exists: the agent never writes the log — the session pump does, ADR-004);
  * each read op routes to the matching wrapped ``ThreadStore`` method;
  * an unknown / write-shaped ``op`` is refused **fail-closed** (no store call);
  * the tool is **change-scoped server-side** — it binds to the bound change's
    store (``SULIS_CHANGE_ID``), so a ``thread_id`` that is not in that change's
    store is refused (``ExpectedError`` ``THREAD_NOT_FOUND``); the agent cannot
    widen its scope by passing a different change's id;
  * the three universal error categories (``ProtocolError`` / ``ExpectedError``
    / ``InternalError``) serialise correctly (category + code + message).

The server reimplements **no** store logic — it marshals args, calls the wrapped
read ops, and serialises the typed result / typed error (D6 wrap-don't-restate).
It codes against the ``ThreadStore`` **Protocol** (WP-001, merged), not WP-002's
concrete durable adapter; the reference subject here is the contract's
``InMemoryThreadStore`` stub.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[2]
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import _thread_context_mcp as mcp_server  # noqa: E402
from _session_manager.thread_contract import (  # noqa: E402
    THREAD_NOT_FOUND,
    ExpectedError,
    InMemoryThreadStore,
    InternalError,
    ProtocolError,
    Thread,
    ThreadMemory,
    ThreadMemoryContent,
    ThreadMessage,
)

# ─── test fixtures (the contract's reference stub, populated for one change) ──

_CHANGE_ID = "CH-GJ9KQR"
_THREAD_ID = "T-001"


def _populated_store() -> InMemoryThreadStore:
    """An ``InMemoryThreadStore`` (the WP-001 reference stub) holding one thread
    with a memory checkpoint and two ordered messages — the bound change's
    store."""
    store = InMemoryThreadStore()
    store.put_thread(
        Thread(
            id=_THREAD_ID,
            platform_id="local",
            topic="resume drill",
            activity_summary=None,
            created_at="2026-06-24T00:00:00+00:00",
            updated_at="2026-06-24T00:00:00+00:00",
            participant_count=1,
        )
    )
    store.put_memory(
        _THREAD_ID,
        ThreadMemory(
            thread_id=_THREAD_ID,
            version=1,
            content=ThreadMemoryContent(
                messages=[],
                exploration_journal=[],
                participant_context={"change_id": _CHANGE_ID},
            ),
            created_at="2026-06-24T00:00:00+00:00",
            updated_at="2026-06-24T00:00:00+00:00",
        ),
    )
    store.append_message(
        _THREAD_ID,
        ThreadMessage(
            id="M-1",
            participant_id="agent",
            participant_type="studio_agent",
            content="first",
            role="observation",
            created_at="2026-06-24T00:00:00+00:00",
            order=1,
        ),
    )
    store.append_message(
        _THREAD_ID,
        ThreadMessage(
            id="M-2",
            participant_id="agent",
            participant_type="studio_agent",
            content="second",
            role="decision",
            created_at="2026-06-24T00:00:01+00:00",
            order=2,
        ),
    )
    return store


class _SpyStore:
    """Records which read method each ``thread_context`` op routes to, and proves
    no write op is ever reachable (read-only). Raising on a write method makes a
    mistaken write-route a loud failure, not a silent one."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []
        self._backing = _populated_store()

    def get_thread(self, thread_id: str) -> Thread:
        self.calls.append(("get_thread", {"thread_id": thread_id}))
        return self._backing.get_thread(thread_id)

    def get_memory(self, thread_id: str) -> ThreadMemory:
        self.calls.append(("get_memory", {"thread_id": thread_id}))
        return self._backing.get_memory(thread_id)

    def get_messages(
        self, thread_id: str, since: int | None = None, limit: int | None = None
    ) -> list[ThreadMessage]:
        self.calls.append(
            ("get_messages", {"thread_id": thread_id, "since": since, "limit": limit})
        )
        return self._backing.get_messages(thread_id, since=since, limit=limit)

    # write surface — must NEVER be reachable from the read-only tool.
    def append_message(self, thread_id: str, message: ThreadMessage) -> None:
        raise AssertionError("read-only tool routed a write: append_message")

    def put_memory(self, thread_id: str, memory: ThreadMemory) -> None:
        raise AssertionError("read-only tool routed a write: put_memory")


def _enumerate(server) -> dict:
    tools = asyncio.run(server.list_tools())
    return {t.name: t for t in tools}


# ─── test_one_tool_enumerates_read_ops ────────────────────────────────────────


def test_one_tool_enumerates_read_ops() -> None:
    """The server registers EXACTLY one tool, ``thread_context``, with the
    parameterised read schema (ADR-005: one parameterised tool, not three
    identities — mirrors ``scoped_file``)."""
    server = mcp_server.build_server(store=_populated_store(), change_id=_CHANGE_ID)
    tools = _enumerate(server)

    assert set(tools) == {"thread_context"}

    props = tools["thread_context"].inputSchema["properties"]
    assert set(props) >= {"op", "thread_id", "since", "limit"}
    required = tools["thread_context"].inputSchema["required"]
    assert "op" in required
    assert "thread_id" in required


# ─── test_read_ops_dispatch_each_op ───────────────────────────────────────────


def test_read_ops_dispatch_each_op() -> None:
    """Each read ``op`` routes to the matching wrapped ``ThreadStore`` method;
    ``since`` / ``limit`` reach ``get_messages``."""
    spy = _SpyStore()
    server = mcp_server.build_server(store=spy, change_id=_CHANGE_ID)

    asyncio.run(
        server.call_tool(
            "thread_context", {"op": "get_thread", "thread_id": _THREAD_ID}
        )
    )
    asyncio.run(
        server.call_tool(
            "thread_context", {"op": "get_memory", "thread_id": _THREAD_ID}
        )
    )
    asyncio.run(
        server.call_tool(
            "thread_context",
            {"op": "get_messages", "thread_id": _THREAD_ID, "since": 2, "limit": 5},
        )
    )

    routed = [name for name, _ in spy.calls]
    assert routed == ["get_thread", "get_memory", "get_messages"]
    # since/limit reached the wrapped read op.
    last = spy.calls[-1][1]
    assert last["since"] == 2
    assert last["limit"] == 5


def test_get_messages_returns_ordered_log() -> None:
    """``get_messages`` returns the offset-ordered messages serialised to plain
    dicts (the raw record the agent fetches on demand)."""
    server = mcp_server.build_server(store=_populated_store(), change_id=_CHANGE_ID)

    result = mcp_server.thread_context(
        op="get_messages",
        thread_id=_THREAD_ID,
        store=_populated_store(),
        change_id=_CHANGE_ID,
    )
    assert result["ok"] is True
    messages = result["payload"]
    assert [m["order"] for m in messages] == [1, 2]
    assert messages[0]["content"] == "first"
    # also drive the registered closure
    asyncio.run(
        server.call_tool(
            "thread_context", {"op": "get_messages", "thread_id": _THREAD_ID}
        )
    )


# ─── test_no_write_op_exists / test_unknown_op_refused_fail_closed ────────────


def test_no_write_op_exists_read_only() -> None:
    """The tool is READ-ONLY: write-shaped ops (``append_message`` / ``put_memory``
    / ``write``) are outside the closed read enum and refused fail-closed — the
    store's write methods are never reached (ADR-005: the agent never writes)."""
    spy = _SpyStore()
    for write_op in ("append_message", "put_memory", "write"):
        result = mcp_server.thread_context(
            op=write_op,
            thread_id=_THREAD_ID,
            store=spy,
            change_id=_CHANGE_ID,
        )
        assert result["ok"] is False
        assert write_op in result["reason"] or "unknown" in result["reason"].lower()
    # No read NOR write method was routed — fail-closed before any store call.
    assert spy.calls == []


def test_unknown_op_refused_fail_closed() -> None:
    """An ``op`` outside the closed read enum is refused fail-closed — no wrapped
    method is called (mirrors ``scoped_file``'s ``_FILE_OPS`` guard)."""
    spy = _SpyStore()
    result = mcp_server.thread_context(
        op="exfiltrate",
        thread_id=_THREAD_ID,
        store=spy,
        change_id=_CHANGE_ID,
    )
    assert result["ok"] is False
    assert "exfiltrate" in result["reason"] or "unknown" in result["reason"].lower()
    assert spy.calls == []


# ─── test_cross_change_thread_refused (change-scoped server-side) ─────────────


def test_cross_change_thread_refused() -> None:
    """A ``thread_id`` that is not in the bound change's store is refused with an
    Expected-category ``THREAD_NOT_FOUND`` — the tool is change-scoped
    server-side (each change's threads live under its own store; the agent cannot
    read another change's thread)."""
    server = mcp_server.build_server(store=_populated_store(), change_id=_CHANGE_ID)

    out = asyncio.run(
        server.call_tool(
            "thread_context",
            {"op": "get_thread", "thread_id": "T-OTHER-CHANGE"},
        )
    )
    payload = _call_tool_payload(out)
    assert payload["ok"] is False
    assert payload["error"]["category"] == "expected"
    assert payload["error"]["code"] == THREAD_NOT_FOUND


# ─── test_three_error_categories_serialise ────────────────────────────────────


def _call_tool_payload(out) -> dict:
    """Extract the structured dict a FastMCP ``call_tool`` returns.

    FastMCP returns ``(content_blocks, structured_result)``; the structured
    result is the dict our tool returned."""
    if isinstance(out, tuple):
        out = out[1]
    return out


class _RaisingStore:
    """A store whose read op raises a chosen contract error — to prove each of
    the three universal categories serialises (category + code + message)."""

    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    def get_thread(self, thread_id: str) -> Thread:
        raise self._exc

    def get_memory(self, thread_id: str) -> ThreadMemory:
        raise self._exc

    def get_messages(self, thread_id, since=None, limit=None):
        raise self._exc


def test_three_error_categories_serialise() -> None:
    """The three universal error categories (CF-03) serialise: each carries a
    machine ``category`` discriminator + the code + the message."""
    cases = [
        (ProtocolError("BAD_SHAPE", "malformed request"), "protocol", "BAD_SHAPE"),
        (
            ExpectedError(THREAD_NOT_FOUND, "no such thread"),
            "expected",
            THREAD_NOT_FOUND,
        ),
        (InternalError("BUG", "unexpected"), "internal", "BUG"),
    ]
    for exc, expected_category, expected_code in cases:
        result = mcp_server.thread_context(
            op="get_thread",
            thread_id=_THREAD_ID,
            store=_RaisingStore(exc),
            change_id=_CHANGE_ID,
        )
        assert result["ok"] is False
        assert result["error"]["category"] == expected_category
        assert result["error"]["code"] == expected_code
        assert result["error"]["message"]


# ─── test_store_resolved_from_launch_env_not_agent_args ───────────────────────


def test_change_id_resolved_from_launch_env(monkeypatch) -> None:
    """The bound ``change_id`` comes from the launch environment
    (``SULIS_CHANGE_ID``) — never an agent call arg (mirrors safe-tools
    ADR-001/ADR-004 scoping; the agent cannot widen its own scope)."""
    monkeypatch.setenv("SULIS_CHANGE_ID", "CH-FROM-ENV")
    assert mcp_server._resolve_change_id() == "CH-FROM-ENV"


def test_default_store_binds_to_change_store(monkeypatch) -> None:
    """With no injected store, the server resolves the bound change's
    ``ThreadStore`` from the launch environment — never an agent arg. The default
    binding conforms to the ``ThreadStore`` read surface."""
    monkeypatch.setenv("SULIS_CHANGE_ID", _CHANGE_ID)
    store = mcp_server._default_store(_CHANGE_ID)
    # Conforms to the contract read surface (the seam the tool depends on).
    assert hasattr(store, "get_thread")
    assert hasattr(store, "get_memory")
    assert hasattr(store, "get_messages")


# ─── test_denyable_identity_and_honesty_docstring ─────────────────────────────


def test_single_denyable_identity_named_thread_context() -> None:
    """The tool registers under the contract-pinned name ``thread_context`` (the
    ``RAW_FETCH_TOOL_NAME`` the payload pointer advertises) as ONE denyable
    identity (the founder can withhold it)."""
    from _session_manager.thread_contract import RAW_FETCH_TOOL_NAME

    server = mcp_server.build_server(store=_populated_store(), change_id=_CHANGE_ID)
    assert set(_enumerate(server)) == {RAW_FETCH_TOOL_NAME}
    assert mcp_server.SERVER_NAME  # the server has a stable identity


def test_module_docstring_states_read_only_and_honesty_boundary() -> None:
    """ADR-005 / safe-tools D6 honesty: the module docstring states the tool is
    READ-ONLY and that registering the MCP identity is availability +
    denyability, NOT enforcement."""
    doc = (mcp_server.__doc__ or "").lower()
    assert "read-only" in doc or "read only" in doc
    assert "availability" in doc or "available" in doc
    assert "not enforcement" in doc or "not enforce" in doc


# ─── end-to-end production-default wiring ─────────────────────────────────────


def test_build_server_with_production_defaults_enumerates_one_tool(monkeypatch) -> None:
    """``build_server()`` with NO injection (full production wiring) still
    registers exactly the one ``thread_context`` tool."""
    monkeypatch.setenv("SULIS_CHANGE_ID", _CHANGE_ID)
    server = mcp_server.build_server()
    assert set(_enumerate(server)) == {"thread_context"}
