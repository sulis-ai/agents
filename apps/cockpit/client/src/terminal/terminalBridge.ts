// WP-008 — client-side TerminalBridge factory.
//
// The <LiveTerminal/> component consumes the WP-007 TerminalBridge PORT for all
// transport (WPF-02 — no raw socket in the component). This module is the one
// place that constructs the concrete bridge for the browser: it reuses the
// WP-007 TerminalBridgeClient (the port's socket-client implementation, EP-03
// reuse-first — we do NOT re-implement the attach/feed/detach decoding) over a
// browser-side SocketTransport.
//
// Transport selection (WP-006): the factory builds a WebSocketTransport to the
// §2.8 NDJSON socket (bridged WS→AF_UNIX by the terminal sidecar) whenever
// `terminalWsUrl()` resolves — which, since WP-006, is in ANY browser context:
// it derives the same-origin `ws(s)://<host>/terminal` default so the running
// cockpit reaches its OWN sidecar with no env configuration. An explicit
// `VITE_TERMINAL_WS_URL` or the `window.__COCKPIT_TERMINAL_WS__` global the e2e
// injects still override that default. Only in the non-browser path (no
// `window`/`location` — SSR / unit tests) does the factory fall back to the
// not-yet-wired transport that yields the "no terminal here" expected state
// rather than a blank pane (acceptance #1; production-safe). The component
// reaches `done` against the injected fake bridge in its contract test; this
// factory is the production composition seam (WPF-09).
//
// References: WP-008 Contract (component consumes ONLY the TerminalBridge port);
// WP-007 (TerminalBridgeClient); WP-006 (same-origin live wiring); §2.13.5; ADR-003.

import {
  TerminalBridgeClient,
  type SocketTransport,
  type TerminalBridge,
  type WireResponse,
} from "../../../server/ports/TerminalBridge";
import { WebSocketTransport, terminalWsUrl } from "./socketWsTransport";

/**
 * The non-browser fallback transport. Since WP-006 the live WebSocketTransport
 * is selected in any browser context (same-origin default); this fallback is
 * reached only when there is no `window`/`location` (SSR / unit tests), where
 * every request resolves to the expected `NOT_PTY_SESSION` value (a typed error
 * the port surfaces as the "no terminal here" state) — never a throw, never a
 * hang, never a blank pane (acceptance #1).
 */
const notYetWiredTransport: SocketTransport = {
  async request(): Promise<WireResponse> {
    return {
      id: "0",
      ok: false,
      error: {
        category: "expected",
        code: "NOT_PTY_SESSION",
        message: "no live terminal in this (non-browser) context",
      },
    };
  },
  async *openStream(): AsyncIterable<WireResponse> {
    yield {
      id: "0",
      ok: false,
      error: {
        category: "expected",
        code: "NOT_PTY_SESSION",
        message: "no live terminal in this (non-browser) context",
      },
    };
  },
};

/**
 * Construct the cockpit's terminal bridge. Reuses {@link TerminalBridgeClient}
 * — the port's socket-client — over the chosen transport:
 *
 *   - an explicit `transport` arg always wins (tests inject a fake; the
 *     contract test pins both shapes);
 *   - otherwise, when `terminalWsUrl()` resolves (the same-origin default in
 *     any browser, WP-006), the live {@link WebSocketTransport} to the socket;
 *   - otherwise (no `window`/`location`) the {@link notYetWiredTransport}
 *     fallback (production-safe — the "no terminal here" state, never a
 *     blank pane).
 */
export function createTerminalBridge(
  transport?: SocketTransport,
): TerminalBridge {
  const chosen =
    transport ?? liveTransportIfConfigured() ?? notYetWiredTransport;
  return new TerminalBridgeClient(chosen);
}

/** The live WS transport when a terminal endpoint is configured, else
 *  undefined (so the caller falls back to the not-yet-wired transport). */
function liveTransportIfConfigured(): SocketTransport | undefined {
  const url = terminalWsUrl();
  if (!url) return undefined;
  return new WebSocketTransport(url);
}
