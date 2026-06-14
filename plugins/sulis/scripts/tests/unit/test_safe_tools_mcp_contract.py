"""Contract test for the safe-tools MCP server (``_safe_tools_mcp``) — WP-001.

TDD §Form + ADR-001 (one ``scoped_file``) + ADR-002 (Python stdio MCP, wrap don't
reimplement). The server exposes the shipped L1 (`_safe_fetch.tool`) and L2
(`_file_tools`) functions as **three** denyable MCP identities so an allowlist
can express "allow-safe / deny-raw":

  * ``safe_fetch(url, format)`` / ``safe_search(query)`` — delegate to the
    wrapped L1 tool through an injected ``FetchGateway`` (no network here).
  * ONE ``scoped_file(op, path, content?, dst?)`` — ``op ∈ {read,write,move,
    remove}`` (closed enum; unknown op → fail-closed refusal) — dispatches via
    an explicit ``match`` to the matching ``_file_tools`` function.

These are in-process contract assertions over the real ``FastMCP`` instance the
launcher would run over stdio: enumerate the tools + schemas, and prove each tool
delegates to the wrapped function (spies / a tmp tree / a fake gateway). The
server reimplements **no** fetch/scope logic — it marshals args and serialises
the typed results (D6).
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[2]
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import _safe_tools_mcp as mcp_server  # noqa: E402
from _file_tools import FileToolResult  # noqa: E402
from _safe_fetch.ports import FetchRequest, FetchResult  # noqa: E402


# ─── test doubles (no network, no real fs needed for delegation asserts) ──────


class _RecordingGateway:
    """In-memory ``FetchGateway`` — records the request, returns framed data."""

    def __init__(self) -> None:
        self.requests: list[FetchRequest] = []

    def fetch(self, req: FetchRequest) -> FetchResult:
        self.requests.append(req)
        return FetchResult(
            source_url=req.url,
            fetched_at="2026-06-13T00:00:00+00:00",
            content_is_untrusted_data=True,
            content=f"<<<UNTRUSTED>>>body for {req.url}<<<END>>>",
            format=req.format,
        )


class _SpyFileOps:
    """Records which ``_file_tools`` function each ``scoped_file`` op routes to,
    plus the kwargs it was handed, and returns a canned ``FileToolResult``."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def _spy(self, name: str, payload: str | None = None):
        def _fn(*args, **kwargs):
            self.calls.append((name, {"args": args, "kwargs": kwargs}))
            return FileToolResult(ok=True, reason=f"{name} ok", payload=payload)

        return _fn

    def as_mapping(self) -> dict:
        return {
            "read": self._spy("read_file", payload="file contents"),
            "write": self._spy("write_file"),
            "move": self._spy("move_file"),
            "remove": self._spy("remove_file"),
        }


def _enumerate(server) -> dict:
    tools = asyncio.run(server.list_tools())
    return {t.name: t for t in tools}


# ─── test_three_tools_enumerate ───────────────────────────────────────────────


def test_three_tools_enumerate() -> None:
    """The server registers EXACTLY the three named tools with the right param
    schemas (ADR-001: one ``scoped_file``, not four)."""
    server = mcp_server.build_server(gateway=_RecordingGateway())
    tools = _enumerate(server)

    assert set(tools) == {"safe_fetch", "safe_search", "scoped_file"}

    fetch_props = tools["safe_fetch"].inputSchema["properties"]
    assert "url" in fetch_props and "format" in fetch_props
    assert "url" in tools["safe_fetch"].inputSchema["required"]

    search_props = tools["safe_search"].inputSchema["properties"]
    assert "query" in search_props

    sf_props = tools["scoped_file"].inputSchema["properties"]
    assert set(sf_props) >= {"op", "path", "content", "dst"}
    assert "op" in tools["scoped_file"].inputSchema["required"]
    assert "path" in tools["scoped_file"].inputSchema["required"]


# ─── test_scoped_file_dispatches_each_op ──────────────────────────────────────


def test_scoped_file_dispatches_each_op() -> None:
    """Each ``op`` routes to the matching ``_file_tools`` function; the scope
    (change_id/repo_root) is server-resolved, not taken from the call args."""
    spy = _SpyFileOps()
    server = mcp_server.build_server(
        gateway=_RecordingGateway(),
        file_ops=spy.as_mapping(),
        change_id="CH-TEST",
        repo_root="/repo/root",
    )

    asyncio.run(
        server.call_tool("scoped_file", {"op": "read", "path": "/repo/root/a.txt"})
    )
    asyncio.run(
        server.call_tool(
            "scoped_file", {"op": "write", "path": "/repo/root/b.txt", "content": "x"}
        )
    )
    asyncio.run(
        server.call_tool(
            "scoped_file",
            {"op": "move", "path": "/repo/root/b.txt", "dst": "/repo/root/c.txt"},
        )
    )
    asyncio.run(
        server.call_tool("scoped_file", {"op": "remove", "path": "/repo/root/c.txt"})
    )

    routed = [name for name, _ in spy.calls]
    assert routed == ["read_file", "write_file", "move_file", "remove_file"]

    # Server-resolved scope reached the wrapped function (not from agent args).
    first_kwargs = spy.calls[0][1]["kwargs"]
    assert first_kwargs.get("repo_root") == "/repo/root"
    # change_id is passed (positionally or by keyword) to the wrapped function.
    first = spy.calls[0][1]
    assert "CH-TEST" in first["args"] or first["kwargs"].get("change_id") == "CH-TEST"


def test_scoped_file_unknown_op_refused_fail_closed() -> None:
    """An ``op`` outside the closed enum is refused fail-closed — no wrapped
    function is called (mirrors ``_file_scope``'s ``_OPERATIONS`` guard)."""
    spy = _SpyFileOps()

    result = mcp_server.scoped_file(
        op="exfiltrate",
        path="/repo/root/a.txt",
        file_ops=spy.as_mapping(),
        change_id="CH-TEST",
        repo_root="/repo/root",
    )
    assert result["ok"] is False
    assert "exfiltrate" in result["reason"] or "unknown" in result["reason"].lower()
    assert spy.calls == []  # fail-closed: nothing routed


# ─── test_safe_fetch_delegates_to_gateway ─────────────────────────────────────


def test_safe_fetch_delegates_to_gateway() -> None:
    """``safe_fetch`` delegates to the wrapped ``_safe_fetch.tool.safe_fetch``
    through the injected gateway — no network, no reimplemented logic."""
    gateway = _RecordingGateway()
    content = mcp_server.safe_fetch(
        "https://example.com/page", format="markdown", gateway=gateway
    )

    assert len(gateway.requests) == 1
    assert gateway.requests[0].url == "https://example.com/page"
    assert gateway.requests[0].format == "markdown"
    # Returns the framed FetchResult.content (the WP Contract surface).
    assert "body for https://example.com/page" in content


def test_safe_search_delegates_to_gateway() -> None:
    """``safe_search`` rides the same gateway seam as ``safe_fetch``."""
    gateway = _RecordingGateway()
    content = mcp_server.safe_search("agent execution boundary", gateway=gateway)

    assert len(gateway.requests) == 1
    # The query reaches the gateway (so the proxy's scrub would see it).
    assert "agent" in gateway.requests[0].url
    assert "UNTRUSTED" in content


def test_module_docstring_states_honesty_boundary() -> None:
    """ADR-002 A2 / D6: the module docstring must state MCP identity is
    availability + denyability, NOT enforcement."""
    doc = (mcp_server.__doc__ or "").lower()
    assert "availability" in doc or "available" in doc
    assert "not enforcement" in doc or "not enforce" in doc


# ─── production-default wiring (no injection) ─────────────────────────────────


def test_default_file_ops_map_to_the_shipped_file_tools() -> None:
    """The production file-op mapping wraps the four shipped ``_file_tools``
    functions one-to-one — no bespoke path logic added (D6)."""
    import _file_tools

    ops = mcp_server._default_file_ops()
    assert ops["read"] is _file_tools.read_file
    assert ops["write"] is _file_tools.write_file
    assert ops["move"] is _file_tools.move_file
    assert ops["remove"] is _file_tools.remove_file


def test_default_gateway_is_the_production_proxy() -> None:
    """With no injected gateway, the server wires the real ``SafeFetchProxy``
    over the production ``UrllibFetcher`` — built lazily, no network on build."""
    from _safe_fetch.ports import FetchGateway
    from _safe_fetch.proxy import SafeFetchProxy

    gateway = mcp_server._default_gateway()
    assert isinstance(gateway, SafeFetchProxy)
    assert isinstance(gateway, FetchGateway)


def test_scope_resolved_from_launch_env_not_agent_args(monkeypatch) -> None:
    """``change_id`` / ``repo_root`` come from the launch environment
    (ADR-001 / ADR-004) — explicit ``SULIS_REPO_ROOT`` wins."""
    monkeypatch.setenv("SULIS_CHANGE_ID", "CH-FROM-ENV")
    monkeypatch.setenv("SULIS_REPO_ROOT", "/launch/repo/root")
    assert mcp_server._resolve_change_id() == "CH-FROM-ENV"
    assert mcp_server._resolve_repo_root("CH-FROM-ENV") == "/launch/repo/root"


def test_repo_root_falls_back_to_change_worktree(monkeypatch) -> None:
    """When ``SULIS_REPO_ROOT`` is unset but a change id is known, the repo root
    falls back to the change's canonical worktree dir (never an agent arg)."""
    from _change_state import change_worktree_dir

    monkeypatch.delenv("SULIS_REPO_ROOT", raising=False)
    resolved = mcp_server._resolve_repo_root("CH-WT")
    assert resolved == str(change_worktree_dir("CH-WT"))


def test_build_server_with_production_defaults_enumerates_three_tools(
    monkeypatch,
) -> None:
    """End-to-end: ``build_server()`` with NO injection (full production wiring)
    still registers exactly the three tools."""
    monkeypatch.setenv("SULIS_CHANGE_ID", "CH-DEFAULT")
    monkeypatch.setenv("SULIS_REPO_ROOT", "/repo")
    server = mcp_server.build_server()
    assert set(_enumerate(server)) == {"safe_fetch", "safe_search", "scoped_file"}


def test_registered_tool_closures_invoke_via_call_tool() -> None:
    """Exercise each registered tool through the MCP ``call_tool`` path (not just
    the free functions) so the closures themselves are covered: ``safe_fetch`` /
    ``safe_search`` delegate to the injected gateway; ``scoped_file`` routes to
    the spy file-op."""
    gateway = _RecordingGateway()
    spy = _SpyFileOps()
    server = mcp_server.build_server(
        gateway=gateway,
        file_ops=spy.as_mapping(),
        change_id="CH-T",
        repo_root="/repo",
    )

    asyncio.run(server.call_tool("safe_fetch", {"url": "https://example.com/x"}))
    asyncio.run(server.call_tool("safe_search", {"query": "boundary"}))
    asyncio.run(server.call_tool("scoped_file", {"op": "read", "path": "/repo/a.txt"}))

    # Both web calls rode the injected gateway; the file op routed to the spy.
    assert [r.url for r in gateway.requests][0] == "https://example.com/x"
    assert any("example.com" not in r.url for r in gateway.requests)  # the search
    assert spy.calls and spy.calls[0][0] == "read_file"
