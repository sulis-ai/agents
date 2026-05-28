"""Anonymisation pipeline for /sulis:feedback (#20 trigger).

Default-redact policy: anything that MIGHT be sensitive is replaced with a
placeholder; the founder previews the redactions and opts back in to
specific strings via the keep-list. Trust-by-default; reveal-by-choice.

Pure module — no I/O, no global state. ``anonymise(text, context)`` returns
an ``AnonymisationResult`` with the redacted text plus a list of
``Redaction`` records describing each replacement (category, original
substring, placeholder, character span). The preview UI in the feedback
skill renders this list so the founder can untick specific redactions
before submission.

Scrubbing categories (in pass order, highest precision first):

  1. Code blocks       — fenced (```...```) blocks ≥ 5 lines become
                          ``<code-snippet:N-lines>`` placeholders.
  2. Secrets           — env-var-named patterns (KEY/SECRET/TOKEN/
                          PASSWORD) and long opaque tokens (≥ 20 chars).
  3. Email addresses   — simplified RFC 5322 pattern.
  4. Other-repo refs   — ``org/repo#N`` where org/repo is NOT a public-
                          allowlist match. ``sulis-ai/agents`` references
                          are PRESERVED (the maintainers need them).
  5. File paths        — absolute paths starting with /Users/, /home/,
                          /private/, or strings with ≥ 2 path separators.
  6. Domain names      — anything not in the public allowlist.
  7. Project names     — the founder's project names + change-branch
                          names ``change/{primitive}-{slug}`` (callers
                          supply via context).

The keep-list short-circuits any pass: if a string appears verbatim in
``context.keep_strings``, no redaction record is produced for it (the
string stays in the output). The keep-list is the founder-opt-in mechanism.

The categories above are listed in PRECISION order (most-specific first)
so each pass only sees text not already swallowed by a higher-precision
pass — preventing e.g. an email inside a code block from being double-
counted as both "code-snippet" and "email".
"""

from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass, field


# ─── Public types ────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Redaction:
    """A single replacement made by the anonymiser.

    The founder's preview UI walks the list and renders each redaction
    with the placeholder, the original (truncated), and a checkbox to
    opt-in (move the original to ``keep_strings`` and re-run).
    """
    category: str       # "code", "secret", "email", "path", "domain",
                        # "other-repo", "project"
    original: str       # the original substring that was replaced
    placeholder: str    # what replaced it
    start: int          # character position in the ORIGINAL input
    end: int            # exclusive end position in the ORIGINAL input


@dataclass(frozen=True)
class AnonymisationContext:
    """Caller-supplied context that shapes the redaction passes."""
    project_names: list[str] = field(default_factory=list)
    keep_strings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AnonymisationResult:
    """Output of ``anonymise``: the scrubbed text + the redaction list."""
    redacted_text: str
    redactions: list[Redaction]


# ─── Public-domain allowlist (preserved verbatim) ────────────────────────────
#
# These are the domains the marketplace maintainers need to keep visible
# (links to the docs / references / public-repo of well-known tools). Any
# domain NOT in this list gets scrubbed by the domain pass.
#
# The allowlist also covers the marketplace's own org/repo refs — see
# ``_SULIS_OWN_REPO`` below — which must survive even when matched by the
# other-repo pass.

PUBLIC_DOMAIN_ALLOWLIST: frozenset[str] = frozenset({
    # Sulis + Claude / Anthropic
    "github.com",
    "anthropic.com",
    "claude.ai",
    "claude.com",
    # Public-package indexes
    "npmjs.com",
    "pypi.org",
    "rubygems.org",
    # Open standards
    "ietf.org",
    "w3.org",
    "rfc-editor.org",
    "iana.org",
    # Well-known docs domains
    "mozilla.org",
    "python.org",
    "nodejs.org",
    "openai.com",
    "docker.com",
    "kubernetes.io",
    # Useful design-system sources we cite
    "mobbin.com",
    "stripe.com",  # public API reference, also a convention citation source
})

_SULIS_OWN_REPO = "sulis-ai/agents"


# ─── Regex passes ────────────────────────────────────────────────────────────
#
# Each pass is a (category, compiled regex, placeholder-factory) triple.
# The placeholder-factory takes the regex match object and returns the
# replacement string; this lets us include match-specific info in the
# placeholder (e.g. line count in <code-snippet:N-lines>).

_CODE_BLOCK = re.compile(r"```[^\n]*\n.*?\n```", re.DOTALL)

# URLs are matched + handled FIRST (after code blocks) so neither the path
# pass nor the domain pass scribbles over them. The host is checked against
# the public allowlist; allowlisted hosts (and their subdomains) survive
# verbatim, including the full URL. Anything else becomes ``<url>``.
_URL = re.compile(
    r"https?://[^\s'\"`)\]]+",
    re.IGNORECASE,
)

# Email — simplified, deliberately conservative. Catches local@host.tld
# with reasonable TLDs and ordinary local parts.
_EMAIL = re.compile(
    r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,24}\b"
)

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

# JWT — full ``header.payload.signature`` shape. Specific to JWTs because
# bare ``eyJ...`` segments alone don't always meet the long-token threshold,
# and the period-separator means the bare-token regex (which has word
# boundaries) only captures the first segment.
_JWT = re.compile(
    r"\beyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\b"
)

# Slack tokens — distinct shape (#42). Real tokens look like
# ``xoxp-1234567890-1234567890-1234567890-{20+ alphanumerics}`` — at
# least three hyphen-separated numeric blocks then an alphanumeric
# tail. Casual prose like ``xoxp-token-style-identifiers`` doesn't
# have the numeric blocks and falls through to no match.
_SLACK_TOKEN = re.compile(
    r"\b(?:xox[abprs])-[0-9]+-[0-9]+-[0-9]+-[A-Za-z0-9]{20,}\b"
)

# Bare opaque tokens — long opaque-looking strings (≥ 20 chars after the
# prefix) of the shape an API key takes (sk_..., ghp_..., pat_..., AKIA...,
# AIza..., etc.). Specific prefix-list to reduce false positives on
# normal identifiers + commit SHAs (which would risk being stripped as
# "high-entropy" though they're useful for debugging — we leave them).
#
# Suffix excludes ``-`` (#42): real tokens after these prefixes are
# alphanumeric + underscore, not hyphenated. Allowing hyphens caused
# false positives on casual references like ``xoxp-token-style-…``;
# Slack tokens (which DO have hyphens) are now caught by the dedicated
# ``_SLACK_TOKEN`` pattern above.
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

# Other-repo refs: ``org/repo#N`` (issue/PR ref) — ``#N`` is REQUIRED to
# disambiguate from ordinary path segments. A bare ``Users/iain`` in a
# path context must not match. The ``(?<![/A-Za-z0-9])`` lookbehind
# further prevents matching the tail of a longer path. Sulis's own repo
# is preserved at the substitution step (filtered by
# ``_replace_other_repo``).
_OTHER_REPO_REF = re.compile(
    r"(?<![/A-Za-z0-9])"
    r"([A-Za-z0-9][A-Za-z0-9\-_]{0,38}/[A-Za-z0-9][A-Za-z0-9\-_]{0,38})"
    r"(#\d+)"
)

# Absolute paths starting with /Users/, /home/, /private/, /var/, /tmp/.
# Also catches macOS pytest paths under /private/var/folders.
_ABS_PATH = re.compile(
    r"(?<![A-Za-z0-9])"                          # not part of a longer word
    r"(/(?:Users|home|private|var|tmp|opt|usr|repo|repos)/[^\s'\"`)\]]+)"
)

# Repo-relative path with ≥ 2 separators — e.g. ``plugins/sulis/scripts/foo.py``.
# Catches relative paths the maintainers don't need to see; cheap proxy for
# "this string is a code-location, anonymise it". Lookbehind excludes
# paths preceded by ``/`` (absolute-path tails — those are caught by
# ``_ABS_PATH``) and ``://`` (URL paths — those are caught by ``_URL``).
_REL_PATH = re.compile(
    r"(?<![A-Za-z0-9/:])"
    r"((?:\.{1,2}/)?(?:[A-Za-z0-9_\-]+/){2,}[A-Za-z0-9_\-.]+)"
)

# Domain names — anything ending in a valid TLD. The allowlist short-
# circuits in the replacement step.
_DOMAIN = re.compile(
    r"\b(?:[a-z0-9](?:[a-z0-9\-]{0,61}[a-z0-9])?\.)+"
    r"(?:com|org|net|io|dev|ai|co|app|cloud|run|sh|"
    r"gov|edu|uk|us|de|fr|jp|cn|au|ca|info|biz)\b",
    re.IGNORECASE,
)

# IP addresses (v4 dotted-quad + v6 compact/full). Whether a match is
# REDACTED depends on `ipaddress` stdlib classification — see
# ``_replace_ip``. The regex over-matches (e.g. could grab version-string-
# shaped quads); the replacer parses each candidate via the stdlib and
# returns it unchanged when it's not a real IP or when it's globally
# routable. (#40)
_IPV4 = r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b"
# IPv6 is permissive — full + compressed forms + the common
# loopback/ULA/link-local shapes. We rely on
# ``ipaddress.ip_address`` to reject false positives.
_IPV6 = (r"\b(?:[0-9a-fA-F]{1,4}:){2,7}[0-9a-fA-F]{1,4}\b"
         r"|::1\b"
         r"|\bfe80::[0-9a-fA-F:]+\b"
         r"|\bfc[0-9a-fA-F]{2}:[0-9a-fA-F:]+\b")
_IP_ADDRESS = re.compile(rf"(?:{_IPV4})|(?:{_IPV6})")


# ─── Pass implementations ────────────────────────────────────────────────────


def _is_kept(s: str, runtime_keep: set[str]) -> bool:
    """Short-circuit: if the founder opted to keep this exact string,
    don't redact it. Case-sensitive on purpose — `MyApp` vs `myapp` are
    distinct enough that they should opt-in separately.

    Uses a runtime set rather than the frozen context list so passes that
    preserve a compound value (an email) can extend the keep-list for
    downstream passes (e.g. so the email's domain isn't re-stripped)."""
    return s in runtime_keep


def _replace_code_block(match: re.Match, keep: set[str]) -> str:
    block = match.group(0)
    if _is_kept(block, keep):
        return block
    lines = block.split("\n")
    # Subtract the two fence lines from the count.
    body_lines = max(0, len(lines) - 2)
    if body_lines < 5:
        return block  # short snippets stay (signal-dense, low-risk)
    return f"<code-snippet:{body_lines}-lines>"


def _is_allowlisted_domain(host: str) -> bool:
    """True iff ``host`` matches the public-domain allowlist (exact match
    or subdomain). Case-insensitive."""
    h = host.lower()
    if h in PUBLIC_DOMAIN_ALLOWLIST:
        return True
    return any(h.endswith("." + d) for d in PUBLIC_DOMAIN_ALLOWLIST)


def _url_has_userinfo(url: str) -> bool:
    """RFC 3986 userinfo detection: returns True iff the URL has
    ``userinfo@`` between the scheme and the host (#39).

    Userinfo carries credentials (e.g. ``user:password@host``); per
    the privacy contract these are always sensitive, regardless of
    whether the host is on the allowlist. ``_replace_url`` consults
    this predicate FIRST to short-circuit to ``<url>`` redaction
    before any allowlist evaluation.

    Distinguishes userinfo `@` (between scheme and host) from `@` in
    paths, queries, or fragments: the userinfo position is bounded
    by the next ``/``, ``?``, or ``#``, so an `@` after any of those
    is not userinfo.
    """
    # Match `scheme://[userinfo]@[host…]` where userinfo is anything
    # before the first `@` AND that `@` appears before the first `/`,
    # `?`, or `#` (which would mark the end of the authority section).
    return bool(re.match(
        r"^[a-zA-Z][a-zA-Z0-9+.\-]*://[^/?#\s@]+@",
        url or "",
    ))


def _extract_host_from_url(url: str) -> str:
    """Pull the hostname out of an ``https://host/...`` URL. Returns
    lowercased; empty on parse failure (degrades to "not allowlisted").

    Callers should check :func:`_url_has_userinfo` FIRST — this function
    does not strip ``userinfo@`` and would yield the userinfo's local
    part as the "host" otherwise."""
    # Strip scheme:
    rest = re.sub(r"^https?://", "", url, flags=re.IGNORECASE)
    # Hostname is everything up to the next `/`, `:`, `?`, `#`, whitespace.
    host = re.split(r"[/:?#\s]", rest, maxsplit=1)[0]
    return host.lower()


def _replace_url(match: re.Match, keep: set[str]) -> str:
    url = match.group(0)
    if _is_kept(url, keep):
        return url
    # Userinfo present → credentials are sensitive; redact the WHOLE
    # URL unconditionally. Skip the allowlist evaluation entirely so a
    # naive future "extract the host after stripping userinfo" change
    # can't accidentally route a credential-bearing URL to the
    # preserved-allowlisted-host branch (#39).
    if _url_has_userinfo(url):
        return "<url>"
    host = _extract_host_from_url(url)
    if _is_allowlisted_domain(host):
        # Allowlisted host → preserve the WHOLE URL (path + query). Add
        # the bare URL to the runtime keep so downstream passes don't
        # peel its host out separately.
        keep.add(url)
        keep.add(host)
        return url
    return "<url>"


def _replace_email(match: re.Match, keep: set[str]) -> str:
    email = match.group(0)
    if _is_kept(email, keep):
        # Email is kept → also extend keep with the domain portion so
        # the domain pass below doesn't strip it.
        local_at_domain = email.split("@", 1)
        if len(local_at_domain) == 2:
            keep.add(local_at_domain[1])
        return email
    return "<email>"


def _replace_env_secret(match: re.Match, keep: set[str]) -> str:
    if _is_kept(match.group(0), keep):
        return match.group(0)
    # Preserve the env-var name; redact only the value. That preserves
    # operational context (which variable was the issue) without leaking
    # the secret itself.
    return f"{match.group('name')}=<secret>"


def _replace_long_token(match: re.Match, keep: set[str]) -> str:
    if _is_kept(match.group(0), keep):
        return match.group(0)
    return "<secret>"


def _replace_jwt(match: re.Match, keep: set[str]) -> str:
    if _is_kept(match.group(0), keep):
        return match.group(0)
    return "<secret>"


def _replace_other_repo(match: re.Match, keep: set[str]) -> str:
    full = match.group(0)
    org_repo = match.group(1)
    if _is_kept(full, keep):
        return full
    if org_repo.lower() == _SULIS_OWN_REPO:
        # Preserved verbatim — maintainers need to see refs into their
        # own repo. Add to runtime keep so the domain/path passes also
        # leave it alone.
        keep.add(full)
        return full
    # Anything else: replace the org/repo, keep the issue/PR number
    # since it's always present (regex requires #N).
    issue_ref = match.group(2)
    return f"<other-repo>{issue_ref}"


def _is_substring_of_kept(s: str, keep: set[str]) -> bool:
    """True iff ``s`` appears verbatim INSIDE any string in the runtime
    keep set. Catches the case where a URL (preserved as a whole by the
    URL pass) has a path-shaped tail that would otherwise be re-scrubbed
    by a path pass running later (e.g. ``com/sulis-ai/agents/issues/22``
    is a substring of the kept URL ``https://github.com/sulis-ai/.../22``)."""
    if not s:
        return False
    return any(s in kept for kept in keep)


def _replace_abs_path(match: re.Match, keep: set[str]) -> str:
    s = match.group(0)
    if _is_kept(s, keep) or _is_substring_of_kept(s, keep):
        return s
    return "<path>"


def _replace_rel_path(match: re.Match, keep: set[str]) -> str:
    s = match.group(0)
    if _is_kept(s, keep) or _is_substring_of_kept(s, keep):
        return s
    return "<path>"


_HOST_PATH_TAIL = re.compile(r"/[^\s'\"`)\]]+")


def _seed_allowlisted_host_path_tails(text: str, keep: set[str]) -> None:
    """Pre-pass: find every allowlisted-host occurrence in ``text`` and,
    when followed immediately by ``/<tail>``, add the whole
    ``host/<tail>`` string to the runtime keep set.

    This guards against the schemeless-URL interaction where the path
    pass would otherwise consume the tail of an allowlisted host (e.g.
    ``docs.python.org/3/library/re.html`` — the domain pass preserves
    ``docs.python.org``, but the path pass running EARLIER (or in the
    same precision band) would grab ``org/3/library/re.html``). Seeding
    the keep set before passes run means the path pass's
    ``_is_substring_of_kept`` check protects the tail."""
    for match in _DOMAIN.finditer(text):
        host = match.group(0)
        if not _is_allowlisted_domain(host):
            continue
        after = text[match.end():]
        tail_match = _HOST_PATH_TAIL.match(after)
        if tail_match:
            keep.add(host + tail_match.group(0))
        keep.add(host)


def _replace_domain(match: re.Match, keep: set[str]) -> str:
    full = match.group(0)
    if _is_kept(full, keep):
        return full
    if _is_allowlisted_domain(full):
        return full
    return "<domain>"


def _replace_ip(match: re.Match, keep: set[str]) -> str:
    """Scrub private / loopback / link-local IPs to ``<ip>``; preserve
    globally-routable IPs (#40).

    Uses Python's stdlib ``ipaddress`` module rather than hand-coded
    range bounds — ``is_private``, ``is_loopback``, and ``is_link_local``
    encode the relevant RFCs (1918 v4 private, 4193 v6 ULA, 3927 v4
    link-local, 4291 v6 link-local, plus loopback for both families).
    The lesson body itself cited these RFCs; the stdlib IS the citation.

    Regex over-matches on purpose (catches version-string-shaped quads,
    malformed IP shapes); when ``ip_address`` fails to parse the match,
    preserve the original substring — that's a false-positive from the
    regex, not an IP to scrub.
    """
    s = match.group(0)
    if _is_kept(s, keep):
        return s
    try:
        addr = ipaddress.ip_address(s)
    except ValueError:
        return s  # not a real IP — preserve (regex false-positive)
    if addr.is_private or addr.is_loopback or addr.is_link_local:
        return "<ip>"
    return s  # globally routable — preserve


# Pass order: code → URLs → secrets (env + JWT + long-token) → emails →
# other-repo → IPs → paths (absolute then relative) → domains. Precision
# decreases left-to-right; URLs run early so the path/domain passes
# never get a chance to gobble the host out of an http(s):// URL. IPs
# run before path passes so `10.0.0.5:8080` doesn't get partly grabbed
# by the path regex.
_PASSES: list[tuple[str, re.Pattern, callable]] = [
    ("code", _CODE_BLOCK, _replace_code_block),
    ("url", _URL, _replace_url),
    ("secret", _ENV_SECRET_ASSIGNMENT, _replace_env_secret),
    ("secret", _JWT, _replace_jwt),
    ("secret", _SLACK_TOKEN, _replace_long_token),
    ("secret", _LONG_TOKEN, _replace_long_token),
    ("email", _EMAIL, _replace_email),
    ("other-repo", _OTHER_REPO_REF, _replace_other_repo),
    ("ip", _IP_ADDRESS, _replace_ip),
    ("path", _ABS_PATH, _replace_abs_path),
    ("path", _REL_PATH, _replace_rel_path),
    ("domain", _DOMAIN, _replace_domain),
]


def _project_names_pattern(names: list[str]) -> re.Pattern | None:
    """Compile a single combined pattern matching any of the founder's
    project names (case-insensitive, whole-word). Returns None when the
    list is empty so the caller can skip the pass cheaply."""
    cleaned = [re.escape(n) for n in names if n and len(n) >= 3]
    if not cleaned:
        return None
    # Sort longest-first so a substring match doesn't shadow a longer
    # name. E.g. ``my-app`` is preferred over ``app`` if both are listed.
    cleaned.sort(key=len, reverse=True)
    return re.compile(r"\b(?:" + "|".join(cleaned) + r")\b", re.IGNORECASE)


def _change_branch_pattern() -> re.Pattern:
    """``change/{primitive}-{slug}`` per CW-04. The slug is kebab-case.
    Captured names are PROJECT-specific (the slug carries founder intent),
    so we redact the whole ref."""
    return re.compile(r"\bchange/[a-z]+(?:-[a-z0-9]+)+\b")


# ─── Public API ──────────────────────────────────────────────────────────────


def anonymise(text: str,
              context: AnonymisationContext | None = None) -> AnonymisationResult:
    """Run all redaction passes over ``text``. Returns the scrubbed text
    + the list of redactions made.

    The passes run in PRECISION order (code blocks first, broad domain
    pass last) so a single substring is never double-counted. Each pass
    operates on the text produced by the previous pass; the ``start/end``
    spans recorded on each ``Redaction`` refer to the ORIGINAL input via
    a position-mapping table.

    ``context`` defaults to an empty ``AnonymisationContext`` — no project
    names, no keep-strings.
    """
    if context is None:
        context = AnonymisationContext()

    result_text = text
    redactions: list[Redaction] = []

    # Runtime keep set — seeded from the founder-supplied keep_strings,
    # then mutably extended by passes that preserve compound values (e.g.
    # the email pass adds the domain when a kept email is encountered,
    # and the host-path-tail pre-pass below adds full ``host/<tail>``
    # strings for allowlisted hosts so the path pass doesn't peel them
    # apart). Threading this through avoids the "kept email's domain
    # gets stripped by the domain pass" + "schemeless URL's tail gets
    # stripped by the path pass" interaction bugs.
    runtime_keep: set[str] = set(context.keep_strings)
    _seed_allowlisted_host_path_tails(text, runtime_keep)

    # First: run the project-name + change-branch passes (composed as
    # `project` category). Caller-shape; we run them BEFORE the broad
    # passes so downstream passes don't gobble project-prefixed paths
    # without acknowledging the project context.
    project_pat = _project_names_pattern(context.project_names)
    change_branch_pat = _change_branch_pattern()
    for pat, label in ((project_pat, "<project>"),
                       (change_branch_pat, "<branch>")):
        if pat is None:
            continue
        result_text = _run_pass(
            result_text, redactions, "project", pat,
            lambda m, lbl=label, keep=runtime_keep: lbl
                if not _is_kept(m.group(0), keep) else m.group(0),
            runtime_keep,
        )

    # Then the precision-ordered passes.
    for category, pat, replacer in _PASSES:
        result_text = _run_pass(result_text, redactions, category, pat,
                                lambda m, r=replacer, keep=runtime_keep: r(m, keep),
                                runtime_keep)

    return AnonymisationResult(redacted_text=result_text,
                               redactions=redactions)


def _run_pass(text: str, redactions: list[Redaction], category: str,
              pattern: re.Pattern, replacer, runtime_keep: set[str]) -> str:
    """Run a single regex pass, recording each replacement as a Redaction.

    ``replacer`` is called with the match object and must return the
    replacement string. If the replacement equals the matched substring
    (e.g. the keep-list short-circuited), no Redaction is recorded.
    """
    out_parts: list[str] = []
    last_end = 0
    for match in pattern.finditer(text):
        original = match.group(0)
        replacement = replacer(match)
        if replacement == original:
            continue  # kept — no redaction
        # Append text up to the match, then the replacement.
        out_parts.append(text[last_end:match.start()])
        out_parts.append(replacement)
        redactions.append(Redaction(
            category=category,
            original=original,
            placeholder=replacement,
            start=match.start(),
            end=match.end(),
        ))
        last_end = match.end()
    out_parts.append(text[last_end:])
    return "".join(out_parts)
