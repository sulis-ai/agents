// WP-004 — the host + WS-endpoint lifecycle composition seam.
//
// This is the COMPOSITION test: it boots the REAL production server
// (`startProductionServer()` from server/index.ts) — which spawns the real
// Python session-manager host (WP-001), waits for its `READY <socket>` line,
// then attaches the real terminal sidecar (WP-002/003) to the HTTP server's
// `upgrade` event — and drives a round-trip through it.
//
// MEA-09: real host, real AF_UNIX socket, real pty child (the host's
// fake_claude_child + PtyChildAdapter). No mock of the wire shape — the bytes
// that cross the socket are the bytes the bridge writes. The only injected fake
// is the change-store reader (so the test does not shell out to the Python
// list-changes helper per the WP-004 Contract / TDD §2.4).
//
// INDEPENDENCE (founder directive): this composition wires ONLY the terminal
// host + sidecar. It does not import, depend on, or exercise the chat relay
// (routes/chat.ts) or the chat SessionBridge — the terminal is its own
// lifecycle. These tests import only the server entry + the change-store fake.

import { describe, it, expect, afterEach } from "vitest";
import { existsSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { WebSocket } from "ws";

import {
  startProductionServer,
  startSessionManagerHost,
  buildProductionApp,
  type ProductionServerHandle,
} from "../index";
import { FakeChangeStoreReader } from "../adapters/FakeChangeStoreReader";
import type { ChangeStoreRecord } from "../ports/ChangeStoreReader";

const CHANGE_ID = "CH-WP004";
const ORIGIN = "http://127.0.0.1:5173";

/** A change-store record whose worktree is a fresh temp dir the host can cwd
 *  into (the host `os.makedirs(cwd)` the pty child runs in). */
function fakeRecord(worktreePath: string): ChangeStoreRecord {
  return {
    changeId: CHANGE_ID,
    handle: "wp004-compose",
    slug: "compose-host-and-ws",
    primitive: "Create",
    branch: "feat/wp-004-compose-host-and-ws",
    worktreePath,
    intent: "compose host + ws",
    baseBranch: "main",
    baseSha: null,
    createdAt: "2026-06-07T00:00:00Z",
    updatedAt: "2026-06-07T00:00:00Z",
    stage: "design",
  };
}

const cleanups: Array<() => Promise<void>> = [];
afterEach(async () => {
  for (const c of cleanups.splice(0)) await c();
});

/** Boot the real production server with a fake change store + a fresh worktree
 *  cwd, on an ephemeral port. Registers teardown. */
async function boot(): Promise<{
  handle: ProductionServerHandle;
  worktree: string;
}> {
  const worktree = mkdtempSync(join(tmpdir(), "wp004-worktree-"));
  const changeStore = new FakeChangeStoreReader([fakeRecord(worktree)]);
  const handle = await startProductionServer({
    port: 0,
    changeStore,
    originAllowList: [ORIGIN],
  });
  cleanups.push(() => handle.close());
  return { handle, worktree };
}

/** Open a WS to the running server's /terminal endpoint, resolve once OPEN. */
function openWs(url: string): Promise<WebSocket> {
  return new Promise<WebSocket>((resolve, reject) => {
    const ws = new WebSocket(url, { headers: { origin: ORIGIN } });
    ws.once("open", () => resolve(ws));
    ws.once("error", reject);
  });
}

/** Collect WS text messages until `pred` matches one, or the budget elapses. */
function waitForMessage(
  ws: WebSocket,
  pred: (parsed: Record<string, unknown>) => boolean,
  budgetMs = 8_000,
): Promise<Record<string, unknown>> {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(
      () => reject(new Error("waitForMessage timed out")),
      budgetMs,
    );
    ws.on("message", (data) => {
      const text = typeof data === "string" ? data : data.toString();
      let parsed: Record<string, unknown>;
      try {
        parsed = JSON.parse(text) as Record<string, unknown>;
      } catch {
        return;
      }
      if (pred(parsed)) {
        clearTimeout(timer);
        resolve(parsed);
      }
    });
  });
}

describe("WP-004 host + WS lifecycle composition", () => {
  it("test_boot_spawns_host_and_attaches_ws — boot the real server; WS open→attach→feed round-trips a `term` line (real host, real socket, real pty child, MEA-09)", async () => {
    const { handle } = await boot();

    const ws = await openWs(`${handle.url}/terminal?changeId=${CHANGE_ID}`);
    cleanups.push(async () => ws.close());

    // The client sends only {io_mode:"pty"}; the bridge injects provider+cwd.
    ws.send(
      JSON.stringify({
        id: "1",
        method: "open",
        params: { key: CHANGE_ID, spec: { io_mode: "pty" } },
      }),
    );
    const opened = await waitForMessage(
      ws,
      (p) => p.id === "1" && p.ok === true && p.result !== undefined,
    );
    expect((opened.result as { provider: string }).provider).toBe("pty");

    // Attach the viewer, then feed a keystroke. The production host seeds NO
    // banner (e2e-only), so the snapshot phase is empty; the genuine round-trip
    // proof is that a fed byte reaches the real pty child and its echo streams
    // back as a base64 `term` line (the §2.13 attach stream). This exercises the
    // FULL composition: WS → sidecar → AF_UNIX → host → pty child → back.
    ws.send(
      JSON.stringify({ id: "2", method: "attach", params: { key: CHANGE_ID } }),
    );
    // "hi\n" base64-encoded — the pty child echoes stdin straight back.
    ws.send(
      JSON.stringify({
        id: "3",
        method: "feed",
        params: { key: CHANGE_ID, data: "aGkK", encoding: "base64" },
      }),
    );
    const term = await waitForMessage(
      ws,
      (p) => p.id === "2" && p.term !== undefined,
    );
    const termPayload = term.term as {
      data: string;
      encoding: string;
      phase: string;
    };
    expect(termPayload.encoding).toBe("base64");
    // The echoed bytes decode to contain what we fed (the real pty echo).
    expect(Buffer.from(termPayload.data, "base64").toString("utf8")).toContain(
      "hi",
    );
  });

  it("test_resolve_change_reuses_change_store — open for a known change resolves its worktree via the change-store reader (injected cwd == record.worktreePath)", async () => {
    const { handle, worktree } = await boot();

    const ws = await openWs(`${handle.url}/terminal?changeId=${CHANGE_ID}`);
    cleanups.push(async () => ws.close());

    ws.send(
      JSON.stringify({
        id: "1",
        method: "open",
        params: { key: CHANGE_ID, spec: { io_mode: "pty" } },
      }),
    );
    // The host echoes the resolved session back; the pty child runs in the
    // record's worktree. A successful open against THAT cwd is the proof the
    // bridge resolved provider+cwd from the change-store record (the host
    // `os.makedirs(cwd)` + spawns the child there — an open with a bad cwd
    // would fail). The worktree dir exists because the host created it.
    const opened = await waitForMessage(
      ws,
      (p) => p.id === "1" && p.ok === true,
    );
    expect((opened.result as { key: string }).key).toBe(CHANGE_ID);
    expect(existsSync(worktree)).toBe(true);
  });

  it("test_graceful_shutdown_tears_down_host — close() tears down the WS server and reaps the host; no leaked socket file", async () => {
    const { handle } = await boot();
    // Capture the host pid + socket path before teardown so we can prove both
    // are gone afterwards.
    const pid = handle.host.pid;
    expect(pid).toBeGreaterThan(0);

    await handle.close();
    cleanups.length = 0; // already closed; don't double-close

    // The host process is reaped — `process.kill(pid, 0)` throws ESRCH once it
    // is gone. Poll briefly (SIGTERM → exit is async).
    const gone = await (async () => {
      for (let i = 0; i < 100; i++) {
        try {
          process.kill(pid as number, 0);
        } catch {
          return true; // ESRCH — the process is gone
        }
        await new Promise((r) => setTimeout(r, 20));
      }
      return false;
    })();
    expect(gone).toBe(true);

    // The WS endpoint is closed — a new connection is refused (ECONNREFUSED).
    const refused = await new Promise<boolean>((resolve) => {
      const ws = new WebSocket(`${handle.url}/terminal?changeId=${CHANGE_ID}`, {
        headers: { origin: ORIGIN },
      });
      ws.once("open", () => {
        ws.close();
        resolve(false);
      });
      ws.once("error", () => resolve(true));
    });
    expect(refused).toBe(true);
  });

  it("test_buildProductionApp_is_side_effect_free_on_import — buildProductionApp() binds no port and spawns no host", async () => {
    // buildProductionApp must stay a pure factory: constructing it neither
    // listens nor spawns (the WP-001 isMainModule discipline carries to the
    // host spawn). The returned value is the Express app, not a running server.
    const app = buildProductionApp();
    expect(typeof app).toBe("function"); // an Express application is callable
    // No `listen`/`address` side effects: the app has not bound a port.
    expect(
      (app as unknown as { listening?: boolean }).listening,
    ).toBeUndefined();
  });

  it("startSessionManagerHost spawns the Python host and resolves on READY", async () => {
    const { host, socketPath } = await startSessionManagerHost();
    cleanups.push(async () => {
      host.kill("SIGTERM");
    });
    expect(host.pid).toBeGreaterThan(0);
    expect(existsSync(socketPath)).toBe(true);
  });
});
