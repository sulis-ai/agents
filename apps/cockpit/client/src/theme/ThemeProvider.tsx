// WP-003 — ThemeProvider + useTheme() (ADR-001, TDD §3/§5.2).
//
// The provider owns the active theme as state (initialised from the pure
// resolveInitialTheme() seam), reflects it onto documentElement.dataset.theme
// before paint, and persists the choice to localStorage whenever it changes
// via setTheme/toggle. useTheme() is the app-wide read/write surface.
//
// Scope (WP-003): the mechanism only. The toggle control is WP-004; the
// Monaco binding is WP-005; the dark token values are WP-002.

import {
  createContext,
  useContext,
  useLayoutEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  resolveInitialTheme,
  THEME_STORAGE_KEY,
  type Theme,
} from "./resolveInitialTheme";

// Re-export the shared type + key so consumers (WP-004/WP-005) have a single
// import surface for the whole theme module.
export { THEME_STORAGE_KEY, type Theme } from "./resolveInitialTheme";

interface ThemeContextValue {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  toggle: () => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

/** Persist the chosen theme; a throwing/absent store is silently tolerated. */
function persistTheme(theme: Theme): void {
  try {
    window.localStorage.setItem(THEME_STORAGE_KEY, theme);
  } catch {
    // Private mode / quota / old runtime — the in-memory choice still applies
    // for this session; we simply can't remember it across reloads.
  }
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  // Lazy initialiser: resolve once, synchronously, on first render so the
  // first paint already has the right theme (ADR-001 FOUC avoidance).
  const [theme, setThemeState] = useState<Theme>(resolveInitialTheme);

  // Reflect the active theme onto the document root before paint, on mount and
  // on every change. useLayoutEffect (not useEffect) keeps it pre-paint.
  useLayoutEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  const value = useMemo<ThemeContextValue>(() => {
    const setTheme = (next: Theme) => {
      setThemeState(next);
      persistTheme(next);
    };
    return {
      theme,
      setTheme,
      toggle: () => setTheme(theme === "dark" ? "light" : "dark"),
    };
  }, [theme]);

  return (
    <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
  );
}

/**
 * Read the active theme and its setters. Must be called inside a
 * <ThemeProvider>; throws a clear error otherwise so the wiring mistake
 * surfaces at the call site rather than as an undefined-context crash.
 */
export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (ctx === null) {
    throw new Error("useTheme() must be used within a <ThemeProvider>");
  }
  return ctx;
}
