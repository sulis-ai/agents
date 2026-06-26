"""Shared secret-detection module — one seam, two named policies (ADR-002/006).

This module owns the marketplace's secret detectors. It is pure (no I/O of its
own beyond detect-secrets' in-process plugin scan, no mutable global state) and
exposes ``SecretHit`` + three named functions so the two consumers can pick
*different* detection policies over a shared seam:

  - ``find_catalogue_secrets(text)`` — the in-house, prefix-anchored / format-
    based catalogue (env-assignment, JWT, Slack, long-token, private-IP). This
    is the **supplementary** layer: it owns detections detect-secrets does not
    cover (private/loopback IPs via the ``ipaddress`` stdlib, env-var-named
    assignments, the slack/jwt/long-token hardening lessons #39/#40/#42).

  - ``find_secrets(text)`` — the **OUTBOUND-SCRUB policy** (WP-006 / ADR-006):
    the UNION of ``detect-secrets`` (Yelp — the established detector, adopted as
    PRIMARY per CP-01) and the in-house catalogue. The L1 safe-fetch proxy
    (WP-002/003) calls this unchanged; any hit in an outbound request line →
    fail closed, refuse the fetch before DNS (SC-L1.3). It leans fail-closed: a
    false-positive costs one blocked fetch (acceptable); a false-negative leaks
    a secret (not). ADR-006 supersedes ADR-002's entropy-rejection for THIS
    policy only — detect-secrets' entropy plugins use a quote/assignment
    heuristic, so commit SHAs / ULIDs / UUIDs in prose stay clean while
    quoted/assigned high-entropy provider tokens are caught. ``detect-secrets``
    is an OPTIONAL dependency: when it is unavailable (e.g. the cockpit chat-turn
    scrub spawns a plain ``python3`` with no uv env), the union DEGRADES to the
    in-house catalogue alone — ``find_secrets`` still redacts the real provider
    key shapes and NEVER crashes on the missing enhancer (CH-G3Y4RM). When
    detect-secrets IS present, behaviour is byte-for-byte unchanged.

  - ``_anonymiser`` does NOT call either function above — it imports the raw
    compiled catalogue patterns directly and applies its own **redact policy**.
    Its posture is unchanged by WP-006 (catalogue-only, ADR-002 entropy-
    rejection still applies there — low false positives so the founder preview
    is not noise). The detect-secrets union is the outbound-scrub's alone.

One catalogue means a new in-house secret format is added once and the redact +
scrub consumers both inherit it (Non-Negotiable #2). Adopting detect-secrets as
the scrub's PRIMARY detector means the scrub also inherits Yelp's maintained
provider catalogue (AWS keys, Google API keys, high-entropy tokens, …) without
re-encoding it here (CP-01 — adopt the convention, don't reinvent).

Catalogue categories (the supplementary layer):

  - ``env-secret``  — env-var-named assignment (``*_KEY``/``*_SECRET``/
                      ``*_TOKEN``/``*_PASSWORD`` ``= value``); the value is the
                      secret, the whole assignment is the hit span.
  - ``jwt``         — ``header.payload.signature`` JWT shape.
  - ``slack``       — Slack token (``xox[abprs]-`` + ≥3 numeric blocks + tail).
  - ``long-token``  — long opaque provider token (``sk_live_``/``ghp_``/
                      ``AKIA``/``AIza``/``npm_``/… + ≥20 alnum, no hyphens).
  - ``openai-key``  — OpenAI API key: the modern project-scoped ``sk-proj-…``
                      (hyphenated) form and the legacy ``sk-`` + ≥40-alnum form.
                      Distinct from ``long-token`` because the OpenAI shapes are
                      hyphenated and so escape the underscore-anchored,
                      hyphen-excluding ``long-token`` pattern (#WP-010, GAP 3).
  - ``private-ip``  — private / loopback / link-local IP (RFC 1918/4193/3927/
                      4291 + loopback), classified via the ``ipaddress`` stdlib;
                      globally-routable IPs are NOT secrets and are not returned.

detect-secrets categories (the primary layer) are prefixed ``ds:`` so a hit's
provenance is legible in the proxy's refusal message (e.g. ``ds:AWS Access
Key``, ``ds:Base64 High Entropy String``). The proxy refuses on ANY category,
so the exact label is for the human-readable refusal, not control flow.
"""

from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass

# detect-secrets (Yelp) — the PRIMARY outbound-scrub detector (WP-006 / ADR-006).
# ``default_settings`` populates the plugin registry with Yelp's default plugin
# set; ``get_plugins`` returns the configured plugin instances we run per line.
# In-process plugin API — no shell-out (the WP constraint), portable.
#
# OPTIONAL dependency (CH-G3Y4RM robustness fix). ``detect_secrets`` is a uv-
# locked dependency, present under the project's pytest/uv environment but NOT
# guaranteed in every interpreter that reaches this module — notably the cockpit
# server spawns a PLAIN ``python3`` (no uv env) to run the chat-turn scrub, where
# the package is absent. A module-level import would make that import fatal and
# crash the append ("chat turn append failed"). So the import is optional: when
# ``detect_secrets`` is unavailable, the outbound-scrub union DEGRADES to the
# in-house catalogue ALONE (``find_secrets`` == ``find_catalogue_secrets``),
# which still redacts the real provider key shapes. The scrub must never crash on
# the missing optional enhancer. When ``detect_secrets`` IS present, behaviour is
# byte-for-byte unchanged (no regression to the shipped portable-context union).
try:
    from detect_secrets.core.scan import get_plugins
    from detect_secrets.settings import default_settings

    _DETECT_SECRETS_AVAILABLE = True
except ImportError:  # pragma: no cover — exercised via a meta-path block in tests
    get_plugins = None  # type: ignore[assignment]
    default_settings = None  # type: ignore[assignment]
    _DETECT_SECRETS_AVAILABLE = False

# ─── Public type ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class SecretHit:
    """A single located secret. Pure value object — immutable.

    ``value`` is the exact matched substring; ``start``/``end`` are character
    offsets into the scanned ``text`` such that ``text[start:end] == value``.
    """
    category: str   # "env-secret" | "jwt" | "slack" | "long-token" | "openai-key" | "private-ip"
    value: str
    start: int
    end: int


# ─── Regex catalogue (lifted verbatim from _anonymiser — single source) ───────
#
# These patterns are the canonical secret detectors. ``_anonymiser`` imports
# them back from here (one catalogue, two policies). The inline comments record
# the hardening lessons (#39/#40/#42) that shaped each pattern; do not loosen
# without re-running the characterisation + anonymiser suites.

# Env-var-style secret assignments (e.g. STRIPE_SECRET_KEY=sk_live_...,
# DB_PASSWORD: "..."). Captures the value irrespective of quoting style.
_ENV_SECRET_ASSIGNMENT = re.compile(
    r"""
    (?P<name>\b[A-Z][A-Z0-9_]*                 # an env-var-shaped name...
        (?:KEY|SECRET|TOKEN|PASSWORD|PASSWD|API_?KEY)\b)
    \s*[:=]\s*                                  # ... assignment glue ...
    (?P<value>
        " [^"\n]+ "                             # ... a quoted value ...
        | ' [^'\n]+ '
        | [^\s'"]+                              # ... or a bareword
    )
    """,
    re.VERBOSE,
)

# JWT — full ``header.payload.signature`` shape.
_JWT = re.compile(
    r"\beyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\b"
)

# Slack tokens — distinct shape (#42): at least three hyphen-separated numeric
# blocks then a 20+ alphanumeric tail. Casual prose like
# ``xoxp-token-style-identifiers`` lacks the numeric blocks and does not match.
_SLACK_TOKEN = re.compile(
    r"\b(?:xox[abprs])-[0-9]+-[0-9]+-[0-9]+-[A-Za-z0-9]{20,}\b"
)

# Bare opaque tokens — long opaque-looking strings (≥ 20 chars after a known
# provider prefix). Prefix-anchored to avoid false positives on commit SHAs and
# ordinary identifiers. Suffix excludes ``-`` (#42).
_LONG_TOKEN = re.compile(
    r"""
    \b
    (?:sk_live_|sk_test_|ghp_|gho_|ghr_|gha_|ghs_|github_pat_|pat_|
       AKIA|AIza|ya29\.|nrn_|
       npm_|pypi-)
    [A-Za-z0-9_]{20,}                            # high-entropy suffix, no hyphens
    \b
    """,
    re.VERBOSE,
)

# OpenAI API keys (#WP-010 — verified blind spot GAP 3). The modern project-
# scoped form is hyphenated (``sk-proj-…``) and the legacy form is ``sk-`` + a
# long alphanumeric tail; BOTH use a hyphen after the ``sk`` token, so the
# underscore-anchored ``_LONG_TOKEN`` above (``sk_live_``/``sk_test_`` + a
# hyphen-excluding suffix) never matches them. A dedicated pattern is needed.
#
# Two alternatives, each ``\b``-anchored and length-floored to keep ordinary
# ``sk-``-prefixed prose (``sk-arund``, ``ask-me``, ``sk-1``, ``risk-averse``)
# and SHA/ULID/UUID shapes clean:
#   - project-scoped: the ``sk-proj-`` infix is the discriminator; the tail is
#     base62 plus ``-``/``_`` (the chars OpenAI uses), ≥20 long.
#   - legacy: ``sk-`` + ≥40 alphanumeric (real legacy keys are ``sk-`` + 48);
#     the high length floor + the leading ``sk-`` anchor exclude prose and bare
#     hex/Crockford identifiers, which are never ``sk-``-prefixed.
_OPENAI_KEY = re.compile(
    r"""
    \b
    (?:
        sk-proj-[A-Za-z0-9_-]{20,}      # modern project-scoped key (hyphenated)
      | sk-[A-Za-z0-9]{40,}             # legacy key (sk- + long alnum tail)
    )
    \b
    """,
    re.VERBOSE,
)

# IP addresses (v4 dotted-quad + v6 compact/full). The regex over-matches on
# purpose (catches version-string-shaped quads); ``ipaddress`` stdlib decides
# whether a candidate is a *private/loopback/link-local* secret (#40).
_IPV4 = r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b"
_IPV6 = (r"\b(?:[0-9a-fA-F]{1,4}:){2,7}[0-9a-fA-F]{1,4}\b"
         r"|::1\b"
         r"|\bfe80::[0-9a-fA-F:]+\b"
         r"|\bfc[0-9a-fA-F]{2}:[0-9a-fA-F:]+\b")
_IP_ADDRESS = re.compile(rf"(?:{_IPV4})|(?:{_IPV6})")


# The ordered catalogue of (category, compiled regex) the plain regex passes
# scan. ``env-secret`` records the *value* as the secret while spanning the
# whole assignment; the others record the whole match. The private-IP pass is
# handled separately because its membership test needs the ``ipaddress`` stdlib.
_REGEX_CATALOGUE: list[tuple[str, re.Pattern[str]]] = [
    ("env-secret", _ENV_SECRET_ASSIGNMENT),
    ("jwt", _JWT),
    ("slack", _SLACK_TOKEN),
    ("long-token", _LONG_TOKEN),
    ("openai-key", _OPENAI_KEY),
]


def _is_private_ip(candidate: str) -> bool:
    """True iff ``candidate`` parses as a private / loopback / link-local IP.

    Uses the ``ipaddress`` stdlib — ``is_private``, ``is_loopback``,
    ``is_link_local`` encode RFC 1918 (v4 private), 4193 (v6 ULA), 3927 (v4
    link-local), 4291 (v6 link-local) plus loopback. A regex over-match that
    is not a real IP, or that is globally routable, is NOT a secret (#40)."""
    try:
        addr = ipaddress.ip_address(candidate)
    except ValueError:
        return False
    return addr.is_private or addr.is_loopback or addr.is_link_local


# ─── Catalogue layer (supplementary) ──────────────────────────────────────────


def find_catalogue_secrets(text: str) -> list[SecretHit]:
    """Scan ``text`` with the in-house catalogue, left-to-right.

    Pure: same input → same output, no mutation, no I/O. This is the
    **supplementary** layer of the outbound-scrub union AND the sole detector
    the redact consumers reach (indirectly, via the raw patterns). Overlapping
    hits from different catalogue entries are each reported — the catalogue does
    not de-duplicate across categories; consumers apply their own precedence
    (``_anonymiser`` runs its passes in a fixed precision order; the L1 proxy
    refuses on *any* hit so order is moot).
    """
    if not text:
        return []

    hits: list[SecretHit] = []

    # The plain regex passes each report the whole match as the secret. For
    # ``env-secret`` that span covers the full ``NAME=value`` assignment, so the
    # redact consumer can rebuild ``NAME=<secret>`` and the refuse consumer sees
    # the assignment; for the others it is the bare token.
    for category, pattern in _REGEX_CATALOGUE:
        for match in pattern.finditer(text):
            hits.append(SecretHit(
                category=category,
                value=match.group(0),
                start=match.start(),
                end=match.end(),
            ))

    # Private-IP pass: regex over-matches, the stdlib classifier decides.
    for match in _IP_ADDRESS.finditer(text):
        if _is_private_ip(match.group(0)):
            hits.append(SecretHit(
                category="private-ip",
                value=match.group(0),
                start=match.start(),
                end=match.end(),
            ))

    hits.sort(key=lambda h: (h.start, h.end))
    return hits


# ─── detect-secrets layer (primary) ───────────────────────────────────────────

# Build detect-secrets' default plugin set ONCE and cache it. The plugins are
# stateless analyzers (each call to ``analyze_line`` is pure over its input), so
# the instances are safe to reuse across calls — and rebuilding the registry per
# request part (the proxy scans method + url + every header + body) is wasted
# work in the scrub-before-DNS path. Lazily initialised so importing the module
# is cheap and the detect-secrets settings context is entered exactly once.
_DETECT_SECRETS_PLUGINS: tuple = ()


def _detect_secrets_plugins() -> tuple:
    """Return the cached detect-secrets plugin instances, building them once.

    Returns an empty tuple when ``detect_secrets`` is unavailable (the optional
    dependency is absent — e.g. the cockpit plain-python3 env), so the
    outbound-scrub union degrades gracefully to the in-house catalogue alone."""
    if not _DETECT_SECRETS_AVAILABLE:
        return ()
    global _DETECT_SECRETS_PLUGINS
    if not _DETECT_SECRETS_PLUGINS:
        with default_settings():
            _DETECT_SECRETS_PLUGINS = tuple(get_plugins())
    return _DETECT_SECRETS_PLUGINS


def _find_detect_secrets(text: str) -> list[SecretHit]:
    """Scan ``text`` with detect-secrets' default plugin set (the PRIMARY
    outbound-scrub detector, WP-006 / ADR-006).

    Uses detect-secrets' programmatic plugin API in-process (no shell-out): the
    ``default_settings()`` context populates the plugin registry, ``get_plugins``
    returns the configured plugin instances, and each plugin's ``analyze_line``
    is run over the single line of ``text``. ``analyze_line`` (NOT ``scan_line``)
    is deliberate: ``scan_line`` aggressively word-splits and over-reports on
    ordinary URLs; ``analyze_line`` applies each plugin's own extraction
    (entropy plugins use a quote/assignment heuristic), which keeps benign
    URLs / bodies / prose SHAs clean while catching quoted/assigned provider
    tokens.

    The character offsets detect-secrets reports are line-relative and it does
    not expose a stable start/end for the matched substring, so we locate the
    reported ``secret_value`` within ``text`` (best-effort, ``find``); the
    offsets are advisory. The L1 proxy refuse policy uses only the category, so
    advisory offsets are sufficient. Categories are prefixed ``ds:`` to record
    detect-secrets provenance in the refusal message.
    """
    if not text or not _DETECT_SECRETS_AVAILABLE:
        # No text, or the optional detect-secrets enhancer is absent — the union
        # degrades to the catalogue alone, so this primary layer contributes
        # nothing rather than crashing on the missing dependency.
        return []

    # detect-secrets scans line-by-line; a request part may contain newlines
    # (multi-line body), so scan each line and offset back into ``text``.
    hits: list[SecretHit] = []
    line_offset = 0
    plugins = _detect_secrets_plugins()
    for line in text.splitlines(keepends=True):
        stripped = line.rstrip("\n")
        for plugin in plugins:
            for secret in plugin.analyze_line(
                filename="<outbound-request>",
                line=stripped,
                line_number=1,
            ):
                value = secret.secret_value or ""
                local = stripped.find(value) if value else -1
                start = line_offset + local if local >= 0 else line_offset
                end = start + len(value) if local >= 0 else line_offset
                hits.append(SecretHit(
                    category=f"ds:{secret.type}",
                    value=value,
                    start=start,
                    end=end,
                ))
        line_offset += len(line)

    return hits


# ─── Outbound-scrub policy (union: detect-secrets ∪ catalogue) ─────────────────


def find_secrets(text: str) -> list[SecretHit]:
    """Scan ``text`` with the OUTBOUND-SCRUB policy: the UNION of detect-secrets
    (primary) and the in-house catalogue (supplementary). (WP-006 / ADR-006.)

    This is the stable seam the L1 safe-fetch proxy calls (SC-L1.3) — the
    signature and ``SecretHit`` return are unchanged, so the proxy is an
    unchanged caller; only the *detection surface* widens. Leans fail-closed:
    any hit from EITHER detector is reported, so the proxy refuses the fetch
    before DNS. Pure apart from detect-secrets' in-process plugin scan; same
    input → same output.

    The two detectors are composed here as one named union (not entangled): the
    catalogue layer (``find_catalogue_secrets``) and the detect-secrets layer
    (``_find_detect_secrets``) each scan independently; their hits are
    concatenated and sorted by span. ``_anonymiser`` deliberately does NOT call
    this — it stays catalogue-only (ADR-002 redact posture).
    """
    if not text:
        return []

    hits = find_catalogue_secrets(text) + _find_detect_secrets(text)
    hits.sort(key=lambda h: (h.start, h.end))
    return hits
