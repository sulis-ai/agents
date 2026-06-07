// WP-010 — Server bootstrap.  ·  WP-004 — terminal host + WS lifecycle.
//
// Replaces the WP-001 placeholder banner with the real Express HTTP
// surface (six GET routes on 127.0.0.1:5174 by default). Composition:
//
//   1. Resolve runtime config (CONFIG) — bind address, ports, sulis
//      state dir, claude projects dir, file cap, git timeout, caps.
//   2. Wire the production ChangeStoreReader adapter
//      (SulisChangeStoreReader → shells out to the Python helper).
//   3. createApp() with those deps.
//   4. app.listen(port, "127.0.0.1") — the bind address is the literal
//      from CONFIG; never read from env per TDD §13.1.
//   5. WP-004 — spawn the Python session-manager host (ADR-011), wait for
//      its `READY <socket>` line, then attach the terminal sidecar
//      (WP-002/003) to the running HTTP server's `upgrade` event. The host +
//      sidecar are torn down on SIGTERM/SIGINT alongside the HTTP server.
//
// The dev runner (`npm run dev`) calls this via `tsx watch`, restarts
// the server on file changes. Vite serves the client in parallel.
//
// `buildProductionApp()` stays a PURE FACTORY: importing this file or calling
// it binds no port and spawns no host. The host spawn + WS attach live in
// `startProductionServer()`, invoked only from the `isMainModule` boot block
// (the WP-001 isMainModule discipline carries to the host spawn) or explicitly
// from a test/harness.
//
// INDEPENDENCE (founder directive — MUST): the terminal host + sidecar are
// their OWN lifecycle. This composition does NOT wire the terminal path through
// the chat relay (routes/chat.ts) or the chat SessionBridge — `startProduction
// Server` attaches the terminal sidecar to the shared HTTP server directly. The
// chat bridge (above) and the terminal host (below) are independent processes
// composed into one server entry; neither imports the other.

import { spawn, type ChildProcess } from "node:child_process";
import type { Server } from "node:http";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { SulisChangeStoreReader } from "./adapters/SulisChangeStoreReader";
import {
  StreamJsonSessionBridge,
  spawnClaudeBridge,
} from "./adapters/StreamJsonSessionBridge";
import {
  createTerminalSidecar,
  type TerminalSidecar,
} from "./adapters/TerminalSidecar";
import { resolveSessionFor } from "./lib/resolveSession";
import type { ChangeStoreReader } from "./ports/ChangeStoreReader";
import type { SessionResolution } from "./ports/SessionBridge";
import { CONFIG } from "./config";
import { createApp } from "./app";

/**
 * Resolve the absolute path to the bundled Python helper
 * `plugins/sulis/scripts/sulis-list-changes`. Honours an explicit
 * override via `SULIS_LIST_CHANGES_HELPER` (used by tests + CI).
 */
function resolveHelperPath(): string {
  const override = process.env.SULIS_LIST_CHANGES_HELPER;
  if (override !== undefined && override.length > 0) {
    return override;
  }
  // server/index.ts lives at apps/cockpit/server/index.ts; the helper
  // lives at plugins/sulis/scripts/sulis-list-changes off the repo
  // root (= 3 levels up from this file).
  const here = path.dirname(fileURLToPath(import.meta.url));
  const repoRoot = path.resolve(here, "..", "..", "..");
  return path.join(
    repoRoot,
    "plugins",
    "sulis",
    "scripts",
    "sulis-list-changes",
  );
}

/**
 * Resolve the absolute path to the bundled Python session-manager host
 * `plugins/sulis/scripts/session_manager_host.py` (WP-001, ADR-011). Mirrors
 * `resolveHelperPath` exactly (EP-03 — same repo-root-relative resolution, an
 * env override for tests/CI), keyed on the host script name. Honours
 * `SULIS_SESSION_MANAGER_HOST` (used by tests + CI).
 */
function resolveHostPath(): string {
  const override = process.env.SULIS_SESSION_MANAGER_HOST;
  if (override !== undefined && override.length > 0) {
    return override;
  }
  const here = path.dirname(fileURLToPath(import.meta.url));
  const repoRoot = path.resolve(here, "..", "..", "..");
  return path.join(
    repoRoot,
    "plugins",
    "sulis",
    "scripts",
    "session_manager_host.py",
  );
}

/**
 * Build the production app. Exported so a test or external harness
 * can construct the same dependency graph without binding a port.
 */
export function buildProductionApp() {
  const changeStore = new SulisChangeStoreReader({
    helperPath: resolveHelperPath(),
    sulisStateDir: CONFIG.sulisStateDir,
    timeoutMs: CONFIG.gitTimeoutMs,
  });

  // WP-005 — the production SessionBridge (ADR-002). Its `resolve` looks up the
  // change's worktree (the cwd the session runs in + the binding identity) via
  // the change store, then composes the side-effect-free liveness + transcript
  // reads (FR-N4). The real `claude` process start is confined to
  // `spawnClaudeBridge` inside the adapter — the one sanctioned process-start
  // site (ADR-003). The real round-trip is the founder-machine observation.
  const sessionBridge = new StreamJsonSessionBridge({
    resolve: async (changeId): Promise<SessionResolution> => {
      const record = await changeStore.readChangeRecord(changeId);
      if (record === null) {
        // Unknown change → fresh with no usable worktree; the relay's
        // requireChange already 404s before relay, so this is defensive.
        return { kind: "fresh", session: { changeId, cwd: "" } };
      }
      return resolveSessionFor(changeId, {
        sulisStateDir: CONFIG.sulisStateDir,
        claudeProjectsDir: CONFIG.claudeProjectsDir,
        worktreePath: record.worktreePath,
      });
    },
    spawnBridge: spawnClaudeBridge,
    // The bridge's startup-to-first-output budget is its OWN config — a cold
    // headless `claude` legitimately takes ~5–9 s to first output, well past a
    // git operation's 5 s. Reusing gitTimeoutMs killed the agent right as it
    // woke ⇒ false `unreachable` on every live chat (WP-005 fix-forward).
    startupTimeoutMs: CONFIG.chatBridgeStartupTimeoutMs,
  });

  return createApp({
    changeStore,
    sessionBridge,
    // The relay's one-structured-line-per-send log (NFR-SEC-03: never the body
    // or reply). Routed through the dev-runner heartbeat console; no bodies.
    chatLogSink: (line) => {
      // eslint-disable-next-line no-console -- intentional: structured relay log
      console.log(JSON.stringify({ at: "chat-relay", ...line }));
    },
    // WP-009 — the concierge's one-structured-line-per-query log (NFR-SEC-03:
    // never the question or reply text — only outcome / route / code).
    conciergeLogSink: (line) => {
      // eslint-disable-next-line no-console -- intentional: structured concierge log
      console.log(JSON.stringify({ at: "concierge-query", ...line }));
    },
    sulisStateDir: CONFIG.sulisStateDir,
    claudeProjectsDir: CONFIG.claudeProjectsDir,
    fileMaxBytes: CONFIG.fileMaxBytes,
    gitTimeoutMs: CONFIG.gitTimeoutMs,
    clientOrigin: CONFIG.clientOrigin,
  });
}

/** A spawned session-manager host + the AF_UNIX socket it serves on. */
export interface SessionManagerHostHandle {
  /** The long-lived host process (killed with SIGTERM on shutdown). */
  host: ChildProcess;
  /** The AF_UNIX socket path the host's `SocketServer` is serving on. */
  socketPath: string;
}

/** Options for {@link startSessionManagerHost}. All have safe defaults so a
 *  bare call works in dev; tests inject a python override / fixed socket dir. */
export interface StartSessionManagerHostOptions {
  /** python executable (defaults to `python3`). */
  python?: string;
  /** The AF_UNIX socket path to serve on (defaults to a fresh per-run temp). */
  socketPath?: string;
  /** How long to wait for the `READY <socket>` line before failing (ms). */
  readyTimeoutMs?: number;
}

/**
 * Spawn the Python session-manager host (ADR-011) and resolve once it prints
 * its `READY <socket>` line on stdout. The production sibling of the e2e
 * `terminal-proxy.ts::startBackend`, extracted here as a small, unit-testable
 * named helper (WP-004 Blue): same READY-line handshake, but the production
 * host runs with the binding guard ON (its default) and seeds no banner.
 *
 * The socket lives in a per-run temp dir with 0o600 perms (the engine's
 * `SocketServer.start` chmods it). The host runs until killed (SIGTERM) — the
 * cockpit owns its lifetime (tied to `startProductionServer`'s shutdown).
 *
 * READ-ONLY GATE (ADR-010 / WP-005): this is the ONE new sanctioned process-
 * start site this change introduces. It is named in the read-only gate's
 * allow-list (WP-005 owns the full gate reconciliation; ADR-010).
 */
export function startSessionManagerHost(
  opts: StartSessionManagerHostOptions = {},
): Promise<SessionManagerHostHandle> {
  const python = opts.python ?? "python3";
  const socketPath =
    opts.socketPath ??
    path.join(mkdtempSync(path.join(tmpdir(), "wp004-sock-")), "terminal.sock");
  const readyTimeoutMs = opts.readyTimeoutMs ?? 30_000;

  return new Promise<SessionManagerHostHandle>((resolve, reject) => {
    const host = spawn(python, [resolveHostPath(), "--socket", socketPath], {
      stdio: ["ignore", "pipe", "pipe"],
    });
    let ready = false;
    const timer = setTimeout(() => {
      if (!ready) {
        host.kill("SIGKILL");
        reject(new Error("session_manager_host.py did not become READY"));
      }
    }, readyTimeoutMs);

    host.stdout.on("data", (chunk: Buffer) => {
      if (chunk.toString().includes("READY")) {
        ready = true;
        clearTimeout(timer);
        resolve({ host, socketPath });
      }
    });
    host.stderr.on("data", (chunk: Buffer) => {
      // Surface host errors to the dev-runner console for debugging (NFR-SEC-03:
      // the host never writes terminal bytes to stderr — only diagnostics).
      // eslint-disable-next-line no-console -- intentional: dev-runner host diagnostics
      console.error(`[session-manager-host] ${chunk.toString().trimEnd()}`);
    });
    host.on("exit", (code) => {
      if (!ready) {
        clearTimeout(timer);
        reject(
          new Error(`session_manager_host.py exited early (code ${code})`),
        );
      }
    });
  });
}

/** A running production server: the HTTP surface + the terminal host + the
 *  attached sidecar, with a single `close()` that tears all three down. */
export interface ProductionServerHandle {
  /** The bound HTTP server (the GET surface + the WS upgrade endpoint). */
  httpServer: Server;
  /** The terminal sidecar attached to `httpServer`'s `upgrade` event. */
  sidecar: TerminalSidecar;
  /** The spawned Python session-manager host process. */
  host: ChildProcess;
  /** The bound port (resolves an ephemeral `port: 0` to the actual port). */
  port: number;
  /** The `ws://host:port` base URL the terminal endpoint rides (`/terminal`). */
  url: string;
  /** Tear down the sidecar, then the host, then the HTTP server. Idempotent. */
  close(): Promise<void>;
}

/** Options for {@link startProductionServer}. Defaults reproduce the dev boot;
 *  tests inject a fake change store, an ephemeral port, and a tight origin. */
export interface StartProductionServerOptions {
  /** Port to bind (defaults to `CONFIG.serverPort`; pass `0` for ephemeral). */
  port?: number;
  /** The change-store reader the sidecar resolves change→worktree through
   *  (defaults to the production `SulisChangeStoreReader`). Reuse-first: this is
   *  the same port the chat path uses — no second resolution path (TDD §2.4). */
  changeStore?: ChangeStoreReader;
  /** The allowed browser origin(s) for the WS upgrade (defaults to
   *  `[CONFIG.clientOrigin]` — the same allow-one-origin posture as CORS). */
  originAllowList?: string[];
  /** python executable for the host (defaults to `python3`). */
  python?: string;
}

/**
 * Boot the full production server: build the app, listen, spawn the session-
 * manager host, wait for READY, then attach the terminal sidecar to the running
 * HTTP server's `upgrade` event (WP-004, the composition seam, TDD §2.3).
 *
 * The sidecar's `resolveChange` is bound to the change-store reader
 * (`readChangeRecord(id).worktreePath` → `{provider:"pty", cwd:worktreePath}`)
 * — REUSE-FIRST (EP-03), the same lookup the chat path uses, no second
 * resolution path. The origin allow-list is `CONFIG.clientOrigin`; the caps are
 * the frozen `CONFIG.terminal*` ceilings; the log sink routes one structured
 * line per refuse through the dev-runner console (NFR-SEC-03: outcome/code/
 * change-id only, never a terminal byte).
 *
 * A host crash drops live terminals but NEVER the HTTP surface (separate
 * processes); attached clients receive `SOCKET_CLOSED` (handled client-side).
 */
export async function startProductionServer(
  opts: StartProductionServerOptions = {},
): Promise<ProductionServerHandle> {
  const port = opts.port ?? CONFIG.serverPort;
  const originAllowList = opts.originAllowList ?? [CONFIG.clientOrigin];
  const changeStore =
    opts.changeStore ??
    new SulisChangeStoreReader({
      helperPath: resolveHelperPath(),
      sulisStateDir: CONFIG.sulisStateDir,
      timeoutMs: CONFIG.gitTimeoutMs,
    });

  const app = buildProductionApp();

  // 1. Bind the HTTP surface first (the WS endpoint rides the same port + bind
  //    invariant). Resolve once listening; reject on a bind error.
  const httpServer = await new Promise<Server>((resolve, reject) => {
    const s = app.listen(port, CONFIG.bindAddress);
    s.once("error", reject);
    s.once("listening", () => {
      s.off("error", reject);
      resolve(s);
    });
  });
  const addr = httpServer.address();
  const boundPort = addr && typeof addr !== "string" ? addr.port : port;

  // 2. Spawn the host + wait for READY (ADR-011). If it never becomes READY,
  //    tear down the HTTP server we already bound so we leak nothing.
  let hostHandle: SessionManagerHostHandle;
  try {
    hostHandle = await startSessionManagerHost({ python: opts.python });
  } catch (err) {
    await new Promise<void>((res) => httpServer.close(() => res()));
    throw err;
  }

  // 3. Attach the terminal sidecar (WP-002/003) to the upgrade event. The
  //    change→spec resolution REUSES the change-store reader (TDD §2.4); the
  //    origin allow-list + caps + log sink are the production controls (WP-003).
  const sidecar = createTerminalSidecar({
    socketPath: hostHandle.socketPath,
    resolveChange: async (changeId: string) => {
      const record = await changeStore.readChangeRecord(changeId);
      if (record === null) return null;
      return { provider: "pty", cwd: record.worktreePath };
    },
    originAllowList,
    caps: {
      maxConnections: CONFIG.terminalMaxConnections,
      maxAttachmentsPerConnection: CONFIG.terminalMaxAttachmentsPerConnection,
    },
    logSink: (line) => {
      // eslint-disable-next-line no-console -- intentional: structured terminal log
      console.log(JSON.stringify({ at: "terminal-sidecar", ...line }));
    },
  });
  sidecar.attach(httpServer);

  let closed = false;
  const close = async (): Promise<void> => {
    if (closed) return;
    closed = true;
    // Sidecar first (stop accepting/serving WS), then the host (drop the
    // engine), then the HTTP surface. A host crash never reaches here — it
    // drops terminals but leaves the HTTP server up (separate processes).
    await sidecar.close();
    hostHandle.host.kill("SIGTERM");
    await new Promise<void>((res) => httpServer.close(() => res()));
  };

  return {
    httpServer,
    sidecar,
    host: hostHandle.host,
    port: boundPort,
    url: `ws://${CONFIG.bindAddress}:${boundPort}`,
    close,
  };
}

/** True when this file was invoked as the main module via `tsx`/`node`. */
function isMainModule(): boolean {
  if (process.argv[1] === undefined) return false;
  const invokedPath = path.resolve(process.argv[1]);
  const thisPath = fileURLToPath(import.meta.url);
  return invokedPath === thisPath;
}

const banner = `cockpit server up — bound to http://${CONFIG.bindAddress}:${CONFIG.serverPort}`;

if (isMainModule()) {
  // WP-004 — boot the full server: HTTP surface + session-manager host + the
  // attached terminal sidecar (the composition seam). A failure to spawn the
  // host is fatal at boot (the terminal would be dead); the HTTP surface is
  // never bound without the host because they boot together here.
  startProductionServer()
    .then((handle) => {
      // eslint-disable-next-line no-console -- intentional: dev-runner heartbeat
      console.log(banner);

      // Graceful shutdown so `tsx watch` can restart cleanly: tear down the
      // sidecar + host (handle.close) then exit. A host crash drops terminals
      // but never the HTTP surface — only this signal-driven path exits.
      let shuttingDown = false;
      const shutdown = (signal: NodeJS.Signals): void => {
        if (shuttingDown) return;
        shuttingDown = true;
        // eslint-disable-next-line no-console -- intentional: dev-runner heartbeat
        console.log(`[cockpit] received ${signal} — closing server + host`);
        handle.close().finally(() => process.exit(0));
      };
      process.on("SIGTERM", () => shutdown("SIGTERM"));
      process.on("SIGINT", () => shutdown("SIGINT"));
    })
    .catch((err: unknown) => {
      // eslint-disable-next-line no-console -- intentional: dev-runner heartbeat
      console.error(`[cockpit] failed to start: ${String(err)}`);
      process.exit(1);
    });
} else {
  // Imported (not invoked as main) — emit the banner so the WP-001
  // skeleton smoke test still sees a heartbeat without binding a port.
  // eslint-disable-next-line no-console -- intentional: dev-runner heartbeat
  console.log(banner);
}

export { banner };
