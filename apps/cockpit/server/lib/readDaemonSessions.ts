// Liveness from the session-manager DAEMON — the authoritative source.
//
// The cockpit's signal-0 `probeLiveness` reads session.json + a pid existence
// check. That can't see a macOS session: the launcher exits, so the session
// records a tty with a NULL pid, and a pid-only probe has nothing to check →
// "unknown" even when the session is genuinely live. The session-manager daemon
// OWNS the per-change pty session and tracks each one's state, exposing them
// over its socket `status` op (one round-trip → every live session, keyed by
// change_id). This reads that list so the feed can derive liveness from the
// truth, falling back to the signal-0 probe only when the daemon is unreachable.
//
// Read-only: one `status` round-trip, no writes, no process control, no signals.

import { connect } from "node:net";
import { existsSync } from "node:fs";

// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits; the rule blocks escapes OUT of apps/cockpit/, which import/no-restricted-paths enforces)
import type { Liveness } from "../../shared/api-types";
// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/
import { createNdjsonLineFramer } from "../../shared/ndjsonLineFramer";

export interface DaemonSession {
  /** The daemon session key = the change_id (ULID). */
  key: string;
  /** The daemon's session-state-machine state (e.g. "ready"). */
  state: string;
  /** The pty process pid the daemon owns for this session (may be null). */
  pid: number | null;
}

interface StatusReply {
  ok?: boolean;
  result?: Array<{ key?: unknown; state?: unknown; pid?: unknown }>;
}

/**
 * Read the daemon's live sessions via ONE `status` round-trip. Returns a map
 * keyed by change_id, or `null` when the daemon is unreachable (no socket,
 * refused connect, timeout, malformed reply). `null` ("no authority — fall back
 * to the signal-0 probe") is deliberately distinct from an empty map ("daemon
 * up, zero live sessions"). Never throws — every transport failure → `null`.
 */
export function readDaemonLiveSessions(
  socketPath: string,
  timeoutMs = 1000,
): Promise<Map<string, DaemonSession> | null> {
  return new Promise((resolve) => {
    if (!existsSync(socketPath)) {
      resolve(null);
      return;
    }
    const framer = createNdjsonLineFramer();
    let settled = false;
    const sock = connect(socketPath);

    const done = (value: Map<string, DaemonSession> | null): void => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      sock.destroy();
      resolve(value);
    };

    const timer = setTimeout(() => done(null), timeoutMs);
    sock.setTimeout(timeoutMs, () => done(null));

    sock.on("connect", () => {
      sock.write(
        JSON.stringify({ id: "live", method: "status", params: {} }) + "\n",
      );
    });
    sock.on("data", (chunk: Buffer) => {
      for (const line of framer.push(chunk)) {
        try {
          const reply = JSON.parse(line) as StatusReply;
          if (reply.ok !== true || !Array.isArray(reply.result)) {
            done(null);
            return;
          }
          const map = new Map<string, DaemonSession>();
          for (const row of reply.result) {
            const key = typeof row.key === "string" ? row.key : null;
            if (key === null) continue;
            map.set(key, {
              key,
              state: typeof row.state === "string" ? row.state : "unknown",
              pid: typeof row.pid === "number" ? row.pid : null,
            });
          }
          done(map);
        } catch {
          done(null);
        }
        return; // only the first framed line matters
      }
    });
    sock.on("error", () => done(null));
  });
}

/**
 * Resolve a change's liveness using the daemon as the authority.
 *
 *  - daemon UNREACHABLE (`sessions === null`) → fall back to the caller's
 *    signal-0 probe result (the only honest read we have without the daemon).
 *  - daemon REACHABLE → it owns the truth: a change the daemon is managing reads
 *    `running` (the card then splits working vs live on recency); a change it is
 *    NOT managing reads `not-running` (idle) — no "unknown" guesswork, because
 *    the daemon definitively has no session for it.
 */
export function livenessFromDaemon(
  changeId: string,
  sessions: Map<string, DaemonSession> | null,
  fallback: Liveness,
): Liveness {
  if (sessions === null) return fallback;
  const session = sessions.get(changeId);
  if (session) {
    // The daemon owns a live pty for this change → running. Its pty pid is the
    // honest pid; 0 is only a sentinel for the rare managed-without-pid case
    // (the card derives working/live from lastActivityAt, not this pid).
    return { status: "running", pid: session.pid ?? 0 };
  }
  return { status: "not-running" };
}
