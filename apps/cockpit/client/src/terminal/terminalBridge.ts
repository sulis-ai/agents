// WP-008 — client-side TerminalBridge factory.
//
// The <LiveTerminal/> component consumes the WP-007 TerminalBridge PORT for all
// transport (WPF-02 — no raw socket in the component). This module is the one
// place that constructs the concrete bridge for the browser: it reuses the
// WP-007 TerminalBridgeClient (the port's socket-client implementation, EP-03
// reuse-first — we do NOT re-implement the attach/feed/detach decoding) over a
// browser-side SocketTransport.
//
// Mock-first then live (WP-008 Notes / WPF-03): the live socket transport is
// wired end-to-end by WP-010 (the Playwright round-trip drives the running
// cockpit against the real §2.8 socket). Until then this factory supplies a
// transport that yields the "no terminal here" expected state rather than a
// blank pane — so the component is safe to mount in production before the live
// wiring lands. The component reaches `done` against the injected fake bridge
// in its contract test; this factory is the production seam WP-010 completes.
//
// References: WP-008 Contract (component consumes ONLY the TerminalBridge port);
// WP-007 (TerminalBridgeClient); contract §2.13.5; ADR-003.

import {
  TerminalBridgeClient,
  type SocketTransport,
  type TerminalBridge,
  type WireResponse,
} from "../../../server/ports/TerminalBridge";

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
 * — the port's socket-client — over the supplied transport (defaulting to the
 * not-yet-wired transport WP-010 replaces with the live socket).
 */
export function createTerminalBridge(
  transport: SocketTransport = notYetWiredTransport,
): TerminalBridge {
  return new TerminalBridgeClient(transport);
}
