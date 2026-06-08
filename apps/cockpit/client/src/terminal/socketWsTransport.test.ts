// WP-006 — terminalWsUrl() resolution tests.
//
// REORGANISE-Refactor (behaviour-changing): characterisation tests FIRST
// (Fowler discipline). The two `characterisation` cases pin TODAY's behaviour
// and MUST pass on the pre-refactor code (verified before the refactor); the
// `new behaviour` cases pin the production same-origin default this WP adds
// (acceptance #1 — no more no-op fallback in the real running cockpit) and the
// env-precedence read through the Vite-standard `import.meta.env` access that
// the refactor adopts (so `vi.stubEnv` — the documented Vitest API — controls
// it; the pre-refactor cast/optional-chain read was untestable via that API).
//
// `terminalWsUrl()` resolution order (most specific wins, Contract):
//   1. explicit `VITE_TERMINAL_WS_URL` (e2e / override) — unchanged;
//   2. `window.__COCKPIT_TERMINAL_WS__` global — unchanged;
//   3. NEW default: derive `ws(s)://<location.host>/terminal` from the page
//      origin (same-origin, same port the WS endpoint rides per TDD §3.1);
//   4. `undefined` only when there is no `window`/`location` (the non-browser
//      path), preserving the no-op fallback there.

import { afterEach, describe, expect, it, vi } from "vitest";

import { terminalWsUrl } from "./socketWsTransport";

/** Stub `window.location` (origin) for the same-origin derivation tests. jsdom
 *  provides a real `location`; we override just the fields the function reads. */
function stubLocation(protocol: string, host: string): void {
  vi.stubGlobal("window", {
    ...globalThis.window,
    location: { protocol, host },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

describe("terminalWsUrl", () => {
  // --- characterisation (pin TODAY's behaviour; verified to pass pre-refactor) ---

  it("test_falls_back_to_undefined_when_unconfigured: no env, no window global, no window/location → undefined", () => {
    // No VITE_TERMINAL_WS_URL set (env key absent by default; afterEach clears).
    vi.stubGlobal("window", undefined);

    expect(terminalWsUrl()).toBeUndefined();
  });

  // --- new behaviour (the production same-origin default this WP adds) ---

  it("test_explicit_env_still_wins: VITE_TERMINAL_WS_URL takes precedence", () => {
    // The explicit env override beats everything else (e2e / deployment
    // override), even with a window global and a browser location present.
    // Read via the Vite-standard `import.meta.env` access so `vi.stubEnv`
    // controls it (the refactor adopts that access for testability).
    vi.stubEnv("VITE_TERMINAL_WS_URL", "ws://injected.example/terminal");
    stubLocation("http:", "localhost:5173");
    (
      window as unknown as { __COCKPIT_TERMINAL_WS__?: string }
    ).__COCKPIT_TERMINAL_WS__ = "ws://global.example/terminal";

    expect(terminalWsUrl()).toBe("ws://injected.example/terminal");
  });

  it("test_returns_same_origin_terminal_endpoint: browser location, no overrides → ws://<host>/terminal", () => {
    // No env, no window global, but a real browser `location` → derive the
    // same-origin endpoint so socketWsTransport connects to the live sidecar.
    // No VITE_TERMINAL_WS_URL set (env key absent by default).
    stubLocation("http:", "localhost:5173");

    expect(terminalWsUrl()).toBe("ws://localhost:5173/terminal");
  });

  it("test_returns_same_origin_terminal_endpoint: https origin → wss://<host>/terminal", () => {
    // A TLS page origin maps http→ws to https→wss (RFC 6455 scheme parity).
    // No VITE_TERMINAL_WS_URL set (env key absent by default).
    stubLocation("https:", "cockpit.example.com");

    expect(terminalWsUrl()).toBe("wss://cockpit.example.com/terminal");
  });

  it("test_window_global_still_overrides_default: the window global beats the same-origin default", () => {
    // With a browser location present (which would otherwise derive a
    // same-origin URL), the runtime window global still wins.
    // No VITE_TERMINAL_WS_URL set (env key absent by default).
    stubLocation("http:", "localhost:5173");
    (
      window as unknown as { __COCKPIT_TERMINAL_WS__?: string }
    ).__COCKPIT_TERMINAL_WS__ = "ws://global.example/terminal";

    expect(terminalWsUrl()).toBe("ws://global.example/terminal");
  });
});
