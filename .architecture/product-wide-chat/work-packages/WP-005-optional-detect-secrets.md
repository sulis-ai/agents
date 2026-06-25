---
id: WP-005
change_id: "01KW064YHSG3Y4RMD4M9Y3M72S"
kind: backend
primitive: reinforce-harden
group: reinforce
title: Make detect_secrets optional in the shared scrub (degrade to the catalogue)
status: step-7-complete
dependsOn: []
implements:
  - "spec:create-product-wide-chat#redaction-on-write"
verification:
  adapter: backend
  artifact: plugins/sulis/scripts/tests/unit/test_secret_patterns.py
prov:
  wasGeneratedBy: "concierge:regression-hotfix"
---

# WP-005 — Make `detect_secrets` optional in the shared scrub

## Context

A regression-hotfix surfaced by the WP-004 integration train: the cockpit
`read-only-and-tests` CI check failed (3 tests in `chat-scope-store.contract.test.ts`)
with `ModuleNotFoundError: No module named 'detect_secrets'`. The chat-append
redaction path (`sulis-chat-append` → `_session_manager` scrub →
`plugins/sulis/scripts/_secret_patterns.py`) imported `detect_secrets` at module
level. `detect_secrets` is a uv-locked dep present under the pytest/uv env (so the
portable-context Python tests pass), but the cockpit server spawns plain `python3`
(no uv env), so the import crashed and took down every chat-turn save.

## Contract / Definition of Done

- The `detect_secrets` import in `_secret_patterns.py` is OPTIONAL (try/except
  ImportError → `_DETECT_SECRETS_AVAILABLE` flag); when absent, `_find_detect_secrets`
  / `_detect_secrets_plugins` degrade to no-op and `find_secrets` falls back to the
  in-house catalogue alone (still redacts Stripe/AWS/GitHub/OpenAI/env/private-IP
  shapes). The scrub NEVER crashes on the missing optional enhancer.
- When `detect_secrets` IS present (pytest/uv), behaviour is byte-for-byte unchanged
  (no regression to the shipped portable-context redaction).
- RED→GREEN: a test simulating the missing dependency (meta-path block) asserting
  the module imports, a catalogue secret is still redacted, and `find_secrets` does
  not raise; the 3 `chat-scope-store.contract.test.ts` tests pass.

## Sequence (RGB)

Red (4 tests, missing-dep simulated) → Green (optional import + flag-gated degrade)
→ Blue (no duplication; single fallback path). Code-review gate PASS.

> Note (record): for stronger runtime redaction the cockpit could invoke the
> chat-append under the uv env so detect_secrets is present — but graceful
> degradation to the catalogue is the correct robustness posture regardless.

## Acceptance Evidence

- Branch: wp/create-product-wide-chat/wp-005-optional-detect-secrets (deleted post-merge)
- Completed: `2026-06-25T23:43:21Z` (Step 12 by calling session)
