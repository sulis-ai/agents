"""WP-002 — Tenant derivation tests for the ``Sha256CrockfordTenantDeriver``
adapter (implements the ``TenantDeriver`` Protocol).

Canonical source for the recipe under test: ADR-002 (consumer-tenant ULID
derivation — SHA256('tenant-name:' + repo-org/name) → 130 bits → Crockford
base32 → 26 chars → ULID first-char clamp). The recipe applies to NEW
consumer Projects only; the marketplace tenant ULID is grandfathered per
ADR-002's Decision section (predates the recipe; exhaustive search across
192 hash-variant combinations couldn't reproduce it from this recipe).

Test surface (9 tests per WP-002 Definition of Done — Red):

- 3 × ``test_fixed_vectors`` (one per locked input) — recipe encoding via
  byte-exact lockfile. The expected ULIDs are computed-at-Green-time and
  hard-locked here; any future change to the recipe that breaks
  byte-equivalence fails these.
- ``test_determinism`` — 100 invocations with the same input produce
  byte-identical output (pure-function invariant).
- ``test_different_inputs_different_outputs`` — 10 distinct inputs → 10
  distinct outputs (collision-resistance sanity check).
- ``test_output_shape`` — output regex ``^dna:tenant:[0-9A-HJKMNP-TV-Z]{26}$``
  (Crockford alphabet, 26 chars).
- ``test_first_char_clamped`` — first body character in ``'0'..'7'``
  (per ULID-spec first-char clamp; encodes top 3 bits of the timestamp
  prefix).
- ``test_no_I_L_O_U_chars`` — output contains none of ``I``, ``L``, ``O``,
  ``U`` (Crockford exclusions).
- ``test_implements_port_protocol`` — ``Sha256CrockfordTenantDeriver``
  satisfies the runtime-checkable ``TenantDeriver`` Protocol.
"""

from __future__ import annotations

import re

import pytest

from _discovery.tenant import Sha256CrockfordTenantDeriver, TenantDeriver

# ─── Fixed vectors (computed at GREEN; locked here byte-exact) ────────────
#
# Sorted alphabetically by input for deterministic diff (Blue invariant).
# Per ADR-002 amendment: the marketplace tenant ULID is grandfathered;
# the recipe applies to NEW consumer Projects only. These three vectors
# are the canonical lockfile for the recipe.

FIXED_VECTORS = [
    ("acme/payments-app", "dna:tenant:3BXM96KC569S8G1MY3K7616YBB"),
    ("iain/agents", "dna:tenant:6C5HB258H3061YBE1G34KZQPPG"),
    ("widgets-co/web-app", "dna:tenant:3APBDFGKJPFBDEGSTYRRMR8784"),
]


# ─── Tests ────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("input_, expected", FIXED_VECTORS)
def test_fixed_vectors(input_: str, expected: str) -> None:
    """Recipe lockfile — input → output is byte-identical to FIXED_VECTORS."""
    deriver = Sha256CrockfordTenantDeriver()
    assert deriver.derive_consumer_tenant(input_) == expected


def test_determinism() -> None:
    """100 invocations with the same input produce byte-identical output.

    Asserts the pure-function invariant: no I/O, no clock, no random.
    """
    deriver = Sha256CrockfordTenantDeriver()
    first = deriver.derive_consumer_tenant("acme/payments-app")
    outputs = {deriver.derive_consumer_tenant("acme/payments-app") for _ in range(100)}
    assert outputs == {first}, (
        f"Determinism failure — observed {len(outputs)} distinct outputs across "
        f"100 invocations: {sorted(outputs)}"
    )


def test_different_inputs_different_outputs() -> None:
    """10 distinct inputs produce 10 distinct outputs (collision sanity)."""
    deriver = Sha256CrockfordTenantDeriver()
    inputs = [
        "acme/payments-app",
        "acme/web-app",
        "iain/agents",
        "iain/llma",
        "widgets-co/web-app",
        "widgets-co/api",
        "alpha/beta",
        "gamma/delta",
        "foo/bar",
        "baz/qux",
    ]
    outputs = {deriver.derive_consumer_tenant(i) for i in inputs}
    assert len(outputs) == len(inputs), (
        f"Collision detected: {len(inputs)} inputs → {len(outputs)} outputs"
    )


_CROCKFORD_OUTPUT_RE = re.compile(r"^dna:tenant:[0-9A-HJKMNP-TV-Z]{26}$")


def test_output_shape() -> None:
    """Output matches the Crockford-alphabet ULID shape regex."""
    deriver = Sha256CrockfordTenantDeriver()
    for input_, _ in FIXED_VECTORS:
        output = deriver.derive_consumer_tenant(input_)
        assert _CROCKFORD_OUTPUT_RE.match(output), (
            f"Output {output!r} for input {input_!r} fails Crockford regex"
        )


def test_first_char_clamped() -> None:
    """First char of the ULID body is in ``'0'..'7'`` (ULID spec clamp).

    The first character encodes the top 3 bits of the 48-bit timestamp
    prefix; values > 7 would overflow. ADR-002 codifies the property
    ("only 0..7 are valid for the first character") with an ASCII-
    arithmetic shorthand that is correct in concept but incorrect in
    code form for the Crockford alphabet (which is not ASCII-continuous
    due to the I/L/O/U exclusions). The implementation maps the concept
    to a value-space modulo; this test asserts the property — first body
    char in '01234567' — for any input, which is what the ADR-002 clamp
    is for.
    """
    deriver = Sha256CrockfordTenantDeriver()
    # Test a broad input space so the clamp branch is exercised.
    inputs = [
        "acme/payments-app",
        "iain/agents",
        "widgets-co/web-app",
        "z/z",
        "ZZZZZZZZZZ/ZZZZZZZZZZ",
        "0/0",
        "alpha/beta",
        "delta/epsilon",
    ]
    for input_ in inputs:
        output = deriver.derive_consumer_tenant(input_)
        # "dna:tenant:" is 11 chars; body starts at index 11.
        first_body_char = output[11]
        assert first_body_char in "01234567", (
            f"First body char {first_body_char!r} for input {input_!r} "
            f"is out of 0..7 range (ULID spec violation)"
        )


def test_no_I_L_O_U_chars() -> None:
    """Output contains none of ``I``, ``L``, ``O``, ``U`` (Crockford exclusions)."""
    deriver = Sha256CrockfordTenantDeriver()
    forbidden = set("ILOU")
    for input_, _ in FIXED_VECTORS:
        output = deriver.derive_consumer_tenant(input_)
        body = output[len("dna:tenant:") :]
        used = set(body)
        bad = used & forbidden
        assert not bad, (
            f"Output {output!r} for input {input_!r} contains Crockford-"
            f"forbidden chars: {sorted(bad)}"
        )


def test_implements_port_protocol() -> None:
    """``Sha256CrockfordTenantDeriver`` satisfies the runtime-checkable
    ``TenantDeriver`` Protocol (structural typing — has the method with the
    right signature).
    """
    deriver = Sha256CrockfordTenantDeriver()
    assert isinstance(deriver, TenantDeriver), (
        "Sha256CrockfordTenantDeriver does not satisfy the TenantDeriver "
        "Protocol — check that derive_consumer_tenant is defined with the "
        "expected signature."
    )
