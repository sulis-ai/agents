"""L1 proxy — the production ``FetchGateway`` adapter (ADR-002 / ADR-003).

``SafeFetchProxy`` is the real outbound-fetch gateway behind the WP-001
``FetchGateway`` port. It composes two controls over an injected
``OutboundFetcher`` (the proxy → open-web seam):

  1. **Secret scrub — fail-closed REFUSE, before DNS (ADR-002, SC-L1.3).**
     Before resolving DNS or opening any socket, the proxy runs the shared
     ``_secret_patterns.find_secrets`` catalogue over the *entire* outbound
     request line — method + URL + every header value + body. ANY hit →
     ``SecretInOutboundRequest`` is raised and the request **never leaves the
     process**: the injected fetcher is not called at all. This is a **refuse**
     policy, not redact-and-send — silently mutating a request can corrupt a
     legitimate call and teaches the agent nothing; refusing is the honest, safe
     default (the agent learns the request carried a secret and must not send
     it). The refusal names the secret *category*, never echoes the value.

     The scrub is **defence-in-depth, not the primary control.** The primary
     control is the Rule-of-Two credential exclusion (ADR-001 / SPEC §L1(d),
     wired at spawn time in WP-003): the proxy runs without the credential-
     bearing env in its scope, so a configured credential cannot be *read* into
     an outbound request in the first place. The catalogue is format-based, so a
     novel secret shape it does not recognise can pass — the exclusion is the
     real wall, this scrub is the belt to those braces (documented, not hidden).

  2. **Untrusted-data framing (ADR-003, SC-L1.4 framing half).** A benign fetch
     returns the page text verbatim, wrapped in the deterministic spotlighting
     envelope (``framing.frame_as_untrusted_data``) and flagged
     ``content_is_untrusted_data=True``. Content is NOT sanitised.

The proxy's only I/O is via the injected ``OutboundFetcher`` (network) plus a
single wall-clock read for the ``fetched_at`` provenance stamp; the scrub and
framing logic are pure. Stdlib + WP-001 modules only.
"""

from __future__ import annotations

from datetime import datetime, timezone

from _secret_patterns import find_secrets

from .framing import frame_as_untrusted_data
from .ports import FetchRequest, FetchResult, OutboundFetcher


class SecretInOutboundRequest(Exception):
    """Raised when a catalogued secret is found in an outbound request.

    Fail-closed: the proxy refuses the fetch *before* DNS resolution, so the
    request never leaves the process (ADR-002, SC-L1.3). The message names the
    secret *category* for an honest, actionable refusal but never echoes the
    secret value.
    """


class SafeFetchProxy:
    """Production ``FetchGateway``: scrub-before-DNS, then fetch-and-frame.

    Wired with an ``OutboundFetcher`` (real HTTP leg in production, an in-memory
    fake in tests). The injected ``timeout`` is passed through to every fetch
    so no external call is unbounded (Armor).
    """

    def __init__(self, fetcher: OutboundFetcher, *, timeout: float = 10.0) -> None:
        self._fetcher = fetcher
        self._timeout = timeout

    def fetch(self, req: FetchRequest) -> FetchResult:
        # 1. Scrub the full outbound request line BEFORE any DNS/socket.
        self._refuse_if_secret(req)

        # 2. No secret → perform the bounded fetch via the injected seam.
        raw = self._fetcher.get(req.url, timeout=self._timeout)

        # 3. Frame the verbatim content as untrusted data (ADR-003).
        return FetchResult(
            source_url=req.url,
            fetched_at=datetime.now(timezone.utc).isoformat(),
            content_is_untrusted_data=True,
            content=frame_as_untrusted_data(raw, req.url),
        )

    def _refuse_if_secret(self, req: FetchRequest) -> None:
        """Scan method + url + every header value + body; refuse on any hit.

        Runs before the fetcher is touched (scrub-before-DNS). Raises
        ``SecretInOutboundRequest`` naming the offending categories, without
        echoing any secret value.
        """
        parts: list[str] = [req.method, req.url]
        # Scan both header names and values — a secret could be placed in either
        # (defence-in-depth; real-world header names never match the catalogue).
        parts.extend(req.headers.keys())
        parts.extend(req.headers.values())
        if req.body is not None:
            parts.append(req.body)

        categories: list[str] = []
        for part in parts:
            for hit in find_secrets(part):
                if hit.category not in categories:
                    categories.append(hit.category)

        if categories:
            raise SecretInOutboundRequest(
                "refused: outbound request carries a secret "
                f"({', '.join(categories)}); fail-closed before DNS"
            )
