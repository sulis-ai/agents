---
id: CH-GJ9KQR-WP-010
change_id: "01KVX26BDXGJ9KQRJ11HACHMZV"
kind: backend
primitive: reinforce-harden
group: reinforce
title: Scrub modern OpenAI API keys (sk-proj-… / sk-…) on write to the thread store
status: pending
dependsOn: [CH-GJ9KQR-WP-002]
characterisation_test: plugins/sulis/scripts/tests/unit/test_secret_patterns.py
implements:
  - "spec:create-portable-agent-context#no-secret-leakage"
verification:
  adapter: backend
  artifact: plugins/sulis/scripts/tests/unit/test_secret_patterns.py
prov:
  wasGeneratedBy: "engineering-architect:codebase-audit"
  source: "prove-run gap GAP-3 (verified blind spot); spec Constraint 'No secret leakage'; TDD.md§4 (redaction-on-write)"
estimatedTokenCost:
  input: ~9k
  output: ~5k
---

## Context

Spec Constraint **"No secret leakage"** + TDD §4 (redaction-on-write to the new
durable store). The thread store (`thread_store_local.py`) scrubs every
persisted string through the shared catalogue (`_secret_patterns.find_secrets`)
before bytes land — so the catalogue is the single control point for "what gets
scrubbed on write."

**Verified blind spot (GAP 3).** The shared detector
`_secret_patterns.find_secrets` MISSES modern OpenAI keys. Driving the real
detector confirmed it: a realistic project key `sk-proj-…` and a legacy `sk-…`
key both produce **zero hits** from BOTH layers (detect-secrets AND the in-house
catalogue), while Stripe (`sk_live_…`), AWS (`AKIA…`) and GitHub (`ghp_…`) keys
are all correctly caught. Cause: the catalogue's `_LONG_TOKEN` prefix set
anchors on `sk_live_` / `sk_test_` (underscore) and uses a `[A-Za-z0-9_]{20,}`
suffix that excludes hyphens — so the hyphenated OpenAI shapes never match, and
the installed detect-secrets plugin set does not flag them either.

The thread store is a **new content-persistence surface** for agent
conversations, which routinely contain LLM API keys (the agent pastes/echoes
provider keys far more than a generic outbound request line does). An OpenAI key
echoed in a session would be saved VERBATIM into the durable store today. Close
the catalogue gap so OpenAI keys are scrubbed on write like the others.

## Contract

- Add OpenAI key pattern(s) to the in-house catalogue in `_secret_patterns.py`
  so `find_catalogue_secrets` (and therefore the `find_secrets` union, and
  therefore the store's `_scrub`) returns a hit for:
  - the project-scoped shape `sk-proj-<alnum/-/_ ≥20>`; and
  - the legacy shape `sk-<alnum ≥20>`,
  guarded against false positives on ordinary `sk-`-prefixed prose / short
  identifiers (anchor on length + the `proj-` infix where present; keep the
  same fail-closed-but-low-noise posture the catalogue already targets).
- Because the catalogue is the **one** shared source (Non-Negotiable #2), the
  redact consumer (`_anonymiser`), the outbound scrub (`find_secrets`), and the
  store's redaction-on-write all inherit the new pattern automatically — no
  second encoding. Add the new category to the catalogue's documented category
  list + the `SecretHit.category` comment.

## Definition of Done

**Red** — add failing cases to `test_secret_patterns.py` (catalogue layer) and
`test_secret_patterns_outbound.py` (union layer):

- A realistic `sk-proj-…` key → at least one hit (the new category).
- A realistic legacy `sk-…` key (≥ the chosen length floor) → at least one hit.
- Confirm the *current* failure: assert these are caught (the test fails before
  the pattern is added — the verified blind spot).
- **Negative cases (no false positives):** ordinary `sk-` prose
  (`sk-arund`, `ask-me`, a short `sk-1`), a git SHA, a ULID/UUID → NO hit.

**Green** — the OpenAI pattern(s) added to `_REGEX_CATALOGUE`; all Red cases
pass; the catalogue's existing characterisation + anonymiser suites still pass
(no loosening of the other patterns); a store-write redaction test (an OpenAI
key fed through `append_message` → stored bytes scrubbed to `[redacted-secret]`)
passes, proving the new pattern reaches the persistence surface.

**Blue** —
- One catalogue entry, two consumers inherit it (no duplication); category
  documented in the module docstring + `SecretHit.category` comment.
- No regression: re-run the full `_secret_patterns` + anonymiser + outbound
  suites; the Stripe/AWS/GitHub cases stay green and the false-positive guards
  hold (the `is_private_ip` / SHA-in-prose discipline is unchanged).

## Verification

Shape 1 (concrete): `adapter: backend`,
`artifact: tests/unit/test_secret_patterns.py` (+ outbound + a store-write
redaction case). A small, self-contained harden — the catalogue is the single
control point, so the change is one pattern + tests.

## Notes

- **Why REINFORCE-Harden.** A security primitive (the secret detector) is
  widened to cover a verified blind spot on a new persistence surface — the
  REINFORCE-Harden move, orthogonal to the structural WPs.
- **File scope (no overlap with WP-009):** `_secret_patterns.py` +
  `tests/unit/test_secret_patterns.py` + `tests/unit/test_secret_patterns_outbound.py`
  (+ optionally a store-write redaction case in
  `tests/integration/test_thread_store_local.py`). Parallelisable with WP-009.
- **Convention note (CP-01):** prefer extending the existing in-house catalogue
  (the established seam this codebase already uses for the slack/jwt/long-token
  hardening lessons #39/#40/#42) over reaching for a new detector dependency —
  the boring, single-source choice.

## Acceptance Evidence

- Branch: wp/create-portable-agent-context/wp-010-openai-key-detector-pattern (deleted post-merge)
- Completed: `2026-06-24T21:49:18Z` (Step 12 by calling session)
