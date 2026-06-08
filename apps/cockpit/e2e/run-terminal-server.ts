// WP-010 — boot the cockpit Express server for the live-terminal e2e.
//
// Mirrors run-server.ts but uses the DEDICATED terminal seed (its own
// state/projects dirs) so the live-terminal run is fully isolated from a
// developer's running cockpit. Calls ensureTerminalSeeded() — idempotent —
// rather than reading the handoff directly, so this wrapper works regardless of
// whether globalSetup or the webServer boots first (the WP-016 ensureSeeded
// pattern). Whichever runs first seeds; the rest read.

import { ensureTerminalSeeded } from "./live-terminal-setup";

const handoff = await ensureTerminalSeeded();

process.env.SULIS_STATE_DIR = handoff.stateDir;
process.env.CLAUDE_PROJECTS_DIR = handoff.projectsDir;

const { buildProductionApp } = await import("../server/index.ts");
const { CONFIG } = await import("../server/config.ts");

const app = buildProductionApp();
app.listen(CONFIG.serverPort, CONFIG.bindAddress, () => {
  // eslint-disable-next-line no-console -- e2e heartbeat for Playwright readiness
  console.log(
    `live-terminal e2e server up on ${CONFIG.bindAddress}:${CONFIG.serverPort}`,
  );
});
