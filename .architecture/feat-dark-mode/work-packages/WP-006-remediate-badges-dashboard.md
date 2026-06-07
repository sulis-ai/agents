---
# Identity (WP-01)
id: WP-006
title: "Tokenise hardcoded colours in the dashboard change-card surface"
kind: frontend
source: feature
change: CH-01KTHP
parent_phase: dark-mode-remediation
primitive: REORGANISE-Refactor
group: reorganise
purpose: "Tokenise the raw colour literals in the dashboard change-card styles."

# Scope
atomic_branch: yes
estimate: medium
blast_radius: low
dependsOn: [WP-001, WP-002]
characterisation_test: "apps/cockpit/client/src/tests/no-raw-colours.badges.test.ts"

# Verification (ADR-003 shape 1 — concrete)
verification:
  adapter: frontend
  artifact: "apps/cockpit/client/src/tests/no-raw-colours.badges.test.ts"

estimated_token_cost: "input: ~5k / output: ~4k"
status: pending

rollback: |
  Revert the commit. The badge/dashboard CSS returns to raw literals; any new
  stage-badge tokens added to tokens.css in this WP are removed from both the
  light and dark blocks. No component logic changes to undo.
---

# WP-006 — Remediate hardcoded colours: stage badges + dashboard chrome

## Context

TDD §2 (audit finding — 32 hardcoded colour sites that will not re-theme) and
the spec's acceptance criterion 4 ("no raw hard-coded colours that ignore the
theme"). This WP tokenises the two files that make up the dashboard's
change-card surface:

- `components/StageBadge.module.css` — ~12 raw literals: per-stage light tints
  (recon / specify / design / implement / review / ship) with raw backgrounds,
  text colours, and borders that stay light-on-light in dark mode.
- `pages/Dashboard.module.css` — ~4 raw literals (error banner stays light).

This is a REORGANISE-Refactor: behaviour-preserving in light mode (the visible
colour must not change in light), correct in dark mode. Per the TDD remediation
pattern, the stage-badge tints are a **genuinely new semantic need** → add a
token pair to **both** the light `:root` and the dark block in `tokens.css`
and reference it. The mockup already proposes the stage-badge token pairings
(WP-001 visual contract). Dashboard error colours map to the existing
`--destructive` / `--destructive-foreground` tokens.

## Contract

**Files modified:**
- `apps/cockpit/client/src/tokens.css` — add the new stage-badge semantic
  tokens to **both** the light `:root` block and the
  `:root[data-theme="dark"]` block (created by WP-002). Names follow the
  existing convention (e.g. `--stage-recon-bg`, `--stage-recon-fg`,
  `--stage-recon-border`, … per stage) using the values from the signed-off
  mockup.
- `apps/cockpit/client/src/components/StageBadge.module.css` — replace every
  raw literal with `var(--*)`.
- `apps/cockpit/client/src/pages/Dashboard.module.css` — replace raw error
  colours with the existing `--destructive*` tokens.

**Files created:**
- `apps/cockpit/client/src/tests/no-raw-colours.badges.test.ts`

**Public surface:** none (CSS + tokens only). The contract is: zero raw colour
literals remain in the two CSS modules; light-mode rendered colour is
unchanged; the new tokens exist in both theme blocks.

> **Peer-collision note:** this WP edits `tokens.css`, which WP-002 creates the
> dark block in → it `dependsOn: WP-002` and runs sequentially after it, not in
> parallel. It is the only remediation WP that touches `tokens.css`.

## Definition of Done

**Red (characterisation):**
- `no-raw-colours.badges.test.ts` parses `StageBadge.module.css` and
  `Dashboard.module.css` and asserts **no raw colour literal** (`#hex`,
  `rgb()/rgba()`, named colours) appears — only `var(--*)`. Run it; it fails
  (raw literals present today). This also captures the current light-mode
  colour values as the regression baseline (assert each new token's light
  value equals the literal it replaces).

**Green:**
- Add the stage-badge token pairs to both theme blocks in `tokens.css` (light
  values = the current literals; dark values from the mockup). Replace the
  literals in both CSS modules with the corresponding `var(--*)`. Map dashboard
  error colours to `--destructive*`. Specs go green.

**Blue:**
- Confirm light-mode colours are pixel-unchanged (the baseline assertions).
  Confirm the new tokens appear in BOTH the light and dark blocks (re-run
  WP-002's `tokens.dark.test.ts` set-equality — it must still pass with the
  added pairs present in both). Confirm `StageBadge.test.tsx` and
  `Dashboard.test.tsx` stay green. Status-style dots (LivenessDot) are out of
  scope here — handled in WP-008.

## Sequence

- Sequence ID: WP-006
- dependsOn: [WP-001, WP-002]

## Estimated Token Cost

input: ~5k / output: ~4k
