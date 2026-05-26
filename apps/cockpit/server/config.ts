// WP-010 — Server config (TDD §13.1, ADR-002).
//
// The cockpit binds to 127.0.0.1 — exclusively. The `bindAddress` field
// below is the single source of truth; the bind-address.test.ts gate
// scans every active server file for the forbidden literal "0.0.0.0"
// to keep the invariant from drifting in future WPs.
//
// `Object.freeze` is the runtime-side belt-and-braces: even if a
// future contributor accidentally writes `CONFIG.bindAddress = "..."`,
// strict mode (which this module uses via "type": "module") throws.

import os from "node:os";

import { COCKPIT_HOST, getServerPort } from "../shared/dev-ports";

/**
 * Server config — frozen. The bind address is hard-coded. The port,
 * client origin, sulis state dir, claude projects dir, file-size cap,
 * and git-subprocess timeout are read from env at module-load time
 * with sensible defaults.
 */
export const CONFIG = Object.freeze({
  /** The loopback address — never configurable. (TDD §13.1) */
  bindAddress: COCKPIT_HOST,
  /** The HTTP server port. Overridable via COCKPIT_SERVER_PORT. */
  serverPort: getServerPort(),
  /** CORS origin allowed in dev mode. */
  clientOrigin: process.env.COCKPIT_CLIENT_ORIGIN ?? "http://127.0.0.1:5173",
  /** ~/.sulis (or test override via SULIS_STATE_DIR). */
  sulisStateDir: process.env.SULIS_STATE_DIR ?? `${os.homedir()}/.sulis`,
  /** ~/.claude/projects (or test override via CLAUDE_PROJECTS_DIR). */
  claudeProjectsDir:
    process.env.CLAUDE_PROJECTS_DIR ?? `${os.homedir()}/.claude/projects`,
  /** 1 MiB — the WP-007 cap, reused. (TDD §5.2, §13.6) */
  fileMaxBytes: 1024 * 1024,
  /** 5 s — the WP-008 git timeout. (TDD §13.6) */
  gitTimeoutMs: 5_000,
} as const);

export type ServerConfig = typeof CONFIG;
