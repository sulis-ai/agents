// WP-003 — resolveInitialTheme() unit tests (TDD §5.1).
//
// The pure resolver is the testable seam: no React, no DOM beyond the two
// browser APIs it reads (localStorage + matchMedia). Resolution order per
// ADR-001: a saved-and-valid choice wins outright (OS ignored); otherwise the
// OS `prefers-color-scheme` signal decides; if either API throws (private
// mode / old runtime), it falls back to "light" without crashing.

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  resolveInitialTheme,
  THEME_STORAGE_KEY,
} from "../../theme/resolveInitialTheme";

/** Install a matchMedia stub that reports the given dark-mode preference. */
function stubMatchMedia(prefersDark: boolean) {
  const mql = {
    matches: prefersDark,
    media: "(prefers-color-scheme: dark)",
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  } as unknown as MediaQueryList;
  vi.stubGlobal(
    "matchMedia",
    vi.fn((query: string) => ({ ...mql, media: query })),
  );
}

describe("resolveInitialTheme", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    window.localStorage.clear();
    vi.restoreAllMocks();
  });

  it("returns the saved choice and ignores the OS preference when a valid choice is stored", () => {
    window.localStorage.setItem(THEME_STORAGE_KEY, "light");
    stubMatchMedia(true); // OS says dark — must be ignored

    expect(resolveInitialTheme()).toBe("light");
  });

  it("returns the saved dark choice over a light OS preference", () => {
    window.localStorage.setItem(THEME_STORAGE_KEY, "dark");
    stubMatchMedia(false); // OS says light — must be ignored

    expect(resolveInitialTheme()).toBe("dark");
  });

  it("falls back to the OS dark preference when nothing is saved", () => {
    stubMatchMedia(true);

    expect(resolveInitialTheme()).toBe("dark");
  });

  it("falls back to the OS light preference when nothing is saved", () => {
    stubMatchMedia(false);

    expect(resolveInitialTheme()).toBe("light");
  });

  it("ignores an invalid saved value and falls back to the OS preference", () => {
    window.localStorage.setItem(THEME_STORAGE_KEY, "purple");
    stubMatchMedia(true);

    expect(resolveInitialTheme()).toBe("dark");
  });

  it("returns light without throwing when localStorage access throws", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("localStorage unavailable (private mode)");
    });
    stubMatchMedia(true); // even with OS dark, the throw short-circuits to light

    expect(() => resolveInitialTheme()).not.toThrow();
    expect(resolveInitialTheme()).toBe("light");
  });

  it("returns light without throwing when matchMedia throws", () => {
    vi.stubGlobal(
      "matchMedia",
      vi.fn(() => {
        throw new Error("matchMedia unavailable (old runtime)");
      }),
    );

    expect(() => resolveInitialTheme()).not.toThrow();
    expect(resolveInitialTheme()).toBe("light");
  });
});
