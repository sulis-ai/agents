// WP-001 — Vitest config for the cockpit workspace.
//
// One config, two test environments:
//   - server/tests/**          → node
//   - client/src/**/tests/**   → jsdom (+ jest-dom matchers via setup)
// We use Vitest's projects feature so a single `npx vitest run` covers
// both surfaces with the right env per file.

import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  test: {
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
