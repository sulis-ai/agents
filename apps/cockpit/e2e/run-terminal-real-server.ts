// WP-007 — boot the REAL cockpit production server for the real-server e2e.
//
// The production sibling of run-terminal-server.ts. Where that wrapper called
// buildProductionApp() + app.listen() directly (the GET surface only — no
// daemon, no sidecar), THIS wrapper boots the FULL production path:
// startProductionServer() `ensureDaemon`s the SHARED Python session-manager
// daemon (binding guard ON) at the injected fixed socket and attaches the real
// terminal sidecar to the /terminal WS upgrade (WP-004/007 composition). That is
// the load-bearing difference — the round-trip runs through the production
// composition, not the harness proxy (MEA-09).
//
// WP-007 MIGRATION: the cockpit no longer spawns its OWN ephemeral host. It
// `ensureDaemon`s the SHARED daemon at the (injected, isolated) fixed socket.
// The daemon defaults its pty provider to the REAL interactive `claude` adapter;
// CI cannot run that binary (the deferred observed-done, TDD §4), so this wrapper
// points the daemon's pty provider at the shared FAKE pty child via the
// `SULIS_DAEMON_PTY_CHILD` seam — the same MEA-09 substrate the Python daemon
// suite uses — BEFORE the ensure spawns the daemon.
//
// It calls ensureRealTerminalSeeded() — idempotent — so it works regardless of
// whether globalSetup or this webServer boots first (the harness ensureSeeded
// pattern). The fixed socket path from the handoff is passed into
// startProductionServer so globalSetup's pre-seed connection and the running
// server share ONE socket. The client origin is pinned so the sidecar's Origin
// gate allow-lists the e2e client's port.

import { execFileSync } from "node:child_process";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

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

// WP-007 — point the (ensure-spawned) SHARED daemon's pty provider at the shared
// fake pty child: the daemon defaults to the real `claude` adapter, which CI
// cannot run (the WP-009 lesson; the real round-trip is the deferred observed-
// done). A long idle window so the daemon never self-exits mid-run. Set BEFORE
// startProductionServer → ensureDaemon spawns the daemon (it inherits this env).
const here = dirname(fileURLToPath(import.meta.url));
const scriptsDir = join(here, "..", "..", "..", "plugins", "sulis", "scripts");
const childHome = mkdtempSync(join(tmpdir(), "wp007-e2e-pty-child-"));
const fakePtyChild = execFileSync(
  "python3",
  [
    "-c",
    [
      "import sys",
      "from pathlib import Path",
      `sys.path.insert(0, ${JSON.stringify(join(scriptsDir, "tests", "lib"))})`,
      "import fake_claude_child",
      `print(fake_claude_child.write_child(Path(${JSON.stringify(childHome)})))`,
    ].join("\n"),
  ],
  { encoding: "utf8" },
).trim();
process.env.SULIS_DAEMON_PTY_CHILD = fakePtyChild;
process.env.SULIS_DAEMON_IDLE_EXIT_SECS = "3600";

const { startProductionServer } = await import("../server/index.ts");

const handle = await startProductionServer({
  // Share the one socket with globalSetup's pre-seed (the production daemon seeds
  // no banner; the setup feeds the scrollback over this same socket). The ensure
  // cold-starts the SHARED daemon at this fixed isolated socket.
  socketPath: handoff.socketPath,
});

// eslint-disable-next-line no-console -- e2e heartbeat for Playwright readiness
console.log(
  `live-terminal REAL e2e server up on 127.0.0.1:${handle.port} ` +
    `(shared daemon socket ${handle.socketPath})`,
);

// Graceful shutdown so Playwright can reap the webServer cleanly. close() tears
// down the sidecar + HTTP surface; the SHARED daemon survives close() (WP-007),
// so this wrapper also reaps the isolated daemon it cold-started (by argv match
// on the per-run socket) so no detached process leaks across e2e runs.
function reapDaemon(): void {
  try {
    execFileSync("pkill", ["-TERM", "-f", handoff.socketPath], {
      stdio: "ignore",
    });
  } catch {
    /* no matching process — fine */
  }
}

const shutdown = (signal: NodeJS.Signals): void => {
  // eslint-disable-next-line no-console -- e2e heartbeat
  console.log(`[real-e2e] received ${signal} — closing server (reaping daemon)`);
  handle
    .close()
    .finally(() => {
      reapDaemon();
      process.exit(0);
    });
};
process.on("SIGTERM", () => shutdown("SIGTERM"));
process.on("SIGINT", () => shutdown("SIGINT"));
