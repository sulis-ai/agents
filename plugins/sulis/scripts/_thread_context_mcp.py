"""``thread_context`` MCP server — the raw-on-demand half of the discovery seam
(CH-GJ9KQR WP-005, ADR-005, TDD §3.1).

This server exposes the **read side** of the WP-001 ``ThreadStore`` contract
(``_session_manager.thread_contract``) as ONE denyable MCP tool identity, so an
agent allowlist can express "allow-context / deny-context". It follows the
established safe-tools pattern (``_safe_tools_mcp.py``): one parameterised ``op``
tool over a wrapped library, scope resolved server-side, the typed result (or the
typed contract error) serialised to a plain dict.

It registers exactly ONE tool (ADR-005 — one parameterised ``thread_context``,
not three identities, to avoid the permission-surface explosion the safe-tools
ADR-001 reasoning rejects):

  * ``thread_context(op, thread_id, since=None, limit=None) -> dict`` — ``op`` is
    the closed **READ** enum ``get_thread | get_memory | get_messages`` (the read
    half of the WP-001 contract). An ``op`` outside that set — including a
    write-shaped op (``append_message`` / ``put_memory``) — is a fail-closed
    refusal: **no** store method is called.

**Read-only (ADR-005).** The tool exposes only the contract's read operations.
The agent never writes the log — the session pump does (ADR-004). There is no
write op in the enum, so the wrapped store's write methods are unreachable from
this surface.

**Change-scoped server-side (ADR-005 / safe-tools ADR-001/ADR-004).** The tool
binds to the **bound change's** ``ThreadStore``, resolved from the launch
environment (``SULIS_CHANGE_ID``) — never from the agent's call args. Each
change's threads live under its own store root
(``thread_contract.store_root_for_change``), so a ``thread_id`` that is not in
the bound change's store is refused (``ExpectedError`` ``THREAD_NOT_FOUND``); the
agent cannot read another change's thread by passing a different id.

**Wrap, reimplement nothing (D6).** This module marshals MCP args to the
``ThreadStore`` read methods and serialises their typed results / typed errors.
It owns no persistence, no path/scope logic, and no error model — those live in
the contract (``thread_contract``) and the store adapter (WP-002). It codes
against the ``ThreadStore`` **Protocol**, not a concrete adapter, so the same
tool works unchanged when the store's transport later swaps to the hosted
communication-service (ADR-002) — only the binding moves.

**Honesty (safe-tools D6 / ADR-002 A2).** Registering this tool makes the
context-read path an **available** + **denyable** identity — it is
**NOT enforcement**. A consumer who registers this server but does not also load the
permission deny-rule gets only the availability half; the founder withholding
the tool is the deny-rule's job, not this server's. The MCP layer adds no
network and no new wall.

Stdlib + the ``mcp`` SDK + the wrapped ``thread_contract`` contract module only;
no transport and no store logic here (it is all wrapped). Python 3.11-safe.
"""

from __future__ import annotations

import os
from dataclasses import asdict
from typing import Any

from mcp.server.fastmcp import FastMCP

from _session_manager.thread_contract import (
    RAW_FETCH_TOOL_NAME,
    SessionError,
    ThreadStore,
)

# The server's stable MCP identity (the denyable name the allowlist references).
SERVER_NAME = "sulis-thread-context"

# The closed enum of READ operations (ADR-005 — the read half of the WP-001
# contract, and only the read half). An ``op`` outside this set — including a
# write-shaped op — is a fail-closed refusal: the tool is read-only.
_READ_OPS = ("get_thread", "get_memory", "get_messages")


# ─── result / error serialisation (the ONE place each becomes the MCP dict) ───


def _ok(payload: Any) -> dict[str, Any]:
    """Frame a successful read result. ``payload`` is the contract value
    serialised to a plain dict / list (vendor-neutral, JSON-shaped)."""
    return {"ok": True, "reason": None, "payload": payload}


def _refused(reason: str) -> dict[str, Any]:
    """Frame a fail-closed refusal (an unknown / write-shaped ``op``) — no store
    method was called."""
    return {"ok": False, "reason": reason, "payload": None, "error": None}


def _error(exc: SessionError) -> dict[str, Any]:
    """Frame a typed contract error, carrying its universal category
    discriminator + code + message (CF-03 — the three-category model). The ONE
    place a ``SessionError`` becomes the MCP payload."""
    return {
        "ok": False,
        "reason": exc.message,
        "payload": None,
        "error": {
            "category": exc.category,
            "code": exc.code,
            "message": exc.message,
        },
    }


# ─── the wrapped read dispatch (no store logic of its own) ────────────────────


def thread_context(
    op: str,
    thread_id: str,
    since: int | None = None,
    limit: int | None = None,
    *,
    store: ThreadStore,
    change_id: str,
) -> dict[str, Any]:
    """Dispatch one of the three READ ops to the matching ``ThreadStore`` method
    and serialise its typed result (or typed contract error).

    ``op`` is the closed read enum ``_READ_OPS`` (the single source of that
    truth); an unknown or write-shaped ``op`` is refused **fail-closed** (no
    wrapped method is called) — the explicit ``match`` over the validated enum
    mirrors ``scoped_file``'s guard (no reflection, no dynamic dispatch). The
    scope (``change_id`` + the bound ``store``) is supplied by the caller from
    the launch environment, never from the agent — a ``thread_id`` not in the
    bound change's store surfaces as the store's own ``THREAD_NOT_FOUND``
    refusal (change-scoped server-side).
    """
    if op not in _READ_OPS:
        return _refused(
            f"unknown thread_context op: {op!r} (read-only; allowed: "
            f"{', '.join(_READ_OPS)})"
        )
    try:
        match op:
            case "get_thread":
                return _ok(asdict(store.get_thread(thread_id)))
            case "get_memory":
                return _ok(asdict(store.get_memory(thread_id)))
            case "get_messages":
                messages = store.get_messages(thread_id, since=since, limit=limit)
                return _ok([asdict(m) for m in messages])
            case _:  # pragma: no cover - unreachable: guarded by the _READ_OPS check
                raise AssertionError(
                    f"op passed the _READ_OPS guard but matched nothing: {op!r}"
                )
    except SessionError as exc:
        # Every contract refusal (THREAD_NOT_FOUND / MEMORY_NOT_FOUND / …) and
        # every protocol/internal error rides the three-category serialiser.
        return _error(exc)


# ─── production wiring (lazy — keeps the store adapter import out of import time)


def _resolve_change_id() -> str:
    """The bound change id from the launch environment (ADR-005 / safe-tools
    ADR-001 / ADR-004) — never an agent call arg."""
    return os.environ.get("SULIS_CHANGE_ID", "")


def _default_store(change_id: str) -> ThreadStore:
    """The production ``ThreadStore`` binding for the bound change.

    Resolved lazily from the durable local adapter (WP-002) under the change's
    pinned store root (``thread_contract.store_root_for_change``). Imported
    lazily so this module carries no store/filesystem dependency at import time
    and codes against the ``ThreadStore`` Protocol, not the concrete adapter
    (the adapter is the parallel WP-002; the binding swaps to the hosted
    transport later behind the same port, ADR-002). Until the durable adapter
    lands, the contract's in-memory reference adapter conforms to the same read
    surface, so the tool is exercisable end-to-end against the contract.
    """
    try:
        from _session_manager.thread_store_local import (  # type: ignore[import-not-found]
            LocalThreadStore,
        )

        return LocalThreadStore(change_id)
    except ImportError:
        # WP-002's durable adapter is the parallel WP; fall back to the contract's
        # in-memory reference adapter (same ThreadStore read surface) so the tool
        # is wired and conformant before the durable binding merges.
        from _session_manager.thread_contract import InMemoryThreadStore

        return InMemoryThreadStore()


# ─── server factory ───────────────────────────────────────────────────────────


def build_server(
    *,
    store: ThreadStore | None = None,
    change_id: str | None = None,
) -> FastMCP:
    """Build the ``FastMCP`` server with the one ``thread_context`` tool
    registered.

    Every collaborator is injectable so the contract test drives the server with
    a spy / reference store + a fixed change scope; production passes nothing and
    the defaults resolve the bound change (launch env) + its durable store.
    """
    resolved_change_id = change_id if change_id is not None else _resolve_change_id()
    resolved_store = store if store is not None else _default_store(resolved_change_id)

    server = FastMCP(SERVER_NAME)

    @server.tool(name=RAW_FETCH_TOOL_NAME)
    def _thread_context_tool(
        op: str,
        thread_id: str,
        since: int | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        """Read the bound change's thread context: op ∈ get_thread | get_memory |
        get_messages (READ-ONLY). Change-scoped server-side (cannot read another
        change's thread). ``since`` / ``limit`` slice the offset-ordered message
        log. Returns {ok, reason, payload, error}; error carries {category, code,
        message}."""
        return thread_context(
            op,
            thread_id,
            since,
            limit,
            store=resolved_store,
            change_id=resolved_change_id,
        )

    return server


def main() -> None:
    """Entry point: build the server and run it over stdio (the launcher path)."""
    build_server().run()


if __name__ == "__main__":
    main()
