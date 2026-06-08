// WP-016 — Playwright config for the cockpit end-to-end smoke.
//
// Boots BOTH halves of the cockpit against a seeded fixture:
//   - the Express server (run-server.ts) on COCKPIT_SERVER_PORT (5174)
//   - the Vite dev client on COCKPIT_CLIENT_PORT (5173), which proxies
//     /api/* to the server.
// Playwright drives a real Chromium against the client origin.
//
// globalSetup seeds the fixture and writes a handoff JSON; globalTeardown
// removes the temp dirs. Both webServers read that handoff so they boot
// against the same seeded SULIS_STATE_DIR / CLAUDE_PROJECTS_DIR.
//
// Visual-regression / screenshot comparison is intentionally OFF (no
// font/theme drift flake in CI). A founder can opt-in locally by setting
// PWTEST_SCREENSHOTS=1 — but the default suite asserts behaviour, not
// pixels (WP-016 Blue requirement).
//
// Browser availability: `npx playwright install chromium` is a one-time
// local step (documented in the cockpit README). In CI the workflow runs
// it before the tests; if the download is unavailable the workflow skips
// the e2e job rather than failing the whole gate (the read-only inventory
// gate + the combined vitest suite still run).

import { defineConfig, devices } from "@playwright/test";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

import {
  getClientPort,
  getServerPort,
  COCKPIT_HOST,
} from "../shared/dev-ports";

const here = dirname(fileURLToPath(import.meta.url));
const cockpitRoot = join(here, "..");

const serverPort = getServerPort();
const clientPort = getClientPort();
const clientOrigin = `http://${COCKPIT_HOST}:${clientPort}`;

export default defineConfig({
  testDir: here,
  // Specs only — fixtures/seed/run-server are helpers, not test files. The
  // live-terminal round-trips run under their OWN configs (live-terminal.config.ts
  // / live-terminal-real.config.ts: dedicated ports + the terminal transport +
  // their own globalSetup that seeds the terminal handoff), so exclude BOTH from
  // this smoke run. The `-real` infix means a `live-terminal\.spec\.ts$` pattern
  // would NOT exclude live-terminal-real.spec.ts — it would then run here without
  // its handoff and fail; match any `live-terminal*.spec.ts`.
  testMatch: /.*\.spec\.ts$/,
  testIgnore: /live-terminal.*\.spec\.ts$/,
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: process.env.CI
    ? [["html", { open: "never" }], ["list"]]
    : [["list"]],
  globalSetup: join(here, "global-setup.ts"),
  globalTeardown: join(here, "global-teardown.ts"),
  use: {
    baseURL: clientOrigin,
    trace: "on-first-retry",
    // No screenshot/visual comparison by default.
    screenshot: process.env.PWTEST_SCREENSHOTS ? "only-on-failure" : "off",
    // The copy-path affordance writes to the clipboard; the happy-path
    // reads it back to assert. Grant clipboard access for the test context.
    permissions: ["clipboard-read", "clipboard-write"],
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: [
    {
      command: "npx tsx e2e/run-server.ts",
      cwd: cockpitRoot,
      url: `http://${COCKPIT_HOST}:${serverPort}/api/changes`,
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
      stdout: "pipe",
      stderr: "pipe",
    },
    {
      // The client's index.html + vite config live under client/; point
      // vite's root there (positional arg) with the client config.
      command: "npx vite client --config client/vite.config.ts",
      cwd: cockpitRoot,
      url: clientOrigin,
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
      stdout: "pipe",
      stderr: "pipe",
    },
  ],
});
