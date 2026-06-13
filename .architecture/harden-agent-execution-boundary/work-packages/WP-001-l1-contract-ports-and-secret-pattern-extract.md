---
# Identity (WP-01)
id: WP-001
title: L1 contract — FetchGateway/OutboundFetcher ports + extract the secret-pattern catalogue
status: pending
change_id: 01KTZVX7RBE22SX6DNHA4Y6Y7B
kind: contract
source: harden
primitive: abstract
group: REORGANISE

# Scope (WP-02..04)
atomic_branch: yes
estimate: medium
blast_radius: medium

# Lifecycle (WP-07)
sequence_id: WP-001
dependsOn: []
blocks: [WP-002, WP-003]

# Composite (WP-08)
child_wps: []
kinds: null

# Contract-first
contract_type: data
characterisation_test: plugins/sulis/scripts/tests/unit/test_anonymiser_characterisation.py

estimated_token_cost:
  input: 10k
  output: 8k
tdd_section: §Form (new components — ports + _secret_patterns); §Armor L1 scrub
adrs: [ADR-002, ADR-003]
verification:
  adapter: backend
  artifact: plugins/sulis/scripts/tests/unit/test_safe_fetch_gateway_contract.py

rollback: |
  Delete _secret_patterns.py and the new port-defining module + their tests;
  revert _anonymiser.py to its pre-extract form (the characterisation test is
  the safety net proving the revert is behaviour-identical). No consumer
  depends on the ports until WP-002/003 land.
---

# L1 contract — ports + secret-pattern extract

## Context

TDD §Form — the L1 seam between the agent-facing tool and the proxy is a
**producer/consumer boundary**, so per CONTRACT_FIRST the contract is pinned
first (CF-01). This WP defines the two ports (`FetchGateway`, `OutboundFetcher`)
as the typed seam, and performs the [ADR-002](../adrs/ADR-002-secret-scrub-mechanism-and-what-is-a-secret.md)
**extract** of the secret-pattern catalogue out of `_anonymiser.py` into a
shared `_secret_patterns.py` (Non-Negotiable #2 — extract the shared primitive
before a second copy is written).

The extract is REORGANISE-Abstract over existing code → **characterisation
test first** (Non-Negotiable #3): pin `_anonymiser`'s current redaction output
on a corpus, confirm green, extract, confirm still green.

## Contract

### Files

```
plugins/sulis/scripts/_secret_patterns.py        (CREATE — extracted catalogue)
plugins/sulis/scripts/_safe_fetch/__init__.py     (CREATE)
plugins/sulis/scripts/_safe_fetch/ports.py        (CREATE — the typed ports)
plugins/sulis/scripts/_anonymiser.py              (MODIFY — import the catalogue)
```

### Public surface (pin exactly)

```python
# _secret_patterns.py — pure, no I/O
@dataclass(frozen=True)
class SecretHit:
    category: str   # "env-secret" | "jwt" | "slack" | "long-token" | "private-ip"
    value: str
    start: int
    end: int

def find_secrets(text: str) -> list[SecretHit]: ...

# _safe_fetch/ports.py
@dataclass(frozen=True)
class FetchRequest:
    url: str
    method: str = "GET"
    headers: dict[str, str] = field(default_factory=dict)
    body: str | None = None

@dataclass(frozen=True)
class FetchResult:
    source_url: str
    fetched_at: str
    content_is_untrusted_data: bool   # always True from a real fetch
    content: str                      # framed envelope (ADR-003)

class FetchGateway(Protocol):
    """Agent → proxy seam. tool.py depends on THIS, never on proxy internals."""
    def fetch(self, req: FetchRequest) -> FetchResult: ...

class OutboundFetcher(Protocol):
    """proxy → open web seam. The real HTTP leg is an adapter behind this."""
    def get(self, url: str, *, timeout: float) -> str: ...
```

### Reused (imported, not reimplemented)

| Symbol | From | Role |
|---|---|---|
| the secret regexes (`_ENV_SECRET_ASSIGNMENT`, `_JWT`, `_SLACK_TOKEN`, `_LONG_TOKEN`, `_replace_ip` logic) | moved out of `_anonymiser` | become `_secret_patterns`'s catalogue; `_anonymiser` imports them back |

## Definition of Done

> **Satisfies (scenario):** none directly — this is the contract + primitive
> extract that WP-002/003 (SC-L1.1–1.4) build on. CF-01 contract-first WP.

### Red
- [ ] `test_anonymiser_characterisation.py` written: pins `_anonymiser.anonymise`
  output over a secret-bearing corpus (env secret, JWT, Slack, long-token,
  private IP). Confirmed GREEN against current `_anonymiser` **before** the extract.
- [ ] `test_safe_fetch_gateway_contract.py` written failing: asserts a
  `FetchGateway`/`OutboundFetcher` conformer's shape (import fails first).
- [ ] `test_secret_patterns.py` written failing: `find_secrets` finds each
  catalogued shape; asserts no false positive on a commit SHA / UUID.

### Green
- [ ] `_secret_patterns.py` created; `find_secrets` passes its tests.
- [ ] `_anonymiser.py` modified to import the catalogue from `_secret_patterns`
  (one catalogue, two policies — ADR-002). Characterisation test still GREEN.
- [ ] `_safe_fetch/ports.py` created with the two Protocols + request/result
  dataclasses; the contract test's in-memory conformer passes.

### Blue
- [ ] `_secret_patterns` docstring states it is the single catalogue consumed by
  both `_anonymiser` (redact policy) and the L1 proxy (refuse policy — ADR-002).
- [ ] Ports docstring states the Stripe-rule discriminator: these are ports the
  domain owns (EXPAND-Create adapters implement them) — not Wraps.
- [ ] No third-party imports; Python 3.11-safe; dependency-inward.

## Verification Plan
- **Adapter:** `backend` (pytest). **Shape:** concrete.
- **Artifact:** `plugins/sulis/scripts/tests/unit/test_safe_fetch_gateway_contract.py`
  (+ `test_secret_patterns.py`, `test_anonymiser_characterisation.py`).
- **Proves:** the seam shape + the catalogue extract is behaviour-preserving.
