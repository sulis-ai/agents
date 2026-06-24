"""Outbound-scrub coverage tests — detect-secrets union (WP-006 / ADR-006).

WP-006 hardens the L1 outbound secret-scrub by adopting the established
``detect-secrets`` (Yelp) as the PRIMARY detector for the OUTBOUND-SCRUB policy,
union'd with the in-house ``_secret_patterns`` catalogue (kept as the
SUPPLEMENTARY layer — it owns private-IP / env-assignment / slack / jwt /
long-token detection that detect-secrets does not cover).

The seam is unchanged: the proxy calls ``find_secrets(text) -> list[SecretHit]``
(SC-L1.3). After WP-006 that function returns the UNION. These tests prove the
union now catches provider shapes the bespoke catalogue alone missed — an
AWS access-key id, an AWS secret-access-key, a Google API key, and a generic
high-entropy quoted/assigned bearer token — while staying clean on benign
requests (plain URL, plain body) in prose context.

Fixtures are synthetic-but-detect-secrets-flaggable and push-safe: the AWS pair
uses the canonical AWS docs ``...EXAMPLE...`` literals (well-known dummies,
never live), the others are clearly-fake high-entropy strings. No live-key
literal that a real secret-scanner's push protection would reject (the WP-002
Stripe-shaped-literal push rejection is the lesson here).

ADR-006 supersedes ADR-002's entropy-rejection FOR THIS POLICY ONLY: the
outbound-scrub leans fail-closed (a false-positive costs one blocked fetch;
a false-negative leaks a secret). The anonymiser's catalogue-only, low-false-
positive redaction policy is unchanged and is asserted elsewhere
(``test_anonymiser`` + ``test_anonymiser_characterisation``).
"""

from __future__ import annotations

from _secret_patterns import SecretHit, find_secrets

# ─── Provider-shape fixtures (push-safe; validated against detect-secrets) ─────
#
# AWS access-key id: the canonical AWS-documentation example id (a well-known
# dummy, flagged by detect-secrets' AWSKeyDetector, never a live credential).
_AWS_ACCESS_KEY_ID = "AKIA" + "IOSFODNN7EXAMPLE"
# AWS secret-access-key: the canonical AWS-docs example secret (dummy).
_AWS_SECRET_ACCESS_KEY = "wJalrXUtnFEMI" + "K7MDENG" + "bPxRfiCYEXAMPLEKEY"
# Google-style API key: AIza-prefixed, fake high-entropy tail.
_GOOGLE_API_KEY = "AIza" + "SyAbcdefghijklmnopqrstuvwxyz0123456"
# Generic high-entropy bearer/opaque token: clearly fake, no provider prefix the
# in-house catalogue recognises — exactly the gap detect-secrets fills.
_GENERIC_TOKEN = "xK9pLm2QrT7vWnB4cE6gH1jD8sF3aZ5yU0iO9wQ2eR4"
# OpenAI keys (WP-010 — GAP 3 blind spot, supplied by the in-house catalogue
# layer of the union). Assembled from parts; push-safe.
_OPENAI_PROJ_KEY = "sk-proj-" + "T3BlbkFJ" + "aB3dEf6hIjKlMn0pQrStUvWx" + "Yz12_3-4"
_OPENAI_LEGACY_KEY = "sk-" + "aB3dEf6hIjKlMn0pQrStUvWxYz0123456789ABCDEFGHijkl"


def _categories(text: str) -> set[str]:
    return {hit.category for hit in find_secrets(text)}


# ─── New provider shapes are caught by the outbound-scrub union ───────────────


def test_aws_access_key_id_in_url_is_caught() -> None:
    """AWS access-key id in an outbound URL — missed by the bespoke catalogue,
    caught by detect-secrets' AWSKeyDetector via the union."""
    hits = find_secrets(f"https://example.com/x?id={_AWS_ACCESS_KEY_ID}")
    assert hits, "AWS access-key id must be detected by the outbound-scrub union"
    assert all(isinstance(h, SecretHit) for h in hits)


def test_aws_secret_access_key_in_body_is_caught() -> None:
    """AWS secret-access-key in an outbound body (assignment context)."""
    body = f'aws_secret_access_key = "{_AWS_SECRET_ACCESS_KEY}"'
    assert find_secrets(body), "AWS secret-access-key must be detected"


def test_google_api_key_in_body_is_caught() -> None:
    """Google-style API key in a quoted JSON body."""
    body = f'{{"api_key": "{_GOOGLE_API_KEY}"}}'
    assert find_secrets(body), "Google API key must be detected"


def test_generic_high_entropy_bearer_token_is_caught() -> None:
    """Generic high-entropy opaque token in a header/body value — no catalogue
    prefix, so only the detect-secrets entropy plugin catches it."""
    header_value = f'{{"authorization": "{_GENERIC_TOKEN}"}}'
    assert find_secrets(header_value), "high-entropy bearer token must be detected"


def test_openai_project_key_caught_via_union() -> None:
    """Modern ``sk-proj-…`` OpenAI key in an outbound URL — supplied by the
    in-house catalogue layer of the union (WP-010, GAP 3 blind spot)."""
    assert "openai-key" in _categories(
        f"https://example.com/x?key={_OPENAI_PROJ_KEY}"
    )


def test_openai_legacy_key_caught_via_union() -> None:
    """Legacy ``sk-<48 alnum>`` OpenAI key in an outbound body — supplied by the
    in-house catalogue layer of the union (WP-010, GAP 3 blind spot)."""
    body = f'{{"authorization": "Bearer {_OPENAI_LEGACY_KEY}"}}'
    assert "openai-key" in _categories(body)


# ─── Benign requests in prose context stay clean (no fail-open, no FP storm) ──


def test_benign_url_is_not_flagged() -> None:
    assert find_secrets("https://example.com/page?q=hello") == []


def test_benign_body_is_not_flagged() -> None:
    assert find_secrets('{"payload": "hello world"}') == []


def test_commit_sha_in_prose_is_not_flagged() -> None:
    """ADR-002's prose-context posture is preserved: a commit SHA mentioned in
    prose (not quoted/assigned as a credential) is not a secret. The union's
    detect-secrets entropy plugins use a quote/assignment heuristic, so prose
    SHAs stay clean — matching the existing catalogue suite."""
    sha = "b2cc82565aa7f60369c356b6fa1d2f046e84c7ad"
    assert find_secrets(f"commit {sha} landed") == []


# ─── The supplementary catalogue layer is still active in the union ───────────


def test_catalogue_private_ip_still_caught_via_union() -> None:
    """The in-house catalogue (supplementary layer) keeps its private-IP
    detection — detect-secrets does not cover this, so it must survive the
    union."""
    assert "private-ip" in _categories("connect to 192.168.1.50 now")


def test_catalogue_env_secret_still_caught_via_union() -> None:
    """The in-house env-assignment shape is still caught through the union."""
    assert "env-secret" in _categories("API_KEY=supersecretvalue123")


# ─── Seam stability + multi-line body handling ────────────────────────────────


def test_empty_text_returns_no_hits() -> None:
    """The seam tolerates empty parts (a request with no body) without error."""
    assert find_secrets("") == []


def test_secret_on_second_line_of_body_is_caught_with_valid_span() -> None:
    """A multi-line outbound body: a secret on a non-first line is still caught,
    and every reported hit's span points at its own value in the original text
    (offsets are advisory but must be internally consistent)."""
    body = (
        "line one\n"
        f'{{"api_key": "{_GOOGLE_API_KEY}"}}\n'
        "line three"
    )
    hits = find_secrets(body)
    assert hits, "secret on the second line must be caught"
    for hit in hits:
        if hit.value and hit.value in body:
            assert body[hit.start:hit.end] == hit.value
