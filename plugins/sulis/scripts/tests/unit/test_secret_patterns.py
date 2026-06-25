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

# OpenAI API keys (WP-010 — the verified blind spot, GAP 3). Assembled at
# runtime from parts so the contiguous provider signature never appears verbatim
# in committed source (matching the push-safe convention the store + outbound
# suites use). ``find_secrets`` detects the assembled value all the same.
#   - project-scoped modern shape: ``sk-proj-`` + a base62/-/_ tail.
#   - legacy shape: ``sk-`` + a 48-char alphanumeric tail (a real legacy key).
_OPENAI_PROJ_KEY = "sk-proj-" + "T3BlbkFJ" + "aB3dEf6hIjKlMn0pQrStUvWx" + "Yz12_3-4"
_OPENAI_LEGACY_KEY = "sk-" + "aB3dEf6hIjKlMn0pQrStUvWxYz0123456789ABCDEFGHijkl"


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


def test_finds_openai_project_key():
    """Modern project-scoped OpenAI key ``sk-proj-…`` → a hit (WP-010, GAP 3).

    Fails before the pattern is added — the verified catalogue blind spot."""
    assert _values(f"my key is {_OPENAI_PROJ_KEY} keep safe")
    assert "openai-key" in _categories(f"my key is {_OPENAI_PROJ_KEY}")


def test_finds_openai_legacy_key():
    """Legacy OpenAI key ``sk-<48 alnum>`` → a hit (WP-010, GAP 3)."""
    assert _values(f"OPENAI key {_OPENAI_LEGACY_KEY} here")
    assert "openai-key" in _categories(f"OPENAI key {_OPENAI_LEGACY_KEY}")


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


# ─── OpenAI pattern: no false positives on ordinary ``sk-`` prose (WP-010) ────


def test_ordinary_sk_prose_is_not_an_openai_key():
    """Short / wordy ``sk-``-prefixed prose is NOT an OpenAI key — the pattern
    anchors on the ``proj-`` infix or a long alphanumeric tail, not the bare
    ``sk-`` prefix (WP-010 false-positive guard)."""
    for benign in ("sk-arund", "ask-me", "sk-1", "task-manager", "risk-averse"):
        assert "openai-key" not in _categories(benign), benign


def test_commit_sha_is_not_an_openai_key():
    """A git SHA is not ``sk-``-prefixed, so the legacy OpenAI pattern (which
    requires the ``sk-`` anchor) never matches it."""
    sha = "b2cc82565aa7f60369c356b6fa1d2f046e84c7ad"
    assert "openai-key" not in _categories(f"commit {sha} landed")


def test_ulid_is_not_an_openai_key():
    ulid = "01KTZVX7RBE22SX6DNHA4Y6Y7B"
    assert "openai-key" not in _categories(f"change {ulid} referenced")


def test_uuid_is_not_an_openai_key():
    uuid = "550e8400-e29b-41d4-a716-446655440000"
    assert "openai-key" not in _categories(f"row {uuid} updated")


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


# ─── robustness: optional detect-secrets dependency (cockpit plain-python3) ────
#
# Regression (CH-G3Y4RM): the cockpit server spawns a PLAIN ``python3`` to run
# the chat-turn scrub (``_session_manager`` -> ``find_secrets``), and that
# interpreter has no ``detect_secrets`` on its path (it is a uv-locked dep, not
# installed in the bare-python3 env). The module-level ``from detect_secrets...``
# import therefore raised ``ModuleNotFoundError`` at import time, crashing the
# append ("chat turn append failed"). The fix: the detect_secrets import is
# OPTIONAL — when it is unavailable the outbound-scrub union degrades to the
# in-house catalogue ALONE (which still redacts real provider key shapes), and
# ``find_secrets`` must NEVER raise.
#
# These tests simulate the absence with a meta-path finder that blocks
# ``detect_secrets`` from importing, then reimport ``_secret_patterns`` in that
# environment — the same condition the cockpit's plain python3 hits.

import importlib  # noqa: E402
import sys  # noqa: E402

import pytest  # noqa: E402


class _BlockDetectSecrets:
    """A ``sys.meta_path`` finder that makes ``detect_secrets`` unimportable,
    reproducing the cockpit plain-python3 environment where the package is
    absent."""

    def find_spec(self, name, path=None, target=None):
        if name == "detect_secrets" or name.startswith("detect_secrets."):
            raise ModuleNotFoundError(f"No module named '{name}'")
        return None


@pytest.fixture
def _secret_patterns_without_detect_secrets():
    """Reimport ``_secret_patterns`` with ``detect_secrets`` blocked, yielding
    the freshly-imported module. Restores the real module + meta_path after."""
    blocker = _BlockDetectSecrets()
    saved_modules = {
        name: mod
        for name, mod in list(sys.modules.items())
        if name == "detect_secrets"
        or name.startswith("detect_secrets.")
        or name == "_secret_patterns"
    }
    for name in saved_modules:
        del sys.modules[name]
    sys.meta_path.insert(0, blocker)
    try:
        module = importlib.import_module("_secret_patterns")
        yield module
    finally:
        sys.meta_path.remove(blocker)
        for name in list(sys.modules):
            if name == "_secret_patterns" or name == "detect_secrets" \
                    or name.startswith("detect_secrets."):
                del sys.modules[name]
        sys.modules.update(saved_modules)
        importlib.import_module("_secret_patterns")


def test_module_imports_when_detect_secrets_absent(
    _secret_patterns_without_detect_secrets,
):
    """``_secret_patterns`` imports cleanly even when detect_secrets is missing
    — the import must not be fatal (cockpit plain-python3 regression)."""
    module = _secret_patterns_without_detect_secrets
    assert hasattr(module, "find_secrets")


def test_find_secrets_redacts_catalogue_secret_when_detect_secrets_absent(
    _secret_patterns_without_detect_secrets,
):
    """With detect_secrets unavailable, ``find_secrets`` STILL detects a
    catalogue-shaped provider key (Stripe ``sk_live_…``) — the catalogue layer
    keeps the real key shapes redacted on its own."""
    module = _secret_patterns_without_detect_secrets
    hits = module.find_secrets(f"key = {_STRIPE_KEY}")
    assert any(_STRIPE_KEY in h.value for h in hits)


def test_find_secrets_catches_aws_secret_assignment_when_detect_secrets_absent(
    _secret_patterns_without_detect_secrets,
):
    """An AWS secret-access-key in an env-assignment (``AWS_SECRET_ACCESS_KEY=…``,
    a catalogue ``env-secret`` shape) is still caught by the catalogue alone when
    detect_secrets is absent.

    Note: a bare AWS access-key *id* (``AKIA`` + 16 chars) is detect-secrets'
    AWSKeyDetector's job and is shorter than the catalogue ``long-token`` floor,
    so it is NOT catalogue-detectable on its own — the realistic AWS shape the
    catalogue does cover is the credentials-line assignment, asserted here."""
    module = _secret_patterns_without_detect_secrets
    aws_secret = "wJalrXUtnFEMI" + "K7MDENG" + "bPxRfiCYEXAMPLEKEY"
    line = f"AWS_SECRET_ACCESS_KEY={aws_secret}"
    hits = module.find_secrets(line)
    assert any(h.category == "env-secret" and aws_secret in h.value for h in hits)


def test_find_secrets_does_not_raise_when_detect_secrets_absent(
    _secret_patterns_without_detect_secrets,
):
    """The append path must never crash on the missing optional enhancer —
    ``find_secrets`` returns cleanly (possibly empty) on benign text."""
    module = _secret_patterns_without_detect_secrets
    assert module.find_secrets("an ordinary chat turn with no secrets") == []
