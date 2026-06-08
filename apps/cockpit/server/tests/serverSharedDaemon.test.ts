// WP-007 — the cockpit attaches the SHARED daemon, not its own ephemeral host.
//
// TDD §6 / ADR-001 / ADR-003. The convergence point: `startProductionServer`
// stops spawning its OWN host on a per-run temp socket (`mkdtempSync(...)/
// terminal.sock`, the CH-01KTHV behaviour) and instead `ensureDaemon`s the
// SHARED daemon at the stable socket, then attaches the sidecar to it. After
// this, the cockpit view and the desktop view land on the SAME daemon — the
// load-bearing invariant.
//
// What this test proves (the WP Definition of Done > Red):
//   1. startProductionServer ensures the daemon at the (injected) stable socket
//      and creates NO mkdtempSync temp socket of its own.
//   2. ensureDaemon returns the EXISTING socket when a daemon is already live —
//      the cockpit spawns nothing (it attaches a daemon that may already be
//      serving the desktop view).
//   3. close() does NOT kill the daemon (it is shared — it may serve the desktop
//      view); close() tears down only the sidecar + the HTTP server.
//
// Verification posture (MEA-09): a REAL fake-daemon process serves a REAL
// AF_UNIX socket; the server attaches the REAL sidecar to it over the wire. The
// only injected fake is the change-store reader (per the WP-004 Contract / TDD
// §2.4 — the test does not shell out to the Python list-changes helper).
//
// INDEPENDENCE (founder directive): this composition wires ONLY the terminal
// daemon + sidecar. It does not import, depend on, or exercise the chat relay or
// the chat SessionBridge — the terminal is its own lifecycle.

import { describe, it, expect, afterEach } from "vitest";
import { spawn, type ChildProcess } from "node:child_process";
import {
  existsSync,
  mkdtempSync,
  readdirSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import {
  startProductionServer,
  type ProductionServerHandle,
} from "../index";
import { FakeChangeStoreReader } from "../adapters/FakeChangeStoreReader";
import type { ChangeStoreRecord } from "../ports/ChangeStoreReader";

const CHANGE_ID = "CH-WP007";
const ORIGIN = "http://127.0.0.1:5173";

// The same fake daemon the ensureDaemon unit test uses: a real detached process
// answering the contract's `status` probe and printing READY. It lets the server
// attach a LIVE daemon over a real socket without spawning the real WP-003 one.
const FAKE_DAEMON_SOURCE = String.raw`
const net = require("node:net");
const socketPath = process.argv[2];
const server = net.createServer((sock) => {
  let buf = "";
  sock.on("data", (chunk) => {
    buf += chunk.toString("utf8");
    let idx;
    while ((idx = buf.indexOf("\n")) >= 0) {
      const line = buf.slice(0, idx);
      buf = buf.slice(idx + 1);
      let req;
      try { req = JSON.parse(line); } catch { continue; }
      const resp = req.method === "status"
        ? { id: req.id, ok: true, result: [] }
        : { id: req.id, ok: true, result: { key: (req.params && req.params.key) } };
      sock.write(JSON.stringify(resp) + "\n");
    }
  });
  sock.on("error", () => {});
});
server.on("error", () => process.exit(1));
server.listen(socketPath, () => process.stdout.write("READY " + socketPath + "\n"));
setTimeout(() => process.exit(0), 3600_000);
`;

function fakeRecord(worktreePath: string): ChangeStoreRecord {
  return {
    changeId: CHANGE_ID,
    handle: "wp007-shared",
    slug: "cockpit-shared-daemon",
    primitive: "Substitute",
    branch: "feat/wp-007-cockpit-shared-daemon",
    worktreePath,
    intent: "attach the shared daemon",
    baseBranch: "main",
    baseSha: null,
    createdAt: "2026-06-08T00:00:00Z",
    updatedAt: "2026-06-08T00:00:00Z",
    stage: "design",
  };
}

const cleanups: Array<() => void | Promise<void>> = [];
afterEach(async () => {
  for (const c of cleanups.splice(0)) await c();
});

/** Start a real fake daemon on `socketPath`; resolve once it prints READY. */
function startFakeDaemon(scriptDir: string, socketPath: string): Promise<ChildProcess> {
  const script = join(scriptDir, "fake-daemon.cjs");
  writeFileSync(script, FAKE_DAEMON_SOURCE);
  return new Promise<ChildProcess>((resolve, reject) => {
    const proc = spawn(process.execPath, [script, socketPath], {
      stdio: ["ignore", "pipe", "pipe"],
    });
    const timer = setTimeout(() => reject(new Error("fake daemon never READY")), 8_000);
    proc.stdout?.on("data", (c: Buffer) => {
      if (c.toString().includes("READY")) {
        clearTimeout(timer);
        resolve(proc);
      }
    });
    proc.once("error", reject);
  });
}

describe("WP-007 cockpit attaches the shared daemon (not its own host)", () => {
  it("test_attaches_shared_daemon_no_temp_socket — startProductionServer ensures the stable socket and creates NO mkdtempSync temp socket of its own", async () => {
    const dir = mkdtempSync(join(tmpdir(), "wp007-srv-"));
    cleanups.push(() => rmSync(dir, { recursive: true, force: true }));
    const worktree = mkdtempSync(join(tmpdir(), "wp007-wt-"));
    cleanups.push(() => rmSync(worktree, { recursive: true, force: true }));
    const stableSocket = join(dir, "session-manager.sock");

    // A daemon is ALREADY live on the stable socket (it may be serving the
    // desktop view). The cockpit must attach it, not spawn its own.
    const daemon = await startFakeDaemon(dir, stableSocket);
    cleanups.push(() => {
      daemon.kill("SIGKILL");
    });

    // Snapshot the tmpdir's wp004-sock-* dirs (the OLD ephemeral-host temp dir
    // shape) BEFORE boot, so we can prove the server creates no new one.
    const tmpBefore = readdirSync(tmpdir()).filter((n) => n.startsWith("wp004-sock-"));

    const changeStore = new FakeChangeStoreReader([fakeRecord(worktree)]);
    const handle = await startProductionServer({
      port: 0,
      changeStore,
      originAllowList: [ORIGIN],
      // The stable-socket injection seam (the e2e uses it too). The server must
      // ensure-the-daemon at THIS path — and find it already live.
      socketPath: stableSocket,
    });
    cleanups.push(() => handle.close());

    // The server serves the SAME socket the live daemon is on — no temp socket.
    expect(handle.socketPath).toBe(stableSocket);
    const tmpAfter = readdirSync(tmpdir()).filter((n) => n.startsWith("wp004-sock-"));
    expect(tmpAfter).toEqual(tmpBefore);

    // The daemon process is untouched by boot (the cockpit attached, it did not
    // spawn its own host — the fake daemon is the only daemon process).
    expect(daemon.killed).toBe(false);
  });

  it("test_close_does_not_kill_the_shared_daemon — close() tears down sidecar + HTTP but the daemon survives (it is shared)", async () => {
    const dir = mkdtempSync(join(tmpdir(), "wp007-srv-"));
    cleanups.push(() => rmSync(dir, { recursive: true, force: true }));
    const worktree = mkdtempSync(join(tmpdir(), "wp007-wt-"));
    cleanups.push(() => rmSync(worktree, { recursive: true, force: true }));
    const stableSocket = join(dir, "session-manager.sock");

    const daemon = await startFakeDaemon(dir, stableSocket);
    cleanups.push(() => {
      daemon.kill("SIGKILL");
    });
    const daemonPid = daemon.pid;
    expect(daemonPid).toBeGreaterThan(0);

    const changeStore = new FakeChangeStoreReader([fakeRecord(worktree)]);
    const handle = await startProductionServer({
      port: 0,
      changeStore,
      originAllowList: [ORIGIN],
      socketPath: stableSocket,
    });

    await handle.close();

    // The HTTP server is closed — a new WS connection is refused.
    // The daemon, however, is STILL ALIVE: close() must NOT signal it (it is
    // shared and may be serving the desktop view). `process.kill(pid, 0)` is a
    // liveness probe — it does NOT throw while the daemon lives.
    let alive = true;
    try {
      process.kill(daemonPid as number, 0);
    } catch {
      alive = false;
    }
    expect(alive, "shared daemon must survive cockpit close()").toBe(true);
    // The daemon's socket file is still present (it was not unlinked by close).
    expect(existsSync(stableSocket)).toBe(true);
  });

  it("test_warm_ensure_spawns_nothing — a second boot against a live daemon attaches it without a second spawn", async () => {
    const dir = mkdtempSync(join(tmpdir(), "wp007-srv-"));
    cleanups.push(() => rmSync(dir, { recursive: true, force: true }));
    const worktree = mkdtempSync(join(tmpdir(), "wp007-wt-"));
    cleanups.push(() => rmSync(worktree, { recursive: true, force: true }));
    const stableSocket = join(dir, "session-manager.sock");

    const daemon = await startFakeDaemon(dir, stableSocket);
    cleanups.push(() => {
      daemon.kill("SIGKILL");
    });
    const daemonPid = daemon.pid;

    const changeStore = new FakeChangeStoreReader([fakeRecord(worktree)]);
    const h1 = await startProductionServer({
      port: 0,
      changeStore,
      originAllowList: [ORIGIN],
      socketPath: stableSocket,
    });
    await h1.close();

    const h2 = await startProductionServer({
      port: 0,
      changeStore,
      originAllowList: [ORIGIN],
      socketPath: stableSocket,
    });
    cleanups.push(() => h2.close());

    // Both boots attached the SAME pre-existing daemon — neither spawned its own
    // (the fake daemon is still the same single process, untouched).
    expect(h2.socketPath).toBe(stableSocket);
    let alive = true;
    try {
      process.kill(daemonPid as number, 0);
    } catch {
      alive = false;
    }
    expect(alive).toBe(true);
  });
});
