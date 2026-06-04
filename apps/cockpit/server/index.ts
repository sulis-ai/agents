// WP-010 — Server bootstrap.
//
// Replaces the WP-001 placeholder banner with the real Express HTTP
// surface (six GET routes on 127.0.0.1:5174 by default). Composition:
//
//   1. Resolve runtime config (CONFIG) — bind address, ports, sulis
//      state dir, claude projects dir, file cap, git timeout.
//   2. Wire the production ChangeStoreReader adapter
//      (SulisChangeStoreReader → shells out to the Python helper).
//   3. createApp() with those deps.
//   4. app.listen(port, "127.0.0.1") — the bind address is the literal
//      from CONFIG; never read from env per TDD §13.1.
//
// The dev runner (`npm run dev`) calls this via `tsx watch`, restarts
// the server on file changes. Vite serves the client in parallel.
//
// The `if (isMainModule)` guard means importing this file in a test
// (e.g. the WP-001 skeleton smoke) does NOT auto-bind a port; binding
// only happens when `tsx server/index.ts` runs this file as the main
// module.

import path from "node:path";
import { fileURLToPath } from "node:url";

import { SulisChangeStoreReader } from "./adapters/SulisChangeStoreReader";
import {
  StreamJsonSessionBridge,
  spawnClaudeBridge,
} from "./adapters/StreamJsonSessionBridge";
import { resolveSessionFor } from "./lib/resolveSession";
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

/** True when this file was invoked as the main module via `tsx`/`node`. */
function isMainModule(): boolean {
  if (process.argv[1] === undefined) return false;
  const invokedPath = path.resolve(process.argv[1]);
  const thisPath = fileURLToPath(import.meta.url);
  return invokedPath === thisPath;
}

const banner = `cockpit server up — bound to http://${CONFIG.bindAddress}:${CONFIG.serverPort}`;

if (isMainModule()) {
  const app = buildProductionApp();
  const server = app.listen(CONFIG.serverPort, CONFIG.bindAddress, () => {
    // eslint-disable-next-line no-console -- intentional: dev-runner heartbeat
    console.log(banner);
  });

  // Graceful shutdown so `tsx watch` can restart cleanly.
  const shutdown = (signal: NodeJS.Signals): void => {
    // eslint-disable-next-line no-console -- intentional: dev-runner heartbeat
    console.log(`[cockpit] received ${signal} — closing server`);
    server.close(() => {
      process.exit(0);
    });
  };
  process.on("SIGTERM", () => shutdown("SIGTERM"));
  process.on("SIGINT", () => shutdown("SIGINT"));
} else {
  // Imported (not invoked as main) — emit the banner so the WP-001
  // skeleton smoke test still sees a heartbeat without binding a port.
  // eslint-disable-next-line no-console -- intentional: dev-runner heartbeat
  console.log(banner);
}

export { banner };
