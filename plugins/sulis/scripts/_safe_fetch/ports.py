"""L1 ports — the typed seam between the agent-facing tool and the proxy.

WP-001 / TDD §Form pins the L1 contract first (CF-01) because it is a
producer/consumer boundary. Two ports, two value objects:

  - ``FetchGateway``   — the **agent → proxy** seam. ``tool.py`` (WP-003) depends
                         on THIS, never on proxy internals. The production
                         adapter is ``proxy.py`` (WP-002); the test adapter is an
                         in-memory ``FakeGateway``.
  - ``OutboundFetcher``— the **proxy → open-web** seam. The real HTTP leg inside
                         the proxy sits behind this port so the scrub/frame logic
                         is tested with no real network (the adapter sets an
                         explicit connect+read timeout — Armor: no unbounded
                         external call).

**Stripe-rule discriminator — these are ports the domain owns, not Wraps.** The
public face is *our* ``FetchGateway`` / ``OutboundFetcher`` interface; the HTTP
client is *called by* the adapter that implements ``OutboundFetcher``, it is not
the thing we re-export. So the adapters that implement these ports in WP-002/003
are EXPAND-Create adapters for domain-owned ports — not Wraps of a vendor SDK.

Dependency direction is inward: ``tool`` → ``FetchGateway`` ← ``proxy`` →
``OutboundFetcher`` + framing + ``_secret_patterns``. Nothing here imports the
manager, the daemon, or a vendor CLI. **No third-party imports; Python
3.11-safe** (``typing.Protocol`` + ``dataclasses`` are stdlib; ``str | None`` is
the 3.10+ union syntax).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

# ─── Value objects ────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class FetchRequest:
    """An outbound fetch the agent asks the gateway to perform.

    Frozen value object — the proxy scrubs and inspects it without risk of
    mutation. The proxy runs the secret scrub over ``method`` + ``url`` + every
    ``headers`` value + ``body`` before any DNS resolution (ADR-002, SC-L1.3).

    ``format`` selects the *shape* of the content the proxy returns AFTER it has
    fetched the page (CH-9SYSNE). Additive, frozen-safe, and defaulted — one of
    ``raw | text | markdown | structured`` (see ``FetchResult.format``). The
    default is ``markdown``: clean, readable, token-cheap extracted main
    content. Extraction runs after the fetch and before framing, so the
    scrub-before-DNS path is unaffected by this field.
    """
    url: str
    method: str = "GET"
    headers: dict[str, str] = field(default_factory=dict)
    body: str | None = None
    format: str = "markdown"


@dataclass(frozen=True)
class FetchResult:
    """The gateway's reply: fetched content framed as untrusted data (ADR-003).

    ``content_is_untrusted_data`` is always ``True`` from a real fetch — fetched
    content is data, never instructions. ``content`` is the framed envelope
    (deterministic delimiter-wrapping, spotlighting) around the *processed*
    content (CH-9SYSNE: extracted-and-shaped per the request's ``format``, or
    the verbatim source when ``format="raw"`` or extraction fell back). The
    framing is the injection control — extraction is defence-in-depth that
    strips active/hidden content, NOT injection-removal (a visible-prose
    injection survives extraction; SPEC non-goal).

    ``format`` reports the shape actually returned (``raw | text | markdown |
    structured``) so the caller knows how to read ``content`` inside the
    envelope.
    """
    source_url: str
    fetched_at: str                   # ISO 8601
    content_is_untrusted_data: bool   # always True from a real fetch
    content: str                      # framed envelope (ADR-003)
    format: str                       # shape returned (CH-9SYSNE)


# ─── Ports ────────────────────────────────────────────────────────────────────


@runtime_checkable
class FetchGateway(Protocol):
    """Agent → proxy seam. ``tool.py`` depends on THIS, never on proxy internals.

    The production adapter (``proxy.py``, WP-002) scrubs the request for secrets
    before DNS, fetches via an ``OutboundFetcher``, frames the result as
    untrusted data, and returns it. An in-memory fake satisfies the same shape
    for tests (MEA-09 — contract test the fake + the real adapter both satisfy).
    """

    def fetch(self, req: FetchRequest) -> FetchResult: ...


@runtime_checkable
class OutboundFetcher(Protocol):
    """proxy → open-web seam. The real HTTP leg is an adapter behind this.

    The adapter sets an explicit connect+read ``timeout`` (Armor: no unbounded
    external call). Keeping the HTTP leg behind this port lets the proxy's
    scrub/frame logic be tested with an in-memory fetcher and no real network.
    """

    def get(self, url: str, *, timeout: float) -> str: ...
