// WP-004 — computeStatus: the FR-05 read-time status derivation (pure).
//
// Derives the plain-English "what's happening" headline at READ time from
// the change record + parsed transcript + liveness — NEVER from a stored
// periodic post (FR-05). The status route calls this on every GET; nothing
// is persisted.
//
// The headline is grounded in three facts: (a) the lifecycle stage,
// (b) the session liveness, (c) the attention signals. It deliberately
// does NOT echo the agent's reply text — that would leak the message body
// the observability discipline (NFR-SEC-03) keeps out of every surface.
// Instead it describes the SHAPE of what's happening in the founder's
// words.
//
// Attention is delegated to `needsAttention` (FR-12), the single source of
// truth shared with journey D (search). computeStatus gathers the signals
// from the transcript and passes them in.

// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits; the rule's `../../*` pattern is intended to block escapes out of apps/cockpit/, which `import/no-restricted-paths` already enforces correctly)
import type {
  ChangeStatus,
  Liveness,
  TranscriptMessage,
  WorkflowStage,
} from "../../shared/api-types";
import type { ChangeStoreRecord } from "../ports/ChangeStoreReader";
import {
  needsAttention,
  type AttentionSignals,
  type AttentionVerdict,
} from "./needsAttention";

export interface ComputeStatusInput {
  record: ChangeStoreRecord;
  /** Parsed transcript messages, chronological ascending (parseTranscripts). */
  transcript: TranscriptMessage[];
  liveness: Liveness;
  /** Whether an open BLOCKER parks the change (read by the route). */
  hasOpenBlocker: boolean;
}

/** Human stage names — the founder reads "Design", not "design". */
const STAGE_NAME: Record<WorkflowStage, string> = {
  recon: "Reconnaissance",
  specify: "Specifying the requirements",
  design: "Designing the technical approach",
  implement: "Building the change",
  review: "Reviewing the work",
  ship: "Shipping",
  shipped: "Shipped",
};

/**
 * Derive a change's read-time status. Pure: no I/O. The headline names
 * the stage and the liveness in plain English and never includes the
 * verbatim reply body.
 */
export function computeStatus(input: ComputeStatusInput): ChangeStatus {
  const { record, transcript, liveness, hasOpenBlocker } = input;

  const signals = deriveSignals(
    record.stage,
    transcript,
    liveness,
    hasOpenBlocker,
  );
  const attention = needsAttention(signals);
  const headline = buildHeadline(record.stage, liveness, attention);

  return {
    changeId: record.changeId,
    stage: record.stage,
    headline,
    needsAttention: attention,
  };
}

/** Gather the attention signals from the read-time inputs. */
function deriveSignals(
  stage: WorkflowStage,
  transcript: TranscriptMessage[],
  liveness: Liveness,
  hasOpenBlocker: boolean,
): AttentionSignals {
  const last = transcript.length > 0 ? transcript[transcript.length - 1] : null;
  const lastMessageKind = last ? last.kind : null;
  const lastAssistantEndedCleanly =
    last && last.kind === "assistant" ? assistantEndedCleanly(last) : true;
  const awaitingDecision =
    last && last.kind === "assistant" ? posesQuestion(last) : false;

  return {
    stage,
    liveness: liveness.status,
    lastMessageKind,
    lastAssistantEndedCleanly,
    hasOpenBlocker,
    awaitingDecision,
  };
}

/**
 * A clean assistant turn ends with a text block — the agent said its
 * piece. A turn whose last block is a tool-use (an action with no closing
 * narration) reads as interrupted.
 */
function assistantEndedCleanly(msg: TranscriptMessage): boolean {
  if (msg.kind !== "assistant") return true;
  const blocks = msg.blocks;
  if (blocks.length === 0) return false;
  const lastBlock = blocks[blocks.length - 1];
  return lastBlock?.kind === "text" && lastBlock.text.trim().length > 0;
}

/**
 * Does the last assistant turn pose an unanswered question? A trailing
 * text block ending in "?" is the read-time signal that the agent asked
 * and stopped. We inspect only the SHAPE (presence of a question mark) —
 * the headline never echoes the question text (NFR-SEC-03).
 */
function posesQuestion(msg: TranscriptMessage): boolean {
  if (msg.kind !== "assistant") return false;
  const textBlocks = msg.blocks.filter(
    (b): b is { kind: "text"; text: string } => b.kind === "text",
  );
  if (textBlocks.length === 0) return false;
  const lastText = textBlocks[textBlocks.length - 1]?.text.trim() ?? "";
  return lastText.endsWith("?");
}

/**
 * Build the plain-English headline. Grounded in stage + liveness +
 * attention; never the reply body. Attention reasons take priority so the
 * founder reads the urgent thing first.
 */
function buildHeadline(
  stage: WorkflowStage,
  liveness: Liveness,
  attention: AttentionVerdict,
): string {
  const stageName = STAGE_NAME[stage] ?? stage;

  if (attention.flagged) {
    switch (attention.reason) {
      case "blocked":
        return `${stageName} — blocked, waiting on you to clear it.`;
      case "waiting-on-decision":
        return `${stageName} — waiting on you for a decision.`;
      case "stopped-mid-reply":
        return `${stageName} — stopped mid-reply; pick it back up when you're ready.`;
    }
  }

  if (liveness.status === "running") {
    return `${stageName} — working now.`;
  }

  // Not running and nothing wrong → idle but fine (FR-12: not flagged).
  return `${stageName} — paused and idle; not running right now.`;
}
