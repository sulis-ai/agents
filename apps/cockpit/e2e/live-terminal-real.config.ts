// WP-007 — dedicated Playwright config for the REAL-server live-terminal e2e.
//
// SEPARATE from both playwright.config.ts (read-only smoke) and
// live-terminal.config.ts (the harness-proxy e2e) because this run:
//
//   1. Boots the FULL production server (startProductionServer → spawns the real
//      Python host + attaches the real terminal sidecar), NOT the harness proxy.
//      run-terminal-real-server.ts is the boot wrapper.
//   2. Gives the client NO VITE_TERMINAL_WS_URL — so the WP-006 same-origin
//      default resolves to the cockpit's OWN /terminal endpoint. The e2e vite
//      config (vite.real-terminal.config.ts) proxies the /terminal WS upgrade to
//      the real server so that same-origin default genuinely reaches the sidecar.
//   3. Uses DEDICATED ports (server 5194, client 5293) + `reuseExistingServer:
//      false` + a seeded state dir, so it never touches a developer's cockpit or
//      ~/.sulis (the isolation invariant, DoD Blue).
//
// MEA-09: real interface, real socket, real pty child — no proxy in the loop.

import { defineConfig, devices } from "@playwright/test";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

import { REAL_SERVER_PORT, REAL_CLIENT_PORT } from "./live-terminal-real-setup";

const here = dirname(fileURLToPath(import.meta.url));
const cockpitRoot = join(here, "..");

const HOST = "127.0.0.1";
const clientOrigin = `http://${HOST}:${REAL_CLIENT_PORT}`;

export default defineConfig({
  testDir: here,
  // Only the real-server spec — the smoke + harness-proxy specs run elsewhere.
  testMatch: /live-terminal-real\.spec\.ts$/,
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: process.env.CI
    ? [["html", { open: "never" }], ["list"]]
    : [["list"]],
  globalSetup: join(here, "live-terminal-real-setup.ts"),
  globalTeardown: join(here, "live-terminal-real-teardown.ts"),
  use: {
    baseURL: clientOrigin,
    trace: "on-first-retry",
    screenshot: process.env.PWTEST_SCREENSHOTS ? "only-on-failure" : "off",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: [
    {
      // The REAL production server: HTTP surface + spawned host + attached sidecar.
      command: "npx tsx e2e/run-terminal-real-server.ts",
      cwd: cockpitRoot,
      url: `http://${HOST}:${REAL_SERVER_PORT}/api/changes`,
      reuseExistingServer: false,
      timeout: 60_000,
      stdout: "pipe",
      stderr: "pipe",
      env: {
        COCKPIT_SERVER_PORT: String(REAL_SERVER_PORT),
        COCKPIT_CLIENT_PORT: String(REAL_CLIENT_PORT),
      },
    },
    {
      // The client — deliberately NO VITE_TERMINAL_WS_URL: the WP-006 same-origin
      // default must be what wires the live terminal (the production proof).
      command:
        "npx vite --config e2e/vite.real-terminal.config.ts",
      cwd: cockpitRoot,
      url: clientOrigin,
      reuseExistingServer: false,
      timeout: 60_000,
      stdout: "pipe",
      stderr: "pipe",
      env: {
        COCKPIT_SERVER_PORT: String(REAL_SERVER_PORT),
        COCKPIT_CLIENT_PORT: String(REAL_CLIENT_PORT),
      },
    },
  ],
});
