// WP-003 — ThemeProvider + useTheme() component tests (TDD §5.2).
//
// Real DOM via jsdom + Testing Library. The provider owns the active theme,
// writes documentElement.dataset.theme on mount and on every change, and
// persists the choice to localStorage on toggle/setTheme. The persistence-
// ordering acceptance (a saved choice that contradicts the OS wins after a
// simulated remount) is the load-bearing case here.

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, renderHook, screen } from "@testing-library/react";
import {
  THEME_STORAGE_KEY,
  ThemeProvider,
  useTheme,
} from "../../theme/ThemeProvider";

/** Install a matchMedia stub that reports the given dark-mode preference. */
function stubMatchMedia(prefersDark: boolean) {
  vi.stubGlobal(
    "matchMedia",
    vi.fn((query: string) => ({
      matches: prefersDark,
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  );
}

function wrapper({ children }: { children: React.ReactNode }) {
  return <ThemeProvider>{children}</ThemeProvider>;
}

describe("<ThemeProvider /> + useTheme()", () => {
  beforeEach(() => {
    window.localStorage.clear();
    delete document.documentElement.dataset.theme;
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    window.localStorage.clear();
    delete document.documentElement.dataset.theme;
    vi.restoreAllMocks();
  });

  it("renders its children", () => {
    stubMatchMedia(false);
    render(
      <ThemeProvider>
        <div data-testid="child">hello</div>
      </ThemeProvider>,
    );
    expect(screen.getByTestId("child")).toBeInTheDocument();
  });

  it("sets data-theme to dark on mount when nothing is saved and the OS prefers dark", () => {
    stubMatchMedia(true);
    render(
      <ThemeProvider>
        <div />
      </ThemeProvider>,
    );
    expect(document.documentElement.dataset.theme).toBe("dark");
  });

  it("sets data-theme to light on mount when nothing is saved and the OS prefers light", () => {
    stubMatchMedia(false);
    render(
      <ThemeProvider>
        <div />
      </ThemeProvider>,
    );
    expect(document.documentElement.dataset.theme).toBe("light");
  });

  it("exposes the active theme via useTheme()", () => {
    stubMatchMedia(true);
    const { result } = renderHook(() => useTheme(), { wrapper });
    expect(result.current.theme).toBe("dark");
  });

  it("toggle() flips data-theme and persists the new choice to localStorage", () => {
    stubMatchMedia(false); // start light
    const { result } = renderHook(() => useTheme(), { wrapper });

    expect(result.current.theme).toBe("light");
    expect(document.documentElement.dataset.theme).toBe("light");

    act(() => {
      result.current.toggle();
    });

    expect(result.current.theme).toBe("dark");
    expect(document.documentElement.dataset.theme).toBe("dark");
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe("dark");
  });

  it("setTheme() sets the requested theme and persists it", () => {
    stubMatchMedia(false);
    const { result } = renderHook(() => useTheme(), { wrapper });

    act(() => {
      result.current.setTheme("dark");
    });

    expect(result.current.theme).toBe("dark");
    expect(document.documentElement.dataset.theme).toBe("dark");
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe("dark");
  });

  it("honours a saved choice that contradicts the OS preference after a simulated remount", () => {
    // First session: OS dark, user toggles to light, which persists.
    stubMatchMedia(true);
    const first = renderHook(() => useTheme(), { wrapper });
    expect(first.result.current.theme).toBe("dark");
    act(() => {
      first.result.current.setTheme("light");
    });
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe("light");
    first.unmount();
    delete document.documentElement.dataset.theme;

    // Second session (simulated reload): OS still dark, but the saved light
    // choice must win.
    stubMatchMedia(true);
    const second = renderHook(() => useTheme(), { wrapper });
    expect(second.result.current.theme).toBe("light");
    expect(document.documentElement.dataset.theme).toBe("light");
  });

  it("throws a clear error when useTheme() is called outside a ThemeProvider", () => {
    // Silence React's error-boundary console noise for this expected throw.
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    expect(() => renderHook(() => useTheme())).toThrow(/ThemeProvider/);
    spy.mockRestore();
  });
});
