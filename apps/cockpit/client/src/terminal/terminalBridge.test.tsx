// WP-008 — client TerminalBridge factory tests.
//
// The factory reuses the WP-007 TerminalBridgeClient (EP-03 reuse-first) over
// a browser-side transport. Until WP-010 wires the live socket, the default
// transport yields the expected NOT_PTY_SESSION value — never a throw, never a
// blank pane (acceptance #1). These tests pin that contract.

import { describe, it, expect } from "vitest";

import { createTerminalBridge } from "./terminalBridge";
import type { AttachResult } from "../../../server/ports/TerminalBridge";

describe("createTerminalBridge", () => {
  it("returns a bridge whose default attach yields NOT_PTY_SESSION (no throw)", async () => {
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

  it("uses a supplied transport (the WP-010 live-socket seam)", async () => {
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
