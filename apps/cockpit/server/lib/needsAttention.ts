// WP-004 — needsAttention: the FR-12 attention predicate (pure).
//
// The single source of truth for "does this change need the founder's
// attention right now?" — journey D (search, WP-006) reuses it; do not
// re-implement it there.
//
// It is a PURE function of read-time signals (the change's stage, the
// session liveness, the shape of the last conversation turn, and whether
// an open BLOCKER exists). It performs no I/O — the caller (computeStatus
// / the status route) gathers the signals and passes them in.
//
// The three flagged reasons, most-urgent-first:
//   1. blocked              — an open BLOCKER parks the change.
//   2. waiting-on-decision  — the agent asked a question and stopped.
//   3. stopped-mid-reply    — the session died part-way through a reply.
//
// idle-but-fine (the session is simply not running, with a cleanly-ended
// last turn and nothing wrong) is explicitly NOT flagged — the founder's
// confirmed default (TDD §11; SRD FR-12).

// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits; the rule's `../../*` pattern is intended to block escapes out of apps/cockpit/, which `import/no-restricted-paths` already enforces correctly)
import type { ChangeStatus, WorkflowStage } from "../../shared/api-types";

/** The reason union (mirrors ChangeStatus.needsAttention.reason). */
export type AttentionReason = ChangeStatus["needsAttention"]["reason"];

/** The read-time signals the predicate decides on. */
export interface AttentionSignals {
  /** The change's lifecycle stage (carried through for future rules). */
  stage: WorkflowStage;
  /** Whether the change's session is currently alive. */
  liveness: "running" | "not-running" | "unknown";
  /** The kind of the most-recent transcript message, or null if none. */
  lastMessageKind: "user" | "assistant" | "system" | null;
  /**
   * Whether the last assistant turn ended cleanly (a closing text block).
   * False when the turn trails off in a tool-use with no closing text —
   * the shape of an interrupted reply.
   */
  lastAssistantEndedCleanly: boolean;
  /** Whether an open BLOCKER parks the change. */
  hasOpenBlocker: boolean;
  /** Whether the last assistant turn poses an unanswered question. */
  awaitingDecision: boolean;
}

/** The predicate result (the ChangeStatus.needsAttention shape). */
export interface AttentionVerdict {
  flagged: boolean;
  reason: AttentionReason;
}

const NOT_FLAGGED: AttentionVerdict = { flagged: false, reason: null };

/**
 * Decide whether a change needs attention, and why. Pure; most-urgent
 * reason wins (blocked > waiting-on-decision > stopped-mid-reply).
 */
export function needsAttention(signals: AttentionSignals): AttentionVerdict {
  // 1. An open BLOCKER is the most urgent — the change cannot proceed.
  if (signals.hasOpenBlocker) {
    return { flagged: true, reason: "blocked" };
  }

  // 2. The agent asked and stopped — the founder owes a decision.
  if (signals.awaitingDecision) {
    return { flagged: true, reason: "waiting-on-decision" };
  }

  // 3. The session died mid-reply — only "stopped" once it is no longer
  //    running. A still-running session with an unfinished turn is simply
  //    mid-reply, not stopped (so it is not flagged).
  if (
    signals.liveness === "not-running" &&
    signals.lastMessageKind === "assistant" &&
    !signals.lastAssistantEndedCleanly
  ) {
    return { flagged: true, reason: "stopped-mid-reply" };
  }

  // Everything else — including idle-but-fine and a fresh change with no
  // conversation — is not flagged (FR-12).
  return NOT_FLAGGED;
}
