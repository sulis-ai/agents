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
 * Parse a positive-integer env override, falling back to `fallback` when the
 * value is absent, empty, non-numeric, or non-positive. Keeps a typo in an
 * override from silently zeroing a timeout (which would defeat the watchdog).
 */
function parsePositiveIntEnv(
  raw: string | undefined,
  fallback: number,
): number {
  if (raw === undefined || raw.trim().length === 0) return fallback;
  const parsed = Number(raw);
  if (!Number.isFinite(parsed) || !Number.isInteger(parsed) || parsed <= 0) {
    return fallback;
  }
  return parsed;
}

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
  /**
   * Per-call budget for the change-LISTING path
   * (`sulis-list-changes list` via SulisChangeStoreReader). Its OWN
   * config — NEVER reuse `gitTimeoutMs`: enumerating MANY changes (40+ in
   * a busy repo) legitimately takes longer than a single git op, so a 5 s
   * budget false-fails the dashboard's first load (the founder sees
   * "Something went wrong loading your changes" even though a retry
   * succeeds). 30 s matches the I/O-heavy precedent already set by the
   * recreate / starter adapters. Overridable via CHANGE_LIST_TIMEOUT_MS.
   * The single-git-op paths (diff, origin attribution) keep `gitTimeoutMs`
   * — only the listing gets the generous budget.
   */
  changeListTimeoutMs: parsePositiveIntEnv(
    process.env.CHANGE_LIST_TIMEOUT_MS,
    30_000,
  ),
  /**
   * WP-005 — startup budget for the chat bridge child (the headless
   * `claude` session), from spawn to its FIRST stream-json output. A cold
   * headless `claude -p --output-format stream-json --include-partial-messages`
   * legitimately takes ~5–9 s to first output (measured live: ~3.5 s
   * time-to-first-token + model wake). That far exceeds a git operation's
   * budget, so this is its OWN config — NEVER reuse `gitTimeoutMs`, whose 5 s
   * would kill the agent right as it wakes ⇒ false `unreachable` on every
   * live chat. Overridable via CHAT_BRIDGE_STARTUP_TIMEOUT_MS. Default 60 s
   * gives generous headroom; the idle/inter-output budget is separate.
   */
  chatBridgeStartupTimeoutMs: parsePositiveIntEnv(
    process.env.CHAT_BRIDGE_STARTUP_TIMEOUT_MS,
    60_000,
  ),
  /**
   * WP-004 / TDD §3.4 — terminal sidecar resource ceilings. Conservative,
   * localhost-tuned defaults for a single-founder local app: refuse new WS
   * upgrades past `terminalMaxConnections`, and refuse an `attach` past
   * `terminalMaxAttachmentsPerConnection` open attachments on one WS. Frozen
   * constants (not env-driven beyond the existing override convention) — the
   * composition seam passes them straight into `createTerminalSidecar`.
   */
  terminalMaxConnections: 8,
  terminalMaxAttachmentsPerConnection: 4,
} as const);

export type ServerConfig = typeof CONFIG;
