"""Behaviour tests for the agent-facing L1 tool (``_safe_fetch.tool``) — WP-003.

TDD §Form. ``safe_fetch`` / ``safe_search`` are the **only sanctioned outbound
path the agent is told about** (ADR-001). They are thin over the WP-001
``FetchGateway`` seam: build a ``FetchRequest``, delegate to the injected
gateway, return the gateway's framed-as-untrusted ``FetchResult`` unchanged.

The tool owns no network and no proxy internals — it depends only on the
``FetchGateway`` port, so a fake gateway proves its behaviour with no network
(MEA-09). The honesty contract (this is a door, not the only door — L3 owns the
wall) lives in the module docstring (asserted present below).
"""

from __future__ import annotations

import _safe_fetch.tool as tool_module
from _safe_fetch.ports import FetchGateway, FetchRequest, FetchResult
from _safe_fetch.tool import safe_fetch, safe_search


class _RecordingGateway:
    """In-memory ``FetchGateway`` that records the request it was handed and
    returns a fixed framed result."""

    def __init__(self) -> None:
        self.requests: list[FetchRequest] = []

    def fetch(self, req: FetchRequest) -> FetchResult:
        self.requests.append(req)
        return FetchResult(
            source_url=req.url,
            fetched_at="2026-06-13T00:00:00+00:00",
            content_is_untrusted_data=True,
            content=f"<<<UNTRUSTED>>>body for {req.url}<<<END>>>",
        )


def test_safe_fetch_delegates_to_gateway_and_returns_framed_result() -> None:
    gateway = _RecordingGateway()

    result = safe_fetch("https://example.com/page", gateway=gateway)

    assert isinstance(result, FetchResult)
    assert result.content_is_untrusted_data is True
    assert "body for https://example.com/page" in result.content
    # Delegated through the WP-001 seam with a GET FetchRequest.
    assert len(gateway.requests) == 1
    assert gateway.requests[0].url == "https://example.com/page"
    assert gateway.requests[0].method == "GET"


def test_safe_fetch_returns_the_gateways_result_unchanged() -> None:
    """The tool does not re-frame or mutate — it returns exactly what the
    gateway produced (framing is WP-002's job, behind the port)."""
    gateway = _RecordingGateway()
    result = safe_fetch("https://example.com/x", gateway=gateway)
    # Same object identity is not required, but content must be verbatim.
    assert result.source_url == "https://example.com/x"
    assert result.content.endswith("<<<END>>>")


def test_safe_search_rides_the_same_sanctioned_path() -> None:
    gateway = _RecordingGateway()

    result = safe_search("agent execution boundary", gateway=gateway)

    assert isinstance(result, FetchResult)
    assert result.content_is_untrusted_data is True
    # A search is performed as a fetch through the same gateway seam — one
    # sanctioned outbound path, not a second raw channel.
    assert len(gateway.requests) == 1


def test_safe_search_encodes_the_query_into_the_request() -> None:
    """The query must reach the gateway (so the proxy's scrub sees it); the
    tool must not silently drop it."""
    gateway = _RecordingGateway()
    safe_search("stripe sk leak", gateway=gateway)
    req = gateway.requests[0]
    # The query terms appear somewhere in the outbound request the gateway saw.
    assert "stripe" in req.url or (req.body is not None and "stripe" in req.body)


def test_tool_accepts_any_fetch_gateway_conformer() -> None:
    """The tool depends on the PORT, not the concrete proxy — any
    ``FetchGateway`` conformer works (dependency-inward)."""
    gateway: FetchGateway = _RecordingGateway()
    result = safe_fetch("https://fresh.example/never-listed", gateway=gateway)
    assert isinstance(result, FetchResult)


def test_module_docstring_names_l3_as_the_only_door_owner() -> None:
    """ADR-001 honesty: the tool's docstring must state it is the only
    *sanctioned* path the agent is told about, and that the *only-door*
    guarantee is L3's, not this tool's."""
    doc = (tool_module.__doc__ or "").lower()
    assert "sanctioned" in doc
    # Names L3 as the owner of the only-door guarantee (door vs wall).
    assert "l3" in doc
