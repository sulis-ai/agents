"""Unit tests for the extracted secret-pattern catalogue (``_secret_patterns``).

WP-001 / ADR-002: ``_secret_patterns`` is the single, pure secret-detection
catalogue — one source of truth consumed by two policies: ``_anonymiser``
(redact-and-preview) and the L1 proxy (refuse-fail-closed). It exposes
``find_secrets(text) -> list[SecretHit]`` with no I/O.

These tests assert the catalogue finds every catalogued shape (env-secret, jwt,
slack, long-token, private-ip) and — critically — does NOT false-positive on a
commit SHA or a ULID/UUID (ADR-002 rejected entropy-based detection precisely
because it trips on those).

Secret-shaped fixtures are reversed in source (matching ``test_anonymiser``'s
convention) so literal secret bytes never land in a committed position.
"""

from __future__ import annotations

from _secret_patterns import SecretHit, find_secrets

# ─── fixtures (reversed in source; un-reversed at runtime) ────────────────────

_STRIPE_KEY = "vutsrqponmlkj987ihg654fed321cba_evil_ks"[::-1]
_GITHUB_PAT = "876543210ZyXwVuTsRqPoNmLkJiHgFeDcBa_phg"[::-1]
_JWT_HEAD = "9NiS1zUIiOicGla_Jye"[::-1]
_JWT_BODY = "QfigxX4iOiIBUDz_Jye"[::-1]
_JWT_SIG = "98765432109876543210fedcba9876543210fedcba"[::-1]
_JWT = f"{_JWT_HEAD}.{_JWT_BODY}.{_JWT_SIG}"
_SLACK_TOKEN = "xoxp-" + "1234567890" + "-" + "9876543210" + "-" + \
    "1122334455" + "-" + "abcdef0123456789abcdef0123456789"


def _categories(text: str) -> set[str]:
    return {hit.category for hit in find_secrets(text)}


def _values(text: str) -> list[str]:
    return [hit.value for hit in find_secrets(text)]


# ─── shape: SecretHit is a frozen value object with the pinned fields ─────────


def test_secret_hit_shape_and_span_point_into_input():
    text = f"API_KEY={_STRIPE_KEY}"
    hits = find_secrets(text)
    assert len(hits) >= 1
    hit = next(h for h in hits if h.category == "env-secret")
    assert isinstance(hit, SecretHit)
    # span points back into the original input
    assert text[hit.start:hit.end] == hit.value


def test_secret_hit_is_frozen():
    hit = find_secrets(f"API_KEY={_STRIPE_KEY}")[0]
    try:
        hit.category = "mutated"  # type: ignore[misc]
    except Exception:  # FrozenInstanceError is a subclass of Exception
        return
    raise AssertionError("SecretHit must be frozen (immutable)")


# ─── each catalogued shape is found ───────────────────────────────────────────


def test_finds_env_named_secret_assignment():
    hits = find_secrets(f"export STRIPE_SECRET_KEY={_STRIPE_KEY}")
    assert "env-secret" in {h.category for h in hits}


def test_finds_jwt():
    assert "jwt" in _categories(f"Authorization: Bearer {_JWT}")


def test_finds_slack_token():
    assert "slack" in _categories(f"hook {_SLACK_TOKEN} here")


def test_finds_long_opaque_token():
    assert "long-token" in _categories(f"the key is {_STRIPE_KEY}")


def test_finds_github_pat_as_long_token():
    assert "long-token" in _categories(f"token {_GITHUB_PAT}")


def test_finds_private_ip():
    assert "private-ip" in _categories("the pod is at 10.0.0.5 internally")


def test_finds_loopback_ip():
    assert "private-ip" in _categories("bound to 127.0.0.1 only")


# ─── no false positives on routable IP / commit SHA / ULID ────────────────────


def test_globally_routable_ip_is_not_a_secret():
    assert "private-ip" not in _categories("resolver at 8.8.8.8 responded")


def test_dotted_quad_shaped_non_ip_is_not_a_secret():
    """A version-string-shaped dotted quad (e.g. ``999.1.2.3``) matches the IPv4
    regex but is not a parseable IP — the stdlib classifier rejects it, so it is
    NOT reported (#40 regex-over-match guard)."""
    assert "private-ip" not in _categories("version 999.1.2.3 of the tool")


def test_commit_sha_is_not_a_secret():
    sha = "b2cc82565aa7f60369c356b6fa1d2f046e84c7ad"
    assert find_secrets(f"commit {sha} landed") == [] or \
        sha not in _values(f"commit {sha} landed")


def test_ulid_is_not_a_secret():
    ulid = "01KTZVX7RBE22SX6DNHA4Y6Y7B"
    assert ulid not in _values(f"change {ulid} referenced")


def test_plain_uuid_is_not_a_secret():
    uuid = "550e8400-e29b-41d4-a716-446655440000"
    assert uuid not in _values(f"row {uuid} updated")


# ─── purity: same input → same output, no mutation ───────────────────────────


def test_find_secrets_is_deterministic_and_non_mutating():
    text = f"a={_STRIPE_KEY} b={_JWT}"
    first = find_secrets(text)
    second = find_secrets(text)
    assert [(h.category, h.value, h.start, h.end) for h in first] == \
        [(h.category, h.value, h.start, h.end) for h in second]


def test_empty_text_yields_no_hits():
    assert find_secrets("") == []


def test_clean_text_yields_no_hits():
    assert find_secrets("the quick brown fox jumps over the lazy dog") == []
