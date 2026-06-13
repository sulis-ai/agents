"""L1 agent-facing safe-fetch / safe-search tool (WP-003 / TDD §Form).

``safe_fetch`` and ``safe_search`` are the **only sanctioned outbound path the
agent is told about** (ADR-001). They are deliberately thin over the WP-001
``FetchGateway`` seam: build a :class:`~_safe_fetch.ports.FetchRequest`, hand it
to the injected gateway, and return the gateway's
:class:`~_safe_fetch.ports.FetchResult` **unchanged** — already framed as
untrusted data and flagged ``content_is_untrusted_data=True`` by the proxy
(WP-002, ADR-003).

The tool owns no network, no HTTP client, and no proxy internals. It depends
only on the ``FetchGateway`` **port** (dependency-inward, MEA-01), so the same
function serves the production :class:`~_safe_fetch.proxy.SafeFetchProxy` and an
in-memory fake in tests with no special-casing.

**Honest boundary (ADR-001 — door, not yet the only door).** This tool is the
*sanctioned* door: the path the agent is told to use, the one the secret scrub
(WP-002) and the spawn-time credential exclusion (WP-003 spawn-env) protect. It
is **not** the *only* door — a hijacked process can still open a raw socket in
userland. The guarantee that the proxy is the **only** egress is owned by **L3**
(the deferred ``l3-os-egress-denial`` OS sandbox), not by this tool. The L1
scenario tests confine the process in a test-only shim (ADR-005) that simulates
that L3 denial, and say so in their docstrings.

Stdlib + WP-001 ports only; no third-party imports; Python 3.11-safe.
"""

from __future__ import annotations

from urllib.parse import urlencode

from .ports import FetchGateway, FetchRequest, FetchResult

# The default open-web search endpoint a bare ``safe_search`` query is turned
# into. A real deployment may point this at an internal search service; the
# point for L1 is that a search rides the SAME sanctioned gateway as a fetch —
# one outbound door, never a second raw channel.
_SEARCH_ENDPOINT = "https://duckduckgo.com/html/"


def safe_fetch(
    url: str, *, gateway: FetchGateway, format: str = "markdown"
) -> FetchResult:
    """Fetch ``url`` through the sanctioned gateway and return framed content.

    The agent's only told-about way to reach the open web. The returned
    ``FetchResult`` is the gateway's reply: content wrapped as untrusted
    **data** (ADR-003), ``content_is_untrusted_data=True``. The gateway (the
    proxy in production) runs the outbound secret scrub before any DNS
    resolution (WP-002); this tool adds no policy of its own and imposes no URL
    allowlist — arbitrary public URLs are fetched, so open-web research is
    preserved (SC-L1.1).

    ``format`` is a passthrough (CH-9SYSNE): one of ``raw | text | markdown |
    structured``, defaulting to clean ``markdown``. The proxy shapes the fetched
    content accordingly AFTER the fetch and BEFORE framing — the tool itself
    owns no extraction policy, it only forwards the caller's choice.
    """
    return gateway.fetch(FetchRequest(url=url, format=format))


def safe_search(query: str, *, gateway: FetchGateway) -> FetchResult:
    """Run a web search for ``query`` through the same sanctioned gateway.

    A search is performed as a fetch of the search endpoint with the query
    encoded into the request URL — it rides the **same** ``FetchGateway`` door
    as :func:`safe_fetch`, so it inherits the same scrub + framing and adds no
    second outbound channel. The result is framed as untrusted data like any
    fetch (the result page is data, never instructions).
    """
    url = f"{_SEARCH_ENDPOINT}?{urlencode({'q': query})}"
    return gateway.fetch(FetchRequest(url=url))
