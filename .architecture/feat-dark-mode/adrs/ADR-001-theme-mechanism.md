# ADR-001 — Theme mechanism: CSS custom properties under a root `data-theme` selector, with a React context and `localStorage` persistence

> Status: accepted · Date: 2026-06-07 · Change: CH-01KTHP

## Decision

Implement light/dark theming as the **established web convention** for
token-driven theming:

1. **Colour values switch via CSS custom properties overridden under a
   selector on the document root.** The existing `:root { --background: ... }`
   block in `tokens.css` becomes the **light** set. A second block,
   `:root[data-theme="dark"] { --background: ...; ... }`, redefines every
   surface and semantic variable with dark values. Components keep reading
   `var(--*)` and are not touched. This is the mechanism the spec Constraints
   already mandate.
2. **A small React theme context/provider** (`ThemeProvider`) owns the
   active theme as state, sets `document.documentElement.dataset.theme`,
   and exposes `{ theme, setTheme, toggle }` via a `useTheme()` hook.
3. **First-visit default reads the OS preference** via
   `window.matchMedia("(prefers-color-scheme: dark)")`.
4. **Persistence uses `localStorage`** under one key
   (`cockpit.theme`). Resolution order on load: **saved choice if present,
   otherwise the OS preference.** Once the founder toggles, the saved value
   wins on every later visit.
5. **The provider mounts at the app root** (`App.tsx`, wrapping
   `BrowserRouter`) so every route is inside it. The toggle control lives in
   the app shell top bar (`Shell.tsx`) so it is reachable from every screen.

## Why this is the convention (CP-01..CP-05)

- **CSS custom properties + a root attribute selector** is the dominant,
  boring, framework-agnostic way to theme a token-driven web app
  (shadcn/ui, Radix, Tailwind's `darkMode: "class"`, the GOV.UK and USWDS
  systems all do a variant of this). The colours change in one place; the
  whole tree re-themes through CSS cascade with zero per-component logic.
- **`prefers-color-scheme` for first visit** is the W3C Media Queries Level 5
  standard signal for OS theme preference. It is the established answer to
  "what should a first-time visitor see."
- **`localStorage` for the remembered choice** is the established browser
  store for a small, per-device, non-sensitive user preference. The choice
  is read synchronously at startup, so there is no flash of the wrong theme.
- **A React context** is the established React way to make one value
  (the active theme + a setter) available app-wide without prop-drilling.

## Avoiding the flash-of-wrong-theme (FOUC)

The effective theme is resolved and `data-theme` is set **before first
paint** — the provider reads `localStorage` + `matchMedia` during its
initial render (synchronous), and the initial state initialiser sets the
root attribute. Because the cockpit is a Vite SPA (not server-rendered),
a one-line inline bootstrap in `index.html` is the belt-and-braces option;
the TDD specifies the provider-initialiser path as primary and notes the
inline guard as an optional reinforcement.

## Alternatives considered and rejected

- **Two full stylesheets, swapped at runtime.** Rejected: doubles the CSS,
  forces a network/parse swap on toggle, and fights the existing
  single-tokens-file design the spec mandates.
- **Per-component theme props / a theme prop threaded through every
  component.** Rejected: the spec explicitly forbids per-component theme
  awareness; it is also the opposite of boring — every component would need
  to know about themes.
- **A CSS class on `<body>` (`.dark`) instead of `[data-theme]` on the
  root.** Equivalent in power; `data-theme` on `documentElement` is chosen
  because it is a single attribute with an explicit value (`light`/`dark`),
  reads cleanly in tests (`documentElement.dataset.theme`), and sits above
  `body` so the `body { background: var(--background) }` rule in `index.css`
  already inherits it. A class would also work; the attribute is marginally
  more boring/explicit. Not a load-bearing difference.
- **A state-management library (Redux/Zustand) for theme.** Rejected as
  over-engineering for one boolean — React context is the convention for
  this size of state.

## Consequences

- `tokens.css` gains a dark block; the master-source regeneration note is
  knowingly diverged from (see spec Constraints) — recorded here so a future
  regeneration folds the dark values back in rather than dropping them.
- The full-height `html, body, #root` chain in `index.css` is untouched —
  theming only changes colour variable *values*, never layout. No-regression
  on the layout is preserved by construction.
