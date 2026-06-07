// WP-010 — dedicated Playwright config for the live-terminal round-trip.
//
// SEPARATE from playwright.config.ts (the WP-016 read-only smoke) for two
// reasons:
//   1. Isolation — the live-terminal run uses DEDICATED ports and
//      `reuseExistingServer: false`, so it never connects to a developer's
//      running cockpit (the v1 RED run did exactly that and read the real
//      ~/.sulis state). Its own seeded state dir is served on its own ports.
//   2. The terminal WS bridge — the vite client webServer is given
//      VITE_TERMINAL_WS_URL so the cockpit's createTerminalBridge wires the live
//      WebSocketTransport to the proxy (started in live-terminal-setup.ts).
//
// Ports (all dedicated, +10 off the defaults so a default-port cockpit never
// collides): server 5184, client 5183→5283, proxy 5185 (in setup).

import { defineConfig, devices } from "@playwright/test";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const cockpitRoot = join(here, "..");

const HOST = "127.0.0.1";
const SERVER_PORT = 5184;
const CLIENT_PORT = 5283;
const TERMINAL_WS_URL = "ws://127.0.0.1:5185";
const clientOrigin = `http://${HOST}:${CLIENT_PORT}`;

export default defineConfig({
  testDir: here,
  // Only the live-terminal spec — the smoke specs run under the default config.
  testMatch: /live-terminal\.spec\.ts$/,
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: process.env.CI
    ? [["html", { open: "never" }], ["list"]]
    : [["list"]],
  globalSetup: join(here, "live-terminal-setup.ts"),
  globalTeardown: join(here, "live-terminal-teardown.ts"),
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
      command: "npx tsx e2e/run-terminal-server.ts",
      cwd: cockpitRoot,
      url: `http://${HOST}:${SERVER_PORT}/api/changes`,
      // Always boot our own isolated server — never reuse a dev cockpit.
      reuseExistingServer: false,
      timeout: 60_000,
      stdout: "pipe",
      stderr: "pipe",
      env: {
        COCKPIT_SERVER_PORT: String(SERVER_PORT),
        COCKPIT_CLIENT_PORT: String(CLIENT_PORT),
      },
    },
    {
      command: "npx vite client --config client/vite.config.ts",
      cwd: cockpitRoot,
      url: clientOrigin,
      reuseExistingServer: false,
      timeout: 60_000,
      stdout: "pipe",
      stderr: "pipe",
      env: {
        COCKPIT_SERVER_PORT: String(SERVER_PORT),
        COCKPIT_CLIENT_PORT: String(CLIENT_PORT),
        // The cockpit wires the live WebSocketTransport when this is set.
        VITE_TERMINAL_WS_URL: TERMINAL_WS_URL,
      },
    },
  ],
});
