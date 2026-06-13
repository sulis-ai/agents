"""Shared secret-pattern catalogue — one source of truth, two policies.

This module is the single, pure catalogue of known-format secret detectors,
extracted from ``_anonymiser`` (WP-001 / ADR-002). It has **no I/O and no global
state**: ``find_secrets(text) -> list[SecretHit]`` scans text and returns the
located secrets, leaving the *policy* to the caller. There are exactly two
consumers, with deliberately different policies over the same catalogue:

  - ``_anonymiser`` (the /sulis:feedback redaction path) — **redact policy**:
    replace each hit with a placeholder, preserve the env-var name for
    operational context, let the founder opt strings back in.
  - the L1 safe-fetch proxy (WP-002/003) — **refuse policy**: any hit in an
    outbound request line (method + URL + headers + body) → fail closed, refuse
    the fetch before DNS resolution (ADR-002, SC-L1.3).

One catalogue means a new secret format is added once and both consumers inherit
it (Non-Negotiable #2 — extract the shared primitive before a second copy is
written). The catalogue is **prefix-anchored / format-based, not entropy-based**:
ADR-002 rejected entropy heuristics precisely because they false-positive on
commit SHAs and ULIDs/UUIDs, which the format-based catalogue leaves alone.

A residual honest limit (recorded, not hidden — ADR-002): the catalogue is
format-based, so a novel secret shape it does not recognise can pass. For L1 the
real control is the Rule-of-Two credential exclusion (the secret is not in the
fetch path at all); this scrub is defence-in-depth on top.

Categories detected:

  - ``env-secret``  — env-var-named assignment (``*_KEY``/``*_SECRET``/
                      ``*_TOKEN``/``*_PASSWORD`` ``= value``); the value is the
                      secret, the whole assignment is the hit span.
  - ``jwt``         — ``header.payload.signature`` JWT shape.
  - ``slack``       — Slack token (``xox[abprs]-`` + ≥3 numeric blocks + tail).
  - ``long-token``  — long opaque provider token (``sk_live_``/``ghp_``/
                      ``AKIA``/``AIza``/``npm_``/… + ≥20 alnum, no hyphens).
  - ``private-ip``  — private / loopback / link-local IP (RFC 1918/4193/3927/
                      4291 + loopback), classified via the ``ipaddress`` stdlib;
                      globally-routable IPs are NOT secrets and are not returned.
"""

from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass

# ─── Public type ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class SecretHit:
    """A single located secret. Pure value object — immutable.

    ``value`` is the exact matched substring; ``start``/``end`` are character
    offsets into the scanned ``text`` such that ``text[start:end] == value``.
    """
    category: str   # "env-secret" | "jwt" | "slack" | "long-token" | "private-ip"
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


# ─── Public API ───────────────────────────────────────────────────────────────


def find_secrets(text: str) -> list[SecretHit]:
    """Scan ``text`` and return every catalogued secret, in left-to-right order.

    Pure: same input → same output, no mutation, no I/O. The caller decides the
    policy (redact vs refuse). Overlapping hits from different catalogue entries
    are each reported — the catalogue does not de-duplicate across categories;
    consumers apply their own precedence (``_anonymiser`` runs its passes in a
    fixed precision order; the L1 proxy refuses on *any* hit so order is moot).
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
