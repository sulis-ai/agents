---
# Identity (WP-01)
id: WP-002
title: L1 proxy — scrub-before-DNS + content-as-untrusted-data framing
status: pending
change_id: 01KTZVX7RBE22SX6DNHA4Y6Y7B
kind: backend
source: harden
primitive: create
group: EXPAND

# Scope (WP-02..04)
atomic_branch: yes
estimate: medium
blast_radius: low

# Lifecycle (WP-07)
sequence_id: WP-002
dependsOn: [WP-001]
blocks: [WP-003]

# Composite (WP-08)
child_wps: []
kinds: null

estimated_token_cost:
  input: 9k
  output: 8k
tdd_section: §Form (proxy.py, framing.py); §Armor L1 (scrub-before-DNS, timeout, framing)
adrs: [ADR-002, ADR-003]
verification:
  adapter: backend
  artifact: plugins/sulis/scripts/tests/unit/test_safe_fetch_proxy.py

rollback: |
  Delete _safe_fetch/proxy.py and _safe_fetch/framing.py + their tests.
  The WP-001 ports and _secret_patterns remain; no consumer is wired until
  WP-003. Deleting these two modules alone is inert.
---

# L1 proxy — scrub + framing

## Context

TDD §Form / §Armor L1. Implements the proxy gateway behind the WP-001
`FetchGateway` port: the real outbound-fetch adapter (behind `OutboundFetcher`),
the **scrub-before-DNS** control ([ADR-002](../adrs/ADR-002-secret-scrub-mechanism-and-what-is-a-secret.md)),
and the **untrusted-data framing** ([ADR-003](../adrs/ADR-003-content-as-untrusted-data-framing.md)).

This is EXPAND-Create — a concrete adapter for ports the domain owns (not a
Wrap; the HTTP client is *called by* the adapter).

## Contract

### Files

```
plugins/sulis/scripts/_safe_fetch/proxy.py     (CREATE — the gateway adapter)
plugins/sulis/scripts/_safe_fetch/framing.py   (CREATE — pure data-framing)
```

### Behaviour (pin exactly)

```python
# framing.py — pure
def frame_as_untrusted_data(content: str, source_url: str) -> str:
    """Wrap verbatim content in the deterministic untrusted-data envelope
    (ADR-003). Escapes any embedded sentinel so a page can't forge the
    END marker. Does NOT sanitise the content."""

# proxy.py
class SafeFetchProxy:           # implements FetchGateway
    def __init__(self, fetcher: OutboundFetcher, *, timeout: float = 10.0): ...
    def fetch(self, req: FetchRequest) -> FetchResult:
        # 1. find_secrets over method+url+all header values+body
        # 2. ANY hit -> raise SecretInOutboundRequest (refuse, before DNS/socket)
        # 3. else fetcher.get(url, timeout=...) -> raw content
        # 4. frame_as_untrusted_data(raw, url) -> FetchResult(content_is_untrusted_data=True)
```

### Reused

| Symbol | From | Role |
|---|---|---|
| `find_secrets`, `SecretHit` | `_secret_patterns` (WP-001) | the scrub catalogue — refuse policy |
| `FetchGateway`, `OutboundFetcher`, `FetchRequest`, `FetchResult` | `_safe_fetch.ports` (WP-001) | the seam this implements |

## Definition of Done

> **Satisfies (scenario):** **SC-L1.3** (secret scrub on outbound — refused
> before DNS), and the framing half of **SC-L1.4** (content arrives flagged as
> untrusted data). The egress/no-act halves of SC-L1.2/1.4 are proven in WP-003
> under the confinement harness.

### Red
- [ ] `test_safe_fetch_proxy.py` written failing, using an in-memory
  `OutboundFetcher` (records calls; no real network):
  - **SC-L1.3:** for EACH catalogued secret shape placed in url / a header /
    the body, `proxy.fetch` raises `SecretInOutboundRequest` and the in-memory
    fetcher records **zero** calls (refused before DNS). Assert the secret
    string never appears in any recorded outbound attempt.
  - **SC-L1.4 (framing half):** a benign fetch returns
    `content_is_untrusted_data == True` and the envelope wraps the verbatim
    content (including when the content itself contains an injection string —
    asserted present, verbatim, inside the data envelope; NOT stripped).
  - framing: embedded-sentinel content is escaped (no envelope breakout).
  - timeout is passed through to `fetcher.get`.

### Green
- [ ] `framing.py` + `proxy.py` created; all Red tests pass.
- [ ] `SafeFetchProxy` structurally conforms to `FetchGateway` (WP-001 contract
  test extended to assert this).

### Blue
- [ ] `proxy.py` docstring states the scrub is a **refuse** policy (fail-closed),
  runs **before DNS**, and that the Rule-of-Two creds-exclusion (WP-003 spawn
  wiring) is the primary control — scrub is defence-in-depth (ADR-002).
- [ ] `framing.py` docstring states content is verbatim/not-sanitised and the
  framing is necessary-not-sufficient; the no-egress wall is L3 (ADR-001/003).
- [ ] No I/O in `framing.py`; `proxy.py`'s only I/O is via the injected
  `OutboundFetcher`. Stdlib + WP-001 modules only.

## Verification Plan
- **Adapter:** `backend`. **Shape:** concrete.
- **Artifact:** `plugins/sulis/scripts/tests/unit/test_safe_fetch_proxy.py`.
- **Proves:** SC-L1.3 (refuse-before-DNS for every catalogued secret) + the
  data-framing half of SC-L1.4, with no real network (in-memory fetcher).
