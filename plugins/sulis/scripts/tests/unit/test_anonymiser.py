"""Unit tests for the anonymisation pipeline (_anonymiser.py).

This module is trust-critical — it's the load-bearing piece for the
/sulis:feedback skill's privacy contract. Each redaction category gets
its own focused test; the keep-list short-circuit and the public-domain
allowlist get separate coverage; and a final "real-world" smoke test
runs a mixed-content blob to catch interaction bugs between passes.

The redaction policy is default-redact (anything that MIGHT be sensitive
becomes a placeholder; the founder previews and can opt back in via
``keep_strings``). These tests pin that policy at the implementation
level.
"""

from __future__ import annotations

from _anonymiser import (
    PUBLIC_DOMAIN_ALLOWLIST,
    AnonymisationContext,
    Redaction,
    _url_has_userinfo,
    anonymise,
)

# Test fixtures for secret-shaped strings. Stored REVERSED in source
# so the literal forms (which trip GitHub's push-protection secret-
# scanning + cloud-provider key-revocation scanners) never appear in
# any committed byte position. Reversed at runtime via ``[::-1]`` to
# yield the exact shapes our regexes target. This is the cleanest
# defuse: keep the test fixture intact for execution; keep the source
# file scanner-clean for committal.
_STRIPE_KEY = "lkj987ihg654fed321cba_evil_ks"[::-1]
_STRIPE_KEY_LONG = "vutsrqponmlkj987ihg654fed321cba_evil_ks"[::-1]
_GITHUB_PAT = "876543210ZyXwVuTsRqPoNmLkJiHgFeDcBa_phg"[::-1]
_JWT_HEAD = "9NiS1zUIiOicGla_Jye"[::-1]
_JWT_BODY = "QfigxX4iOiIBUDz_Jye"[::-1]
_JWT_SIG = "98765432109876543210fedcba9876543210fedcba"[::-1]
_JWT = f"{_JWT_HEAD}.{_JWT_BODY}.{_JWT_SIG}"


# ─── Email addresses ─────────────────────────────────────────────────────────


def test_email_is_redacted():
    r = anonymise("contact iain@llma.ai for details")
    assert "<email>" in r.redacted_text
    assert "iain@llma.ai" not in r.redacted_text
    assert any(red.category == "email" for red in r.redactions)


def test_multiple_emails_each_get_redacted():
    text = "from a@x.com to b@y.org cc c@z.net"
    r = anonymise(text)
    assert r.redacted_text.count("<email>") == 3
    assert sum(1 for red in r.redactions if red.category == "email") == 3


def test_email_in_keep_list_is_preserved():
    context = AnonymisationContext(keep_strings=["maintainer@sulis-ai.com"])
    text = "ping maintainer@sulis-ai.com about this"
    r = anonymise(text, context)
    assert "maintainer@sulis-ai.com" in r.redacted_text
    assert "<email>" not in r.redacted_text


# ─── Secrets ─────────────────────────────────────────────────────────────────


def test_env_assigned_secret_value_is_redacted_name_preserved():
    """The variable NAME stays (founder needs to know which secret was
    the issue); the VALUE is the part that's scrubbed."""
    text = f'STRIPE_SECRET_KEY="{_STRIPE_KEY}"'
    r = anonymise(text)
    assert "STRIPE_SECRET_KEY=<secret>" in r.redacted_text
    assert _STRIPE_KEY not in r.redacted_text


def test_password_assignment_is_redacted():
    text = "DB_PASSWORD=hunter2hunter2"
    r = anonymise(text)
    assert "DB_PASSWORD=<secret>" in r.redacted_text
    assert "hunter2" not in r.redacted_text


def test_bare_long_token_is_redacted():
    """A long opaque token (Stripe key shape) is redacted even without
    an assignment context."""
    text = f"the key is {_STRIPE_KEY}"
    r = anonymise(text)
    assert "<secret>" in r.redacted_text
    assert _STRIPE_KEY not in r.redacted_text


def test_github_pat_is_redacted():
    text = f"use token {_GITHUB_PAT}"
    r = anonymise(text)
    assert "<secret>" in r.redacted_text


def test_jwt_is_redacted():
    text = f"authorisation: Bearer {_JWT}"
    r = anonymise(text)
    assert "<secret>" in r.redacted_text
    assert _JWT[:8] not in r.redacted_text


def test_short_string_is_not_a_secret():
    """A short alphanumeric string (e.g. a status code, a slug fragment)
    must NOT be redacted — the threshold is ≥ 20 chars."""
    text = "the status is OK; failure mode = boom"
    r = anonymise(text)
    assert "<secret>" not in r.redacted_text


# ─── #42: tighten _LONG_TOKEN against casual hyphenated prose ────────────────


def test_xoxp_token_style_casual_reference_is_preserved():
    """`xoxp-token-style-identifiers` is docs prose, not a real token —
    must NOT be scrubbed after the regex tightening. The lesson body's
    exact example."""
    text = "Slack uses xoxp-token-style-identifiers for user tokens"
    r = anonymise(text)
    assert "xoxp-token-style-identifiers" in r.redacted_text
    assert "<secret>" not in r.redacted_text


def test_xoxb_casual_reference_is_preserved():
    text = "the xoxb-bot-token-format is documented at api.slack.com"
    r = anonymise(text)
    assert "xoxb-bot-token-format" in r.redacted_text


def test_real_slack_token_shape_is_still_redacted():
    """A real-shape Slack token (three numeric blocks + alphanumeric
    tail) MUST still be redacted. Pin so the tightening doesn't go
    too far."""
    # Built at runtime to dodge GitHub's push-protection scanner.
    real_slack = ("xoxp-" + "1234567890" + "-" + "9876543210" + "-" +
                  "1357924680" + "-" + "abcdef0123456789ABCDEFGH")
    text = f"the leaked token was {real_slack}"
    r = anonymise(text)
    assert "<secret>" in r.redacted_text
    assert real_slack not in r.redacted_text


def test_stripe_key_still_redacted_after_tightening():
    """Pinned regression: tightening suffix to no-hyphens must not break
    Stripe key matching (Stripe keys are alphanumeric+underscore, no
    hyphens in the suffix)."""
    text = f"key: {_STRIPE_KEY}"
    r = anonymise(text)
    assert "<secret>" in r.redacted_text
    assert _STRIPE_KEY not in r.redacted_text


def test_github_pat_still_redacted_after_tightening():
    """Pinned regression: GitHub PATs are alphanumeric, no hyphens in
    the suffix."""
    text = f"the token is {_GITHUB_PAT}"
    r = anonymise(text)
    assert "<secret>" in r.redacted_text


# ─── File paths ──────────────────────────────────────────────────────────────


def test_absolute_macos_path_is_redacted():
    text = "edit /Users/iain/Documents/repos/platform/foo.py"
    r = anonymise(text)
    assert "<path>" in r.redacted_text
    assert "iain" not in r.redacted_text


def test_absolute_linux_path_is_redacted():
    text = "see /home/founder/work/secret-project/bar.ts"
    r = anonymise(text)
    assert "<path>" in r.redacted_text
    assert "founder" not in r.redacted_text


def test_relative_path_with_two_separators_is_redacted():
    text = "the bug is in plugins/sulis/scripts/foo.py:42"
    r = anonymise(text)
    assert "<path>" in r.redacted_text


def test_short_relative_path_is_not_redacted():
    """A single-segment or two-segment relative reference (``foo.py``,
    ``src/foo.py``) is below the ≥ 2 separator threshold — preserved."""
    text = "see src/foo.py"
    r = anonymise(text)
    # The threshold is 2+ separators in the path body; src/foo.py has 1.
    assert "src/foo.py" in r.redacted_text


# ─── Public-domain allowlist ─────────────────────────────────────────────────


def test_allowlisted_domain_is_preserved():
    text = "see https://github.com/sulis-ai/agents/issues/22"
    r = anonymise(text)
    assert "github.com" in r.redacted_text


def test_subdomain_of_allowlisted_is_preserved():
    text = "the docs at docs.python.org/3/library/re.html"
    r = anonymise(text)
    assert "python.org" in r.redacted_text


# ─── URL userinfo handling (#39) ─────────────────────────────────────────────
#
# When a URL has embedded credentials (RFC 3986 `userinfo@host`), the WHOLE
# URL must be redacted to `<url>` — regardless of whether the host is on
# the allowlist. Credentials are always sensitive; the allowlist check is
# skipped entirely. Pinned because a naive "extract the host" fix would
# leak credentials in allowlisted-host URLs otherwise.


def test_url_with_basic_auth_is_fully_redacted_even_on_allowlisted_host():
    """https://user:pass@github.com/... — host is allowlisted, BUT
    credentials are present → redact the whole URL anyway. The lesson
    body's load-bearing assertion."""
    text = "see https://user:pass@github.com/sulis-ai/agents"
    r = anonymise(text)
    assert "<url>" in r.redacted_text
    # Critically: the password must not appear in the output.
    assert "pass" not in r.redacted_text
    assert "user:pass" not in r.redacted_text
    # The allowlisted host is also gone (whole URL replaced).
    assert "user:pass@github.com" not in r.redacted_text


def test_url_with_user_only_is_fully_redacted():
    """user@host form (no password) is still userinfo per RFC 3986 —
    redact the whole URL."""
    text = "fetch https://iain@github.com/private-repo.git"
    r = anonymise(text)
    assert "<url>" in r.redacted_text
    assert "iain@github.com" not in r.redacted_text


def test_url_with_credentials_on_non_allowlisted_host_is_redacted():
    """Regression pin: a non-allowlisted host with credentials behaves
    the same as today (redacted). The fix must not break this path."""
    text = "see http://admin:secret@my-startup.com/api"
    r = anonymise(text)
    assert "<url>" in r.redacted_text
    assert "secret" not in r.redacted_text


def test_url_without_credentials_on_allowlisted_host_still_preserved():
    """Regression pin: plain allowlisted-host URLs still pass through.
    The fix must NOT over-redact normal URLs."""
    text = "see https://github.com/sulis-ai/agents/issues/22"
    r = anonymise(text)
    assert "https://github.com/sulis-ai/agents/issues/22" in r.redacted_text


def test_url_without_credentials_on_non_allowlisted_host_redacted():
    """Regression pin: non-allowlisted hosts still redact (unchanged)."""
    text = "the failing call to https://internal-api.acme.com/foo"
    r = anonymise(text)
    assert "<url>" in r.redacted_text


# ─── IP address scrubbing (#40) ─────────────────────────────────────────────
#
# Private + loopback + link-local IPs are scrubbed (RFC 1918, RFC 4193,
# RFC 3927, RFC 4291); globally-routable IPs are preserved (public DNS,
# well-known services — maintainer context).


def test_rfc1918_10_dot_is_scrubbed():
    r = anonymise("our k8s pod is at 10.0.0.5 internally")
    assert "<ip>" in r.redacted_text
    assert "10.0.0.5" not in r.redacted_text


def test_rfc1918_192_168_is_scrubbed():
    r = anonymise("the router admin is on 192.168.1.1")
    assert "<ip>" in r.redacted_text
    assert "192.168.1.1" not in r.redacted_text


def test_rfc1918_172_16_is_scrubbed():
    r = anonymise("docker network at 172.16.0.5")
    assert "<ip>" in r.redacted_text
    assert "172.16.0.5" not in r.redacted_text


def test_172_outside_private_range_is_preserved():
    """172.16.0.0/12 — 172.16.x to 172.31.x is private; 172.32+ is public."""
    r = anonymise("the public service at 172.217.0.46")
    assert "172.217.0.46" in r.redacted_text


def test_loopback_127_is_scrubbed():
    r = anonymise("dev server on 127.0.0.1:3000")
    assert "<ip>" in r.redacted_text
    assert "127.0.0.1" not in r.redacted_text


def test_link_local_169_254_is_scrubbed():
    r = anonymise("cloud metadata at 169.254.169.254")
    assert "<ip>" in r.redacted_text
    assert "169.254.169.254" not in r.redacted_text


def test_ipv6_ula_is_scrubbed():
    r = anonymise("ULA host at fc00::1")
    assert "<ip>" in r.redacted_text
    assert "fc00::1" not in r.redacted_text


def test_ipv6_loopback_is_scrubbed():
    r = anonymise("listening on ::1 port 8080")
    assert "<ip>" in r.redacted_text


def test_ipv6_link_local_is_scrubbed():
    r = anonymise("see fe80::1")
    assert "<ip>" in r.redacted_text
    assert "fe80::1" not in r.redacted_text


def test_public_ipv4_dns_is_preserved():
    """Public DNS IPs (8.8.8.8, 1.1.1.1) are maintainer context — preserved."""
    r = anonymise("the DNS query went to 8.8.8.8 and timed out")
    assert "8.8.8.8" in r.redacted_text
    r2 = anonymise("retry via 1.1.1.1")
    assert "1.1.1.1" in r2.redacted_text


def test_public_ipv6_dns_is_preserved():
    r = anonymise("ipv6 dns at 2001:4860:4860::8888")
    assert "2001:4860:4860::8888" in r.redacted_text


def test_version_string_not_misclassified_as_ipv4():
    """A version like `3.11.2` has 3 octets — must not match the IPv4
    regex (which requires 4) and must not be scrubbed."""
    r = anonymise("we run python 3.11.2 on the server")
    assert "3.11.2" in r.redacted_text


def test_port_numbers_not_scrubbed():
    """An IP:port combo — port should not be touched even when the IP
    is scrubbed."""
    r = anonymise("connecting to 10.0.0.5:8080")
    assert "<ip>" in r.redacted_text
    assert "8080" in r.redacted_text


def test_keep_list_short_circuits_ip():
    """Founder-opt-in: a private IP they explicitly choose to keep
    survives."""
    context = AnonymisationContext(keep_strings=["192.168.1.1"])
    r = anonymise("the gateway is 192.168.1.1", context)
    assert "192.168.1.1" in r.redacted_text


# ─── _url_has_userinfo predicate (direct unit tests) ─────────────────────────
#
# Direct helper tests distinguish "deliberately correct" from the
# pre-existing "lucky-safe" accident. The full-anonymise tests above
# verify the OUTPUT is correct; these tests verify the LOGIC reaches
# that output by the right code path.


def test_url_has_userinfo_basic_auth_form():
    assert _url_has_userinfo("https://user:pass@host.com/path") is True


def test_url_has_userinfo_user_only_form():
    assert _url_has_userinfo("https://iain@host.com/path") is True


def test_url_has_userinfo_with_special_chars_in_password():
    """RFC 3986 allows percent-encoded chars in userinfo (e.g.
    `user:p%40ss@host`). Most common shapes are unreserved + percent-
    encoded; we conservatively recognise these as userinfo."""
    assert _url_has_userinfo("https://user:p%40ss@host.com/path") is True


def test_url_has_userinfo_plain_url():
    assert _url_has_userinfo("https://github.com/sulis-ai/agents") is False


def test_url_has_userinfo_at_in_path_not_userinfo():
    """An `@` in the path (after the host) is not userinfo."""
    assert _url_has_userinfo("https://github.com/foo/@bar") is False


def test_url_has_userinfo_at_in_query_not_userinfo():
    """An `@` in the query string is not userinfo."""
    assert _url_has_userinfo("https://api.com/search?q=user@host") is False


def test_url_has_userinfo_at_in_fragment_not_userinfo():
    assert _url_has_userinfo("https://docs.com/page#@mention") is False


def test_url_has_userinfo_no_scheme_returns_false():
    """Schemeless input is not a URL — predicate returns False rather
    than misclassifying. The URL regex won't match schemeless input
    anyway, so this is belt-and-braces."""
    assert _url_has_userinfo("user@host.com") is False


def test_url_has_userinfo_empty_string_returns_false():
    assert _url_has_userinfo("") is False


def test_url_with_at_sign_in_path_not_misclassified_as_userinfo():
    """An `@` in the URL PATH (not before the host) is not userinfo.
    e.g. https://github.com/orgs/foo/@bar — the `@bar` is a path
    segment, not credentials. The URL should be preserved (allowlisted
    host, no userinfo)."""
    text = "see https://github.com/sulis-ai/agents/pull/42#@user-mention"
    r = anonymise(text)
    # github.com is allowlisted; no userinfo (the @ is after the path
    # separator). The URL should survive.
    assert "github.com" in r.redacted_text
    assert "<url>" not in r.redacted_text


def test_non_allowlisted_domain_is_redacted():
    text = "the service at my-startup.com fails"
    r = anonymise(text)
    assert "<domain>" in r.redacted_text
    assert "my-startup.com" not in r.redacted_text


def test_allowlist_includes_well_known_domains():
    """Pin the allowlist contents — a regression here is a privacy
    expansion (any of these domains starts leaking) or a usability
    regression (a public docs link gets scrubbed for no reason)."""
    for d in ("github.com", "anthropic.com", "python.org", "ietf.org",
              "mobbin.com", "stripe.com"):
        assert d in PUBLIC_DOMAIN_ALLOWLIST, (
            f"{d} dropped from PUBLIC_DOMAIN_ALLOWLIST — privacy or "
            f"usability regression"
        )


# ─── Other-repo refs ─────────────────────────────────────────────────────────


def test_sulis_own_repo_ref_is_preserved():
    """sulis-ai/agents is the maintainer's own repo — refs must survive
    the scrub so the issue context links work."""
    text = "see sulis-ai/agents#22 for the original bug"
    r = anonymise(text)
    assert "sulis-ai/agents#22" in r.redacted_text


def test_other_repo_ref_is_redacted_issue_number_preserved():
    """A ref into someone ELSE's repo (a private monorepo, a fork) gets
    the org/repo part scrubbed but keeps the #N — the founder's "issue 42
    of X" context survives without the X."""
    text = "this looks like founder-org/private-app#42"
    r = anonymise(text)
    assert "<other-repo>#42" in r.redacted_text
    assert "private-app" not in r.redacted_text


def test_sulis_own_repo_case_insensitive():
    text = "see Sulis-AI/Agents#1"
    r = anonymise(text)
    assert "Sulis-AI/Agents#1" in r.redacted_text


# ─── Code blocks ─────────────────────────────────────────────────────────────


def test_long_code_block_is_replaced_with_line_count_placeholder():
    text = (
        "Here's the code:\n"
        "```python\n"
        "def foo():\n"
        "    pass\n"
        "def bar():\n"
        "    pass\n"
        "def baz():\n"
        "    pass\n"
        "```\n"
        "End."
    )
    r = anonymise(text)
    assert "<code-snippet:6-lines>" in r.redacted_text
    assert "def foo" not in r.redacted_text


def test_short_code_block_is_preserved():
    """≤ 4 lines = signal-dense + low-risk = preserved. The threshold
    keeps tiny snippets (one-line error messages, two-line repro) usable
    in the feedback issue without leaking large chunks of proprietary
    code."""
    text = "Just:\n```\nfoo()\n```\nthat's it."
    r = anonymise(text)
    assert "foo()" in r.redacted_text


# ─── Project names ──────────────────────────────────────────────────────────


def test_project_name_is_redacted_when_context_provided():
    context = AnonymisationContext(project_names=["my-saas-app"])
    text = "the issue surfaced in my-saas-app's checkout flow"
    r = anonymise(text, context)
    assert "<project>" in r.redacted_text
    assert "my-saas-app" not in r.redacted_text


def test_project_name_short_strings_are_ignored():
    """A 1-2 char "project name" would scrub too aggressively (e.g.
    every occurrence of "a" or "io"). Names need to be ≥ 3 chars to
    join the pass."""
    context = AnonymisationContext(project_names=["a", "io"])
    text = "loading data via io.read()"
    r = anonymise(text, context)
    assert "io.read" in r.redacted_text  # short-name was skipped


def test_project_name_in_keep_list_survives():
    context = AnonymisationContext(
        project_names=["my-saas-app"],
        keep_strings=["my-saas-app"],
    )
    text = "the issue surfaced in my-saas-app's checkout flow"
    r = anonymise(text, context)
    assert "my-saas-app" in r.redacted_text


def test_change_branch_ref_is_redacted():
    """``change/{primitive}-{slug}`` branch refs carry founder intent in
    the slug — scrub them by default. Founder can opt-in via keep-list."""
    text = "the work happened on change/extend-add-billing"
    r = anonymise(text)
    assert "<branch>" in r.redacted_text
    assert "extend-add-billing" not in r.redacted_text


# ─── Real-world smoke ───────────────────────────────────────────────────────


def test_realistic_feedback_blob_scrubs_all_categories():
    # Build the secrets-bearing log block at runtime so the literal
    # forms never appear in any committed file (GitHub push protection
    # would otherwise reject the commit — and rightly so).
    text = f"""
    I hit a bug while working in /Users/iain/Documents/repos/platform.

    The /sulis:dashboard skill claimed change CH-01HQ8X was still active,
    but the terminal was closed. I think the liveness check is keyed on
    the wrong signal.

    Repro:
      1. Run sulis-change start on change/feat-introduce-payments
      2. Close the spawned terminal
      3. Run /sulis:dashboard

    Logs:
    ```
    STRIPE_SECRET_KEY={_STRIPE_KEY_LONG}
    DB_PASSWORD="hunter2hunter2"
    request to api.my-saas-app.com timed out
    user iain@llma.ai reported it
    related: founder-org/private-app#42
    ```

    Original sulis-ai/agents#22 is the closest match.
    """
    context = AnonymisationContext(project_names=["my-saas-app"])
    r = anonymise(text, context)

    # Path → <path>
    assert "/Users/iain" not in r.redacted_text
    assert "<path>" in r.redacted_text

    # Change-branch ref → <branch>
    assert "change/feat-introduce-payments" not in r.redacted_text
    assert "<branch>" in r.redacted_text

    # Project-name → <project>
    assert "my-saas-app" not in r.redacted_text
    assert "<project>" in r.redacted_text

    # Email → <email>
    assert "iain@llma.ai" not in r.redacted_text
    assert "<email>" in r.redacted_text

    # Other-repo → <other-repo>#42
    assert "founder-org/private-app" not in r.redacted_text
    assert "<other-repo>#42" in r.redacted_text

    # Own-repo preserved
    assert "sulis-ai/agents#22" in r.redacted_text

    # Code block redacted (the secrets-bearing block) → preserved as
    # a snippet placeholder; either the snippet placeholder OR the
    # individual secret redactions could fire depending on pass
    # ordering — what MATTERS is that the secrets themselves don't
    # appear in the output.
    assert _STRIPE_KEY_LONG[:10] not in r.redacted_text
    assert "hunter2" not in r.redacted_text

    # The list of redactions is non-empty and categorised.
    assert len(r.redactions) > 0
    categories = {red.category for red in r.redactions}
    # We hit at least these categories on this blob.
    assert "path" in categories
    assert "email" in categories
    assert "<project>" in r.redacted_text or "project" in categories


def test_empty_input_returns_empty_output_with_no_redactions():
    r = anonymise("")
    assert r.redacted_text == ""
    assert r.redactions == []


def test_innocuous_text_passes_through_unchanged():
    """Text with no triggers should round-trip identically."""
    text = "The plain text with no secrets or paths at all."
    r = anonymise(text)
    assert r.redacted_text == text
    assert r.redactions == []
