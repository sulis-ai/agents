# ADR-002 — Reuse `_anonymiser`'s secret-pattern catalogue; L1 scrub is fail-closed-refuse, not redact

> **Status:** accepted
> **Date:** 2026-06-13
> **Change:** CH-E22SX6 · harden
> **Affects:** L1 proxy (outbound scrub), the shared scrub primitive, SC-L1.3

## Context

SC-L1.3 requires that a known-format secret in an outbound request
(URL / headers / body) **never crosses the proxy's egress boundary** —
scrubbed or refused *before DNS resolution*. We need (a) a secret detector
and (b) a policy for what to do on a hit.

The marketplace already has a mature, well-tested secret detector:
`_anonymiser.py` (CP-01 priority 0 — internal prior art). Its pattern
catalogue covers env-var-named secrets (`*_KEY`/`*_SECRET`/`*_TOKEN`/
`*_PASSWORD`), JWTs, Slack tokens (`xox[abprs]-…`), long opaque
provider tokens (`sk_live_`, `ghp_`, `AKIA`, `AIza`, `npm_`, …), and
private/loopback IP scrub via the `ipaddress` stdlib. It is pure, has no
I/O, and has a dedicated test suite (the `fix-scrub-private-ip-ranges` and
`fix-tighten-long-token-regex` changes hardened it further).

But the **policy differs**. `_anonymiser`'s job is human-preview redaction:
it *replaces* a secret with `<secret>` and *preserves* the env-var name for
operational context. L1's job is exfil prevention: on a secret hit in an
*outbound request*, the safe behaviour is **fail closed — refuse the fetch**
(or, where the secret is incidental and strippable, strip-and-warn), not
silently redact-and-send (which could corrupt a legitimate request) and
never send-anyway.

## Decision

**Extract the secret-detection patterns from `_anonymiser` into a shared
primitive, and give L1 a fail-closed REFUSE policy over it.**

1. **Refactor (REORGANISE-Extract, characterisation-test-first):** lift the
   secret-only passes (`_ENV_SECRET_ASSIGNMENT`, `_JWT`, `_SLACK_TOKEN`,
   `_LONG_TOKEN`, and the private-IP `_replace_ip`) into a shared
   `_secret_patterns.py` module exposing a pure
   `find_secrets(text) -> list[SecretHit]`. `_anonymiser` then *imports and
   composes* this primitive — one catalogue, two policies. The Non-Negotiable
   #2 "extract the shared primitive when two components implement the same
   pattern" applies the moment L1 would otherwise re-encode the same regexes.

2. **L1 policy = scan-then-refuse, before DNS.** The proxy runs
   `find_secrets` over the full outbound request line (method + URL + every
   header value + body) *before* it resolves DNS or opens any socket. Any
   hit → the fetch is **refused fail-closed** with a clear reason; the
   request never leaves the process. This is the SC-L1.3 control.

3. **What counts as a secret = the catalogue, plus the request-position
   rule.** A "secret" is any `_secret_patterns` hit. Additionally, **the
   agent's own configured credentials must not be in the fetch path at all**
   (the Rule-of-Two leg, ADR-001 / SPEC §L1(d)): the proxy is launched
   without the credential-bearing env in its scope, so a credential cannot
   be *read* into an outbound request in the first place. The scrub is
   defence-in-depth on top of that exclusion, not the primary control.

## Alternatives considered

- **Re-encode the regexes inside the proxy (rejected).** Two copies of the
  same secret catalogue = two sources of truth that drift; violates
  Non-Negotiable #2 and CP-01. Extract instead.
- **Redact-and-send like `_anonymiser` (rejected for L1).** Silently
  mutating an outbound request can corrupt a legitimate call (a token in a
  query param the API needs) and, worse, *teaches nothing* — the agent
  thinks the call succeeded. Fail-closed refuse is the honest, safe default;
  the agent learns the request carried a secret and must not.
- **Entropy-based detection (rejected as primary).** High-entropy heuristics
  false-positive on commit SHAs and UUIDs (the `_anonymiser` comments record
  exactly this lesson). The prefix-anchored catalogue is precise; entropy is
  a possible future additive pass, not the v1 control.

## Consequences

- One secret catalogue (`_secret_patterns.py`), consumed by both
  `_anonymiser` (redact policy) and the L1 proxy (refuse policy). A new
  secret format is added once, both consumers inherit it.
- SC-L1.3's test injects a marked secret of each catalogued shape into an
  outbound request and asserts the proxy refuses before any egress (no
  secret in the outbound capture, because there is no outbound).
- The characterisation test pins `_anonymiser`'s current behaviour before the
  extract, so the refactor cannot regress the feedback redaction path
  (EP-07 / Non-Negotiable #3).
- A residual honest limit: the catalogue is format-based; a novel
  secret shape it does not recognise can pass. The Rule-of-Two exclusion
  (secret not in the path at all) is the real control; the scrub is the
  belt to that braces. Documented, not hidden.
