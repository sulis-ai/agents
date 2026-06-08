---
# Identity (WP-01)
id: WP-005
title: "Bind both Monaco wrappers to the active app theme via monacoThemeFor()"
kind: frontend
source: feature
change: CH-01KTHP
parent_phase: dark-mode-ui
primitive: SUBSTITUTE-Replace
group: substitute
purpose: "Replace the hardcoded Monaco theme with one derived from the active app theme."

# Scope
atomic_branch: yes
estimate: medium
blast_radius: low
dependsOn: [WP-001, WP-002, WP-003]

# Verification (ADR-003 shape 1 — concrete)
verification:
  adapter: frontend
  artifact: "apps/cockpit/client/src/tests/theme/monacoThemeFor.test.ts, apps/cockpit/client/src/tests/MonacoFile.test.tsx, apps/cockpit/client/src/tests/MonacoDiff.test.tsx"

estimated_token_cost: "input: ~4k / output: ~3k"
status: pending

rollback: |
  Revert the commit. Both wrappers return to the hardcoded theme="vs-dark";
  monacoThemeFor.ts is removed. Read-only guarantees were never touched.
---

# WP-005 — Monaco follows the app theme

## Context

ADR-002 (Monaco theme binds to the active app theme) and TDD §3 + §5.3.
Monaco does not ride the CSS-variable cascade — it takes a `theme` prop with a
Monaco theme id. Today `MonacoFileInner.tsx` (line 33) and
`MonacoDiffInner.tsx` (line 45) both hardcode `theme="vs-dark"`, producing
dark code inside a light app. This WP replaces those with a value derived from
`useTheme()` through one shared helper, so flipping the toggle restyles both
editors live with no remount.

This is `SUBSTITUTE-Replace` (swap a hardcoded literal for a computed value),
not a wrap — the wrappers are the project's own adapters to Monaco and are
edited in place.

## Contract

**Files created:**
- `apps/cockpit/client/src/theme/monacoThemeFor.ts` — pure function
  `monacoThemeFor(theme: Theme): "vs" | "vs-dark"`: `dark → "vs-dark"`,
  `light → "vs"`. Single source of truth for the mapping (ADR-002).
- `apps/cockpit/client/src/tests/theme/monacoThemeFor.test.ts`

**Files modified:**
- `apps/cockpit/client/src/components/MonacoFileInner.tsx` — replace
  `theme="vs-dark"` with `theme={monacoThemeFor(useTheme().theme)}`.
- `apps/cockpit/client/src/components/MonacoDiffInner.tsx` — same replacement.
- `apps/cockpit/client/src/tests/MonacoFile.test.tsx` — add a
  theme-follows-app assertion; existing `readOnly`/minimap assertions stay.
- `apps/cockpit/client/src/tests/MonacoDiff.test.tsx` — same.

**Public surface:** `monacoThemeFor(theme): "vs" | "vs-dark"`. The wrappers'
external props (`content`, `language`) are unchanged.

## Definition of Done

**Red:**
- `monacoThemeFor.test.ts`: `dark → "vs-dark"`, `light → "vs"`.
- Extend `MonacoFile.test.tsx` / `MonacoDiff.test.tsx` (per TDD §5.3): render
  the wrapper inside a `ThemeProvider`; assert the mocked `<Editor>` receives
  `theme="vs"` in light and `theme="vs-dark"` in dark; flipping the provider
  theme changes the prop. The **existing `options.readOnly === true` and
  minimap assertions must still pass** (no regression). Run; the new
  assertions fail (still hardcoded).

**Green:**
- Implement `monacoThemeFor.ts`. Change the one `theme=` line in each wrapper
  to consume `useTheme()` via the helper. Specs go green.

**Blue:**
- Confirm both Monaco test files are green including the untouched read-only
  assertions. Confirm no second copy of the mapping exists (both wrappers and
  any future surface import `monacoThemeFor`). Confirm the lazy-loading
  assertion in `MonacoFile.test.tsx` still holds (the wrapper stays the lazy
  chunk).

## Sequence

- Sequence ID: WP-005
- dependsOn: [WP-001, WP-002, WP-003]
  (WP-003 for `useTheme()`/`Theme`; WP-002 so the dark surfaces the editor
  sits within are themed when this lands — keeps the integration coherent.)

## Estimated Token Cost

input: ~4k / output: ~3k
