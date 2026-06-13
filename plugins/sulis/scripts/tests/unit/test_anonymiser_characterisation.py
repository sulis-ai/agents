"""Characterisation test for ``_anonymiser`` ahead of the secret-pattern extract.

WP-001 (REORGANISE-Abstract, ADR-002) lifts the secret-detection passes
(``_ENV_SECRET_ASSIGNMENT``, ``_JWT``, ``_SLACK_TOKEN``, ``_LONG_TOKEN`` and the
private-IP ``_replace_ip`` classification) out of ``_anonymiser`` into a shared
``_secret_patterns`` primitive — one catalogue, two policies. The extract MUST
NOT change ``_anonymiser``'s observable behaviour.

This is the Fowler characterisation net (Non-Negotiable #3 / EP-07): it pins the
*current* ``anonymise()`` output on a corpus that exercises every secret shape
the catalogue covers, plus the false-positive guards the catalogue must keep
(commit SHA, UUID). It is written + confirmed GREEN against the pre-extract
``_anonymiser``; after the extract it must still be GREEN, byte-for-byte, with
no edit to the assertions.

Secret-shaped fixtures are stored REVERSED in source (matching the convention in
``test_anonymiser.py``) so the literal secret forms — which trip GitHub push-
protection + provider key-revocation scanners — never appear in a committed byte
position. They are un-reversed at runtime via ``[::-1]``.
"""

from __future__ import annotations

from _anonymiser import anonymise

# ─── Secret-shaped fixtures (reversed in source; un-reversed at runtime) ──────

# Stripe-style long opaque token (matches _LONG_TOKEN's sk_live_ prefix).
_STRIPE_KEY = "vutsrqponmlkj987ihg654fed321cba_evil_ks"[::-1]
# GitHub PAT (ghp_ prefix).
_GITHUB_PAT = "876543210ZyXwVuTsRqPoNmLkJiHgFeDcBa_phg"[::-1]
# JWT header.payload.signature.
_JWT_HEAD = "9NiS1zUIiOicGla_Jye"[::-1]
_JWT_BODY = "QfigxX4iOiIBUDz_Jye"[::-1]
_JWT_SIG = "98765432109876543210fedcba9876543210fedcba"[::-1]
_JWT = f"{_JWT_HEAD}.{_JWT_BODY}.{_JWT_SIG}"
# Real-shaped Slack token: xoxp- + three numeric blocks + 20+ alnum tail.
_SLACK_TOKEN = "xoxp-" + "1234567890" + "-" + "9876543210" + "-" + \
    "1122334455" + "-" + "abcdef0123456789abcdef0123456789"


def _redaction_signature(text: str) -> list[tuple[str, str, str]]:
    """A stable, position-independent signature of ``anonymise``'s redactions:
    ``(category, original, placeholder)`` for each redaction made, in order.

    Position-independent on purpose — the extract may not shift any span, but
    pinning ``(start, end)`` too would make the net brittle to incidental corpus
    edits without adding behavioural coverage. ``redacted_text`` (asserted
    separately) already pins the spans implicitly via the output string."""
    return [(r.category, r.original, r.placeholder)
            for r in anonymise(text).redactions]


# ─── env-var-named secret assignment ─────────────────────────────────────────


def test_char_env_secret_assignment_redacts_value_keeps_name():
    text = f"export STRIPE_SECRET_KEY={_STRIPE_KEY}"
    result = anonymise(text)
    assert result.redacted_text == "export STRIPE_SECRET_KEY=<secret>"
    assert ("secret", f"STRIPE_SECRET_KEY={_STRIPE_KEY}",
            "STRIPE_SECRET_KEY=<secret>") in _redaction_signature(text)


def test_char_password_assignment_redacts_value_keeps_name():
    text = 'DB_PASSWORD: "hunter2-correct-horse-battery"'
    result = anonymise(text)
    assert result.redacted_text == 'DB_PASSWORD=<secret>'


# ─── bare long opaque tokens ─────────────────────────────────────────────────


def test_char_stripe_long_token_redacted():
    text = f"the key is {_STRIPE_KEY} keep it safe"
    result = anonymise(text)
    assert result.redacted_text == "the key is <secret> keep it safe"
    assert ("secret", _STRIPE_KEY, "<secret>") in _redaction_signature(text)


def test_char_github_pat_redacted():
    text = f"token {_GITHUB_PAT} here"
    result = anonymise(text)
    assert result.redacted_text == "token <secret> here"
    assert ("secret", _GITHUB_PAT, "<secret>") in _redaction_signature(text)


# ─── JWT ─────────────────────────────────────────────────────────────────────


def test_char_jwt_redacted():
    text = f"Authorization: Bearer {_JWT}"
    result = anonymise(text)
    assert result.redacted_text == "Authorization: Bearer <secret>"
    assert ("secret", _JWT, "<secret>") in _redaction_signature(text)


# ─── Slack token ─────────────────────────────────────────────────────────────


def test_char_real_slack_token_redacted():
    text = f"slack hook uses {_SLACK_TOKEN} for auth"
    result = anonymise(text)
    assert result.redacted_text == "slack hook uses <secret> for auth"
    assert ("secret", _SLACK_TOKEN, "<secret>") in _redaction_signature(text)


def test_char_casual_xoxp_prose_preserved():
    """``xoxp-token-style-identifiers`` is prose, not a token — must survive
    (the #42 false-positive guard the catalogue must keep)."""
    text = "Slack uses xoxp-token-style-identifiers for user tokens"
    result = anonymise(text)
    assert "xoxp-token-style-identifiers" in result.redacted_text
    assert "<secret>" not in result.redacted_text


# ─── private / loopback / link-local IP scrub ────────────────────────────────


def test_char_rfc1918_ip_scrubbed():
    text = "the pod is at 10.0.0.5 internally"
    result = anonymise(text)
    assert "10.0.0.5" not in result.redacted_text
    assert "<ip>" in result.redacted_text


def test_char_loopback_ip_scrubbed():
    text = "bound to 127.0.0.1 only"
    result = anonymise(text)
    assert "127.0.0.1" not in result.redacted_text
    assert "<ip>" in result.redacted_text


def test_char_globally_routable_ip_preserved():
    """8.8.8.8 is public — the IP pass preserves it (#40). The extract must
    keep this classification (it is the ``ipaddress`` stdlib leg)."""
    text = "resolver at 8.8.8.8 responded"
    result = anonymise(text)
    assert "8.8.8.8" in result.redacted_text


# ─── false-positive guards the catalogue must keep ───────────────────────────


def test_char_commit_sha_not_a_secret():
    """A 40-hex commit SHA must NOT be redacted as a secret (the catalogue is
    prefix-anchored, not entropy-based — ADR-002's rejected-alternative)."""
    text = "see commit b2cc82565aa7f60369c356b6fa1d2f046e84c7ad for context"
    result = anonymise(text)
    assert "b2cc82565aa7f60369c356b6fa1d2f046e84c7ad" in result.redacted_text


def test_char_uuid_not_a_secret():
    text = "change id 01KTZVX7RBE22SX6DNHA4Y6Y7B referenced"
    result = anonymise(text)
    assert "01KTZVX7RBE22SX6DNHA4Y6Y7B" in result.redacted_text


# ─── mixed-corpus interaction pin ────────────────────────────────────────────


def test_char_mixed_secret_corpus_full_output_pinned():
    """One blob exercising every secret shape at once — pins the full
    ``redacted_text`` and the ordered redaction signature so the extract
    cannot reorder, drop, or alter any secret pass."""
    text = (
        f"export API_TOKEN={_STRIPE_KEY}\n"
        f"jwt={_JWT}\n"
        f"slack={_SLACK_TOKEN}\n"
        f"pat {_GITHUB_PAT}\n"
        "internal ip 192.168.1.1 and loopback 127.0.0.1\n"
        "public dns 8.8.8.8 stays\n"
    )
    result = anonymise(text)
    expected = (
        "export API_TOKEN=<secret>\n"
        "jwt=<secret>\n"
        "slack=<secret>\n"
        "pat <secret>\n"
        "internal ip <ip> and loopback <ip>\n"
        "public dns 8.8.8.8 stays\n"
    )
    assert result.redacted_text == expected
    sig = _redaction_signature(text)
    secret_originals = [orig for cat, orig, _ in sig if cat == "secret"]
    assert _STRIPE_KEY in " ".join(secret_originals)
    assert _JWT in secret_originals
    assert _SLACK_TOKEN in secret_originals
    assert _GITHUB_PAT in secret_originals
