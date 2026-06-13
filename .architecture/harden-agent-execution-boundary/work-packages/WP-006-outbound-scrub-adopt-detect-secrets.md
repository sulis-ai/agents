---
# Identity (WP-01)
id: WP-006
title: L1 outbound-scrub — adopt detect-secrets as primary, catalogue supplementary
status: pending
change_id: 01KTZVX7RBE22SX6DNHA4Y6Y7B
kind: backend
source: harden
primitive: harden
group: REINFORCE

# Scope (WP-02..04)
atomic_branch: yes
estimate: medium
blast_radius: low

# Lifecycle (WP-07)
sequence_id: WP-006
dependsOn: [WP-002]
blocks: []

# Composite (WP-08)
child_wps: []
kinds: null

estimated_token_cost:
  input: 11k
  output: 9k
tdd_section: §Armor L1 (scrub-before-DNS)
adrs: [ADR-002, ADR-006]
verification:
  adapter: backend
  artifact: plugins/sulis/scripts/tests/unit/test_secret_patterns_outbound.py

rollback: |
  Revert _secret_patterns.py to catalogue-only find_secrets, drop the
  detect-secrets dependency from pyproject.toml + uv.lock, delete
  test_secret_patterns_outbound.py and ADR-006. The proxy is an unchanged
  caller of find_secrets either way; the anonymiser never depended on this
  change. Reverting restores the pure-catalogue scrub.
---

# L1 outbound-scrub — adopt detect-secrets (catalogue supplementary)

## Context

The L1 proxy's outbound secret-scrub (SC-L1.3) currently uses ONLY the repo's
bespoke regex catalogue (`_secret_patterns.find_secrets`, ~5 shapes). It misses
common provider formats: AWS secret-access-key, Google API keys, and generic
high-entropy bearer/quoted tokens. Per Convention Preference (CP-01..05), adopt
the established `detect-secrets` (Yelp) as the **primary** detector for the
OUTBOUND-SCRUB policy, keeping the in-house catalogue as a **supplementary**
policy (it encodes private-IP detection + the env-assignment / slack / jwt /
long-token hardening lessons #39/#40/#42 that detect-secrets does not cover).

This is REINFORCE-Harden — strengthening an existing control's detection
surface without changing its public seam.

## Decision (ADR-006)

The outbound-scrub policy = detect-secrets' plugin scan ∪ in-house catalogue.
This supersedes ADR-002's entropy-rejection FOR THE OUTBOUND-SCRUB POLICY ONLY.
The anonymiser's redaction policy keeps its catalogue-only, low-false-positive
posture (ADR-002 entropy-rejection still applies there). See ADR-006.

## Contract

### Files

```
plugins/sulis/scripts/_secret_patterns.py                         (MODIFY — add detect-secrets union behind find_secrets; keep catalogue as find_catalogue_secrets)
plugins/sulis/scripts/pyproject.toml                              (MODIFY — add detect-secrets dependency)
plugins/sulis/scripts/uv.lock                                     (MODIFY — uv lock)
plugins/sulis/scripts/tests/unit/test_secret_patterns_outbound.py (CREATE — new provider-shape coverage)
.architecture/harden-agent-execution-boundary/adrs/ADR-006-*.md   (CREATE — supersede ADR-002 for outbound-scrub)
```

### Two-policy split (explicit, named — do NOT entangle)

- **Outbound-scrub policy** = `find_secrets(text)` = detect-secrets plugin scan
  ∪ `find_catalogue_secrets(text)`. The proxy is an UNCHANGED caller of
  `find_secrets` (same signature, same `SecretHit` return). Leans fail-closed.
- **Anonymiser policy** = catalogue only. `_anonymiser` imports the raw compiled
  patterns (`_ENV_SECRET_ASSIGNMENT`, `_IP_ADDRESS`, `_JWT`, `_LONG_TOKEN`,
  `_SLACK_TOKEN`) — NOT routed through detect-secrets. Byte-unchanged behaviour.

### Constraints

- `find_secrets`'s public interface stable (proxy + SC-L1.3 unchanged callers).
- Anonymiser policy byte-unchanged (characterisation + anonymiser suites green).
- Outbound-scrub leans fail-closed: a false-positive blocks one fetch
  (acceptable); a false-negative leaks a secret (not acceptable).
- Portable, no shell-out — use detect-secrets' programmatic plugin API.
- Lint clean (ruff). Conventional Commits.

## Definition of Done

### Red
- New tests prove the OUTBOUND-SCRUB now catches previously-missed shapes:
  AWS-style access-key + secret pair, Google-style API key, generic
  high-entropy quoted/assigned bearer token — using synthetic-but-detect-
  secrets-flaggable, push-safe fixtures (no live-key literals).
- Tests assert benign requests (plain URL, plain body, commit SHA) still pass.

### Green
- `find_secrets` returns the union; the new-shape tests pass; the existing
  SC-L1.3 proxy tests + catalogue tests stay green.

### Blue
- The detect-secrets scan and the catalogue scan compose behind one named
  union; no duplicated detection logic.

### Regression (MUST stay green)
- `tests/unit/test_safe_fetch_proxy.py`
- `tests/unit/test_anonymiser.py`
- `tests/unit/test_anonymiser_characterisation.py`
- `tests/unit/test_secret_patterns.py`
