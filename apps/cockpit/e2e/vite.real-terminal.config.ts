// WP-007 — Vite config for the REAL-server live-terminal e2e client.
//
// Distinct from client/vite.config.ts because the real-server e2e needs the
// client to reach the cockpit's OWN /terminal WS endpoint via the WP-006
// SAME-ORIGIN default — with NO VITE_TERMINAL_WS_URL set. The same-origin default
// resolves to `ws://<client-host>/terminal`; for that to reach the real Express
// sidecar (on the server port) the vite dev server must proxy the /terminal WS
// upgrade to the server (the base client config proxies only /api). Adding
// `ws: true` on the /terminal proxy entry is the one difference — it makes the
// production resolution path (same-origin → server's own sidecar) genuinely
// exercised end-to-end, rather than short-circuited by an explicit env URL.
//
// Ports come from the e2e env (COCKPIT_CLIENT_PORT / COCKPIT_SERVER_PORT) the
// real-server config passes; loopback-only (ADR-002). NO test block here — this
// config is for the e2e dev server only; unit tests use client/vite.config.ts.

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

import { COCKPIT_HOST, getClientPort, getServerPort } from "../shared/dev-ports";
import { TERMINAL_WS_PATH } from "../shared/terminalWsPath";

export default defineConfig(() => {
  const clientPort = getClientPort();
  const serverPort = getServerPort();
  const serverTarget = `http://${COCKPIT_HOST}:${serverPort}`;
  return {
    // The client source root is apps/cockpit/client (this config lives in e2e/).
    root: "client",
    plugins: [react()],
    server: {
      host: COCKPIT_HOST,
      port: clientPort,
      strictPort: true,
      proxy: {
        // The GET API surface (unchanged from the base client config).
        "/api": {
          target: serverTarget,
          changeOrigin: false,
          secure: false,
        },
        // WP-007 — proxy the terminal WS upgrade to the real server's sidecar so
        // the WP-006 same-origin default (ws://<client-host>/terminal) reaches
        // the cockpit's OWN /terminal endpoint. `ws: true` upgrades the proxy.
        [TERMINAL_WS_PATH]: {
          target: serverTarget,
          ws: true,
          changeOrigin: false,
          secure: false,
        },
      },
    },
  };
});
