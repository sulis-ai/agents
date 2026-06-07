// WP-008 — client-side TerminalBridge factory.
//
// The <LiveTerminal/> component consumes the WP-007 TerminalBridge PORT for all
// transport (WPF-02 — no raw socket in the component). This module is the one
// place that constructs the concrete bridge for the browser: it reuses the
// WP-007 TerminalBridgeClient (the port's socket-client implementation, EP-03
// reuse-first — we do NOT re-implement the attach/feed/detach decoding) over a
// browser-side SocketTransport.
//
// Mock-first then live (WP-008 Notes / WPF-03): WP-010 wires the live socket
// transport end-to-end. When a terminal WS endpoint is configured
// (VITE_TERMINAL_WS_URL or the window.__COCKPIT_TERMINAL_WS__ global the e2e
// injects), the factory builds a WebSocketTransport to the §2.8 NDJSON socket
// (bridged WS→AF_UNIX by the terminal sidecar/proxy). When it is NOT configured
// — the default in a plain build with no terminal sidecar — the factory falls
// back to the not-yet-wired transport that yields the "no terminal here"
// expected state rather than a blank pane, so the component is always safe to
// mount (production-safe; no regression). The component reaches `done` against
// the injected fake bridge in its contract test; this factory is the production
// composition seam (WPF-09).
//
// References: WP-008 Contract (component consumes ONLY the TerminalBridge port);
// WP-007 (TerminalBridgeClient); WP-010 (live wiring); contract §2.13.5; ADR-003.

import {
  TerminalBridgeClient,
  type SocketTransport,
  type TerminalBridge,
  type WireResponse,
} from "../../../server/ports/TerminalBridge";
import { WebSocketTransport, terminalWsUrl } from "./socketWsTransport";

/**
 * The not-yet-wired transport. WP-010 replaces this with the real Unix-domain
 * socket client reached over the cockpit server. Until then every request
 * resolves to the expected `NOT_PTY_SESSION` value (a typed error the port
 * surfaces as the "no terminal here" state) — never a throw, never a hang,
 * never a blank pane (acceptance #1).
 */
const notYetWiredTransport: SocketTransport = {
  async request(): Promise<WireResponse> {
    return {
      id: "0",
      ok: false,
      error: {
        category: "expected",
        code: "NOT_PTY_SESSION",
        message: "the live terminal socket is not wired yet (WP-010)",
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
        message: "the live terminal socket is not wired yet (WP-010)",
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
 *   - otherwise, when a terminal WS endpoint is configured, the live
 *     {@link WebSocketTransport} to the §2.8 socket (WP-010 live wiring);
 *   - otherwise the {@link notYetWiredTransport} fallback (production-safe —
 *     the "no terminal here" state, never a blank pane).
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
