# ADR-006 — Adopt detect-secrets as the PRIMARY outbound-scrub detector; catalogue supplementary

> **Status:** accepted
> **Date:** 2026-06-13
> **Change:** CH-E22SX6 · harden
> **Affects:** L1 proxy (outbound scrub), `_secret_patterns.find_secrets`, SC-L1.3
> **Supersedes:** ADR-002 — *for the OUTBOUND-SCRUB policy only* (see Scope)

## Context

The L1 outbound secret-scrub (SC-L1.3) refuses an outbound request fail-closed
when a secret is found in its request line. Per ADR-002 the detector was the
in-house `_secret_patterns` catalogue alone (~5 prefix-anchored shapes:
env-assignment, JWT, Slack, long-token, private-IP). In practice the catalogue
misses common provider formats the agent could plausibly carry outbound:

- AWS access-key ids (`AKIA…`) and secret-access-keys,
- Google API keys (`AIza…`) outside the narrow `long-token` prefix set,
- generic high-entropy bearer / opaque tokens with no recognised prefix.

A false-negative here is the expensive failure: a real secret leaves the
process. ADR-002 explicitly rejected entropy-based detection because it
false-positives on commit SHAs and ULIDs/UUIDs — correct for the anonymiser's
human-preview redaction (a noisy preview erodes trust), but the wrong trade for
the outbound-scrub, where a false-positive merely blocks one fetch.

The Convention Preference standard (CP-01..05) says: when an established,
maintained tool meets the requirement, adopt it rather than hand-rolling. The
established secret detector is **`detect-secrets` (Yelp)** — pip/uv-installable,
in-process plugin API, a maintained provider catalogue plus tunable entropy
plugins.

## Decision

**Adopt `detect-secrets` as the PRIMARY detector for the OUTBOUND-SCRUB policy,
union'd with the in-house catalogue kept as the SUPPLEMENTARY layer.**

1. **Two named policies over one seam.** `_secret_patterns` now exposes
   `find_catalogue_secrets(text)` (the in-house catalogue) and
   `find_secrets(text)` (the outbound-scrub policy = `detect-secrets` plugin
   scan ∪ `find_catalogue_secrets`). The L1 proxy is an **unchanged caller** of
   `find_secrets` — same signature, same `SecretHit` return; only the detection
   surface widens. A hit from EITHER detector → the proxy refuses fail-closed
   before DNS (SC-L1.3 unchanged).

2. **detect-secrets is invoked in-process, no shell-out.** `default_settings()`
   populates Yelp's default plugin registry; `get_plugins()` yields the
   configured plugins; each plugin's `analyze_line` runs over each line of the
   request part. We use `analyze_line`, **not** `scan_line`: `scan_line`
   word-splits aggressively and over-reports on ordinary URLs, whereas
   `analyze_line` applies each plugin's own extraction (the entropy plugins use
   a quote/assignment heuristic). The net effect: benign URLs, benign bodies,
   and commit SHAs **in prose** stay clean, while quoted/assigned high-entropy
   provider tokens are caught. detect-secrets categories are prefixed `ds:` so
   the refusal message records detection provenance.

3. **The catalogue stays as the supplementary layer** because it owns
   detections detect-secrets does not cover: private/loopback/link-local IPs
   (via the `ipaddress` stdlib), env-var-named assignments, and the hardened
   slack/jwt/long-token shapes (lessons #39/#40/#42). The union inherits all of
   them.

4. **Fail-closed lean.** A false-positive costs one blocked fetch (the agent
   learns the request looked like it carried a secret and must not send it); a
   false-negative leaks a secret. The scrub leans toward the former. The
   Rule-of-Two credential exclusion (ADR-001) remains the primary wall; this
   widened scrub is the belt to those braces.

## Scope — what this supersedes, and what it does NOT

This supersedes **ADR-002's entropy-rejection FOR THE OUTBOUND-SCRUB POLICY
ONLY.** Everything else in ADR-002 stands.

**The anonymiser's redaction policy is unchanged.** `_anonymiser` does NOT call
`find_secrets` or `find_catalogue_secrets`; it imports the raw compiled
catalogue patterns (`_ENV_SECRET_ASSIGNMENT`, `_IP_ADDRESS`, `_JWT`,
`_LONG_TOKEN`, `_SLACK_TOKEN`) and applies its own catalogue-only redact passes.
ADR-002's entropy-rejection still governs the anonymiser: its low-false-positive
posture is what keeps the founder's `/sulis:feedback` preview signal-dense
rather than noisy. The anonymiser is **not** routed through detect-secrets. The
`_anonymiser.py` source is byte-unchanged by WP-006, and the anonymiser +
anonymiser-characterisation suites prove it.

So the two policies are an explicit, named split:

| Policy | Detector | Posture |
|---|---|---|
| Outbound-scrub (`find_secrets`) | detect-secrets ∪ catalogue | fail-closed; entropy ON |
| Anonymiser redaction | catalogue only (raw patterns) | low-false-positive; entropy OFF (ADR-002) |

## Alternatives considered

- **Route both consumers through detect-secrets (rejected).** It would make the
  founder's feedback preview noisy with entropy false-positives — exactly what
  ADR-002 avoided. The two policies want different trades; keep them split.
- **Replace the catalogue entirely with detect-secrets (rejected).**
  detect-secrets does not classify private/loopback IPs as secrets, and the
  in-house env-assignment/slack/jwt/long-token shapes encode hardening lessons
  (#39/#40/#42). Keep the catalogue as the supplementary layer.
- **Shell out to the `detect-secrets` CLI (rejected).** The WP requires no
  shell-out (portability, latency, no subprocess in the scrub-before-DNS hot
  path). The in-process plugin API is the convention for embedding.

## Consequences

- The outbound-scrub now catches AWS keys, Google API keys, and generic
  high-entropy quoted/assigned tokens in addition to the catalogue shapes.
- A new runtime dependency (`detect-secrets>=1.5`) is declared in
  `pyproject.toml` and pinned in `uv.lock`; both CI workflows install it via
  `uv sync --frozen`.
- A residual honest limit remains: detection is still not exhaustive (a novel
  shape neither detector recognises can pass). The Rule-of-Two exclusion is the
  real wall; the scrub is defence-in-depth — now with a materially wider net.
- The detect-secrets entropy plugins will refuse some benign high-entropy
  quoted/assigned values in outbound bodies (e.g. a quoted commit SHA). This is
  the accepted fail-closed cost; prose mentions of SHAs/ULIDs/UUIDs stay clean.
