// WP-007 — boot the REAL cockpit production server for the real-server e2e.
//
// The production sibling of run-terminal-server.ts. Where that wrapper called
// buildProductionApp() + app.listen() directly (the GET surface only — no host,
// no sidecar), THIS wrapper boots the FULL production path: startProductionServer()
// spawns the real Python session-manager host (binding guard ON) and attaches the
// real terminal sidecar to the /terminal WS upgrade (WP-004 composition). That is
// the load-bearing difference — the round-trip runs through the production
// composition, not the harness proxy (MEA-09).
//
// It calls ensureRealTerminalSeeded() — idempotent — so it works regardless of
// whether globalSetup or this webServer boots first (the harness ensureSeeded
// pattern). The fixed socket path from the handoff is passed into
// startProductionServer so globalSetup's pre-seed connection and the running
// server share ONE socket. The client origin is pinned so the sidecar's Origin
// gate allow-lists the e2e client's port.

import {
  ensureRealTerminalSeeded,
  REAL_SERVER_PORT,
  REAL_CLIENT_PORT,
} from "./live-terminal-real-setup";

const handoff = await ensureRealTerminalSeeded();

// Isolation: serve the seeded state/projects dirs, never a developer's ~/.sulis.
process.env.SULIS_STATE_DIR = handoff.stateDir;
process.env.CLAUDE_PROJECTS_DIR = handoff.projectsDir;
// Pin the port + the client origin BEFORE config.ts is imported (CONFIG reads
// these at module-load). The sidecar's Origin gate allow-lists CONFIG.clientOrigin
// — it must equal the e2e client's origin or every WS upgrade is refused 403.
process.env.COCKPIT_SERVER_PORT = String(REAL_SERVER_PORT);
process.env.COCKPIT_CLIENT_ORIGIN = `http://127.0.0.1:${REAL_CLIENT_PORT}`;

const { startProductionServer } = await import("../server/index.ts");

const handle = await startProductionServer({
  // Share the one socket with globalSetup's pre-seed (the production host seeds
  // no banner; the setup feeds the scrollback over this same socket).
  socketPath: handoff.socketPath,
});

// eslint-disable-next-line no-console -- e2e heartbeat for Playwright readiness
console.log(
  `live-terminal REAL e2e server up on 127.0.0.1:${handle.port} ` +
    `(host socket ${handle.socketPath})`,
);

// Graceful shutdown so Playwright can reap the webServer cleanly (tears down the
// sidecar + host + HTTP surface).
const shutdown = (signal: NodeJS.Signals): void => {
  // eslint-disable-next-line no-console -- e2e heartbeat
  console.log(`[real-e2e] received ${signal} — closing server + host`);
  handle.close().finally(() => process.exit(0));
};
process.on("SIGTERM", () => shutdown("SIGTERM"));
process.on("SIGINT", () => shutdown("SIGINT"));
