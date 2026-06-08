// WP-003 — theme types, storage key, and the initial-theme resolver.
//
// This module is the single source of truth for the `Theme` type and the
// localStorage key, so WP-004 (the toggle) and WP-005 (the Monaco binding)
// import them rather than re-declaring. The resolver itself is a pure seam
// (no React): it reads the saved choice and the OS preference and applies the
// ADR-001 resolution order.

/** The two themes the cockpit supports. */
export type Theme = "light" | "dark";

/**
 * The localStorage key under which the remembered theme choice lives.
 * One key, app-wide; per-device; non-sensitive (a single "light"/"dark").
 */
export const THEME_STORAGE_KEY = "cockpit.theme";

/** Default when neither a saved choice nor an OS signal is available. */
const FALLBACK_THEME: Theme = "light";

function isTheme(value: unknown): value is Theme {
  return value === "light" || value === "dark";
}

/**
 * Read the persisted theme choice.
 *
 * Returns the saved theme when present and valid, or `null` when the store is
 * reachable but holds nothing valid (a clean miss → defer to the OS). Throws
 * if localStorage itself is unavailable (private mode / old runtime) so the
 * caller can distinguish "nothing saved" from "store broken" — the contract
 * routes a broken store to the safe "light" fallback, not to the OS signal.
 */
function readSavedTheme(): Theme | null {
  const saved = window.localStorage.getItem(THEME_STORAGE_KEY);
  return isTheme(saved) ? saved : null;
}

/**
 * Read the OS colour-scheme preference.
 *
 * Returns "dark" when the OS prefers dark, "light" otherwise. Throws if
 * matchMedia is unavailable so the caller can apply the safe fallback.
 */
function readOsPreference(): Theme {
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

/**
 * Resolve the theme to use on first render.
 *
 * Resolution order (ADR-001 / TDD §5.1):
 *   1. A saved-and-valid choice wins outright (the OS is ignored once the
 *      user has chosen).
 *   2. Otherwise the OS `prefers-color-scheme` signal decides.
 *   3. If either browser API throws (private mode / old runtime), fall back to
 *      "light" without crashing.
 *
 * A throwing API short-circuits straight to "light" — distinct from a clean
 * miss (no saved value), which defers to the OS preference.
 */
export function resolveInitialTheme(): Theme {
  try {
    return readSavedTheme() ?? readOsPreference();
  } catch {
    return FALLBACK_THEME;
  }
}
