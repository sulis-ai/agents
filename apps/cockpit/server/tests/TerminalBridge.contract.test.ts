// WP-007 — Contract test for the TerminalBridge typed socket-client port
// (contract §2.13.5; TDD §1.5; ADR-003).
//
// The cockpit's terminal port is the ONLY thing that talks to the §2.8
// socket for the terminal path (WPF-02). This test replays WP-001's
// recorded byte fixtures (WPF-03 mock-first) — the recorded NDJSON IS the
// contract mock, so the port reaches `done` with no live socket.
//
// The port is built behind a `SocketTransport` seam (mirroring how
// ChangeStoreReader sits behind an adapter): the real adapter speaks the
// Unix-domain socket; this test supplies a fixture-replay transport that
// reads the recorded NDJSON and replays each response by request id. Same
// port surface, two transports — that is the boundary parity guarantee.
//
// What this pins (Definition of Done — Red):
//   - attach() yields the scrollback SNAPSHOT bytes first, then live bytes,
//     decoded base64 → Uint8Array (the inverse of WP-005's encoding);
//   - attach() is lazy — it yields per `term` line, never collecting the
//     whole stream first (Performance §);
//   - feed() returns { written } matching the keystroke byte length;
//   - resize()/detach() resolve against their acks;
//   - the three §2.15 errors (NOT_PTY_SESSION / NO_SESSION / SOCKET_CLOSED)
//     surface as TYPED, narrowable result values — never thrown opaque.

import { describe, it, expect } from "vitest";
import { readFile } from "node:fs/promises";
import path from "node:path";

import {
  TerminalBridgeClient,
  TerminalBridgeError,
  type SocketTransport,
  type WireResponse,
} from "../ports/TerminalBridge";

// ── Locate WP-001's recorded byte fixtures ────────────────────────────────
// Repo root is the parent of apps/. import.meta.url points at this test file
// inside apps/cockpit/server/tests/; four levels up is the repo root.
const FIXTURE_DIR = (() => {
  const here = path.dirname(new URL(import.meta.url).pathname);
  const repoRoot = path.resolve(here, "..", "..", "..", "..");
  return path.join(
    repoRoot,
    "plugins",
    "sulis",
    "scripts",
    "tests",
    "lib",
    "fixtures",
    "terminal",
  );
})();

type WireLine =
  | { id: string; method: string; params: Record<string, unknown> }
  | WireResponse;

/** Read a recorded NDJSON fixture into its parsed lines (one JSON per line). */
async function loadFixture(name: string): Promise<WireLine[]> {
  const raw = await readFile(path.join(FIXTURE_DIR, `${name}.ndjson`), "utf8");
  return raw
    .split("\n")
    .map((l) => l.trim())
    .filter((l) => l.length > 0)
    .map((l) => JSON.parse(l) as WireLine);
}

/** A request line is one that carries a `method`; a response echoes an `id`. */
function isRequest(
  line: WireLine,
): line is { id: string; method: string; params: Record<string, unknown> } {
  return typeof (line as { method?: unknown }).method === "string";
}

/**
 * A fixture-replay SocketTransport. It walks the recorded NDJSON: each
 * request the port issues is matched (by method + key) to the next recorded
 * request line, and the recorded responses sharing that request's `id` are
 * replayed back. `openStream` yields each `term`/`end`/`error` line lazily.
 *
 * This is the test's stand-in for the real socket adapter — same surface,
 * fed by the recorded contract mock instead of a live process.
 */
function replayTransport(lines: WireLine[]): SocketTransport {
  // Group responses by the request id they echo.
  const responsesById = new Map<string, WireResponse[]>();
  const requestsInOrder: {
    id: string;
    method: string;
    params: Record<string, unknown>;
  }[] = [];
  for (const line of lines) {
    if (isRequest(line)) {
      requestsInOrder.push(line);
    } else {
      const id = line.id;
      const bucket = responsesById.get(id) ?? [];
      bucket.push(line);
      responsesById.set(id, bucket);
    }
  }

  let cursor = 0;
  /** Find the next recorded request matching `method`, return its responses. */
  function nextMatch(method: string): WireResponse[] {
    for (let i = cursor; i < requestsInOrder.length; i++) {
      if (requestsInOrder[i]!.method === method) {
        cursor = i + 1;
        return responsesById.get(requestsInOrder[i]!.id) ?? [];
      }
    }
    throw new Error(`fixture has no recorded '${method}' request remaining`);
  }

  return {
    async request(method: string): Promise<WireResponse> {
      const responses = nextMatch(method);
      // Unary methods record exactly one response line.
      return responses[0]!;
    },
    async *openStream(method: string): AsyncIterable<WireResponse> {
      const responses = nextMatch(method);
      for (const r of responses) {
        yield r;
      }
    },
  };
}

const CHANGE_ID = "chg_01KTGY";

describe("TerminalBridge contract — recorded byte fixtures (WPF-03)", () => {
  describe("attach() — renders scrollback then live (acceptance #1)", () => {
    it("yields the snapshot bytes first, decoded base64 → Uint8Array", async () => {
      const bridge = new TerminalBridgeClient(
        replayTransport(await loadFixture("attach_renders_scrollback")),
      );

      const chunks: Uint8Array[] = [];
      for await (const bytes of bridge.attach(CHANGE_ID)) {
        chunks.push(bytes);
      }

      // Three term frames recorded (two snapshot, one live), then `end`.
      expect(chunks).toHaveLength(3);
      // First frame is the clear-screen + prompt snapshot.
      expect(chunks[0]).toBeInstanceOf(Uint8Array);
      const text = Buffer.from(chunks[0]!).toString("utf8");
      expect(text).toContain("ls -la");
      // The clear-screen escape (ESC [ 2 J) leads the snapshot.
      expect(chunks[0]![0]).toBe(0x1b);
      // Last frame is the live tail.
      expect(Buffer.from(chunks[2]!).toString("utf8")).toContain("Jun  7");
    });

    it("is lazy — first frame is available before the stream is drained", async () => {
      const bridge = new TerminalBridgeClient(
        replayTransport(await loadFixture("attach_renders_scrollback")),
      );

      const iterator = bridge.attach(CHANGE_ID)[Symbol.asyncIterator]();
      const first = await iterator.next();
      // We obtained the first frame without collecting the whole stream
      // (matches WP-005's streaming side — MUST NOT buffer all then yield).
      expect(first.done).toBe(false);
      expect(first.value).toBeInstanceOf(Uint8Array);
    });
  });

  describe("feed() — two-way round-trip (acceptance #2)", () => {
    it("returns { written } matching the keystroke byte length", async () => {
      const bridge = new TerminalBridgeClient(
        replayTransport(await loadFixture("two_way_roundtrip")),
      );

      const ack = await bridge.feed(
        CHANGE_ID,
        new TextEncoder().encode("ls\n"),
      );
      expect(ack.written).toBe(3); // len(b"ls\n")
    });
  });

  describe("error narrowing — §2.15 errors are typed values, never thrown", () => {
    it("attach on a pipe-mode session surfaces NOT_PTY_SESSION (not a throw)", async () => {
      const bridge = new TerminalBridgeClient(
        replayTransport(await loadFixture("error_not_pty_session")),
      );

      // The error is the FIRST (and only) yielded value — narrowable, not
      // thrown. A component renders it; it never escapes as an opaque throw.
      let caught: unknown = null;
      let emitted: Awaited<ReturnType<typeof collectAttachResults>> = [];
      try {
        emitted = await collectAttachResults(bridge);
      } catch (e) {
        caught = e;
      }

      expect(caught).toBeNull(); // MUST NOT throw
      expect(emitted).toHaveLength(1);
      const result = emitted[0]!;
      expect(result.ok).toBe(false);
      if (!result.ok) {
        expect(result.error.code).toBe("NOT_PTY_SESSION");
        expect(result.error.category).toBe("expected");
      }
    });

    it("attach on an unknown key surfaces NO_SESSION as a typed value", async () => {
      const bridge = new TerminalBridgeClient(
        replayTransport(await loadFixture("error_no_session")),
      );
      const emitted = await collectAttachResults(bridge);
      expect(emitted).toHaveLength(1);
      const result = emitted[0]!;
      expect(result.ok).toBe(false);
      if (!result.ok) {
        expect(result.error.code).toBe("NO_SESSION");
      }
    });

    it("a mid-stream drop surfaces SOCKET_CLOSED after the live bytes", async () => {
      const bridge = new TerminalBridgeClient(
        replayTransport(await loadFixture("error_socket_closed_mid")),
      );
      const emitted = await collectAttachResults(bridge);
      // snapshot + live frames are ok results, then a SOCKET_CLOSED error.
      const last = emitted[emitted.length - 1]!;
      expect(last.ok).toBe(false);
      if (!last.ok) {
        expect(last.error.code).toBe("SOCKET_CLOSED");
        expect(last.error.category).toBe("protocol");
      }
      // The bytes that DID arrive before the drop are still surfaced.
      expect(emitted.some((r) => r.ok)).toBe(true);
    });
  });

  describe("open() — get-or-spawn a pty-mode session (§2.13.5)", () => {
    it("returns the key, ioMode 'pty' and viewerCount from the open ack", async () => {
      const bridge = new TerminalBridgeClient(
        replayTransport(await loadFixture("attach_renders_scrollback")),
      );
      const opened = await bridge.open(CHANGE_ID);
      expect(opened.key).toBe(CHANGE_ID);
      expect(opened.ioMode).toBe("pty");
      expect(opened.viewerCount).toBe(0);
    });

    it("throws a typed TerminalBridgeError when the open is rejected", async () => {
      const bridge = new TerminalBridgeClient(
        replayTransport([
          { id: "1", method: "open", params: { key: CHANGE_ID } },
          {
            id: "1",
            ok: false,
            error: {
              category: "internal",
              code: "PTY_OPEN_FAILED",
              message: "os.openpty() failed",
            },
          },
        ]),
      );
      await expect(bridge.open(CHANGE_ID)).rejects.toBeInstanceOf(
        TerminalBridgeError,
      );
    });
  });

  describe("throwing variants surface the typed error (the rare catch path)", () => {
    it("attach() (byte stream) throws TerminalBridgeError on a §2.15 error", async () => {
      const bridge = new TerminalBridgeClient(
        replayTransport(await loadFixture("error_not_pty_session")),
      );
      let caught: unknown = null;
      try {
        for await (const _bytes of bridge.attach(CHANGE_ID)) {
          void _bytes;
        }
      } catch (e) {
        caught = e;
      }
      expect(caught).toBeInstanceOf(TerminalBridgeError);
      expect((caught as TerminalBridgeError).terminalError.code).toBe(
        "NOT_PTY_SESSION",
      );
    });

    it("feed() throws TerminalBridgeError when the feed is rejected", async () => {
      const bridge = new TerminalBridgeClient(
        replayTransport([
          { id: "8", method: "feed", params: { key: CHANGE_ID } },
          {
            id: "8",
            ok: false,
            error: {
              category: "expected",
              code: "NO_SESSION",
              message: "no session",
            },
          },
        ]),
      );
      await expect(
        bridge.feed(CHANGE_ID, new TextEncoder().encode("x")),
      ).rejects.toBeInstanceOf(TerminalBridgeError);
    });

    it("resize() throws TerminalBridgeError on NOT_PTY_SESSION", async () => {
      const bridge = new TerminalBridgeClient(
        replayTransport([
          { id: "10", method: "resize", params: { key: CHANGE_ID } },
          {
            id: "10",
            ok: false,
            error: {
              category: "expected",
              code: "NOT_PTY_SESSION",
              message: "pipe session",
            },
          },
        ]),
      );
      await expect(bridge.resize(CHANGE_ID, 40, 120)).rejects.toBeInstanceOf(
        TerminalBridgeError,
      );
    });

    it("detach() throws TerminalBridgeError when the detach is rejected", async () => {
      const bridge = new TerminalBridgeClient(
        replayTransport([
          { id: "9", method: "detach", params: { key: CHANGE_ID } },
          {
            id: "9",
            ok: false,
            error: {
              category: "expected",
              code: "NO_SESSION",
              message: "no session",
            },
          },
        ]),
      );
      await expect(bridge.detach(CHANGE_ID)).rejects.toBeInstanceOf(
        TerminalBridgeError,
      );
    });
  });

  describe("detach() / resize() — control acks (acceptance #3, §2.13.3)", () => {
    it("detach() resolves and leaves the session running", async () => {
      const bridge = new TerminalBridgeClient(
        replayTransport(await loadFixture("detach_leaves_running")),
      );
      // Drain the first attach, then detach, then re-attach catches up.
      await collectAttachResults(bridge);
      await expect(bridge.detach(CHANGE_ID)).resolves.toBeUndefined();
    });

    it("resize() resolves against its ack", async () => {
      // resize is recorded as a unary ack; replay a synthetic one-liner.
      const bridge = new TerminalBridgeClient(
        replayTransport([
          { id: "10", method: "resize", params: { key: CHANGE_ID } },
          { id: "10", ok: true, result: { rows: 40, cols: 120 } },
        ]),
      );
      await expect(bridge.resize(CHANGE_ID, 40, 120)).resolves.toBeUndefined();
    });
  });
});

/**
 * Drive `attach` to completion, capturing each emission as a discriminated
 * result so the test can assert on typed error values without try/catch.
 * The bridge yields `Uint8Array` for bytes; errors must come through as
 * narrowable result objects, NOT thrown — so we adapt via the bridge's
 * `attachResults` surface (the component-facing, error-as-value variant).
 */
async function collectAttachResults(bridge: TerminalBridgeClient) {
  const out: WireAttachResult[] = [];
  for await (const result of bridge.attachResults(CHANGE_ID)) {
    out.push(result);
  }
  return out;
}

type WireAttachResult =
  | { ok: true; bytes: Uint8Array; phase: "snapshot" | "live" }
  | {
      ok: false;
      error: { category: string; code: string; message: string };
    };
