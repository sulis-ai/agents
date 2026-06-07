// WP-008 / WP-006 — client TerminalBridge factory tests.
//
// The factory reuses the WP-007 TerminalBridgeClient (EP-03 reuse-first) over
// a browser-side transport. Transport selection (createTerminalBridge):
//   - an explicit transport arg always wins (tests inject a fake);
//   - else, when `terminalWsUrl()` resolves (WP-006: the same-origin default in
//     any browser context), the live WebSocketTransport;
//   - else (no `window`/`location` — the non-browser path) the no-op
//     not-yet-wired transport, which yields the expected NOT_PTY_SESSION value
//     rather than a blank pane (acceptance #1).
//
// WP-006 changed the DEFAULT: in a real running cockpit (a browser with a
// `location`) the factory now selects the LIVE transport so the terminal
// actually connects to the same-origin sidecar — the no-op fallback is reserved
// for the non-browser path. These tests pin that.

import { afterEach, describe, it, expect, vi } from "vitest";

import { createTerminalBridge } from "./terminalBridge";
import type { AttachResult } from "../../../server/ports/TerminalBridge";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

describe("createTerminalBridge", () => {
  it("with no window/location, the default attach yields NOT_PTY_SESSION (no throw, the no-op fallback)", async () => {
    // The non-browser path: `terminalWsUrl()` returns undefined, so the factory
    // falls back to the not-yet-wired transport — never a throw, never a blank
    // pane (acceptance #1, the SSR/test path).
    vi.stubGlobal("window", undefined);

    const bridge = createTerminalBridge() as unknown as {
      attachResults: (id: string) => AsyncIterable<AttachResult>;
    };

    const emitted: AttachResult[] = [];
    for await (const r of bridge.attachResults("chg_x")) {
      emitted.push(r);
    }

    expect(emitted).toHaveLength(1);
    const first = emitted[0]!;
    expect(first.ok).toBe(false);
    if (!first.ok) {
      expect(first.error.code).toBe("NOT_PTY_SESSION");
      expect(first.error.category).toBe("expected");
    }
  });

  it("in a browser (location present, no overrides), the default selects the LIVE WebSocketTransport (WP-006)", async () => {
    // jsdom provides a `location`, so `terminalWsUrl()` resolves to the
    // same-origin endpoint and the factory builds the live WebSocketTransport,
    // which opens a real WebSocket. We stub the global WebSocket to capture the
    // URL it is constructed with — proof the factory selected the live transport
    // (the no-op fallback never constructs a WebSocket) and that it targets the
    // same-origin `/terminal` endpoint.
    const seenUrls: string[] = [];
    class FakeWebSocket {
      onopen: (() => void) | null = null;
      onerror: (() => void) | null = null;
      onclose: (() => void) | null = null;
      onmessage: ((ev: { data: string }) => void) | null = null;
      readyState = 1;
      OPEN = 1;
      constructor(url: string) {
        seenUrls.push(url);
        // Open the socket (so the transport's connect() resolves and the attach
        // registers its sink), THEN — on a later turn so the sink exists — close
        // it. The transport fans a SOCKET_CLOSED value to every in-flight sink,
        // terminating the attach stream deterministically.
        queueMicrotask(() => this.onopen?.());
        setTimeout(() => this.onclose?.(), 0);
      }
      send(): void {}
      close(): void {}
    }
    vi.stubGlobal("WebSocket", FakeWebSocket);

    const bridge = createTerminalBridge() as unknown as {
      attachResults: (id: string) => AsyncIterable<AttachResult>;
    };

    const emitted: AttachResult[] = [];
    for await (const r of bridge.attachResults("chg_x")) {
      emitted.push(r);
    }

    // The factory constructed the LIVE WebSocket transport against the
    // same-origin endpoint — not the no-op fallback (which builds no socket).
    expect(seenUrls).toEqual(["ws://localhost:3000/terminal"]);
    // And the stream surfaced the connection-close as a typed error value —
    // never the NOT_PTY_SESSION no-op value, never a throw.
    expect(emitted).toHaveLength(1);
    const first = emitted[0]!;
    expect(first.ok).toBe(false);
    if (!first.ok) {
      expect(first.error.code).not.toBe("NOT_PTY_SESSION");
    }
  });

  it("uses a supplied transport (the live-socket seam / test injection)", async () => {
    const bridge = createTerminalBridge({
      async request() {
        return {
          id: "1",
          ok: true,
          result: { key: "chg_x", io_mode: "pty", viewer_count: 0 },
        };
      },
      async *openStream() {
        yield { id: "1", ok: true, end: true };
      },
    });

    const opened = await bridge.open("chg_x");
    expect(opened.ioMode).toBe("pty");
    expect(opened.key).toBe("chg_x");
  });
});
