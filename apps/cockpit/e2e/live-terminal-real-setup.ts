// WP-007 — live-terminal-REAL e2e global setup.
//
// The production sibling of live-terminal-setup.ts. Where that setup started the
// e2e harness WS→AF_UNIX proxy (terminal-proxy.ts + terminal-backend.py), THIS
// setup drives the REAL server endpoint: run-terminal-real-server.ts boots
// startProductionServer() (which spawns the real Python session-manager host and
// attaches the real terminal sidecar to the /terminal WS), and the client reaches
// it via the WP-006 SAME-ORIGIN default with NO VITE_TERMINAL_WS_URL.
//
// Two production-truthful differences from the harness setup:
//
//   1. NO harness proxy. The browser → /terminal WS → real sidecar → AF_UNIX →
//      real host → real pty. The vite client proxies the /terminal WS upgrade to
//      the real Express server (see live-terminal-real.config.ts), so the
//      same-origin default resolves to the running cockpit's own sidecar.
//
//   2. The production host seeds NO scrollback banner (that pre-seed is
//      harness-only in terminal-backend.py). So this setup injects the known
//      scrollback token the way PRODUCTION would see content arrive: it opens a
//      real AF_UNIX connection to the SAME socket the server serves and drives a
//      real `open` + `feed` (the fake pty child echoes the fed bytes into the
//      scrollback ring) BEFORE the browser attaches. The pre-seed connection is
//      transient — it opens, feeds, waits for the ring to catch the token, then
//      closes; the browser's later attach replays the seeded scrollback.
//
// Isolation invariant (DoD Blue): a dedicated state/projects dir + a dedicated
// worktree (the existing seeder), so NO developer `~/.sulis` is read. The seed +
// handoff are IDEMPOTENT and called by BOTH globalSetup AND run-terminal-real-
// server.ts, so the (version-dependent) boot order cannot leave the server
// without its handoff — mirrors the harness ensureTerminalSeeded() pattern.

import { writeFile, rm, mkdir, realpath, mkdtemp } from "node:fs/promises";
import { readFileSync, existsSync } from "node:fs";
import { connect, type Socket } from "node:net";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { createNdjsonLineFramer } from "../shared/ndjsonLineFramer";
import { seed } from "./fixtures/seed";

/** Dedicated handoff path (distinct from the harness-proxy handoff). */
export const REAL_TERMINAL_HANDOFF_PATH = join(
  tmpdir(),
  "cockpit-e2e-terminal-real-handoff.json",
);

/** The known token the setup feeds into the change's pty scrollback BEFORE the
 *  browser attaches, so acceptance #1 can assert "renders existing scrollback,
 *  not blank". Distinct from the harness banner so the two e2e runs never alias. */
export const REAL_SCROLLBACK_TOKEN = "WP007_REAL_SCROLLBACK_TOKEN";

export interface RealTerminalHandoff {
  stateDir: string;
  projectsDir: string;
  worktree: string;
  changeId: string;
  handle: string;
  /** The AF_UNIX socket the real host serves on (fixed so the setup pre-seeds the
   *  same socket the server serves). */
  socketPath: string;
  /** `ws://host:port` base — acceptance #4 drives the real /terminal endpoint. */
  wsBaseUrl: string;
  /** The cockpit's client origin — the Origin the sidecar's gate allow-lists. */
  clientOrigin: string;
}

const HOST = "127.0.0.1";
// Dedicated ports for the REAL-server run, distinct from BOTH the default cockpit
// (5174/5173) AND the harness-proxy e2e (5184/5283/5185) so a default-port
// cockpit or a parallel harness run never collides.
export const REAL_SERVER_PORT = 5194;
export const REAL_CLIENT_PORT = 5293;

/** Idempotent: seed the fixture + compute the fixed socket path + write the
 *  handoff if it does not yet exist; otherwise return the existing one. Called by
 *  globalSetup AND run-terminal-real-server.ts so neither boot order leaves the
 *  server without its state dirs. */
export async function ensureRealTerminalSeeded(): Promise<RealTerminalHandoff> {
  if (existsSync(REAL_TERMINAL_HANDOFF_PATH)) {
    return readRealTerminalHandoff();
  }
  const fx = await seed();
  // A fixed socket path under a dedicated temp dir, shared by the server boot
  // (passed into startProductionServer) and this setup's pre-seed connection.
  const socketDir = await realpath(
    await mkdtemp(join(tmpdir(), "cockpit-e2e-real-sock-")),
  );
  await mkdir(socketDir, { recursive: true });
  const socketPath = join(socketDir, "terminal.sock");

  const handoff: RealTerminalHandoff = {
    stateDir: fx.stateDir,
    projectsDir: fx.projectsDir,
    worktree: fx.worktree,
    changeId: fx.changeId,
    handle: fx.handle,
    socketPath,
    wsBaseUrl: `ws://${HOST}:${REAL_SERVER_PORT}`,
    clientOrigin: `http://${HOST}:${REAL_CLIENT_PORT}`,
  };
  await writeFile(
    REAL_TERMINAL_HANDOFF_PATH,
    JSON.stringify(handoff, null, 2),
    "utf8",
  );
  return handoff;
}

export function readRealTerminalHandoff(): RealTerminalHandoff {
  return JSON.parse(
    readFileSync(REAL_TERMINAL_HANDOFF_PATH, "utf8"),
  ) as RealTerminalHandoff;
}

/** Wait until the host's AF_UNIX socket accepts a connection (the server wrapper
 *  spawns the host async; globalSetup may run before READY). */
async function waitForSocket(
  socketPath: string,
  timeoutMs = 30_000,
): Promise<void> {
  const deadline = Date.now() + timeoutMs;
  for (;;) {
    const ok = await new Promise<boolean>((resolve) => {
      const sock = connect(socketPath);
      const done = (v: boolean): void => {
        sock.removeAllListeners();
        sock.destroy();
        resolve(v);
      };
      sock.once("connect", () => done(true));
      sock.once("error", () => done(false));
    });
    if (ok) return;
    if (Date.now() > deadline) {
      throw new Error(
        `real session-manager host socket never accepted: ${socketPath}`,
      );
    }
    await new Promise((r) => setTimeout(r, 200));
  }
}

/** One NDJSON request/ack over the AF_UNIX socket. Resolves with the first
 *  response line whose id matches (open/feed are unary). */
function rpc(
  sock: Socket,
  framer: ReturnType<typeof createNdjsonLineFramer>,
  id: string,
  method: string,
  params: Record<string, unknown>,
): Promise<Record<string, unknown>> {
  return new Promise((resolve, reject) => {
    const onData = (chunk: Buffer): void => {
      for (const line of framer.push(chunk)) {
        let obj: Record<string, unknown>;
        try {
          obj = JSON.parse(line) as Record<string, unknown>;
        } catch {
          continue;
        }
        if (obj.id === id) {
          sock.off("data", onData);
          resolve(obj);
          return;
        }
      }
    };
    sock.on("data", onData);
    const timer = setTimeout(() => {
      sock.off("data", onData);
      reject(new Error(`rpc ${method} timed out`));
    }, 10_000);
    void timer.unref?.();
    sock.write(JSON.stringify({ id, method, params }) + "\n");
  });
}

/**
 * Pre-seed the change's pty scrollback over the REAL socket: open the session
 * (carrying the full spec, since talking raw to the host bypasses the sidecar's
 * open-rewrite), feed the known token, and wait for it to land in the snapshot
 * the browser's later attach will replay. The pre-seed connection is transient —
 * the binding guard scopes it to THIS connection only; closing it releases the
 * binding so the browser's own connection binds fresh.
 */
async function preSeedScrollback(handoff: RealTerminalHandoff): Promise<void> {
  await waitForSocket(handoff.socketPath);
  const sock = connect(handoff.socketPath);
  const framer = createNdjsonLineFramer();
  await new Promise<void>((resolve, reject) => {
    sock.once("connect", () => resolve());
    sock.once("error", reject);
  });
  try {
    const opened = await rpc(sock, framer, "seed-open", "open", {
      key: handoff.changeId,
      spec: { provider: "pty", cwd: handoff.worktree, io_mode: "pty" },
    });
    if (opened.ok !== true) {
      throw new Error(`pre-seed open failed: ${JSON.stringify(opened)}`);
    }
    // Feed the token (the fake pty child echoes fed bytes into the ring). CRLF so
    // it renders as its own line in xterm's accessible layer.
    const bytes = Buffer.from(`${REAL_SCROLLBACK_TOKEN}\r\n`, "utf8");
    const fed = await rpc(sock, framer, "seed-feed", "feed", {
      key: handoff.changeId,
      data: bytes.toString("base64"),
      encoding: "base64",
    });
    if (fed.ok !== true) {
      throw new Error(`pre-seed feed failed: ${JSON.stringify(fed)}`);
    }
    // Give the pump a beat to drain the echo into the scrollback ring before the
    // browser attaches (the attach snapshot must already contain the token).
    await new Promise((r) => setTimeout(r, 500));
  } finally {
    sock.end();
  }
}

export default async function globalSetup(): Promise<void> {
  const handoff = await ensureRealTerminalSeeded();
  await preSeedScrollback(handoff);
}

export async function globalTeardown(): Promise<void> {
  try {
    if (existsSync(REAL_TERMINAL_HANDOFF_PATH)) {
      const h = readRealTerminalHandoff();
      await rm(h.stateDir, { recursive: true, force: true });
      await rm(h.projectsDir, { recursive: true, force: true });
      await rm(h.worktree, { recursive: true, force: true });
      await rm(REAL_TERMINAL_HANDOFF_PATH, { force: true });
    }
  } catch {
    /* nothing to clean if setup failed */
  }
}
