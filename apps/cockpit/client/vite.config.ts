// WP-001 — Vite config for the cockpit client.
//
// - Binds to 127.0.0.1 (loopback only — ADR-002).
// - Proxies /api/* → the Express server on its loopback port (TDD §11).
// - Pulls both ports from the shared dev-ports module so server and
//   client cannot drift out of sync.

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import {
  COCKPIT_HOST,
  getClientPort,
  getServerPort,
} from "../shared/dev-ports";

export default defineConfig(() => {
  const clientPort = getClientPort();
  const serverPort = getServerPort();
  return {
    plugins: [react()],
    server: {
      host: COCKPIT_HOST,
      port: clientPort,
      strictPort: true,
      proxy: {
        "/api": {
          target: `http://${COCKPIT_HOST}:${serverPort}`,
          changeOrigin: false,
          secure: false,
        },
      },
    },
    test: {
      environment: "jsdom",
      globals: true,
      include: ["src/**/*.test.{ts,tsx}"],
      setupFiles: ["./src/tests/setup.ts"],
    },
  };
});
