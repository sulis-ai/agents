// WP-004 — shared test helper: stub window.matchMedia for theme tests.
//
// The ThemeProvider reads `matchMedia("(prefers-color-scheme: dark)")` to
// resolve the first-visit theme (ADR-001). jsdom has no real matchMedia, so
// every test that mounts the provider (directly or via the Shell that hosts
// the toggle) needs a deterministic stub. Extracted here at the 2-consumer
// threshold (RGB Blue / EP-03) so the toggle, Shell, routing, and smoke tests
// share one source of truth instead of copy-pasting the stub.
//
// Pair with `vi.unstubAllGlobals()` in afterEach to restore the global.

import { vi } from "vitest";

/**
 * Install a `matchMedia` stub that reports the given dark-mode preference.
 *
 * @param prefersDark - what `(prefers-color-scheme: dark)` should report.
 */
export function stubMatchMedia(prefersDark = false): void {
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
