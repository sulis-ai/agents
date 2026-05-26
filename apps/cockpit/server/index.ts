// WP-001 — placeholder server bootstrap.
//
// This module's only job today is to log a banner so the dev runner
// (concurrently → `tsx watch server/index.ts`) has a visible
// heartbeat. WP-010 will replace this body with the real Express HTTP
// surface (six routes, loopback bind on 127.0.0.1, per TDD §5 + §13.1).
//
// No port is bound here. Binding lives in WP-010 alongside the route
// table; binding here without routes would be a half-built state.

import { COCKPIT_HOST, getServerPort } from "../shared/dev-ports";

const banner = `cockpit server up — placeholder (no routes bound yet); intended host ${COCKPIT_HOST}:${getServerPort()}`;

// eslint-disable-next-line no-console -- intentional: dev-runner heartbeat
console.log(banner);

export { banner };
