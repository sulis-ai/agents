---
# Identity (WP-01)
id: WP-004
title: "Add the ThemeToggle control to the Shell top bar"
kind: frontend
source: feature
change: CH-01KTHP
parent_phase: dark-mode-ui
primitive: EXPAND-Create
group: expand
purpose: "Add a light/dark toggle control to the Shell, reachable on every route."

# Scope
atomic_branch: yes
estimate: medium
blast_radius: low
dependsOn: [WP-001, WP-003]
visual_contract: WP-001

# Verification (ADR-003 shape 1 — concrete)
verification:
  adapter: frontend
  artifact: "apps/cockpit/client/src/tests/ThemeToggle.test.tsx"

estimated_token_cost: "input: ~4k / output: ~4k"
status: pending

rollback: |
  Revert the commit. The Shell top-bar region and ThemeToggle are removed;
  Shell returns to sidebar + outlet. The provider (WP-003) is untouched, so
  OS-preference theming still works without a manual control.
---

# WP-004 — `ThemeToggle` in the Shell top bar

## Context

ADR-001 (the toggle "lives in the app shell so it is reachable from every
screen") and TDD §3 (Form — mount points). The actual shell at
`apps/cockpit/client/src/layouts/Shell.tsx` currently renders only
`<Sidebar />` + `<main><Outlet/></main>` with no top bar. This WP introduces
a **minimal, colours-only top-bar region** in the Shell to host the toggle —
no layout redesign of the sidebar or outlet, no spacing/content changes
elsewhere (Non-goal in the spec). The control consumes `useTheme()` from
WP-003.

> **Path note:** TDD §3 proposed `src/components/ThemeToggle.tsx`. That path
> is honoured (the control is a base component under `components/`); the Shell
> top-bar region is added in `layouts/Shell.tsx` since that is where the
> shell actually lives. No user-facing difference — the rendered result is
> the signed-off mockup's toggle.

## Contract

**Files created:**
- `apps/cockpit/client/src/components/ThemeToggle.tsx` — a base component:
  stateless beyond `useTheme()`, token-consuming, accessible. Renders a
  control whose accessible name reflects the action (e.g. an
  `aria-label`/`aria-pressed` button "Switch to dark theme" / "Switch to
  light theme"); calls `toggle()` on activate; keyboard-operable with a
  visible focus ring (no `outline:none`). State is conveyed by name/role, not
  colour alone (WCAG AA, information-not-by-colour).
- `apps/cockpit/client/src/components/ThemeToggle.module.css` — token-only
  styles (`var(--*)`), no raw colours.
- `apps/cockpit/client/src/tests/ThemeToggle.test.tsx`

**Files modified:**
- `apps/cockpit/client/src/layouts/Shell.tsx` — add a minimal top-bar region
  rendering `<ThemeToggle />` above (or adjacent to) the existing two-pane
  layout, present on every route. Existing `data-testid="shell-outlet"` and
  the sidebar are unchanged.
- `apps/cockpit/client/src/layouts/Shell.module.css` — add the top-bar
  region's layout/colour rules using tokens only.

**Public surface:** `ThemeToggle` (default or named export). No new data flow;
it reads/writes theme via the WP-003 context.

## Definition of Done

**Red:**
- `ThemeToggle.test.tsx` (jsdom + Testing Library, rendered inside a
  `ThemeProvider`): the control renders with an accessible name; activating it
  (click + keyboard Enter/Space) flips `documentElement.dataset.theme`;
  `aria-pressed` (or equivalent) reflects the active theme. Includes a
  **jest-axe** assertion (WPF-06 — zero violations). Run it; it fails (no
  component).
- Add/extend a Shell test asserting the toggle is present in the shell on a
  route render (so it is reachable from every screen).

**Green:**
- Implement `ThemeToggle.tsx` + its module CSS (tokens only). Add the minimal
  top-bar region to `Shell.tsx`/`Shell.module.css`. Specs go green.

**Blue:**
- Confirm `Shell.test.tsx` and `routing.test.tsx` stay green (the top bar is
  additive; the outlet and sidebar testids are unchanged). Confirm no raw hex
  entered `ThemeToggle.module.css` or the new Shell rules. Confirm visible
  focus ring + keyboard operation. Confirm the rendered toggle matches the
  signed-off mockup's control (WP-001 visual contract).

## Sequence

- Sequence ID: WP-004
- dependsOn: [WP-001, WP-003]

## Estimated Token Cost

input: ~4k / output: ~4k
