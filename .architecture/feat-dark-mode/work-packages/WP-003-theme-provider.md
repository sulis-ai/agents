---
# Identity (WP-01)
id: WP-003
title: "Add the theme context layer (provider, hook, resolver, root wiring)"
kind: frontend
source: feature
change: CH-01KTHP
parent_phase: dark-mode-foundation
primitive: EXPAND-Create
group: expand
purpose: "Add the theme context layer that owns the active theme."

# Scope
atomic_branch: yes
estimate: medium
blast_radius: low
dependsOn: [WP-001]

# Verification (ADR-003 shape 1 — concrete)
verification:
  adapter: frontend
  artifact: "apps/cockpit/client/src/tests/theme/resolveInitialTheme.test.ts, apps/cockpit/client/src/tests/theme/ThemeProvider.test.tsx"

estimated_token_cost: "input: ~5k / output: ~5k"
status: pending

rollback: |
  Revert the commit. App.tsx returns to wrapping AppRoutes directly in
  BrowserRouter; the theme/ directory is removed. No persisted data depends
  on it (localStorage key is read-tolerant of absence).
---

# WP-003 — Theme provider, hook, initial-theme resolver, and root wiring

## Context

ADR-001 (theme mechanism) and TDD §3 (Form) + §5.1/§5.2 (Proof). This WP
introduces the small React theming layer that owns the active theme as state,
sets `document.documentElement.dataset.theme`, persists the choice, and
exposes it via a hook. It is the **provider that every other theme consumer
depends on** (the toggle in WP-004 and the Monaco binding in WP-005). It does
NOT add the toggle control and does NOT touch the token CSS — those are
separate WPs.

The two pure helpers are the testable seams (no React dependency):
`resolveInitialTheme()` (`saved ?? OS-preference`, with a `light` fallback if
`localStorage`/`matchMedia` throw) and the persistence write on toggle.

## Contract

**Files created:**
- `apps/cockpit/client/src/theme/resolveInitialTheme.ts` — pure function
  `resolveInitialTheme(): "light" | "dark"`. Reads the saved choice from
  `localStorage` (key `cockpit.theme`); if present and valid, returns it
  (ignores OS). If absent, reads `window.matchMedia("(prefers-color-scheme:
  dark)")`. If either API throws (private mode / old runtime), returns
  `"light"` without throwing.
- `apps/cockpit/client/src/theme/ThemeProvider.tsx` — `ThemeProvider`
  component + `useTheme()` hook. Provider holds `theme` state initialised from
  `resolveInitialTheme()`, sets `documentElement.dataset.theme` on mount and
  on every change, and persists to `localStorage` on `setTheme`/`toggle`.
  `useTheme()` returns `{ theme, setTheme, toggle }`.
- `apps/cockpit/client/src/tests/theme/resolveInitialTheme.test.ts`
- `apps/cockpit/client/src/tests/theme/ThemeProvider.test.tsx`

**Files modified:**
- `apps/cockpit/client/src/App.tsx` — wrap `<BrowserRouter>` (in `App`) with
  `<ThemeProvider>`. `AppRoutes` is unchanged so existing `MemoryRouter`-based
  tests keep mounting it directly.

**Public surface (exports):**
- `resolveInitialTheme(): Theme`  where `type Theme = "light" | "dark"`.
- `ThemeProvider({ children }): JSX.Element`
- `useTheme(): { theme: Theme; setTheme(t: Theme): void; toggle(): void }`
- The `localStorage` key constant `cockpit.theme` (exported so WP-004's tests
  and WP-005 reference one source of truth).

## Definition of Done

**Red:**
- `resolveInitialTheme.test.ts` (per TDD §5.1): saved present → returns saved
  (ignores OS); saved absent + OS dark → `dark`; saved absent + OS light →
  `light`; `localStorage` throwing → `light`; `matchMedia` throwing → `light`.
- `ThemeProvider.test.tsx` (per TDD §5.2, jsdom + Testing Library): on mount
  with nothing saved + OS dark, `documentElement.dataset.theme === "dark"`;
  calling `toggle()` flips `data-theme` and writes `localStorage`; after a
  simulated remount with a saved choice that contradicts OS, the saved choice
  wins. Run both; they fail (modules don't exist).

**Green:**
- Implement `resolveInitialTheme.ts` and `ThemeProvider.tsx` (boring code: no
  reflection, explicit try/guard around the two browser APIs). Wire
  `ThemeProvider` into `App.tsx` around `BrowserRouter`. Specs go green.

**Blue:**
- Confirm the full existing suite stays green — in particular
  `routing.test.tsx`, `Shell.test.tsx` (they mount `AppRoutes` via
  `MemoryRouter`, which must not require the provider). Extract the `Theme`
  type and the storage-key constant to one place so WP-004/WP-005 import
  rather than re-declare. jest-axe is N/A here (no rendered UI surface; the
  provider renders only `children`).

## Sequence

- Sequence ID: WP-003
- dependsOn: [WP-001]

## Estimated Token Cost

input: ~5k / output: ~5k
