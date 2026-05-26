// WP-016 — boot the cockpit Express server against the seeded fixture.
//
// Playwright's webServer runs a shell command; the server reads
// SULIS_STATE_DIR / CLAUDE_PROJECTS_DIR from its env at module-load time.
// We call ensureSeeded() (idempotent) so the fixture exists even if this
// wrapper runs before globalSetup, then set those env vars, then build the
// real production app and listen on the e2e port. buildProductionApp() +
// listen() is called directly (rather than running index.ts as main) so
// the loopback bind is explicit here and the seeded env is in scope before
// CONFIG is read.

import { ensureSeeded } from "./fixtures/seed";

const handoff = await ensureSeeded();

process.env.SULIS_STATE_DIR = handoff.stateDir;
process.env.CLAUDE_PROJECTS_DIR = handoff.projectsDir;
process.env.COCKPIT_SERVER_PORT = process.env.COCKPIT_SERVER_PORT ?? "5174";

// Import AFTER setting env so CONFIG (read at module load) picks up the
// seeded dirs.
const { buildProductionApp } = await import("../server/index.ts");
const { CONFIG } = await import("../server/config.ts");

const app = buildProductionApp();
app.listen(CONFIG.serverPort, CONFIG.bindAddress, () => {
  // eslint-disable-next-line no-console -- e2e heartbeat for Playwright readiness
  console.log(
    `e2e cockpit server up on ${CONFIG.bindAddress}:${CONFIG.serverPort}`,
  );
});
