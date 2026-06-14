"""Content extraction — clean main-content shaping behind the framing seam.

CH-9SYSNE. The L1 proxy fetches a page verbatim; this module turns that raw
source into the caller-chosen *shape* (``raw | text | markdown | structured``)
BEFORE the proxy frames it as untrusted data. It sits strictly between fetch and
framing — it never touches the scrub-before-DNS path or the no-raw-egress
posture (those are L1 / L3 and are unchanged).

The extractor is **trafilatura** (CP — the established, purpose-built
main-content extractor, preferred over a hand-rolled BeautifulSoup parse). We
use its programmatic API only (no shell-out).

**Honest boundary (SPEC non-goal).** Extraction strips *active/hidden* content —
scripts, HTML comments, ``display:none`` nodes — which is real defence-in-depth.
It is **not** an injection-removal control: a prompt injection written in
*visible prose* survives extraction (it is genuine main content). The injection
control remains treat-as-data + no-raw-egress (L1), unchanged. Never claim
"clean ⇒ safe."

**Never raises.** Extraction failure (empty body, malformed markup, non-HTML
payload, or trafilatura returning ``None``) degrades gracefully to returning the
available raw text — the proxy then frames that. A degraded fetch is honest and
usable; a crash is neither (SC-X.6).
"""

from __future__ import annotations

import json
from html.parser import HTMLParser

import trafilatura

# The supported output shapes. ``markdown`` is the default the request carries.
RAW = "raw"
TEXT = "text"
MARKDOWN = "markdown"
STRUCTURED = "structured"

_KNOWN_FORMATS = frozenset({RAW, TEXT, MARKDOWN, STRUCTURED})


class _LinkAndTitleParser(HTMLParser):
    """Collect ``href`` targets and the document ``<title>`` from source HTML.

    Used only to populate the ``structured`` contract's ``links`` / ``title``
    fields — trafilatura's JSON output does not expose a links array, and the
    source HTML is the honest provenance for the page's hyperlinks. Stdlib only;
    tolerant of malformed markup (``HTMLParser`` does not raise on bad input).
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[str] = []
        self.title: str | None = None
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            for name, value in attrs:
                if name == "href" and value:
                    if value not in self.links:
                        self.links.append(value)
        elif tag == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title and self.title is None:
            stripped = data.strip()
            if stripped:
                self.title = stripped


def _links_and_title(raw_html: str) -> tuple[list[str], str | None]:
    """Best-effort hyperlink + title scrape from source HTML; never raises."""
    parser = _LinkAndTitleParser()
    try:
        parser.feed(raw_html)
    except Exception:  # noqa: BLE001 — malformed markup must never crash extraction.
        pass
    return parser.links, parser.title


def _extract_text(raw_html: str) -> str | None:
    """Clean plain text of the main content, or ``None`` if not extractable."""
    return trafilatura.extract(raw_html)


def _extract_markdown(raw_html: str) -> str | None:
    """Clean markdown of the main content, or ``None`` if not extractable."""
    return trafilatura.extract(raw_html, output_format="markdown")


def _extract_structured(raw_html: str, *, url: str, fetched_at: str) -> str | None:
    """The structured JSON contract, or ``None`` if main content is missing.

    Returns a JSON object ``{url, title, content, links, fetched_at}`` where
    ``content`` is the extracted markdown. ``title`` prefers trafilatura's
    extracted title and falls back to the document ``<title>``; ``links`` is the
    page's hyperlink targets scraped from the source.
    """
    content = _extract_markdown(raw_html)
    if content is None:
        return None

    links, html_title = _links_and_title(raw_html)
    title = _trafilatura_title(raw_html) or html_title
    payload = {
        "url": url,
        "title": title,
        "content": content,
        "links": links,
        "fetched_at": fetched_at,
    }
    return json.dumps(payload, ensure_ascii=False)


def _trafilatura_title(raw_html: str) -> str | None:
    """trafilatura's own extracted title (from its JSON metadata), or ``None``."""
    meta_json = trafilatura.extract(raw_html, output_format="json", with_metadata=True)
    if not meta_json:
        return None
    try:
        title = json.loads(meta_json).get("title")
    except (ValueError, AttributeError):
        return None
    return title or None


def extract(raw_html: str, fmt: str, *, url: str, fetched_at: str) -> str:
    """Shape ``raw_html`` per ``fmt``; fall back to raw text, never raise.

    - ``raw``        → the verbatim source (today's L1 behaviour, now explicit).
    - ``text``       → clean plain text (boilerplate/scripts/hidden removed).
    - ``markdown``   → clean markdown (the default).
    - ``structured`` → the JSON contract ``{url, title, content, links,
                       fetched_at}``.

    An unrecognised ``fmt`` is treated as ``markdown`` (the default shape). When
    extraction cannot produce clean content (empty / malformed / non-HTML /
    trafilatura returns ``None``), the verbatim ``raw_html`` is returned so the
    proxy frames the available text — a graceful degrade, never an exception
    (SC-X.6).
    """
    if fmt == RAW:
        return raw_html

    try:
        if fmt == TEXT:
            extracted = _extract_text(raw_html)
        elif fmt == STRUCTURED:
            extracted = _extract_structured(raw_html, url=url, fetched_at=fetched_at)
        else:  # markdown (default) + any unrecognised format
            extracted = _extract_markdown(raw_html)
    except Exception:  # noqa: BLE001 — extraction is best-effort; degrade, never crash.
        extracted = None

    # Graceful fallback: when nothing clean could be extracted, return the
    # available raw text so the agent still gets the (framed) content.
    return extracted if extracted is not None else raw_html
