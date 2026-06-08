// WP-004 — computeStatus.ts unit tests (FR-05).
//
// `computeStatus` derives the plain-English "what's happening" headline
// at READ time from the change record + parsed transcript + liveness —
// NEVER from a stored periodic post (FR-05; the route never persists a
// status, it computes one on each GET). It composes `needsAttention`
// (FR-12) for the attention flag.
//
// The headline is a single human-readable sentence the founder reads to
// know where the change is and whether anything is waiting on them. It
// is grounded in (a) the lifecycle stage, (b) the session liveness, and
// (c) the attention signals — not in agent reply text (which would leak
// the message body the read-only/observability discipline keeps out).

import { describe, it, expect } from "vitest";
import { computeStatus } from "../lib/computeStatus";
import type { ComputeStatusInput } from "../lib/computeStatus";
import type { ChangeStoreRecord } from "../ports/ChangeStoreReader";
import type { TranscriptMessage, Liveness } from "../../shared/api-types";

function record(overrides: Partial<ChangeStoreRecord> = {}): ChangeStoreRecord {
  return {
    changeId: "01ABC",
    handle: "CH-01ABC",
    slug: "demo",
    primitive: "create",
    branch: "change/demo",
    worktreePath: "/tmp/wt",
    intent: "demo change",
    baseBranch: "main",
    baseSha: "deadbeef",
    createdAt: "2026-05-01T00:00:00Z",
    updatedAt: "2026-05-02T00:00:00Z",
    stage: "design",
    ...overrides,
  };
}

function assistantMsg(text: string, uuid = "a1"): TranscriptMessage {
  return {
    kind: "assistant",
    uuid,
    timestamp: "2026-05-02T00:00:00Z",
    blocks: [{ kind: "text", text }],
  };
}

function input(
  overrides: Partial<ComputeStatusInput> = {},
): ComputeStatusInput {
  return {
    record: record(),
    transcript: [],
    liveness: { status: "not-running" } as Liveness,
    hasOpenBlocker: false,
    ...overrides,
  };
}

describe("computeStatus (FR-05) — read-time headline", () => {
  it("returns the changeId and stage from the record", () => {
    const status = computeStatus(
      input({ record: record({ changeId: "01XYZ", stage: "design" }) }),
    );
    expect(status.changeId).toBe("01XYZ");
    expect(status.stage).toBe("design");
  });

  it("describes a design-in-progress change in plain English naming the stage", () => {
    const status = computeStatus(
      input({
        record: record({ stage: "design" }),
        liveness: { status: "running", pid: 4242 },
        transcript: [assistantMsg("Drafting the technical design.")],
      }),
    );
    expect(status.headline.length).toBeGreaterThan(0);
    expect(status.headline.toLowerCase()).toContain("design");
    // A running session reads as actively working.
    expect(status.headline.toLowerCase()).toMatch(/working|running|progress/);
    expect(status.needsAttention.flagged).toBe(false);
  });

  it("flags blocked and says so in the headline", () => {
    const status = computeStatus(
      input({
        record: record({ stage: "implement" }),
        hasOpenBlocker: true,
        liveness: { status: "not-running" },
      }),
    );
    expect(status.needsAttention.flagged).toBe(true);
    expect(status.needsAttention.reason).toBe("blocked");
    expect(status.headline.toLowerCase()).toContain("block");
  });

  it("flags waiting-on-decision when the last assistant turn poses a question and the session has stopped", () => {
    const status = computeStatus(
      input({
        record: record({ stage: "specify" }),
        liveness: { status: "not-running" },
        transcript: [
          assistantMsg("Which database should we use — Postgres or MySQL?"),
        ],
      }),
    );
    expect(status.needsAttention.flagged).toBe(true);
    expect(status.needsAttention.reason).toBe("waiting-on-decision");
    expect(status.headline.toLowerCase()).toMatch(
      /waiting|decision|answer|you/,
    );
  });

  it("flags stopped-mid-reply when the session died with an unfinished assistant turn", () => {
    const status = computeStatus(
      input({
        record: record({ stage: "implement" }),
        liveness: { status: "not-running" },
        // A trailing assistant block with only a tool-use and no closing
        // text reads as an interrupted reply.
        transcript: [
          {
            kind: "assistant",
            uuid: "a2",
            timestamp: "2026-05-02T00:00:00Z",
            blocks: [{ kind: "tool-use", toolName: "Edit", input: {} }],
          },
        ],
      }),
    );
    expect(status.needsAttention.flagged).toBe(true);
    expect(status.needsAttention.reason).toBe("stopped-mid-reply");
    expect(status.headline.toLowerCase()).toMatch(/stopped|interrupted|mid/);
  });

  it("does NOT flag an idle-but-fine change and reads calmly (FR-12)", () => {
    const status = computeStatus(
      input({
        record: record({ stage: "design" }),
        liveness: { status: "not-running" },
        transcript: [assistantMsg("Design draft saved. Done for now.")],
        hasOpenBlocker: false,
      }),
    );
    expect(status.needsAttention.flagged).toBe(false);
    expect(status.needsAttention.reason).toBeNull();
    // Idle is described, not alarmed.
    expect(status.headline.toLowerCase()).toMatch(
      /idle|paused|not running|waiting to resume|design/,
    );
  });

  it("handles an empty transcript (fresh change) without flagging", () => {
    const status = computeStatus(
      input({ record: record({ stage: "recon" }), transcript: [] }),
    );
    expect(status.needsAttention.flagged).toBe(false);
    expect(status.headline.length).toBeGreaterThan(0);
  });

  it("never includes the verbatim assistant reply body in the headline (observability discipline, NFR-SEC-03)", () => {
    const secret = "SECRET-PAYLOAD-DO-NOT-LEAK-12345";
    const status = computeStatus(
      input({
        record: record({ stage: "implement" }),
        liveness: { status: "running", pid: 1 },
        transcript: [assistantMsg(secret)],
      }),
    );
    expect(status.headline).not.toContain(secret);
  });
});
