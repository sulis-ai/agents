---
# Identity (WP-01)
id: WP-007
title: "Tokenise hardcoded colours in the conversation-view panels"
kind: frontend
source: feature
change: CH-01KTHP
parent_phase: dark-mode-remediation
primitive: REORGANISE-Refactor
group: reorganise
purpose: "Tokenise the raw colour literals in the conversation-view styles."

# Scope
atomic_branch: yes
estimate: medium
blast_radius: low
dependsOn: [WP-001, WP-002]
characterisation_test: "apps/cockpit/client/src/tests/no-raw-colours.thread-chat.test.ts"

# Verification (ADR-003 shape 1 — concrete)
verification:
  adapter: frontend
  artifact: "apps/cockpit/client/src/tests/no-raw-colours.thread-chat.test.ts"

estimated_token_cost: "input: ~5k / output: ~4k"
status: pending

rollback: |
  Revert the commit. Thread/Chat CSS returns to raw literals. No new tokens
  are added by this WP (it references existing tokens only), so tokens.css is
  untouched and there is nothing else to undo.
---

# WP-007 — Remediate hardcoded colours: thread + chat panels

## Context

TDD §2 (audit finding) and acceptance criterion 4. This WP tokenises the
conversation-view family:

- `styles/Thread.module.css` — ~9 raw literals: error banners, ok/warn status
  dots, white card backgrounds.
- `styles/Chat.module.css` — ~6 raw literals: white message background, yellow
  note callout, blue user bubble.

Behaviour-preserving in light mode; correct in dark. Per the TDD remediation
pattern, each literal maps to the **nearest existing token** wherever one
exists (white card bg → `--card`; error → `--destructive*`; warn → `--warning*`;
ok → `--positive*`; user bubble → `--primary*`; note callout → `--warning*` or
the muted surface). This WP references existing tokens only — it does **not**
edit `tokens.css` (so no peer-collision with WP-002/WP-006). If a literal has
no reasonable existing token, surface it rather than inventing a one-off here.

## Contract

**Files modified:**
- `apps/cockpit/client/src/styles/Thread.module.css` — replace every raw
  literal with the nearest existing `var(--*)`.
- `apps/cockpit/client/src/styles/Chat.module.css` — same.

**Files created:**
- `apps/cockpit/client/src/tests/no-raw-colours.thread-chat.test.ts`

**Public surface:** none. Contract: zero raw colour literals remain in the two
modules; they reference only existing tokens; light-mode rendered colour is
preserved.

## Definition of Done

**Red (characterisation):**
- `no-raw-colours.thread-chat.test.ts` parses both modules and asserts no raw
  colour literal remains (only `var(--*)`). Captures current light-mode values
  as the baseline. Run it; it fails today.

**Green:**
- Replace each literal with the nearest existing token. Specs go green.

**Blue:**
- Confirm light-mode colours unchanged (baseline). Confirm `Chat.test.tsx`,
  `ChatMessage.test.tsx`, `ThreadView.test.tsx` stay green. Confirm no new
  token was silently invented (this WP touches only the two CSS modules — if a
  genuinely new token was needed, that is a flag back to the planner, not an
  inline addition). Re-confirm `tokens.css` was not modified.

## Sequence

- Sequence ID: WP-007
- dependsOn: [WP-001, WP-002]
  (WP-002 so the dark token values these sites reference are defined.)

## Estimated Token Cost

input: ~5k / output: ~4k
