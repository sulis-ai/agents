// WP-001 — vitest setup for client tests.
//
// Imports the jest-dom matchers so .toBeInTheDocument() etc. work, and
// configures cleanup so each test starts from a clean DOM.

import "@testing-library/jest-dom/vitest";
import { afterEach, expect } from "vitest";
import { cleanup } from "@testing-library/react";
// WP-003 — register the jest-axe matcher so `expect(...).toHaveNoViolations()`
// works in component tests (WPF-06 a11y gate).
import { toHaveNoViolations } from "jest-axe";

expect.extend(toHaveNoViolations);

// jsdom does not implement window.matchMedia; xterm.js (mounted by the
// <LiveTerminal/> view) queries it for prefers-color-scheme. Provide a
// no-op stub so terminal-view tests render cleanly (added with WP-008/010).
if (typeof window !== "undefined" && !window.matchMedia) {
  window.matchMedia = (query: string): MediaQueryList =>
    ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    }) as MediaQueryList;
}

afterEach(() => {
  cleanup();
});
