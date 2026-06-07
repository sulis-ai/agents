---
# Identity (WP-01)
id: WP-002
title: "Add the dark token block to tokens.css"
kind: frontend
source: feature
change: CH-01KTHP
parent_phase: dark-mode-foundation
primitive: EXPAND-Extend
group: expand
purpose: "Add a :root[data-theme=\"dark\"] colour block to tokens.css."

# Scope
atomic_branch: yes
estimate: small
blast_radius: low
dependsOn: [WP-001]

# Verification (ADR-003 shape 1 — concrete)
verification:
  adapter: frontend
  artifact: "apps/cockpit/client/src/tests/tokens.dark.test.ts"

estimated_token_cost: "input: ~3k / output: ~2k"
status: pending

rollback: |
  Revert the single commit. The dark block is purely additive — removing it
  returns the app to light-only; no component logic changes were made.
---

# WP-002 — Dark token block in `tokens.css`

## Context

TDD §6 (the dark token set) and ADR-001 (theme mechanism: CSS custom
properties overridden under a root attribute selector). This WP adds a
`:root[data-theme="dark"] { … }` block to
`apps/cockpit/client/src/tokens.css`, redefining every colour variable the
light `:root` already defines with the dark values. **No component is
touched** — components keep reading `var(--*)`; the cascade re-themes them.

The values are copied **verbatim** from the founder-signed mockup at
`.architecture/feat-dark-mode/mockup/dark-theme.html` — its
`:root[data-theme="dark"]` block is the canonical source (TDD §6 authoring
note). The de-duplicated final values are `--border-muted: #2a2e36` and
`--positive: #4caf68` per the TDD note.

## Contract

**Files modified:**
- `apps/cockpit/client/src/tokens.css` — append one
  `:root[data-theme="dark"]` block after the existing `:root` block.

**Files created:**
- `apps/cockpit/client/src/tests/tokens.dark.test.ts` — the spec below.

**Public surface:** none (no exports, no component changes). The contract is
the CSS variable set: every colour custom property defined in light `:root`
MUST also be defined in the dark block. Radius / typography / weight tokens
are intentionally NOT redefined (they inherit from `:root`).

**Variables that must appear in the dark block** (the complete colour set
from light `:root`): `--background --foreground --card --card-foreground
--popover --popover-foreground --muted --muted-foreground --secondary
--secondary-foreground --border --border-muted --input --primary
--primary-foreground --accent --accent-foreground --destructive
--destructive-foreground --positive --positive-foreground --warning
--warning-foreground --ring --brand-gold --brand-depth`.

## Definition of Done

**Red:**
- Write `tokens.dark.test.ts`. It parses `tokens.css` as text and asserts:
  (a) a `:root[data-theme="dark"]` selector block exists; (b) every colour
  custom property present in the light `:root` block is also present in the
  dark block (set-equality over the colour-token names above); (c) no colour
  token in the dark block resolves to a duplicate/contradictory definition
  (each name defined exactly once in the dark block). Run it; it fails
  because the dark block does not yet exist.

**Green:**
- Append the `:root[data-theme="dark"]` block, copied verbatim from the
  mockup's canonical block (final de-duplicated values). The spec goes green.

**Blue:**
- Confirm no light-token name is missing from the dark block and no stray
  radius/type/weight token leaked into the dark block (they belong only in
  `:root`). Confirm the file still parses (no trailing-comma / brace errors)
  and the existing suite stays green. Leave a one-line comment in `tokens.css`
  pointing at the mockup as the value source.

## Sequence

- Sequence ID: WP-002
- dependsOn: [WP-001]  (the signed-off visual contract gate; #45 / UXD-14)

## Estimated Token Cost

input: ~3k / output: ~2k
