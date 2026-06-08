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

- `components/StageBadge.module.css` — ~18 raw literals across all SIX active
  workflow stages (recon / specify / design / implement / review / ship), each
  with raw background, text colour, and border that stay light-on-light in dark
  mode. (The terminal `shipped` / `unknown` classes already use `var(--muted*)`
  tokens and need no change.)
- `pages/Dashboard.module.css` — ~4 raw literals (error banner stays light).

This is a REORGANISE-Refactor: behaviour-preserving in light mode (the visible
colour must not change in light), correct in dark mode. Per the TDD remediation
pattern, the stage-badge tints are a **genuinely new semantic need** → add a
token pair to **both** the light `:root` and the dark block in `tokens.css`
and reference it. The signed-off mockup now provides the stage-badge token
pairings for **all six** stages (WP-001 visual contract). Dashboard error
colours map to the existing `--destructive` / `--destructive-foreground`
tokens.

## Contract

**Files modified:**
- `apps/cockpit/client/src/tokens.css` — add the new stage-badge semantic
  tokens to **both** the light `:root` block and the
  `:root[data-theme="dark"]` block (created by WP-002). One trio per stage
  (`-bg` / `-fg` / `-border`) for **all six** stages. The suffix is `-border`
  (full word, matching `--border` / `--card-foreground`); the early `-bd`
  shorthand is retired. **Copy the exact values from the signed-off mockup**
  (`mockup/dark-theme.html`) — it is the value source of truth. The 18 light
  values equal today's literals (pixel-unchanged); the 18 dark values are the
  signed-off pairings:

  | Stage | Light bg / fg / border | Dark bg / fg / border |
  |---|---|---|
  | recon     | `#f1f8ff` / `#2563EB` / `#c8e1ff` | `#16263a` / `#7fb0ff` / `#234a73` |
  | specify   | `#fff5b1` / `#735c0f` / `#ffd33d` | `#332b10` / `#f0c75a` / `#5c4d1e` |
  | design    | `#e6e6fa` / `#4b0082` / `#c5c5e6` | `#241c3a` / `#b79cff` / `#3d2f63` |
  | implement | `#e1ffe1` / `#22863a` / `#c0e6c0` | `#1a3014` / `#9bd86a` / `#345526` |
  | review    | `#fff0e6` / `#c04a00` / `#ffd0b0` | `#3a2310` / `#f2a368` / `#63401f` |
  | ship      | `#d4edda` / `#155724` / `#a5d6a7` | `#13301d` / `#73d391` / `#245636` |

  **`recon` text — light-mode pixel-unchanged check:** today the `.recon`
  class uses `color: var(--primary)`, which resolves to `#2563EB` in light.
  The signed-off `--stage-recon-fg` light value is `#2563EB` — identical — so
  switching `.recon` to `color: var(--stage-recon-fg)` is pixel-unchanged in
  light. In dark the badge text becomes `#7fb0ff` (a badge-tuned blue brighter
  than core `--primary` `#5b9bff`, for the recon tinted bg) — this is the
  founder-signed value and is the intended dark behaviour, not a regression
  (light is the pixel-unchanged baseline; dark is net-new).
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
  `rgb()/rgba()`, named colours) appears in the six active stage classes or the
  dashboard error chrome — only `var(--*)`. Run it; it fails (raw literals
  present today). This also captures the current light-mode colour values as
  the regression baseline (assert each new token's **light** value equals the
  literal it replaces, per the Contract table above).
- The test references the reconciled token names — `--stage-{stage}-bg`,
  `--stage-{stage}-fg`, `--stage-{stage}-border` for each of
  recon/specify/design/implement/review/ship (suffix `-border`, **not** `-bd`).
  Assert all 18 light + 18 dark token definitions are present in `tokens.css`
  with the exact values from the Contract table (which mirror the signed-off
  mockup).

**Green:**
- Add the six stage-badge token trios to both theme blocks in `tokens.css`
  (light values = the current literals; dark values from the signed-off
  mockup — see Contract table). Use the `-border` suffix. Replace the literals
  in `StageBadge.module.css` for all six active stages with the corresponding
  `var(--stage-*-{bg,fg,border})`, including switching `.recon`'s
  `color: var(--primary)` to `color: var(--stage-recon-fg)` (light value is
  identical → pixel-unchanged). Map dashboard error colours to
  `--destructive*`. Specs go green.

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
