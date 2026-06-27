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

// jsdom does not implement ResizeObserver; xterm.js's fit-addon wiring (mounted
// by <LiveTerminal/>) observes its container with one. Provide a no-op stub so
// terminal-view tests that let the lazy xterm sink resolve render cleanly
// (CH-R5EE44 Fix 3 — the ThreadView agent-picker test mounts the real
// LiveTerminal and waits long enough for the async sink to attach).
if (typeof globalThis !== "undefined" && !("ResizeObserver" in globalThis)) {
  class ResizeObserverStub {
    observe(): void {}
    unobserve(): void {}
    disconnect(): void {}
  }
  (globalThis as unknown as { ResizeObserver: unknown }).ResizeObserver =
    ResizeObserverStub;
}

afterEach(() => {
  cleanup();
});
