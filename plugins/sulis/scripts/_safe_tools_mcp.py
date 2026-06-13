"""safe-tools MCP server — wrap L1 (safe-fetch) + L2 (scoped file-tools) as
three denyable MCP tool identities (WP-001, ADR-001, ADR-002).

This server exposes the shipped, tested Python libraries — ``_safe_fetch.tool``
(``safe_fetch`` / ``safe_search``) and ``_file_tools`` (``read`` / ``write`` /
``move`` / ``remove``) — over the official ``mcp`` SDK's stdio transport, so an
agent allowlist can express "allow-safe / deny-raw". It registers exactly THREE
tools (ADR-001 — one parameterised ``scoped_file``, not four, to avoid the
name-collision / selection-bloat trap):

  * ``safe_fetch(url, format="markdown") -> str`` — delegates to
    ``_safe_fetch.tool.safe_fetch`` through a ``FetchGateway``; returns the
    framed ``FetchResult.content``.
  * ``safe_search(query) -> str`` — delegates to ``_safe_fetch.tool.safe_search``.
  * ``scoped_file(op, path, content=None, dst=None) -> dict`` — ``op`` is the
    closed enum ``read | write | move | remove``; an unknown ``op`` is a
    fail-closed refusal. Dispatches via an explicit ``match`` to the matching
    ``_file_tools`` function and serialises the typed ``FileToolResult``.

**Wrap, reimplement nothing (D6).** This module marshals MCP args to the
existing functions and serialises their typed results. It owns no HTTP client
(the open-web leg is ``_safe_fetch.fetcher.UrllibFetcher``, behind the proxy
port), no fetch/scrub/framing policy, and no path-scope logic (that lives in
``_file_scope`` via ``_file_tools``).

**Scope is server-resolved, not agent-supplied (ADR-001 / ADR-004).** The
``change_id`` and ``repo_root`` ``scoped_file`` passes to the wrapped file-tools
come from the **launch environment** (``SULIS_CHANGE_ID`` / ``SULIS_REPO_ROOT``),
never from the agent's call args — so the agent cannot widen its own write/read
scope by passing a different ``change_id``.

**Honesty (ADR-002 A2, D6).** Registering these tools makes the safe path an
**available** + **denyable** identity — it is **NOT enforcement**. A consumer
who registers this server but does not also load the PreToolUse hook (Phase 2)
+ the OS sandbox (Phase 4) gets only the availability half; enforcement of the
*unsafe* path is the hook (locus ii) and the sandbox (locus iii), not this
server. The MCP layer adds no network and no new wall.

Stdlib + the ``mcp`` SDK + the wrapped ``_safe_fetch`` / ``_file_tools`` modules
only; no ``urllib``/``requests`` and no scope logic here (it is all wrapped).
Python 3.11-safe.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

from mcp.server.fastmcp import FastMCP

import _file_tools
from _file_tools import FileToolResult
from _safe_fetch.ports import FetchGateway
from _safe_fetch.tool import safe_fetch as _wrapped_safe_fetch
from _safe_fetch.tool import safe_search as _wrapped_safe_search

SERVER_NAME = "sulis-safe-tools"

# The closed enum of file operations (ADR-001). Mirrors the four shipped
# ``_file_tools`` functions; an ``op`` outside this set is a fail-closed refusal.
_FILE_OPS = ("read", "write", "move", "remove")

# Type alias for an injected file-op mapping (used by tests to spy; production
# uses ``_default_file_ops``).
FileOps = dict[str, Callable[..., FileToolResult]]


# ─── wrapped-library delegators (no logic of their own) ───────────────────────


def safe_fetch(url: str, format: str = "markdown", *, gateway: FetchGateway) -> str:
    """Delegate to the wrapped ``_safe_fetch.tool.safe_fetch`` and return the
    framed ``FetchResult.content`` (the agent-facing surface)."""
    result = _wrapped_safe_fetch(url, gateway=gateway, format=format)
    return result.content


def safe_search(query: str, *, gateway: FetchGateway) -> str:
    """Delegate to the wrapped ``_safe_fetch.tool.safe_search`` and return the
    framed ``FetchResult.content``."""
    result = _wrapped_safe_search(query, gateway=gateway)
    return result.content


def _serialise_file_result(result: FileToolResult) -> dict[str, Any]:
    """The ONE place a ``FileToolResult`` becomes the MCP JSON payload.

    No duplicate marshalling lives anywhere else in this module.
    """
    return {"ok": result.ok, "reason": result.reason, "payload": result.payload}


def scoped_file(
    op: str,
    path: str,
    content: str | None = None,
    dst: str | None = None,
    *,
    file_ops: FileOps,
    change_id: str,
    repo_root: str,
) -> dict[str, Any]:
    """Dispatch one of the four file ops to the matching ``_file_tools``
    function and serialise its typed result.

    ``op`` is the closed enum ``read | write | move | remove`` (``_FILE_OPS`` —
    the single source of that truth); an unknown ``op`` is refused
    **fail-closed** (no wrapped function is called). The scope (``change_id`` /
    ``repo_root``) is supplied by the caller from the launch environment, never
    from the agent — the explicit ``match`` over the validated enum mirrors
    ``_file_scope``'s ``_OPERATIONS`` guard (no reflection, no dynamic dispatch).
    """
    if op not in _FILE_OPS:
        return _serialise_file_result(
            FileToolResult(
                ok=False, reason=f"unknown scoped_file op: {op!r}", payload=None
            )
        )
    match op:
        case "read":
            result = file_ops["read"](path, change_id, repo_root=repo_root)
        case "write":
            result = file_ops["write"](
                path, content or "", change_id, repo_root=repo_root
            )
        case "move":
            result = file_ops["move"](path, dst, change_id, repo_root=repo_root)
        case "remove":
            result = file_ops["remove"](path, change_id, repo_root=repo_root)
        case _:  # pragma: no cover - unreachable: guarded by the _FILE_OPS check
            raise AssertionError(
                f"op passed the _FILE_OPS guard but matched nothing: {op!r}"
            )
    return _serialise_file_result(result)


# ─── production wiring (lazy — keeps urllib out of import time) ────────────────


def _default_gateway() -> FetchGateway:
    """Build the production ``FetchGateway`` (``SafeFetchProxy`` over the real
    ``UrllibFetcher``). Imported lazily so this module carries no HTTP client at
    import time — the wrapped package owns the open-web leg (Blue: no ``urllib``
    in this module)."""
    from _safe_fetch.fetcher import UrllibFetcher
    from _safe_fetch.proxy import SafeFetchProxy

    return SafeFetchProxy(UrllibFetcher())


def _default_file_ops() -> FileOps:
    """The production file-op mapping — the four shipped ``_file_tools``
    functions, wrapped one-to-one (no bespoke path logic added)."""
    return {
        "read": _file_tools.read_file,
        "write": _file_tools.write_file,
        "move": _file_tools.move_file,
        "remove": _file_tools.remove_file,
    }


def _resolve_change_id() -> str:
    """The active change id from the launch environment (ADR-001 / ADR-004)."""
    return os.environ.get("SULIS_CHANGE_ID", "")


def _resolve_repo_root(change_id: str) -> str:
    """The repo root from the launch environment, else the change's worktree.

    Resolved from ``SULIS_REPO_ROOT`` first; when only the change id is known,
    fall back to the change's canonical worktree dir. Never taken from agent
    args (ADR-001)."""
    explicit = os.environ.get("SULIS_REPO_ROOT")
    if explicit:
        return explicit
    if change_id:
        from _change_state import change_worktree_dir

        return str(change_worktree_dir(change_id))
    return os.getcwd()


# ─── server factory ───────────────────────────────────────────────────────────


def build_server(
    *,
    gateway: FetchGateway | None = None,
    file_ops: FileOps | None = None,
    change_id: str | None = None,
    repo_root: str | None = None,
) -> FastMCP:
    """Build the ``FastMCP`` server with the three safe tools registered.

    Every collaborator is injectable so the contract test drives the server with
    a fake gateway + spy file-ops + a fixed scope; production passes nothing and
    the defaults wire the real proxy + the shipped file-tools + the launch-env
    scope.
    """
    resolved_gateway = gateway if gateway is not None else _default_gateway()
    resolved_file_ops = file_ops if file_ops is not None else _default_file_ops()
    resolved_change_id = change_id if change_id is not None else _resolve_change_id()
    resolved_repo_root = (
        repo_root if repo_root is not None else _resolve_repo_root(resolved_change_id)
    )

    server = FastMCP(SERVER_NAME)

    @server.tool(name="safe_fetch")
    def _safe_fetch_tool(url: str, format: str = "markdown") -> str:
        """Fetch a URL through the sanctioned safe-fetch gateway (secret-scrubbed,
        framed as untrusted data). ``format`` ∈ raw | text | markdown |
        structured. The only sanctioned outbound path."""
        return safe_fetch(url, format, gateway=resolved_gateway)

    @server.tool(name="safe_search")
    def _safe_search_tool(query: str) -> str:
        """Search the web through the same sanctioned gateway as safe_fetch."""
        return safe_search(query, gateway=resolved_gateway)

    @server.tool(name="scoped_file")
    def _scoped_file_tool(
        op: str, path: str, content: str | None = None, dst: str | None = None
    ) -> dict[str, Any]:
        """Scoped file op: op ∈ read | write | move | remove. Confined to the
        change's write/read scope (resolved from the launch environment, not
        these args). Returns {ok, reason, payload}."""
        return scoped_file(
            op,
            path,
            content,
            dst,
            file_ops=resolved_file_ops,
            change_id=resolved_change_id,
            repo_root=resolved_repo_root,
        )

    return server


def main() -> None:
    """Entry point: build the server and run it over stdio (the launcher path)."""
    build_server().run()


if __name__ == "__main__":
    main()
