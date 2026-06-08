// WP-010 — Server bootstrap.  ·  WP-004 — terminal + WS lifecycle.
// WP-007 — migrated onto the SHARED session-manager daemon (ADR-001/ADR-003).
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
//   5. WP-007 — `ensureDaemon` the SHARED session-manager daemon at the STABLE
//      socket (`~/.sulis/session-manager.sock`, env `SULIS_SESSION_MANAGER_SOCKET`)
//      — probe-first, cold-start-on-demand, idempotent (ADR-001). Then attach
//      the terminal sidecar (WP-002/003) to the running HTTP server's `upgrade`
//      event. The sidecar + HTTP server are torn down on SIGTERM/SIGINT — but
//      the SHARED daemon is NOT (it outlives any one cockpit; it may serve the
//      desktop view). This is what lands the cockpit view and the desktop view
//      on the SAME session — the load-bearing invariant.
//
//   The CH-01KTHV behaviour this REPLACES: the cockpit used to spawn its OWN
//   ephemeral host (`startSessionManagerHost`) on a per-run `mkdtempSync` temp
//   socket and own its lifetime. That made the two views land on DIFFERENT
//   managers. The ephemeral host is gone; the cockpit attaches the shared daemon.
//
// The dev runner (`npm run dev`) calls this via `tsx watch`, restarts
// the server on file changes. Vite serves the client in parallel.
//
// `buildProductionApp()` stays a PURE FACTORY: importing this file or calling
// it binds no port and ensures no daemon. The daemon-ensure + WS attach live in
// `startProductionServer()`, invoked only from the `isMainModule` boot block
// (the WP-001 isMainModule discipline carries to the daemon-ensure) or
// explicitly from a test/harness.
//
// INDEPENDENCE (founder directive — MUST): the terminal daemon + sidecar are
// their OWN lifecycle. This composition does NOT wire the terminal path through
// the chat relay (routes/chat.ts) or the chat SessionBridge — `startProduction
// Server` ensures the daemon (via the `ensureDaemon` binding, which imports no
// chat/platform) and attaches the terminal sidecar to the shared HTTP server
// directly. The chat bridge (above) and the terminal path (below) are
// independent processes composed into one server entry; neither imports the other.

import type { Server } from "node:http";
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
import { ensureDaemon, resolveDefaultSocket } from "./lib/ensureDaemon";
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

/** A running production server: the HTTP surface + the attached terminal
 *  sidecar (bridging to the SHARED daemon), with a single `close()` that tears
 *  down the sidecar + HTTP server — but NEVER the shared daemon (WP-007). */
export interface ProductionServerHandle {
  /** The bound HTTP server (the GET surface + the WS upgrade endpoint). */
  httpServer: Server;
  /** The terminal sidecar attached to `httpServer`'s `upgrade` event. */
  sidecar: TerminalSidecar;
  /** The SHARED daemon's AF_UNIX socket path the sidecar bridges to (the stable
   *  socket by default; a fixed path when injected for tests/e2e). Exposed so a
   *  test/e2e harness can pre-seed the same socket the server bridges to. The
   *  daemon behind it is SHARED — it is not owned by this server. */
  socketPath: string;
  /** The bound port (resolves an ephemeral `port: 0` to the actual port). */
  port: number;
  /** The `ws://host:port` base URL the terminal endpoint rides (`/terminal`). */
  url: string;
  /** Tear down the sidecar then the HTTP server. Idempotent. Does NOT touch the
   *  shared daemon — it outlives the cockpit (it may serve the desktop view). */
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
  /** python executable to launch the daemon with (defaults to `python3`). */
  python?: string;
  /** The AF_UNIX socket of the SHARED daemon to bridge to. Defaults to the
   *  STABLE socket (`resolveDefaultSocket()` — `~/.sulis/session-manager.sock`,
   *  env-overridable). Injecting a fixed path is the test/e2e seam: the e2e
   *  passes a fixed isolated path so `ensureDaemon` cold-starts (or finds) a
   *  daemon there and its setup can pre-seed the change's scrollback over the
   *  SAME socket the running server bridges to. Mirrors the existing `python`
   *  test-injection option. */
  socketPath?: string;
}

/**
 * Boot the full production server: build the app, listen, `ensureDaemon` the
 * SHARED session-manager daemon at the stable socket (WP-007, ADR-001), then
 * attach the terminal sidecar to the running HTTP server's `upgrade` event
 * (WP-004, the composition seam, TDD §2.3/§6).
 *
 * `ensureDaemon` is probe-first + idempotent: if the daemon is already live
 * (e.g. the desktop view started it), the cockpit ATTACHES it and spawns
 * nothing; otherwise it cold-starts the daemon detached and waits for `READY`.
 * Either way both views land on the SAME daemon — the load-bearing invariant.
 *
 * The sidecar's `resolveChange` is bound to the change-store reader
 * (`readChangeRecord(id).worktreePath` → `{provider:"pty", cwd:worktreePath}`)
 * — REUSE-FIRST (EP-03), the same lookup the chat path uses, no second
 * resolution path. The origin allow-list is `CONFIG.clientOrigin`; the caps are
 * the frozen `CONFIG.terminal*` ceilings; the log sink routes one structured
 * line per refuse through the dev-runner console (NFR-SEC-03: outcome/code/
 * change-id only, never a terminal byte).
 *
 * A daemon crash drops live terminals but NEVER the HTTP surface (separate
 * processes); attached clients receive `SOCKET_CLOSED` (handled client-side) and
 * the next `ensureDaemon` rebuilds it.
 */
export async function startProductionServer(
  opts: StartProductionServerOptions = {},
): Promise<ProductionServerHandle> {
  const port = opts.port ?? CONFIG.serverPort;
  const originAllowList = opts.originAllowList ?? [CONFIG.clientOrigin];
  const socketPath = opts.socketPath ?? resolveDefaultSocket();
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

  // 2. Ensure the SHARED daemon is live at the stable socket (ADR-001). Probe-
  //    first + idempotent: attaches an already-running daemon (it may serve the
  //    desktop view), or cold-starts one detached. If it never becomes live,
  //    tear down the HTTP server we already bound so we leak nothing.
  let daemonSocket: string;
  try {
    daemonSocket = await ensureDaemon(socketPath, { python: opts.python });
  } catch (err) {
    await new Promise<void>((res) => httpServer.close(() => res()));
    throw err;
  }

  // 3. Attach the terminal sidecar (WP-002/003) to the upgrade event, bridging
  //    to the SHARED daemon's socket. The change→spec resolution REUSES the
  //    change-store reader (TDD §2.4); the origin allow-list + caps + log sink
  //    are the production controls (WP-003).
  const sidecar = createTerminalSidecar({
    socketPath: daemonSocket,
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
    // Sidecar first (stop accepting/serving WS), then the HTTP surface. The
    // SHARED daemon is deliberately NOT torn down here — it outlives the cockpit
    // (it may be serving the desktop view; ADR-001/003). `close()` only detaches
    // this cockpit's view; the daemon's own idle-empty auto-exit bounds it.
    await sidecar.close();
    await new Promise<void>((res) => httpServer.close(() => res()));
  };

  return {
    httpServer,
    sidecar,
    socketPath: daemonSocket,
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
  // WP-007 — boot the full server: HTTP surface + ensure the SHARED daemon + the
  // attached terminal sidecar (the composition seam). A failure to ensure the
  // daemon is fatal at boot (the terminal would be dead); the HTTP surface is
  // never left bound without a daemon because they boot together here.
  startProductionServer()
    .then((handle) => {
      // eslint-disable-next-line no-console -- intentional: dev-runner heartbeat
      console.log(banner);

      // Graceful shutdown so `tsx watch` can restart cleanly: tear down the
      // sidecar + HTTP surface (handle.close) then exit. The SHARED daemon is
      // NOT torn down — it outlives the cockpit (it may serve the desktop view).
      let shuttingDown = false;
      const shutdown = (signal: NodeJS.Signals): void => {
        if (shuttingDown) return;
        shuttingDown = true;
        // eslint-disable-next-line no-console -- intentional: dev-runner heartbeat
        console.log(`[cockpit] received ${signal} — closing server (daemon survives)`);
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
