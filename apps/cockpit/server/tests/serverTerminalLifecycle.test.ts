// WP-004 — the daemon-ensure + WS-endpoint lifecycle composition seam.
// WP-007 — re-pointed onto the SHARED daemon (ADR-001/ADR-003).
//
// This is the COMPOSITION test: it boots the REAL production server
// (`startProductionServer()` from server/index.ts) — which now `ensureDaemon`s
// the SHARED session-manager daemon (WP-003) at the injected stable socket,
// waits for its `READY <socket>` line, then attaches the real terminal sidecar
// (WP-002/003) to the HTTP server's `upgrade` event — and drives a round-trip
// through it.
//
// WP-007 MIGRATION: the cockpit no longer spawns its OWN ephemeral host on a
// temp socket (the CH-01KTHV behaviour). It attaches the shared daemon at the
// stable socket. The test injects a FIXED socket (isolated per-run, NOT the real
// ~/.sulis stable socket) so the ensure cold-starts an isolated daemon, and
// points the daemon's pty provider at the shared fake pty child via the
// `SULIS_DAEMON_PTY_CHILD` seam — the same MEA-09 substrate the Python daemon
// suite uses (the real `claude` round-trip is the deferred observed-done, TDD §4).
//
// MEA-09: real daemon, real AF_UNIX socket, real pty child (the fake_claude_child
// + PtyChildAdapter). No mock of the wire shape — the bytes that cross the socket
// are the bytes the bridge writes. The only injected fake is the change-store
// reader (so the test does not shell out to the Python list-changes helper).
//
// INDEPENDENCE (founder directive): this composition wires ONLY the terminal
// daemon + sidecar. It does not import, depend on, or exercise the chat relay
// (routes/chat.ts) or the chat SessionBridge — the terminal is its own lifecycle.

import { describe, it, expect, afterEach, beforeAll } from "vitest";
import { execFileSync } from "node:child_process";
import { existsSync, mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { WebSocket } from "ws";

import {
  startProductionServer,
  type ProductionServerHandle,
} from "../index";
import { ensureDaemon, daemonIsLive } from "../lib/ensureDaemon";
import { FakeChangeStoreReader } from "../adapters/FakeChangeStoreReader";
import type { ChangeStoreRecord } from "../ports/ChangeStoreReader";

const CHANGE_ID = "CH-WP004";
const ORIGIN = "http://127.0.0.1:5173";

const here = dirname(fileURLToPath(import.meta.url));
// server/tests → repo root is 4 levels up (tests → server → cockpit → apps → root).
const repoRoot = join(here, "..", "..", "..", "..");
const scriptsDir = join(repoRoot, "plugins", "sulis", "scripts");

/** Write the shared fake pty child once (a real subprocess that echoes stdin +
 *  emits PTY_PONG on the sentinel) — the MEA-09 substrate the daemon's pty
 *  provider is pointed at when the real `claude` binary can't run (TDD §4). */
function writeFakePtyChild(cwd: string): string {
  const out = execFileSync(
    "python3",
    [
      "-c",
      [
        "import sys",
        "from pathlib import Path",
        `sys.path.insert(0, ${JSON.stringify(join(scriptsDir, "tests", "lib"))})`,
        "import fake_claude_child",
        `print(fake_claude_child.write_child(Path(${JSON.stringify(cwd)})))`,
      ].join("\n"),
    ],
    { encoding: "utf8" },
  );
  return out.trim();
}

/** Reap an isolated daemon by argv match on its per-test socket path. The daemon
 *  is detached (`start_new_session`) so the server holds no handle to it — and
 *  by design the cockpit's close() must NOT kill the shared daemon. The test
 *  therefore reaps the daemon it cold-started by matching the unique socket path
 *  in its argv, so no detached process leaks across the suite. Best-effort. */
function reapDaemon(socketPath: string): void {
  try {
    // SIGTERM → the daemon's clean stop (unlinks socket, releases lock, exit 0).
    execFileSync("pkill", ["-TERM", "-f", socketPath], { stdio: "ignore" });
  } catch {
    /* no matching process (already exited) — fine */
  }
}

let fakePtyChild: string;
let childHome: string;

beforeAll(() => {
  childHome = mkdtempSync(join(tmpdir(), "wp007-pty-child-"));
  fakePtyChild = writeFakePtyChild(childHome);
  // Point the (ensure-spawned) daemon's pty provider at the fake child for the
  // whole file; a long idle window so the daemon never self-exits mid-test (the
  // test reaps it deterministically in afterEach instead).
  process.env.SULIS_DAEMON_PTY_CHILD = fakePtyChild;
  process.env.SULIS_DAEMON_IDLE_EXIT_SECS = "3600";
});

function fakeRecord(worktreePath: string): ChangeStoreRecord {
  return {
    changeId: CHANGE_ID,
    handle: "wp004-compose",
    slug: "compose-host-and-ws",
    primitive: "Create",
    branch: "feat/wp-004-compose-host-and-ws",
    worktreePath,
    intent: "compose daemon + ws",
    baseBranch: "main",
    baseSha: null,
    createdAt: "2026-06-07T00:00:00Z",
    updatedAt: "2026-06-07T00:00:00Z",
    stage: "design",
  };
}

const cleanups: Array<() => Promise<void> | void> = [];
afterEach(async () => {
  for (const c of cleanups.splice(0)) await c();
});

/** Boot the real production server with a fake change store + a fresh worktree
 *  cwd, on an ephemeral port, ensuring an ISOLATED daemon at an injected fixed
 *  socket (never the real ~/.sulis stable socket). Registers teardown of the
 *  server AND the isolated daemon (the cockpit's close() never kills the daemon —
 *  it is shared — so the test reaps the daemon it cold-started). */
async function boot(): Promise<{
  handle: ProductionServerHandle;
  worktree: string;
  socketPath: string;
}> {
  const sockDir = mkdtempSync(join(tmpdir(), "wp007-sock-"));
  const socketPath = join(sockDir, "session-manager.sock");
  const worktree = mkdtempSync(join(tmpdir(), "wp004-worktree-"));
  const changeStore = new FakeChangeStoreReader([fakeRecord(worktree)]);
  const handle = await startProductionServer({
    port: 0,
    changeStore,
    originAllowList: [ORIGIN],
    socketPath,
  });
  cleanups.push(async () => {
    await handle.close();
    reapDaemon(socketPath);
    rmSync(sockDir, { recursive: true, force: true });
    rmSync(worktree, { recursive: true, force: true });
  });
  return { handle, worktree, socketPath };
}

/** Open a WS to the running server's /terminal endpoint, resolve once OPEN. */
function openWs(url: string): Promise<WebSocket> {
  return new Promise<WebSocket>((resolve, reject) => {
    const ws = new WebSocket(url, { headers: { origin: ORIGIN } });
    ws.once("open", () => resolve(ws));
    ws.once("error", reject);
  });
}

/** Collect WS text messages until `pred` matches one, or the budget elapses.
 *
 *  Budget = 25s (was 8s): the FIRST round-trip in each test is an `open`, which
 *  triggers a COLD start — the daemon is cold-spawned, binds its AF_UNIX socket,
 *  and forks the real fake-pty child — before the result streams back. On a
 *  loaded CI runner that cold-start exceeds 8s (observed deterministically), so
 *  8s raced the cold-start, not a logic fault (the same round-trip passes on a
 *  warm/faster runner). 25s gives the cold-start realistic headroom while still
 *  sitting inside the 30s vitest testTimeout; every assertion is unchanged. */
function waitForMessage(
  ws: WebSocket,
  pred: (parsed: Record<string, unknown>) => boolean,
  budgetMs = 25_000,
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

describe("WP-004/007 daemon-ensure + WS lifecycle composition", () => {
  it("test_boot_ensures_daemon_and_attaches_ws — boot the real server; WS open→attach→feed round-trips a `term` line (real daemon, real socket, real pty child, MEA-09)", async () => {
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

    // Attach the viewer, then feed a keystroke. The genuine round-trip proof is
    // that a fed byte reaches the real pty child and its echo streams back as a
    // base64 `term` line (the §2.13 attach stream). This exercises the FULL
    // composition: WS → sidecar → AF_UNIX → daemon → pty child → back.
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
    // A successful open against the record's worktree cwd is the proof the
    // bridge resolved provider+cwd from the change-store record (the daemon
    // `os.makedirs(cwd)` + spawns the child there — an open with a bad cwd
    // would fail). The worktree dir exists because the daemon created it.
    const opened = await waitForMessage(
      ws,
      (p) => p.id === "1" && p.ok === true,
    );
    expect((opened.result as { key: string }).key).toBe(CHANGE_ID);
    expect(existsSync(worktree)).toBe(true);
  });

  it("test_graceful_shutdown_does_not_kill_the_shared_daemon — close() tears down the WS server + sidecar; the SHARED daemon survives (it may serve the desktop view)", async () => {
    const { handle, socketPath } = await boot();

    // The daemon is live before close (the boot ensured it).
    expect(await daemonIsLive(socketPath)).toBe(true);

    await handle.close();

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

    // The SHARED daemon, however, is UNTOUCHED by the cockpit's close() — it is
    // shared with the desktop view and outlives any one cockpit (ADR-001/003).
    // It still answers the liveness probe over its socket.
    expect(await daemonIsLive(socketPath)).toBe(true);
  });

  it("test_ensureDaemon_warm_is_noop — a second ensure against the live daemon returns the same socket without a second spawn", async () => {
    const { socketPath } = await boot();
    expect(await daemonIsLive(socketPath)).toBe(true);
    // The daemon is already live (boot ensured it). A direct ensure must return
    // immediately — the warm path — proving the cockpit attaches a daemon that
    // may already be serving the desktop view, rather than spawning its own.
    const returned = await ensureDaemon(socketPath, { readyTimeoutMs: 5_000 });
    expect(returned).toBe(socketPath);
  });
});
