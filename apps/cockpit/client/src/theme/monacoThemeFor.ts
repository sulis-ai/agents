// WP-005 — monacoThemeFor() (ADR-002, TDD §3/§5.3).
//
// Monaco does not ride the CSS-variable cascade — it renders into its own
// canvas and takes a `theme` prop with a Monaco theme id. This pure helper is
// the single source of truth for mapping the active app theme to Monaco's
// shipped built-in theme ids, so both wrappers (MonacoFileInner /
// MonacoDiffInner) and any future Monaco surface use one mapping:
//
//   dark  → "vs-dark"  (Monaco's built-in dark)
//   light → "vs"       (Monaco's built-in light)
//
// The built-in `vs` / `vs-dark` themes are the boring, zero-maintenance
// choice (CP-01) — VS Code's defaults, already WCAG-contrasted. A custom
// Monaco theme colour-matched to the cockpit tokens is a deliberately
// deferred enhancement (ADR-002).

import type { Theme } from "./resolveInitialTheme";

/** Map the active app theme to the matching Monaco built-in theme id. */
export function monacoThemeFor(theme: Theme): "vs" | "vs-dark" {
  return theme === "dark" ? "vs-dark" : "vs";
}
