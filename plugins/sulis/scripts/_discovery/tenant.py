"""Consumer-tenant ULID derivation — ADR-002 recipe.

The ``TenantDeriver`` Protocol and its ``Sha256CrockfordTenantDeriver``
adapter implement the deterministic recipe locked in ADR-002 (and
referenced from TDD §Form §Ports & Adapters — Port 3).

Recipe (verbatim from ADR-002):

    input  = "tenant-name:" + <repo-org> + "/" + <repo-name>
             where <repo-org>/<repo-name> is the GitHub-shorthand form
             of source.repo (e.g., "acme/payments-app")

    digest = SHA256(input)                       # 32 bytes / 256 bits

    bits   = digest[:130]                        # first 130 bits, MSB-first

    # Crockford base32 character set: 0123456789ABCDEFGHJKMNPQRSTVWXYZ
    # (excludes I, L, O, U)
    ulid26 = crockford_base32_encode(bits, length=26)

    # ULID first-char clamp per ULID spec: only 0..7 are valid for the
    # first character (it encodes the top 3 bits of the 48-bit timestamp
    # prefix; 5 bits would overflow).
    if ulid26[0] > '7':
        ulid26 = chr(ord(ulid26[0]) - 8) + ulid26[1:]

    result = "dna:tenant:" + ulid26

ADR-002 amendment: the marketplace tenant ULID
(``dna:tenant:6XBZ93FSHN5TRX8MCS5R66FNCM``) is grandfathered as
historically-minted (ad-hoc; predates this recipe). The recipe applies
prospectively to NEW consumer Projects only.
"""

from __future__ import annotations

import hashlib
from typing import Protocol, runtime_checkable

__all__ = ["TenantDeriver", "Sha256CrockfordTenantDeriver"]


# Crockford base32 alphabet — excludes I, L, O, U (Douglas Crockford's
# spec) so the 32 symbols are 0-9 + A-Z minus those four.
_CROCKFORD_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def _crockford_base32_encode_130_bits(digest: bytes) -> str:
    """Encode the top 130 bits of ``digest`` as 26 Crockford-base32 chars.

    ULID body is 26 × 5 = 130 bits. We slice the SHA256 digest's first 17
    bytes (= 136 bits) into a single big-endian integer, then drop the
    bottom 6 bits to land on a 130-bit value. Each 5-bit chunk indexes
    the Crockford alphabet, MSB-first.
    """
    # 17 bytes = 136 bits; drop low 6 bits → 130 bits MSB-aligned.
    n = int.from_bytes(digest[:17], "big") >> 6
    chars = [_CROCKFORD_ALPHABET[(n >> (5 * (25 - i))) & 0x1F] for i in range(26)]
    return "".join(chars)


@runtime_checkable
class TenantDeriver(Protocol):
    """Port — derive a consumer-tenant ULID from a GitHub-shorthand repo ref.

    Pure function: same input → same output, no I/O, no clock, no random.

    canonical-source: TDD.md §Form §Ports & Adapters — Port 3 (TenantDeriver)
    """

    def derive_consumer_tenant(self, repo_org_slash_name: str) -> str:
        """Return ``dna:tenant:<26-char ULID>`` per ADR-002 recipe."""
        ...


class Sha256CrockfordTenantDeriver:
    """Adapter — ADR-002 recipe implemented with stdlib ``hashlib.sha256``
    and a hand-rolled Crockford-base32 encoder (no third-party deps; the
    recipe must be inspectable end-to-end from this file).
    """

    def derive_consumer_tenant(self, repo_org_slash_name: str) -> str:
        """Compute the consumer-tenant ULID for ``repo_org_slash_name``.

        ``repo_org_slash_name`` is the GitHub-shorthand form (e.g.,
        ``acme/payments-app``); the ``"tenant-name:"`` prefix is added
        inside this method per ADR-002.

        Note on the first-char clamp:
        ADR-002 expresses the clamp as ``if ulid26[0] > '7':
        ulid26 = chr(ord(ulid26[0]) - 8) + ulid26[1:]``. That ASCII-
        arithmetic shorthand assumes a base32hex alphabet (0-9A-V is
        ASCII-continuous); it does NOT generalise to Crockford base32,
        whose alphabet skips I, L, O, U. The unambiguous CONCEPT stated
        in ADR-002 — "the first char encodes only the top 3 bits of the
        timestamp prefix; values > 7 would overflow" — maps cleanly to a
        value-space modulo: if the first 5-bit chunk's value is > 7, take
        it mod 8 and look up the resulting alphabet char (which lands in
        the 0..7 character range, since alphabet[0..7] = "01234567").
        That is what this implementation does. The property is then
        directly testable: ``test_first_char_clamped`` asserts the first
        body char is in "01234567" for any input.
        """
        digest = hashlib.sha256(
            f"tenant-name:{repo_org_slash_name}".encode("utf-8")
        ).digest()
        ulid26 = _crockford_base32_encode_130_bits(digest)
        first_value = _CROCKFORD_ALPHABET.index(ulid26[0])
        if first_value > 7:
            ulid26 = _CROCKFORD_ALPHABET[first_value % 8] + ulid26[1:]
        return f"dna:tenant:{ulid26}"
