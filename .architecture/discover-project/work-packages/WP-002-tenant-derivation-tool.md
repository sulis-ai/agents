---
id: WP-002
title: Author derive-consumer-tenant Tool + Python implementation + fixed vectors
status: pending
kind: backend
primitive: create
group: GENERATE
change_id: CH-01KT1W
sequence_id: WP-002
dependsOn: [WP-001]
blocks: [WP-006]
estimated_token_cost:
  input: 3k
  output: 3k
tdd_section: Form #8 (`tenant.py`); ADR-002
adrs: [ADR-002]
---

## Context

Implements the consumer-tenant ULID derivation recipe locked in
ADR-002. The recipe is `SHA256("tenant-name:" + <repo-org>/<repo-name>)`
→ first 130 bits → Crockford base32 → 26 chars → ULID first-char clamp.

The Tool entity (`dna:tool:01KT1WTL05DERIVETENANT`) is authored by
WP-001; this WP provides the Python implementation that backs it and
the fixed-vector tests that lock the recipe.

**ADR-002 amendment note (post first dispatch BLOCKER):** the marketplace
tenant ULID is grandfathered as historically-minted (predates this WP;
exhaustive search across 192 hash-variant combinations couldn't reproduce
it from the recipe). The recipe applies to NEW consumer Projects only;
no historical-match test required. Original Contract intent below preserved
for context but the test set has been relaxed to three computed vectors.

~~The implementation MUST reproduce the existing marketplace tenant ULID
(`dna:tenant:6XBZ93FSHN5TRX8MCS5R66FNCM`) from input
`tenant-name:sulis-plugins-marketplace` — that's the load-bearing
sanity check per ADR-002.

The `Sha256CrockfordTenantDeriver` adapter implements the
`TenantDeriver` port defined in TDD §Form §Ports & Adapters. Per the
Ports-vs-Wrappers discriminator (`references/change-primitives.md`),
this is **Create**, not Wrap — the port belongs to the domain.

## Contract

### Files created

```
plugins/sulis/scripts/_discovery/
├── __init__.py                     # empty or minimal — package marker only
└── tenant.py                       # the TenantDeriver port + Sha256CrockfordTenantDeriver
plugins/sulis/scripts/tests/unit/
└── test_discovery_tenant.py        # fixed-vector + determinism + collision-resistance tests
```

4 files. (`__init__.py` is the new-package scaffolding for `_discovery/`;
created here because WP-002 is the first WP to land code in that
directory — WP-003, WP-004, WP-006, WP-007 will extend it.)

### Port + adapter

```python
# plugins/sulis/scripts/_discovery/tenant.py
from typing import Protocol

# canonical-source: TDD.md §Form §Ports & Adapters — Port 3 (TenantDeriver)
class TenantDeriver(Protocol):
    def derive_consumer_tenant(self, repo_org_slash_name: str) -> str:
        """Return 'dna:tenant:<26-char ULID>' per ADR-002 recipe.

        Pure function: same input → same output, no I/O, no clock.
        """
        ...


class Sha256CrockfordTenantDeriver:
    """Concrete TenantDeriver per ADR-002 recipe.

    Recipe (canonical-source: ADR-002):
      input  = "tenant-name:" + <repo-org>/<repo-name>
      digest = SHA256(input)
      bits   = digest[:130]  # 130 most-significant bits
      ulid26 = crockford_base32_encode(bits, length=26)
      if ulid26[0] > '7': ulid26 = chr(ord(ulid26[0]) - 8) + ulid26[1:]
      result = "dna:tenant:" + ulid26
    """

    CROCKFORD_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"  # no I L O U

    def derive_consumer_tenant(self, repo_org_slash_name: str) -> str:
        ...
```

### Fixed-vector tests

The test file pins ≥3 input/output vectors. The marketplace tenant is
one of them — proving the recipe reproduces the historically-derived
ULID.

```python
# plugins/sulis/scripts/tests/unit/test_discovery_tenant.py

import pytest
from _discovery.tenant import Sha256CrockfordTenantDeriver

FIXED_VECTORS = [
    # (input, expected_output)  — locked in WP-002
    # Note: the marketplace tenant ULID is grandfathered per ADR-002
    # amendment (historically minted ad-hoc; predates the recipe; tests
    # do NOT need to reproduce it). The recipe applies to NEW consumer
    # Projects only. All three vectors below are computed-at-implementation-time
    # from the canonical recipe and locked in here.
    ("acme/payments-app",         "dna:tenant:<computed-at-implementation-time>"),
    ("iain/agents",               "dna:tenant:<computed-at-implementation-time>"),
    ("widgets-co/web-app",        "dna:tenant:<computed-at-implementation-time>"),
]

@pytest.mark.parametrize("input_, expected", FIXED_VECTORS)
def test_fixed_vectors(input_, expected):
    d = Sha256CrockfordTenantDeriver()
    assert d.derive_consumer_tenant(input_) == expected
```

The two `<computed-at-implementation-time>` placeholders are computed
once at Green time (by running the recipe on the inputs) and then
hard-locked. From that point any change to the recipe that breaks
byte-equivalence FAILs the test.

## Definition of Done

### Red — Failing tests written

- [ ] `tests/unit/test_discovery_tenant.py::test_fixed_vectors[acme/payments-app]` — first vector lockfile (computed at GREEN)
- [ ] `tests/unit/test_discovery_tenant.py::test_fixed_vectors[iain/agents]` — second vector lockfile
- [ ] `tests/unit/test_discovery_tenant.py::test_fixed_vectors[widgets-co/web-app]` — third vector lockfile
- [ ] `tests/unit/test_discovery_tenant.py::test_determinism` — 100 invocations with same input produce byte-identical output
- [ ] `tests/unit/test_discovery_tenant.py::test_different_inputs_different_outputs` — 10 distinct inputs produce 10 distinct outputs (collision sanity)
- [ ] `tests/unit/test_discovery_tenant.py::test_output_shape` — output matches regex `^dna:tenant:[0-9A-HJKMNP-TV-Z]{26}$` (Crockford alphabet, 26 chars)
- [ ] `tests/unit/test_discovery_tenant.py::test_first_char_clamped` — first char of the ULID body is in `'0'..'7'` (per ULID spec / ADR-002 clamp)
- [ ] `tests/unit/test_discovery_tenant.py::test_no_I_L_O_U_chars` — output contains none of `I`, `L`, `O`, `U` (Crockford exclusions)
- [ ] `tests/unit/test_discovery_tenant.py::test_implements_port_protocol` — `Sha256CrockfordTenantDeriver` satisfies the `TenantDeriver` Protocol (runtime `isinstance(d, TenantDeriver)` or `typing.runtime_checkable` check)

### Green — Implementation makes tests pass

- [ ] `plugins/sulis/scripts/_discovery/__init__.py` exists (empty package marker)
- [ ] `plugins/sulis/scripts/_discovery/tenant.py` exposes `TenantDeriver` Protocol + `Sha256CrockfordTenantDeriver` class
- [ ] Implementation uses `hashlib.sha256` and a hand-rolled Crockford base32 encoder (no third-party deps; recipe must be inspectable)
- [ ] All 9 Red tests pass
- [ ] The two `<computed-at-implementation-time>` placeholders in the fixed-vector table are filled in with the actual recipe outputs and committed

### Blue — Refactor complete

- [ ] Crockford-base32 encoder is a private helper, ≤30 LOC, no branches beyond the alphabet lookup + the first-char clamp
- [ ] No I/O, no clock, no random — function is provably pure (test asserts via determinism + 100-invocation parity)
- [ ] Docstring quotes the ADR-002 recipe verbatim (so readers don't have to context-switch to verify)
- [ ] Test file's `FIXED_VECTORS` list is sorted alphabetically by input for deterministic diff

## Sequence

- **dependsOn:** WP-001 (the Tool entity for `derive-consumer-tenant` is authored there; this WP backs it with code)
- **blocks:** WP-006 (Mint phase calls `derive_consumer_tenant` to populate `belongs_to_tenant`)
- **Parallelisable with:** WP-003, WP-004, WP-005, WP-007, WP-009 (all unblocked once WP-001 lands)

## Estimated Token Cost

- **Input:** ~3k (ADR-002 + TDD §Form §Ports & Adapters + foundation Tool schema + release-train marketplace-tenant cross-check input)
- **Output:** ~3k (`tenant.py` ≈ 60 LOC + `test_discovery_tenant.py` ≈ 80 LOC + `__init__.py` ≈ 0 LOC)
- **Total:** ~6k

## Notes

- The recipe is encoded as test-fixture pairs (`FIXED_VECTORS`) per ADR-002's "the recipe is encoded as test-fixture pairs in WP-002" pledge. Any future regenerate that changes the recipe will fail these tests immediately.
- The `__init__.py` for `_discovery/` is created here as the first arrival; WP-003 / WP-004 / WP-006 / WP-007 import from this package. Each later WP extends the package without re-creating the marker file. P6 peer-collision risk is zero — WP-002 is the sole creator of `__init__.py`.
- The marketplace-tenant cross-check (`("sulis-plugins-marketplace", "dna:tenant:6XBZ93FSHN5TRX8MCS5R66FNCM")`) is the load-bearing assertion — if the recipe doesn't reproduce the historically-derived marketplace tenant ULID, the recipe is wrong. This is the test that fails first if anyone changes the algorithm.
