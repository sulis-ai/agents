"""Contract test for the L1 ports (``_safe_fetch.ports``).

WP-001 / TDD §Form: the L1 seam between the agent-facing tool and the proxy is a
producer/consumer boundary, so the contract is pinned first (CF-01). This test
defines the shape both the in-memory test adapter and the production adapter
(landing in WP-002/003) must satisfy:

  - ``FetchRequest`` / ``FetchResult`` are frozen typed value objects with the
    pinned fields.
  - ``FetchGateway`` is the agent → proxy seam (``fetch(req) -> FetchResult``).
  - ``OutboundFetcher`` is the proxy → open-web seam (``get(url, *, timeout)``).
  - both are ``typing.Protocol``s — the domain owns them; adapters implement
    them (Stripe-rule: these are ports we own, not Wraps).

The conformers here are in-memory fakes — no network. ``runtime_checkable`` lets
us assert structural conformance at the contract boundary (MEA-09: contract test
the fake + the real adapter both satisfy, no mock-the-internals).
"""

from __future__ import annotations

from _safe_fetch.ports import (
    FetchGateway,
    FetchRequest,
    FetchResult,
    OutboundFetcher,
)

# ─── FetchRequest ─────────────────────────────────────────────────────────────


def test_fetch_request_defaults():
    req = FetchRequest(url="https://example.com")
    assert req.url == "https://example.com"
    assert req.method == "GET"
    assert req.headers == {}
    assert req.body is None
    # CH-9SYSNE: the content-extraction format defaults to clean markdown.
    assert req.format == "markdown"


def test_fetch_request_carries_explicit_format():
    """CH-9SYSNE: ``format`` is an additive, frozen-safe, defaulted field
    selecting the extracted shape (raw | text | markdown | structured)."""
    req = FetchRequest(url="https://example.com", format="raw")
    assert req.format == "raw"


def test_fetch_request_is_frozen():
    req = FetchRequest(url="https://example.com")
    try:
        req.url = "https://evil.com"  # type: ignore[misc]
    except Exception:
        return
    raise AssertionError("FetchRequest must be frozen")


def test_fetch_request_carries_method_headers_body():
    req = FetchRequest(
        url="https://api.example.com/x",
        method="POST",
        headers={"X-Trace": "abc"},
        body='{"k": "v"}',
    )
    assert req.method == "POST"
    assert req.headers["X-Trace"] == "abc"
    assert req.body == '{"k": "v"}'


# ─── FetchResult ──────────────────────────────────────────────────────────────


def test_fetch_result_shape():
    res = FetchResult(
        source_url="https://example.com",
        fetched_at="2026-06-13T00:00:00Z",
        content_is_untrusted_data=True,
        content="<<<UNTRUSTED…>>>hello<<<END…>>>",
        format="markdown",
    )
    assert res.source_url == "https://example.com"
    assert res.fetched_at == "2026-06-13T00:00:00Z"
    assert res.content_is_untrusted_data is True
    assert "hello" in res.content
    # CH-9SYSNE: the result reports the format actually returned.
    assert res.format == "markdown"


def test_fetch_result_is_frozen():
    res = FetchResult(
        source_url="https://example.com",
        fetched_at="2026-06-13T00:00:00Z",
        content_is_untrusted_data=True,
        content="x",
        format="markdown",
    )
    try:
        res.content = "tampered"  # type: ignore[misc]
    except Exception:
        return
    raise AssertionError("FetchResult must be frozen")


# ─── FetchGateway port + in-memory conformer ──────────────────────────────────


class _FakeGateway:
    """In-memory FetchGateway: returns a framed, untrusted-data result without
    touching the network. The kind of adapter WP-002/003 build for real."""

    def fetch(self, req: FetchRequest) -> FetchResult:
        return FetchResult(
            source_url=req.url,
            fetched_at="2026-06-13T00:00:00Z",
            content_is_untrusted_data=True,
            content=f"<<<UNTRUSTED>>>page for {req.url}<<<END>>>",
            format=req.format,
        )


def test_fake_gateway_satisfies_fetch_gateway_protocol():
    gateway: FetchGateway = _FakeGateway()
    result = gateway.fetch(FetchRequest(url="https://fresh.example/never-listed"))
    assert isinstance(result, FetchResult)
    assert result.content_is_untrusted_data is True
    assert "fresh.example" in result.content


def test_fetch_gateway_is_runtime_checkable():
    assert isinstance(_FakeGateway(), FetchGateway)

    class _NotAGateway:
        pass

    assert not isinstance(_NotAGateway(), FetchGateway)


# ─── OutboundFetcher port + in-memory conformer ───────────────────────────────


class _FakeFetcher:
    """In-memory OutboundFetcher: the seam the proxy's real HTTP leg sits
    behind, so scrub/frame logic is tested with no real network."""

    def get(self, url: str, *, timeout: float) -> str:
        assert timeout > 0
        return f"body of {url}"


def test_fake_fetcher_satisfies_outbound_fetcher_protocol():
    fetcher: OutboundFetcher = _FakeFetcher()
    assert fetcher.get("https://example.com", timeout=5.0) == \
        "body of https://example.com"


def test_outbound_fetcher_is_runtime_checkable():
    assert isinstance(_FakeFetcher(), OutboundFetcher)

    class _NotAFetcher:
        pass

    assert not isinstance(_NotAFetcher(), OutboundFetcher)


# ─── Production adapter conforms to the same FetchGateway contract (WP-002) ───


def test_production_proxy_satisfies_fetch_gateway_protocol():
    """MEA-09: the production adapter (``SafeFetchProxy``, WP-002) must satisfy
    the SAME ``FetchGateway`` contract the in-memory fake does. Wired with an
    in-memory ``OutboundFetcher`` so this stays network-free."""
    from _safe_fetch.proxy import SafeFetchProxy

    proxy: FetchGateway = SafeFetchProxy(_FakeFetcher())
    assert isinstance(proxy, FetchGateway)
    result = proxy.fetch(FetchRequest(url="https://example.com/never-listed"))
    assert isinstance(result, FetchResult)
    assert result.content_is_untrusted_data is True
