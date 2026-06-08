// WP-002 — the production terminal sidecar bridge (browser WS ↔ AF_UNIX).
//
// This is the first-class cockpit-server sibling of e2e/terminal-proxy.ts's
// bridge(): a WebSocketServer attached to the existing HTTP server's `upgrade`
// event at path "/terminal" that pipes each NDJSON line VERBATIM to a fresh
// AF_UNIX connection per WS (one socket connection per WebSocket), rewriting
// `open` to inject the resolved provider+cwd from the change store.
//
// Per TDD §4 and the WP verification frontmatter, these tests run against an
// IN-MEMORY LINE-ECHO FAKE AF_UNIX ENDPOINT — a real `net.Server` on a unix
// socket that records each NDJSON line it receives and can reply with NDJSON
// lines. It is a REAL line relay, not a mock of the wire shape: the bytes that
// cross the socket are exactly the bytes the bridge writes. The live engine is
// exercised end-to-end in WP-006/WP-007.
//
// INDEPENDENCE (founder directive): this bridge has ZERO dependency on the chat
// relay (routes/chat.ts) or the chat's SessionBridge. It is the terminal's own
// bridge. These tests import only the sidecar module + the change-store reader
// port fake.

import { describe, it, expect, afterEach } from "vitest";
import { createServer, type Server as NetServer, type Socket } from "node:net";
import { createServer as createHttpServer, type Server } from "node:http";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { WebSocket } from "ws";

import { createTerminalSidecar } from "../adapters/TerminalSidecar";
import type { TerminalSidecarLogLine } from "../adapters/TerminalSidecar";
import { FakeChangeStoreReader } from "../adapters/FakeChangeStoreReader";
import type { ChangeStoreRecord } from "../ports/ChangeStoreReader";

// ── The in-memory line-echo fake AF_UNIX endpoint ──────────────────────────
//
// A real `net.Server` on a per-test unix socket. It buffers inbound bytes into
// NDJSON lines (the same framing the real engine uses), records each line for
// assertion, and exposes a hook so a test can reply with NDJSON lines back down
// the same connection (the socket → browser direction). Every accepted socket
// connection is tracked so a test can assert per-WS fresh connections and drive
// the close/teardown directions.

interface FakeConnection {
  /** Each NDJSON line (no trailing newline) received on this connection. */
  lines: string[];
  /** The raw socket — a test can `end()`/`destroy()` it to drive teardown. */
  socket: Socket;
  /** Send one NDJSON line back down this connection (socket → browser). */
  send: (line: string) => void;
}

interface FakeEndpoint {
  socketPath: string;
  connections: FakeConnection[];
  /** Resolves once the next connection has received at least one line. */
  waitForLine: (connIndex: number) => Promise<void>;
  close: () => Promise<void>;
}

function startFakeEndpoint(): Promise<FakeEndpoint> {
  const dir = mkdtempSync(join(tmpdir(), "wp002-sock-"));
  const socketPath = join(dir, "terminal.sock");
  const connections: FakeConnection[] = [];
  const lineWaiters = new Map<number, Array<() => void>>();

  const server: NetServer = createServer((socket) => {
    let buf = "";
    const conn: FakeConnection = {
      lines: [],
      socket,
      send: (line: string) => {
        if (!socket.destroyed) socket.write(line.endsWith("\n") ? line : line + "\n");
      },
    };
    const index = connections.length;
    connections.push(conn);
    socket.on("data", (chunk: Buffer) => {
      buf += chunk.toString("utf8");
      let nl: number;
      while ((nl = buf.indexOf("\n")) !== -1) {
        const line = buf.slice(0, nl);
        buf = buf.slice(nl + 1);
        if (line.trim()) {
          conn.lines.push(line);
          for (const w of lineWaiters.get(index) ?? []) w();
          lineWaiters.delete(index);
        }
      }
    });
  });

  return new Promise<FakeEndpoint>((resolve, reject) => {
    server.once("error", reject);
    server.listen(socketPath, () => {
      resolve({
        socketPath,
        connections,
        waitForLine: (connIndex: number) =>
          new Promise<void>((res) => {
            const existing = connections[connIndex];
            if (existing && existing.lines.length > 0) {
              res();
              return;
            }
            const arr = lineWaiters.get(connIndex) ?? [];
            arr.push(res);
            lineWaiters.set(connIndex, arr);
          }),
        close: () =>
          new Promise<void>((res) => {
            for (const c of connections) c.socket.destroy();
            server.close(() => {
              rmSync(dir, { recursive: true, force: true });
              res();
            });
          }),
      });
    });
  });
}

// ── A bound HTTP server + sidecar harness ──────────────────────────────────

interface Harness {
  url: string;
  /** `ws://127.0.0.1:PORT` — the bare endpoint, for tests that build their own
   *  path/query/origin (origin-refuse, cap tests). */
  baseUrl: string;
  httpServer: Server;
  /** Every structured log line the sidecar emitted (WP-003 §3.5 observability:
   *  one line per refuse; the test asserts on outcome/code/changeId only). */
  logLines: TerminalSidecarLogLine[];
  close: () => Promise<void>;
}

const CHANGE_ID = "CH-TEST-001";
const WORKTREE = "/tmp/wp002-worktree/CH-TEST-001";

function fakeRecord(overrides: Partial<ChangeStoreRecord> = {}): ChangeStoreRecord {
  return {
    changeId: CHANGE_ID,
    handle: "test-change",
    slug: "test-change",
    primitive: "Create",
    branch: "change/test-change",
    worktreePath: WORKTREE,
    intent: "test",
    baseBranch: "main",
    baseSha: null,
    createdAt: "2026-06-07T00:00:00Z",
    updatedAt: "2026-06-07T00:00:00Z",
    stage: "designing" as ChangeStoreRecord["stage"],
    ...overrides,
  };
}

async function startHarness(
  socketPath: string,
  caps: { maxConnections: number; maxAttachmentsPerConnection: number } = {
    maxConnections: 8,
    maxAttachmentsPerConnection: 4,
  },
  // Artificial latency on the change→spec resolution, to exercise the
  // ordering-under-async-resolution path (the `open` rewrite awaits this).
  resolveDelayMs = 0,
): Promise<Harness> {
  const changeStore = new FakeChangeStoreReader([fakeRecord()]);
  const logLines: TerminalSidecarLogLine[] = [];
  const sidecar = createTerminalSidecar({
    socketPath,
    resolveChange: async (changeId: string) => {
      if (resolveDelayMs > 0) {
        await new Promise((r) => setTimeout(r, resolveDelayMs));
      }
      const rec = await changeStore.readChangeRecord(changeId);
      if (!rec) return null;
      return { provider: "pty", cwd: rec.worktreePath };
    },
    originAllowList: ["http://127.0.0.1:5173"],
    caps,
    logSink: (line) => logLines.push(line),
  });

  const httpServer = createHttpServer((_req, res) => {
    res.statusCode = 404;
    res.end();
  });
  sidecar.attach(httpServer);

  await new Promise<void>((resolve, reject) => {
    httpServer.once("error", reject);
    httpServer.listen(0, "127.0.0.1", () => resolve());
  });
  const addr = httpServer.address();
  if (!addr || typeof addr === "string") throw new Error("no http port bound");
  const baseUrl = `ws://127.0.0.1:${addr.port}`;
  const url = `${baseUrl}/terminal?changeId=${CHANGE_ID}`;

  return {
    url,
    baseUrl,
    httpServer,
    logLines,
    close: async () => {
      await sidecar.close();
      await new Promise<void>((res) => httpServer.close(() => res()));
    },
  };
}

/** Open a WS to the sidecar and resolve once it is OPEN. */
function openWs(url: string): Promise<WebSocket> {
  return new Promise<WebSocket>((resolve, reject) => {
    const ws = new WebSocket(url, {
      headers: { origin: "http://127.0.0.1:5173" },
    });
    ws.once("open", () => resolve(ws));
    ws.once("error", reject);
  });
}

/** Poll until `pred()` is true or the budget elapses. */
async function until(pred: () => boolean, budgetMs = 2_000): Promise<void> {
  const start = Date.now();
  while (!pred()) {
    if (Date.now() - start > budgetMs) throw new Error("until() timed out");
    await new Promise((r) => setTimeout(r, 10));
  }
}

// ── Lifecycle bookkeeping ──────────────────────────────────────────────────

const cleanups: Array<() => Promise<void>> = [];
afterEach(async () => {
  for (const c of cleanups.splice(0)) await c();
});

async function setup(caps?: {
  maxConnections: number;
  maxAttachmentsPerConnection: number;
}): Promise<{ endpoint: FakeEndpoint; harness: Harness }> {
  const endpoint = await startFakeEndpoint();
  cleanups.push(() => endpoint.close());
  const harness = await startHarness(endpoint.socketPath, caps);
  cleanups.push(() => harness.close());
  return { endpoint, harness };
}

/** Open a WS we EXPECT to be refused; resolve with the close code (or "error"
 *  for a handshake-level rejection like a 403, which `ws` surfaces as `error`). */
function openWsExpectClosed(
  url: string,
  origin = "http://127.0.0.1:5173",
): Promise<{ refused: boolean; code?: number }> {
  return new Promise((resolve) => {
    const ws = new WebSocket(url, { headers: { origin } });
    ws.once("error", () => resolve({ refused: true }));
    ws.once("close", (code: number) => resolve({ refused: true, code }));
    ws.once("open", () => {
      // Opened when we expected a refusal — report it so the assertion fails.
      ws.close();
      resolve({ refused: false });
    });
  });
}

describe("WP-002 terminal sidecar bridge", () => {
  it("test_open_injects_provider_cwd — open with only {io_mode:pty} reaches the endpoint carrying the resolved provider+cwd", async () => {
    const { endpoint, harness } = await setup();
    const ws = await openWs(harness.url);
    cleanups.push(async () => ws.close());

    // The client sends ONLY {io_mode:"pty"} — the bridge supplies provider+cwd.
    ws.send(JSON.stringify({ id: "1", method: "open", params: { key: CHANGE_ID, spec: { io_mode: "pty" } } }));

    await endpoint.waitForLine(0);
    const line = endpoint.connections[0]!.lines[0]!;
    const parsed = JSON.parse(line) as {
      method: string;
      params: { spec: Record<string, unknown> };
    };
    expect(parsed.method).toBe("open");
    expect(parsed.params.spec.provider).toBe("pty");
    expect(parsed.params.spec.cwd).toBe(WORKTREE);
    // The client's own io_mode survives the rewrite (merge, not clobber).
    expect(parsed.params.spec.io_mode).toBe("pty");
  });

  it("preserves browser→socket order even when the `open` rewrite resolves slowly (no reordering)", async () => {
    // The `open` rewrite is async (awaits resolveChange); `feed` is sync. A naive
    // fire-and-forget would let the later `feed` overtake the still-resolving
    // `open`, reordering the NDJSON wire and breaking the session. Make
    // resolveChange slow and assert order is still open-then-feed at the endpoint.
    const endpoint = await startFakeEndpoint();
    cleanups.push(() => endpoint.close());
    const harness = await startHarness(endpoint.socketPath, undefined, 50);
    cleanups.push(() => harness.close());
    const ws = await openWs(harness.url);
    cleanups.push(async () => ws.close());

    // Send open immediately followed by feed (the real client's sequence).
    ws.send(JSON.stringify({ id: "1", method: "open", params: { key: CHANGE_ID, spec: { io_mode: "pty" } } }));
    ws.send(JSON.stringify({ id: "2", method: "feed", params: { key: CHANGE_ID, data: "QQ==", encoding: "base64" } }));

    await until(() => (endpoint.connections[0]?.lines.length ?? 0) >= 2, 3_000);
    const methods = endpoint.connections[0]!.lines.map(
      (l) => (JSON.parse(l) as { method: string }).method,
    );
    expect(methods).toEqual(["open", "feed"]);
  });

  it("falls back to the open's own `key` when the connection URL carries no changeId (ADR-010 first-open binding)", async () => {
    const { endpoint, harness } = await setup();
    // Connect with NO ?changeId — the identity must come from the first `open`'s
    // key (the connection-URL identity and the first-open key are both valid
    // sources per ADR-010 §3.3).
    const ws = await openWs(`${harness.baseUrl}/terminal`);
    cleanups.push(async () => ws.close());

    ws.send(JSON.stringify({ id: "1", method: "open", params: { key: CHANGE_ID, spec: { io_mode: "pty" } } }));

    await endpoint.waitForLine(0);
    const parsed = JSON.parse(endpoint.connections[0]!.lines[0]!) as {
      params: { spec: Record<string, unknown> };
    };
    // The spec was resolved from the open's own key and provider+cwd injected.
    expect(parsed.params.spec.cwd).toBe(WORKTREE);
    expect(parsed.params.spec.provider).toBe("pty");
  });

  it("forwards an `open` verbatim when the change cannot be resolved (no spec injected)", async () => {
    const { endpoint, harness } = await setup();
    // Open with an unknown change (no ?changeId, key the store does not know) —
    // the resolver returns null, so the bridge forwards the open UNCHANGED
    // rather than fabricating a spec.
    const ws = await openWs(`${harness.baseUrl}/terminal`);
    cleanups.push(async () => ws.close());

    const original = JSON.stringify({ id: "1", method: "open", params: { key: "CH-UNKNOWN", spec: { io_mode: "pty" } } });
    ws.send(original);

    await endpoint.waitForLine(0);
    expect(endpoint.connections[0]!.lines[0]).toBe(original);
  });

  it("test_open_injects_brief_change_id — the rewritten open sets spec.brief_change_id to the changeId the WS is for", async () => {
    const { endpoint, harness } = await setup();
    const ws = await openWs(harness.url); // URL carries ?changeId=CHANGE_ID
    cleanups.push(async () => ws.close());

    // The client sends only {io_mode:"pty"} — the sidecar supplies the brief
    // target (the same changeId it already keys provider+cwd resolution on).
    ws.send(JSON.stringify({ id: "1", method: "open", params: { key: CHANGE_ID, spec: { io_mode: "pty" } } }));

    await endpoint.waitForLine(0);
    const parsed = JSON.parse(endpoint.connections[0]!.lines[0]!) as {
      params: { spec: Record<string, unknown> };
    };
    expect(parsed.params.spec.brief_change_id).toBe(CHANGE_ID);
  });

  it("test_open_omits_brief_change_id_when_no_identity — no ?changeId and no open key → field omitted (None server-side)", async () => {
    const { endpoint, harness } = await setup();
    // Connect with NO ?changeId, and open with NO key — there is no identity to
    // brief from, so the resolver returns null and the open is forwarded
    // verbatim, carrying no brief_change_id.
    const ws = await openWs(`${harness.baseUrl}/terminal`);
    cleanups.push(async () => ws.close());

    ws.send(JSON.stringify({ id: "1", method: "open", params: { spec: { io_mode: "pty" } } }));

    await endpoint.waitForLine(0);
    const parsed = JSON.parse(endpoint.connections[0]!.lines[0]!) as {
      params?: { spec?: Record<string, unknown> };
    };
    expect(parsed.params?.spec?.brief_change_id).toBeUndefined();
  });

  it("test_forwards_other_methods_verbatim — attach/feed/resize/detach pass through byte-for-byte (incl base64 payloads)", async () => {
    const { endpoint, harness } = await setup();
    const ws = await openWs(harness.url);
    cleanups.push(async () => ws.close());

    const messages = [
      JSON.stringify({ id: "2", method: "attach", params: { key: CHANGE_ID } }),
      JSON.stringify({ id: "3", method: "feed", params: { key: CHANGE_ID, data: "bHMgLWxhCg==", encoding: "base64" } }),
      JSON.stringify({ id: "4", method: "resize", params: { key: CHANGE_ID, rows: 40, cols: 120 } }),
      JSON.stringify({ id: "5", method: "detach", params: { key: CHANGE_ID } }),
    ];
    for (const m of messages) ws.send(m);

    await until(() => (endpoint.connections[0]?.lines.length ?? 0) >= 4);
    // Every non-open method is forwarded byte-for-byte (no rewrite, no decode).
    expect(endpoint.connections[0]!.lines).toEqual(messages);
  });

  it("test_per_ws_fresh_connection — two WS connections get two distinct endpoint connections; request ids do not cross-talk", async () => {
    const { endpoint, harness } = await setup();
    const wsA = await openWs(harness.url);
    cleanups.push(async () => wsA.close());
    const wsB = await openWs(harness.url);
    cleanups.push(async () => wsB.close());

    await until(() => endpoint.connections.length >= 2);
    expect(endpoint.connections.length).toBe(2);

    wsA.send(JSON.stringify({ id: "1", method: "feed", params: { key: CHANGE_ID, data: "QQ==", encoding: "base64" } }));
    wsB.send(JSON.stringify({ id: "1", method: "feed", params: { key: CHANGE_ID, data: "Qg==", encoding: "base64" } }));

    await until(
      () =>
        (endpoint.connections[0]?.lines.length ?? 0) >= 1 &&
        (endpoint.connections[1]?.lines.length ?? 0) >= 1,
    );
    // Each WS's bytes land on ITS OWN socket connection — no cross-talk even
    // though both used request id "1".
    const a = JSON.parse(endpoint.connections[0]!.lines[0]!) as { params: { data: string } };
    const b = JSON.parse(endpoint.connections[1]!.lines[0]!) as { params: { data: string } };
    expect(a.params.data).toBe("QQ==");
    expect(b.params.data).toBe("Qg==");
  });

  it("forwards endpoint NDJSON lines to the browser verbatim (incl base64 term.data), splitting a batched frame", async () => {
    const { endpoint, harness } = await setup();
    const ws = await openWs(harness.url);
    cleanups.push(async () => ws.close());

    const received: string[] = [];
    ws.on("message", (d) => received.push(typeof d === "string" ? d : d.toString()));

    // Establish the per-WS socket connection.
    ws.send(JSON.stringify({ id: "1", method: "attach", params: { key: CHANGE_ID } }));
    await until(() => endpoint.connections.length >= 1);

    // socket → browser: a unary ack, then a base64 `term` line. The bridge
    // forwards each line verbatim — it does NOT decode the base64 payload.
    const ack = JSON.stringify({ id: "1", ok: true, result: { written: 0 } });
    const term = JSON.stringify({
      id: "1",
      ok: true,
      term: { data: "aGVsbG8K", encoding: "base64", phase: "live" },
    });
    // Send both in ONE frame to prove the bridge splits on the newline boundary.
    endpoint.connections[0]!.socket.write(ack + "\n" + term + "\n");

    await until(() => received.length >= 2);
    expect(received[0]).toBe(ack);
    expect(received[1]).toBe(term);
    // The base64 payload crossed untouched (byte-for-byte, no decode).
    expect(JSON.parse(received[1]!).term.data).toBe("aGVsbG8K");
  });

  it("test_socket_close_closes_ws — endpoint socket close tears down the WS", async () => {
    const { endpoint, harness } = await setup();
    const ws = await openWs(harness.url);
    const closed = new Promise<void>((resolve) => ws.once("close", () => resolve()));

    // Establish the per-WS socket connection, then drop it from the endpoint side.
    ws.send(JSON.stringify({ id: "1", method: "attach", params: { key: CHANGE_ID } }));
    await until(() => endpoint.connections.length >= 1);
    endpoint.connections[0]!.socket.destroy();

    await closed; // resolves only if socket-close propagated to a WS close
    expect(ws.readyState).toBe(WebSocket.CLOSED);
  });

  it("test_ws_close_ends_socket — closing the WS ends the underlying AF_UNIX socket", async () => {
    const { endpoint, harness } = await setup();
    const ws = await openWs(harness.url);

    ws.send(JSON.stringify({ id: "1", method: "attach", params: { key: CHANGE_ID } }));
    await until(() => endpoint.connections.length >= 1);
    const sock = endpoint.connections[0]!.socket;
    const sockClosed = new Promise<void>((resolve) => sock.once("close", () => resolve()));

    ws.close();

    await sockClosed; // resolves only if WS-close propagated to sock.end()
    expect(sock.destroyed).toBe(true);
  });

  it("closes the WS when the AF_UNIX connection errors (unreachable socket)", async () => {
    // No fake endpoint: point the sidecar at a socket path that does not exist
    // so `connect()` errors immediately — the bridge's socket-error handler must
    // close the WS rather than leave it hanging (lifecycle parity).
    const harness = await startHarness("/tmp/wp002-nonexistent-" + Date.now() + ".sock");
    cleanups.push(() => harness.close());
    const ws = await openWs(harness.url);
    const closed = new Promise<void>((resolve) => ws.once("close", () => resolve()));

    ws.send(JSON.stringify({ id: "1", method: "attach", params: { key: CHANGE_ID } }));

    await closed; // resolves only if the socket-error handler closed the WS
    expect(ws.readyState).toBe(WebSocket.CLOSED);
  });

  // ── Origin + caps seam coverage ───────────────────────────────────────────
  //
  // The Origin gate and the connection/attachment caps are WP-003's full
  // negative-path matrix; WP-002 supplies the SEAM (the constructor params named
  // in the Contract) and a smoke proof for each implemented branch so no
  // untested branch ships in this file.

  it("refuses the upgrade (no socket opened) when the Origin is not allow-listed", async () => {
    const { endpoint, harness } = await setup();
    const url = `${harness.baseUrl}/terminal?changeId=${CHANGE_ID}`;
    const outcome = await openWsExpectClosed(url, "http://evil.example.com");
    expect(outcome.refused).toBe(true);
    // A refused handshake opens NO AF_UNIX connection (the whole point).
    expect(endpoint.connections.length).toBe(0);
  });

  it("refuses a new WS past the concurrent-connection cap; existing ones survive", async () => {
    const { harness } = await setup({
      maxConnections: 1,
      maxAttachmentsPerConnection: 4,
    });
    const first = await openWs(harness.url);
    cleanups.push(async () => first.close());

    const outcome = await openWsExpectClosed(harness.url);
    expect(outcome.refused).toBe(true);
    // The first connection is unaffected by the second's refusal.
    expect(first.readyState).toBe(WebSocket.OPEN);
  });

  it("refuses an attach past the per-connection attachment cap (closes the WS with a policy code)", async () => {
    const { endpoint, harness } = await setup({
      maxConnections: 8,
      maxAttachmentsPerConnection: 1,
    });
    const ws = await openWs(harness.url);
    const closed = new Promise<number>((resolve) =>
      ws.once("close", (code: number) => resolve(code)),
    );

    // First attach is admitted and relayed; the second exceeds the cap.
    ws.send(JSON.stringify({ id: "1", method: "attach", params: { key: CHANGE_ID } }));
    await until(() => (endpoint.connections[0]?.lines.length ?? 0) >= 1);
    ws.send(JSON.stringify({ id: "2", method: "attach", params: { key: CHANGE_ID } }));

    const code = await closed;
    expect(code).toBe(1008); // policy violation
    // The over-cap attach was NOT relayed to the endpoint.
    expect(endpoint.connections[0]!.lines.length).toBe(1);
  });
});

// ── WP-003 — Origin validation + resource caps (full negative-path matrix) ───
//
// REINFORCE-Secure on the WP-002 bridge (TDD §3.2, §3.4; ADR-010). WP-002 shipped
// the gate MECHANISM and a smoke proof per branch; this block is the COMPLETE
// negative-path matrix the WP Contract names — the four named tests
// (test_rejects_foreign_origin, test_accepts_own_origin, test_connection_cap,
// test_attachment_cap) plus the §3.5 observability assertions: one structured
// log line per refuse, carrying outcome/code/changeId ONLY (NFR-SEC-03: never a
// keystroke byte or terminal-output byte).

describe("WP-003 Origin validation + resource caps", () => {
  it("test_rejects_foreign_origin — upgrade with Origin: http://evil.example is refused 403, no endpoint connection opened", async () => {
    const { endpoint, harness } = await setup();
    const url = `${harness.baseUrl}/terminal?changeId=${CHANGE_ID}`;

    const outcome = await openWsExpectClosed(url, "http://evil.example");
    expect(outcome.refused).toBe(true);
    // The whole point of an upgrade-time refusal: zero AF_UNIX connections open.
    expect(endpoint.connections.length).toBe(0);
  });

  it("test_rejects_foreign_origin — an ABSENT Origin header is also refused (no socket opened)", async () => {
    const { endpoint, harness } = await setup();
    // A WS client with NO Origin header at all — must be refused like a foreign
    // one (the gate is allow-list, not deny-list).
    const refused = await new Promise<boolean>((resolve) => {
      const ws = new WebSocket(`${harness.baseUrl}/terminal?changeId=${CHANGE_ID}`);
      ws.once("error", () => resolve(true));
      ws.once("close", () => resolve(true));
      ws.once("open", () => {
        ws.close();
        resolve(false);
      });
    });
    expect(refused).toBe(true);
    expect(endpoint.connections.length).toBe(0);
  });

  it("test_accepts_own_origin — upgrade with Origin === the allow-listed client origin establishes the connection", async () => {
    const { endpoint, harness } = await setup();
    const ws = await openWs(harness.url); // openWs sends the allow-listed origin
    cleanups.push(async () => ws.close());

    expect(ws.readyState).toBe(WebSocket.OPEN);
    // An accepted upgrade lets the first message reach a real endpoint connection.
    ws.send(JSON.stringify({ id: "1", method: "attach", params: { key: CHANGE_ID } }));
    await until(() => endpoint.connections.length >= 1);
    expect(endpoint.connections.length).toBe(1);
  });

  it("test_connection_cap — the N+1th concurrent WS is refused while the first N stay up", async () => {
    // Ceiling of 2: open two, the third is refused; the first two keep streaming.
    const { endpoint, harness } = await setup({
      maxConnections: 2,
      maxAttachmentsPerConnection: 4,
    });
    const first = await openWs(harness.url);
    cleanups.push(async () => first.close());
    const second = await openWs(harness.url);
    cleanups.push(async () => second.close());
    await until(() => endpoint.connections.length >= 2);

    // The third upgrade is past the ceiling → refused, no third connection.
    const outcome = await openWsExpectClosed(harness.url);
    expect(outcome.refused).toBe(true);
    expect(endpoint.connections.length).toBe(2);

    // The first N are unaffected: each can still relay a message to its socket.
    first.send(JSON.stringify({ id: "1", method: "feed", params: { key: CHANGE_ID, data: "QQ==", encoding: "base64" } }));
    second.send(JSON.stringify({ id: "1", method: "feed", params: { key: CHANGE_ID, data: "Qg==", encoding: "base64" } }));
    await until(
      () =>
        (endpoint.connections[0]?.lines.length ?? 0) >= 1 &&
        (endpoint.connections[1]?.lines.length ?? 0) >= 1,
    );
    expect(first.readyState).toBe(WebSocket.OPEN);
    expect(second.readyState).toBe(WebSocket.OPEN);
  });

  it("test_attachment_cap — the N+1th attach on one WS is refused while earlier attachments keep streaming", async () => {
    // Ceiling of 2 attachments per connection.
    const { endpoint, harness } = await setup({
      maxConnections: 8,
      maxAttachmentsPerConnection: 2,
    });
    const ws = await openWs(harness.url);
    const closed = new Promise<number>((resolve) =>
      ws.once("close", (code: number) => resolve(code)),
    );

    // Two attaches are admitted and relayed.
    ws.send(JSON.stringify({ id: "1", method: "attach", params: { key: CHANGE_ID } }));
    ws.send(JSON.stringify({ id: "2", method: "attach", params: { key: CHANGE_ID } }));
    await until(() => (endpoint.connections[0]?.lines.length ?? 0) >= 2);

    // The earlier attachments keep streaming: a feed relays fine before the cap trips.
    ws.send(JSON.stringify({ id: "f", method: "feed", params: { key: CHANGE_ID, data: "QQ==", encoding: "base64" } }));
    await until(() => (endpoint.connections[0]?.lines.length ?? 0) >= 3);

    // The third attach is past the ceiling → refused (WS closed with policy code),
    // and NOT relayed to the endpoint.
    ws.send(JSON.stringify({ id: "3", method: "attach", params: { key: CHANGE_ID } }));
    const code = await closed;
    expect(code).toBe(1008); // policy violation
    expect(endpoint.connections[0]!.lines.length).toBe(3); // 2 attach + 1 feed, no 3rd attach
  });

  // ── §3.5 observability — one structured log line per refuse ────────────────

  it("emits exactly one structured log line on an Origin refuse (outcome/code/changeId only, no byte content)", async () => {
    const { harness } = await setup();
    const url = `${harness.baseUrl}/terminal?changeId=${CHANGE_ID}`;
    await openWsExpectClosed(url, "http://evil.example");
    await until(() => harness.logLines.length >= 1);

    expect(harness.logLines.length).toBe(1);
    const line = harness.logLines[0]!;
    expect(line.event).toBe("refuse");
    expect(line.outcome).toBe("origin-refused");
    expect(line.code).toBe(403);
    expect(line.changeId).toBe(CHANGE_ID);
    // NFR-SEC-03 parity: the structured line carries NO byte/data content.
    expect(JSON.stringify(line)).not.toContain("data");
    expect(JSON.stringify(line)).not.toContain("term");
  });

  it("emits exactly one structured log line on a connection-cap refuse (code = the WS close code)", async () => {
    const { harness } = await setup({
      maxConnections: 1,
      maxAttachmentsPerConnection: 4,
    });
    const first = await openWs(harness.url);
    cleanups.push(async () => first.close());
    await openWsExpectClosed(harness.url);
    await until(() => harness.logLines.length >= 1);

    expect(harness.logLines.length).toBe(1);
    const line = harness.logLines[0]!;
    expect(line.event).toBe("refuse");
    expect(line.outcome).toBe("connection-cap");
    expect(line.code).toBe(503);
    expect(line.changeId).toBe(CHANGE_ID);
  });

  it("emits exactly one structured log line on an attachment-cap refuse (code = the WS policy close code)", async () => {
    const { endpoint, harness } = await setup({
      maxConnections: 8,
      maxAttachmentsPerConnection: 1,
    });
    const ws = await openWs(harness.url);
    ws.send(JSON.stringify({ id: "1", method: "attach", params: { key: CHANGE_ID } }));
    await until(() => (endpoint.connections[0]?.lines.length ?? 0) >= 1);
    ws.send(JSON.stringify({ id: "2", method: "attach", params: { key: CHANGE_ID } }));
    await until(() => harness.logLines.length >= 1);

    expect(harness.logLines.length).toBe(1);
    const line = harness.logLines[0]!;
    expect(line.event).toBe("refuse");
    expect(line.outcome).toBe("attachment-cap");
    expect(line.code).toBe(1008);
    expect(line.changeId).toBe(CHANGE_ID);
    // NFR-SEC-03 parity: no base64 keystroke payload leaks into the log line.
    expect(JSON.stringify(line)).not.toContain("data");
  });

  it("does NOT emit a refuse log line on an accepted upgrade (only refusals are logged)", async () => {
    const { harness } = await setup();
    const ws = await openWs(harness.url);
    cleanups.push(async () => ws.close());
    // Give any (erroneous) async log a chance to land.
    await new Promise((r) => setTimeout(r, 50));
    const refusals = harness.logLines.filter((l) => l.event === "refuse");
    expect(refusals.length).toBe(0);
  });
});
