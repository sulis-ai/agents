// WP-001 — Vitest config for the cockpit workspace.
//
// One config, two test environments:
//   - server/tests/**          → node
//   - client/src/**/tests/**   → jsdom (+ jest-dom matchers via setup)
// We use Vitest's projects feature so a single `npx vitest run` covers
// both surfaces with the right env per file.
//
// WP-016 — combined-run stability:
//   The combined `npx vitest run` runs the node-env server project and the
//   jsdom/Monaco client project together. We pin the `forks` pool so each
//   test file runs in its own child process — the boring, well-supported
//   isolation primitive — so the two environments cannot interfere under
//   parallel load. The root cause of the prior "socket hang up" flake (a
//   real socket bind in app.integration.test.ts) was also removed in favour
//   of in-process supertest; this pool setting is defence-in-depth.

import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  test: {
    // Process-level isolation between the two environments.
    pool: "forks",
    projects: [
      {
        plugins: [],
        test: {
          name: "server",
          environment: "node",
          include: ["server/tests/**/*.test.ts"],
        },
      },
      {
        plugins: [react()],
        test: {
          name: "client",
          environment: "jsdom",
          include: ["client/src/**/*.test.{ts,tsx}"],
          setupFiles: ["./client/src/tests/setup.ts"],
          globals: true,
        },
      },
    ],
  },
});
