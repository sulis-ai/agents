// WP-005 — session-to-change binding guard (ADR-004; FR-21, FR-N2, NFR-SEC-02/06).
//
// The single most dangerous failure for a multi-change cockpit is delivering
// the founder's message to the WRONG change's agent. This guard is a pure
// function over (requested change, resolved session) that FAILS CLOSED: it
// permits delivery only if it can POSITIVELY prove the session belongs to the
// named change — by carried identity, not by position or convenience:
//
//   1. the session's `change_id` MUST equal the requested change id, and
//   2. the session's `cwd` MUST equal the change's `worktreePath`
//      (the same cwd-equality failsafe `locateTranscripts` uses, MVP ADR-004).
//
// The verdict is identical for live / resumed / spawned sessions (NFR-SEC-02):
// the resolution kind is NOT an input — only identity is. The relay runs this
// BEFORE any process start or prompt delivery, so resume/spawn can only ever
// act on the targeted change's session (NFR-SEC-06). On failure the relay
// returns SESSION_CHANGE_MISMATCH with zero bytes and no process touched.
//
// Pure: no I/O, no clock, no randomness. Unit-testable without a live agent.

import type { SessionRef } from "../ports/SessionBridge";

/** What the guard checks against — the requested change's identity. */
export interface BindingRequest {
  changeId: string;
  worktreePath: string;
}

/**
 * The guard's verdict. `bound: true` is the ONLY path that permits delivery;
 * every other input shape yields `bound: false` with a plain reason (used in
 * the structured log + the typed error, never shown raw to the founder).
 */
export type BindingVerdict = { bound: true } | { bound: false; reason: string };

/**
 * Positively prove the resolved `session` belongs to the named change.
 * Fails closed on any missing/mismatched identity field.
 */
export function checkSessionBinding(
  request: BindingRequest,
  session: SessionRef,
): BindingVerdict {
  // Fail closed on empty/missing identity — an unidentified session can never
  // be positively bound.
  if (!request.changeId || !request.worktreePath) {
    return { bound: false, reason: "requested change is missing identity" };
  }
  if (!session.changeId || !session.cwd) {
    return { bound: false, reason: "resolved session is missing identity" };
  }
  if (session.changeId !== request.changeId) {
    return {
      bound: false,
      reason: "session change_id does not match the requested change",
    };
  }
  if (session.cwd !== request.worktreePath) {
    return {
      bound: false,
      reason: "session cwd does not match the change's worktree",
    };
  }
  return { bound: true };
}
