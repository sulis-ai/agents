// WP-005 — production session resolver (ADR-002, FR-N4).
//
// Composes the EXISTING reads — signal-0 liveness (probeLiveness) + the
// transcript locator (locateTranscripts) — into the side-effect-free
// `resolveSession` decision the SessionBridge port needs (FR-N4): which path
// applies (live | resumable | fresh) WITHOUT acting. Starts no process, sends
// no signal other than the signal-0 probe, writes nothing.
//
//   - live      — the change's recorded session pid is alive (signal 0).
//   - resumable — not live, but a prior transcript exists → resume from it.
//   - fresh     — no live session and no transcript → spawn grounded.
//
// The resolved session carries the binding IDENTITY (change_id + cwd) the
// guard checks: cwd is the change's worktreePath, change_id is the requested
// change id. The session.json on disk also carries change_id; we read it so
// the binding guard can catch a cwd/change_id skew (ADR-004).

import { promises as fs } from "node:fs";
import path from "node:path";

import type { SessionResolution } from "../ports/SessionBridge";
import { probeLiveness } from "./probeLiveness";
import { locateTranscripts } from "./locateTranscripts";

export interface ResolveSessionDeps {
  sulisStateDir: string;
  claudeProjectsDir: string;
  /** The change's worktree path (the cwd the session must run in). */
  worktreePath: string;
}

/**
 * Read the change_id the session.json records (for the binding guard). Falls
 * back to the requested id when the record is absent/malformed — the guard
 * then relies on cwd-equality, and a spawned session is bound to the requested
 * change by construction.
 */
async function readSessionChangeId(
  sulisStateDir: string,
  requestedChangeId: string,
): Promise<string> {
  const sessionPath = path.join(
    sulisStateDir,
    "changes",
    requestedChangeId,
    "session.json",
  );
  try {
    const raw = await fs.readFile(sessionPath, "utf8");
    const parsed = JSON.parse(raw) as { change_id?: unknown };
    if (typeof parsed.change_id === "string" && parsed.change_id.length > 0) {
      return parsed.change_id;
    }
  } catch {
    // No record / malformed — fall back to the requested id.
  }
  return requestedChangeId;
}

/**
 * Resolve the delivery path for `changeId` WITHOUT acting (FR-N4). Pure reads:
 * liveness probe (signal 0) + transcript location. Returns the resolution plus
 * the session identity the binding guard checks.
 */
export async function resolveSessionFor(
  changeId: string,
  deps: ResolveSessionDeps,
): Promise<SessionResolution> {
  const [liveness, transcriptPaths, sessionChangeId] = await Promise.all([
    probeLiveness(deps.sulisStateDir, changeId),
    locateTranscripts(deps.worktreePath, deps.claudeProjectsDir),
    readSessionChangeId(deps.sulisStateDir, changeId),
  ]);

  const session = {
    changeId: sessionChangeId,
    cwd: deps.worktreePath,
    lastSessionRef: transcriptPaths[0],
  };

  if (liveness.status === "running") {
    return { kind: "live", session };
  }
  if (transcriptPaths.length > 0) {
    return { kind: "resumable", session };
  }
  return {
    kind: "fresh",
    session: { changeId: sessionChangeId, cwd: deps.worktreePath },
  };
}
