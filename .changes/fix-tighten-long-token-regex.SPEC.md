---
founder_facing: false
---
# Spec — tighten _LONG_TOKEN to drop casual-reference false positives (closes #42)

**Closes:** [#42](https://github.com/sulis-ai/agents/issues/42)

## Bug

`_LONG_TOKEN`'s suffix allows hyphens (`[A-Za-z0-9_\-]{20,}`). With
prefixes like `xoxp-`, `xoxb-`, casual hyphenated references (e.g.
`xoxp-token-style-identifiers`, 23 chars after `xoxp-`) get scrubbed
to `<secret>` even though they're docs prose.

Usability-only — no privacy regression. Just a paper-cut for founders
discussing Slack token formats in feedback bodies.

## Fix

Split into TWO patterns:

1. `_SLACK_TOKEN`: matches the actual Slack token shape — prefix
   (`xoxp/xoxb/xoxa/xoxr/xoxs`) followed by ≥ 3 hyphen-separated
   numeric blocks then an alphanumeric tail. Real shape:
   `<prefix>-<digits>-<digits>-<digits>-<20+ alnum>`. Casual prose
   like `xoxp-token-style-identifiers` doesn't have the numeric
   blocks, so won't match.
2. `_LONG_TOKEN`: drop `xoxp-/xoxb-/xoxa-/xoxr-` from the prefix
   list (now in `_SLACK_TOKEN`); tighten suffix to
   `[A-Za-z0-9_]{20,}` — disallows hyphens. Real GitHub PATs / Stripe
   keys / AWS access keys / Google API keys / npm tokens use
   alphanumeric + underscore, not hyphens.

## How we'll know it's done

- `xoxp-token-style-identifiers` → preserved (not redacted)
- Real-shape Slack token `xoxp-12345-67890-12345-{20-char alnum tail}`
  → `<secret>`
- All existing token tests still pass (Stripe `sk_live_...`, GitHub
  `ghp_...`, JWT) — pinned regression
- Full anonymiser test suite green
- Step 4.5 review gate PASS

## What to avoid

- **Do NOT drop the Slack prefixes entirely.** They're real tokens
  with hyphens in their shape — `_SLACK_TOKEN` MUST still catch them,
  it just requires the genuine numeric-block structure.
- **Do NOT add token entropy heuristics.** The lesson body floats
  Shannon-entropy as an option; that's over-engineering for the
  one-pattern fix. Shape-based recognition is simpler + correct.

## References

- Issue #42, `_anonymiser.py:174-184` (current `_LONG_TOKEN`)
- `tests/unit/test_anonymiser.py` Secrets section
