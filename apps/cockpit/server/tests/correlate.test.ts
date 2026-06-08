// WP-P09 — unit tests for the pure origin correlation (ADR-012).
//
// correlate() is pure (no I/O): given a commit + the change's runs + turns it
// returns an Origin. We cover every branch the WP DoD names:
//   - commit inside a run window        → autonomous + confidence
//   - run id named in the commit message → autonomous (the strong signal)
//   - commit near a conversation turn    → assisted + turn ref + summary
//   - neither                            → unknown (plain reason)
//   - a recorded `Sulis-Origin:` trailer → recorded wins (overrides inference)
//   - the honesty flag is ALWAYS present and is "inferred" for every inference
//   - fail-soft on an unparseable commit timestamp → unknown

import { describe, it, expect } from "vitest";

import {
  correlate,
  type CorrelateInput,
} from "../lib/originAttribution/correlate";

const RUN: CorrelateInput["runs"][number] = {
  runId: "01RUNAUTONOMOUS0000000000A",
  at: "2026-06-02T12:00:00Z",
  outcome: "completed",
  workflow: "dna:workflow:WF1",
  confidence: 0.88,
};

const TURN: CorrelateInput["turns"][number] = {
  conversationId: "session-abc",
  turn: 3,
  at: "2026-06-03T09:00:00Z",
  summary: "Added the origin contract and the inference backend.",
};

describe("correlate (pure origin inference)", () => {
  it("classifies a commit inside a run window as autonomous + confidence", () => {
    const origin = correlate({
      commit: {
        author: "Sulis Bot <bot@sulis.ai>",
        at: "2026-06-02T12:05:00Z", // 5 min after the run
        message: "feat: do the autonomous thing",
      },
      runs: [RUN],
      turns: [],
    });
    expect(origin.kind).toBe("autonomous");
    if (origin.kind !== "autonomous") throw new Error("narrowing");
    expect(origin.run.runId).toBe(RUN.runId);
    expect(origin.run.workflow).toBe("dna:workflow:WF1");
    expect(origin.confidence).toBe(0.88);
    expect(origin.attribution).toBe("inferred");
  });

  it("classifies a commit whose message names a run id as autonomous", () => {
    const origin = correlate({
      commit: {
        author: "Some Human <h@example.com>",
        at: "2026-01-01T00:00:00Z", // far outside any window
        message: `chore: tidy up\n\nrun=${RUN.runId}`,
      },
      runs: [RUN],
      turns: [],
    });
    expect(origin.kind).toBe("autonomous");
    if (origin.kind !== "autonomous") throw new Error("narrowing");
    expect(origin.run.runId).toBe(RUN.runId);
    expect(origin.attribution).toBe("inferred");
  });

  it("classifies a commit near a conversation turn as assisted + summary", () => {
    const origin = correlate({
      commit: {
        author: "Iain <iain@nivbow.com>",
        at: "2026-06-03T09:05:00Z", // 5 min after the turn
        message: "feat: assisted change",
      },
      runs: [],
      turns: [TURN],
    });
    expect(origin.kind).toBe("assisted");
    if (origin.kind !== "assisted") throw new Error("narrowing");
    expect(origin.conversation.conversationId).toBe("session-abc");
    expect(origin.conversation.turn).toBe(3);
    expect(origin.conversation.summary).toContain("origin contract");
    expect(origin.attribution).toBe("inferred");
  });

  it("returns unknown with a plain reason when neither matches", () => {
    const origin = correlate({
      commit: {
        author: "Iain <iain@nivbow.com>",
        at: "2020-01-01T00:00:00Z",
        message: "ancient unrelated commit",
      },
      runs: [RUN],
      turns: [TURN],
    });
    expect(origin.kind).toBe("unknown");
    if (origin.kind !== "unknown") throw new Error("narrowing");
    expect(origin.reason.length).toBeGreaterThan(0);
    expect(origin.attribution).toBe("inferred");
  });

  it("returns unknown when the change has no runs and no turns", () => {
    const origin = correlate({
      commit: {
        author: "Iain <iain@nivbow.com>",
        at: "2026-06-03T09:05:00Z",
        message: "feat: something",
      },
      runs: [],
      turns: [],
    });
    expect(origin.kind).toBe("unknown");
    if (origin.kind !== "unknown") throw new Error("narrowing");
    expect(origin.reason).toMatch(/no autonomous runs or chat turns/);
    expect(origin.attribution).toBe("inferred");
  });

  it("defers to a recorded Sulis-Origin trailer (recorded overrides inferred)", () => {
    const origin = correlate({
      commit: {
        author: "Sulis Bot <bot@sulis.ai>",
        at: "2026-06-03T09:05:00Z", // would otherwise correlate to the turn
        message:
          "feat: stamped work\n\nSulis-Origin: autonomous; run=01STAMPEDRUN000000000000A; confidence=0.91\nCo-Authored-By: x <x@y.z>",
      },
      runs: [],
      turns: [TURN],
    });
    expect(origin.kind).toBe("autonomous");
    if (origin.kind !== "autonomous") throw new Error("narrowing");
    expect(origin.run.runId).toBe("01STAMPEDRUN000000000000A");
    expect(origin.confidence).toBe(0.91);
    // The honesty flag flips to "recorded" — the whole point of the trailer.
    expect(origin.attribution).toBe("recorded");
  });

  it("parses an assisted recorded trailer too", () => {
    const origin = correlate({
      commit: {
        author: "relay <relay@sulis.ai>",
        at: "2026-06-03T09:05:00Z",
        message:
          "feat: stamped assisted\n\nSulis-Origin: assisted; conversation=conv-9; turn=7",
      },
      runs: [],
      turns: [],
    });
    expect(origin.kind).toBe("assisted");
    if (origin.kind !== "assisted") throw new Error("narrowing");
    expect(origin.conversation.conversationId).toBe("conv-9");
    expect(origin.conversation.turn).toBe(7);
    expect(origin.attribution).toBe("recorded");
  });

  it("is fail-soft on an unreadable commit timestamp → unknown", () => {
    const origin = correlate({
      commit: {
        author: "Iain <iain@nivbow.com>",
        at: "not-a-date",
        message: "feat: weird",
      },
      runs: [RUN],
      turns: [TURN],
    });
    expect(origin.kind).toBe("unknown");
    if (origin.kind !== "unknown") throw new Error("narrowing");
    expect(origin.attribution).toBe("inferred");
  });

  it("attributes a bot-authored commit to a run when no window matches", () => {
    const origin = correlate({
      commit: {
        author: "github-actions[bot] <bot@github.com>",
        at: "2026-01-01T00:00:00Z", // outside the run window
        message: "chore: automated",
      },
      runs: [RUN],
      turns: [],
    });
    expect(origin.kind).toBe("autonomous");
    if (origin.kind !== "autonomous") throw new Error("narrowing");
    expect(origin.attribution).toBe("inferred");
  });
});
