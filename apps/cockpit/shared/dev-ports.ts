// WP-001 (Blue refactor) — dev-port constants.
//
// Hoisted into a named module so the server, client, and Vite config can
// all import from one place rather than each duplicating the literal.
// Subsequent WPs (WP-010, WP-011, WP-016) consume these.
//
// Both ports are overridable via env (TDD §11):
//   COCKPIT_SERVER_PORT, COCKPIT_CLIENT_PORT.
// The bind address is hard-coded to 127.0.0.1 (TDD §13.1, ADR-002).

const DEFAULT_SERVER_PORT = 5174;
const DEFAULT_CLIENT_PORT = 5173;

// Dedicated e2e ports — DISTINCT from the dev ports above so the Playwright
// harness never reuses a developer's running cockpit (which would serve the
// real change store, not the seeded fixture, making count-based e2e tests
// non-deterministic — issue #377). Offset +100 from the dev defaults;
// overridable via COCKPIT_E2E_SERVER_PORT / COCKPIT_E2E_CLIENT_PORT.
const DEFAULT_E2E_SERVER_PORT = 5274;
const DEFAULT_E2E_CLIENT_PORT = 5273;

/** The loopback host the cockpit binds to (never overridable). */
export const COCKPIT_HOST = "127.0.0.1" as const;

/**
 * The Express server's port. Reads `COCKPIT_SERVER_PORT` from env,
 * falling back to {@link DEFAULT_SERVER_PORT}.
 */
export function getServerPort(env: NodeJS.ProcessEnv = process.env): number {
  return parsePort(env.COCKPIT_SERVER_PORT, DEFAULT_SERVER_PORT);
}

/**
 * The Vite dev server's port. Reads `COCKPIT_CLIENT_PORT` from env,
 * falling back to {@link DEFAULT_CLIENT_PORT}.
 */
export function getClientPort(env: NodeJS.ProcessEnv = process.env): number {
  return parsePort(env.COCKPIT_CLIENT_PORT, DEFAULT_CLIENT_PORT);
}

/**
 * The e2e Express server's port. Reads `COCKPIT_E2E_SERVER_PORT` from env,
 * falling back to {@link DEFAULT_E2E_SERVER_PORT}. Distinct from
 * {@link getServerPort} so the Playwright harness boots its own seeded-fixture
 * server instead of reusing a running dev cockpit (issue #377).
 */
export function getE2eServerPort(env: NodeJS.ProcessEnv = process.env): number {
  return parsePort(env.COCKPIT_E2E_SERVER_PORT, DEFAULT_E2E_SERVER_PORT);
}

/**
 * The e2e Vite client's port. Reads `COCKPIT_E2E_CLIENT_PORT` from env,
 * falling back to {@link DEFAULT_E2E_CLIENT_PORT}. Distinct from
 * {@link getClientPort} for the same reason as {@link getE2eServerPort}.
 */
export function getE2eClientPort(env: NodeJS.ProcessEnv = process.env): number {
  return parsePort(env.COCKPIT_E2E_CLIENT_PORT, DEFAULT_E2E_CLIENT_PORT);
}

/** Exposed for tests / explicit reads. */
export const DEFAULT_PORTS = Object.freeze({
  server: DEFAULT_SERVER_PORT,
  client: DEFAULT_CLIENT_PORT,
  e2eServer: DEFAULT_E2E_SERVER_PORT,
  e2eClient: DEFAULT_E2E_CLIENT_PORT,
});

function parsePort(raw: string | undefined, fallback: number): number {
  if (raw === undefined || raw === "") return fallback;
  const n = Number.parseInt(raw, 10);
  if (!Number.isFinite(n) || n <= 0 || n > 65535) return fallback;
  return n;
}
