---
founder_facing: true
---
# Spec — Dark mode for the cockpit

**Change:** CH-01KTHP · feat

## Intent

Give the cockpit a proper dark theme and a light/dark toggle that themes
the whole app at once. The code viewer (Monaco) follows the active theme so
there's never dark code sitting in a light app (or vice-versa). The app
already pulls every colour from one central tokens file and every component
reads from it — so dark mode is a second colour set behind a theme switch,
not a screen-by-screen rebuild.

## Scope

- A **dark colour set** covering every surface the light set already
  defines (backgrounds, text, cards, borders, and the semantic colours:
  primary, accent, success, warning, destructive).
- A **light/dark toggle** in the app, available from every screen.
- **Theme applies app-wide** — the dashboard, the change/thread view, the
  file tree, the code + diff viewers, the chat, the sidebar all re-theme
  together when the toggle flips.
- **The code viewer follows the active theme** — dark editor in dark mode,
  light editor in light mode (today it is hardcoded dark).
- **First-visit default follows the computer's setting** (OS dark → app
  dark; OS light → app light).
- **The choice is remembered** — once the founder flips the toggle, that
  pick wins on every later visit, ahead of the OS setting.

## Non-goals

- No redesign of any screen's layout, spacing, or content — colours only.
- No per-component theme overrides or custom user palettes — one light set,
  one dark set.
- No regeneration of the design-token master source (see Constraints) — the
  dark values are added directly for this change.
- No theming of anything outside the cockpit client app.

## Acceptance

- Opening the cockpit on a machine set to dark mode shows the app in dark;
  on a machine set to light, it shows light.
- A visible toggle switches the whole app between light and dark, including
  the code and diff viewers, with no light-app/dark-code mismatch in either
  state.
- After flipping the toggle, reloading the app keeps the chosen theme
  (overriding the OS setting from then on).
- Every existing screen remains readable and correctly coloured in both
  themes — no unreadable text, no invisible borders, no raw hard-coded
  colours that ignore the theme.

## Constraints

- **Use the existing token system.** Components already reference
  `var(--*)` from `tokens.css`; the dark set must work by overriding those
  same variables under a theme selector — components should not be rewritten
  to know about themes individually.
- **Token-source note (flag, not a blocker):** `tokens.css` is marked
  "generate from the design instance," but that master source isn't present
  in this project. The dark values will be authored directly for this
  change; if/when the master returns, they can be folded back in.
- **Remembered-choice + OS-default ordering:** a saved choice always wins;
  only when there's no saved choice does the OS setting decide.
- **No regressions:** the app's full-height layout and the existing tests
  for the screens and viewers must continue to pass.
