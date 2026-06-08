// WP-004 — needsAttention.ts unit tests (FR-12).
//
// `needsAttention` is the single source of truth for FR-12 (journey D /
// search, WP-006, reuses it — do not re-implement). It is a pure
// predicate over a change's record + read-time signals (the last
// transcript message + liveness) and returns `{ flagged, reason }`.
//
// The three flagged reasons:
//   - blocked              → the change is parked on a BLOCKER
//   - waiting-on-decision  → the agent asked a question and stopped
//   - stopped-mid-reply    → the session died part-way through a reply
//
// idle-but-fine (no recent activity, but nothing wrong) is explicitly
// NOT flagged (the founder's confirmed default; TDD §11).

import { describe, it, expect } from "vitest";
import { needsAttention } from "../lib/needsAttention";
import type { AttentionSignals } from "../lib/needsAttention";

function signals(overrides: Partial<AttentionSignals> = {}): AttentionSignals {
  return {
    stage: "implement",
    liveness: "not-running",
    lastMessageKind: "assistant",
    lastAssistantEndedCleanly: true,
    hasOpenBlocker: false,
    awaitingDecision: false,
    ...overrides,
  };
}

describe("needsAttention (FR-12)", () => {
  it("flags 'blocked' when the change is parked on an open BLOCKER", () => {
    const result = needsAttention(signals({ hasOpenBlocker: true }));
    expect(result.flagged).toBe(true);
    expect(result.reason).toBe("blocked");
  });

  it("flags 'waiting-on-decision' when the agent asked and stopped", () => {
    const result = needsAttention(signals({ awaitingDecision: true }));
    expect(result.flagged).toBe(true);
    expect(result.reason).toBe("waiting-on-decision");
  });

  it("flags 'stopped-mid-reply' when the last assistant turn did not end cleanly and the session is dead", () => {
    const result = needsAttention(
      signals({
        liveness: "not-running",
        lastMessageKind: "assistant",
        lastAssistantEndedCleanly: false,
      }),
    );
    expect(result.flagged).toBe(true);
    expect(result.reason).toBe("stopped-mid-reply");
  });

  it("does NOT flag stopped-mid-reply while the session is still running (it's mid-reply, not stopped)", () => {
    const result = needsAttention(
      signals({
        liveness: "running",
        lastMessageKind: "assistant",
        lastAssistantEndedCleanly: false,
      }),
    );
    expect(result.flagged).toBe(false);
    expect(result.reason).toBeNull();
  });

  it("does NOT flag an idle-but-fine change (no recent activity, nothing wrong)", () => {
    const result = needsAttention(
      signals({
        liveness: "not-running",
        lastMessageKind: "assistant",
        lastAssistantEndedCleanly: true,
        hasOpenBlocker: false,
        awaitingDecision: false,
      }),
    );
    expect(result.flagged).toBe(false);
    expect(result.reason).toBeNull();
  });

  it("does NOT flag a change with no conversation yet (fresh change, nothing to attend to)", () => {
    const result = needsAttention(
      signals({ lastMessageKind: null, lastAssistantEndedCleanly: true }),
    );
    expect(result.flagged).toBe(false);
    expect(result.reason).toBeNull();
  });

  it("prioritises 'blocked' over 'waiting-on-decision' when both are present (most-urgent-first)", () => {
    const result = needsAttention(
      signals({ hasOpenBlocker: true, awaitingDecision: true }),
    );
    expect(result.flagged).toBe(true);
    expect(result.reason).toBe("blocked");
  });
});
