"""Production ``OutboundFetcher`` adapter — the proxy's real open-web leg.

``UrllibFetcher`` is the production adapter behind the WP-001 ``OutboundFetcher``
port (``ports.OutboundFetcher``): the proxy's *proxy → open-web* seam. It is the
only place a real socket is opened, and it sits behind the port so the proxy's
scrub/frame logic stays network-free in tests (the tests inject an in-memory
fetcher; production injects this one).

It does exactly one thing — a single bounded HTTP GET — and owns no policy: the
secret-scrub-before-DNS, untrusted-data framing, and content extraction all live
in :class:`~_safe_fetch.proxy.SafeFetchProxy`, which *calls* this adapter. The
adapter sets the explicit connect+read ``timeout`` the port requires so no
external call is ever unbounded (Armor: no unbounded external call).

Stdlib only (``urllib``); Python 3.11-safe.
"""

from __future__ import annotations

import urllib.request

# A conservative default UA — some endpoints reject the bare urllib agent. The
# proxy's secret-scrub runs over the request line BEFORE this adapter is reached,
# so the header set here carries no caller data.
_USER_AGENT = "sulis-safe-fetch/1.0"


class UrllibFetcher:
    """``OutboundFetcher`` over the stdlib ``urllib`` client (production).

    The single bounded GET behind the proxy's open-web seam. ``timeout`` is
    passed straight to ``urlopen`` so the proxy's injected bound applies to
    both connect and read.
    """

    def get(self, url: str, *, timeout: float) -> str:
        req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
        # The URL has already been secret-scrubbed by the proxy before this
        # adapter is called (scrub-before-DNS, ADR-002). nosec/noqa: the bound
        # timeout is the Armor control; the proxy owns egress policy.
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            charset = resp.headers.get_content_charset() or "utf-8"
            return resp.read().decode(charset, errors="replace")
