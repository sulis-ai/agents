---
# Identity (WP-01)
id: WP-008
title: "Tokenise hardcoded colours in the navigation-chrome stragglers"
kind: frontend
source: feature
change: CH-01KTHP
parent_phase: dark-mode-remediation
primitive: REORGANISE-Refactor
group: reorganise
purpose: "Tokenise the raw colour literals in the navigation-chrome straggler styles."

# Scope
atomic_branch: yes
estimate: small
blast_radius: low
dependsOn: [WP-001, WP-002]
characterisation_test: "apps/cockpit/client/src/tests/no-raw-colours.sidebar-files-liveness.test.ts"

# Verification (ADR-003 shape 1 — concrete)
verification:
  adapter: frontend
  artifact: "apps/cockpit/client/src/tests/no-raw-colours.sidebar-files-liveness.test.ts"

estimated_token_cost: "input: ~4k / output: ~3k"
status: pending

rollback: |
  Revert the commit. The four CSS modules return to raw literals / raw
  fallbacks. References existing tokens only, so tokens.css is untouched.
---

# WP-008 — Remediate hardcoded colours: sidebar + files panel + liveness dot

## Context

TDD §2 (audit finding) and acceptance criterion 4. This WP cleans up the
remaining stragglers, the sidebar/navigation + files-panel + status-dot family:

- `components/SidebarItem.module.css` — 1 raw literal (active-item highlight
  stays light blue) → `--primary` / the active-state token.
- `components/Sidebar.module.css` — 1 raw literal (error text colour) →
  `--destructive`.
- `components/LivenessDot.module.css` — running/terminal dot colours
  (`#28a745`/`#1e7e34`, `#f0a020`/`#c97f00`). **Decision required (per
  TDD §2):** status colours may legitimately stay fixed across themes. Default:
  map running → `--positive*` and terminal → `--warning*` so they re-theme to
  the brightened dark semantics; if the brightened tokens fail AA on the dark
  dot, keep the fixed status hues and document that in a CSS comment as a
  conscious exception (status-by-meaning, not theme-by-surface).
- `styles/FilesPanel.module.css` — `var(--x, #888)` fallback literals. These
  are token-first and low risk, but the raw fallback still counts under
  acceptance criterion 4: replace each `var(--x, #raw)` fallback with a
  token-only form (drop the raw fallback or fall back to another token).

References existing tokens only — does **not** edit `tokens.css`.

## Contract

**Files modified:**
- `apps/cockpit/client/src/components/SidebarItem.module.css`
- `apps/cockpit/client/src/components/Sidebar.module.css`
- `apps/cockpit/client/src/components/LivenessDot.module.css`
- `apps/cockpit/client/src/styles/FilesPanel.module.css`

**Files created:**
- `apps/cockpit/client/src/tests/no-raw-colours.sidebar-files-liveness.test.ts`

**Public surface:** none. Contract: no raw colour literal (including
`var(--x, #raw)` fallbacks) remains in the four modules, **except** any
LivenessDot status hue explicitly retained as a documented conscious exception;
light-mode rendered colour preserved.

## Definition of Done

**Red (characterisation):**
- `no-raw-colours.sidebar-files-liveness.test.ts` parses the four modules and
  asserts no raw colour literal remains (only `var(--*)`), with an allow-list
  for any LivenessDot line carrying the documented status-exception comment.
  Captures current light-mode values as baseline. Run it; it fails today.

**Green:**
- Replace literals/fallbacks with the nearest existing tokens. For LivenessDot,
  apply the default (`--positive*` / `--warning*`); if AA fails on the dark
  dot, retain the fixed hue with the documented-exception comment. Specs go
  green.

**Blue:**
- Confirm light-mode colours unchanged (baseline). Confirm `Sidebar.test.tsx`,
  `LivenessDot.test.tsx`, `FileTree.test.tsx`, `FilePane.test.tsx`,
  `FilePane.diff.test.tsx` stay green. Confirm any retained status hue carries
  a one-line conscious-exception comment. Re-confirm `tokens.css` untouched.

## Sequence

- Sequence ID: WP-008
- dependsOn: [WP-001, WP-002]

## Estimated Token Cost

input: ~4k / output: ~3k
