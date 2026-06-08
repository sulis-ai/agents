// WP-003 — groupChangesByStage helper tests (RED first).
//
// The board groups the active Product's change set into the six lifecycle
// stage columns, in order. Shipped changes are NOT in-flight and are
// excluded (FR-15). Unknown/terminal stages never appear as a seventh
// column — the six columns are fixed (ADR-005 board IA).

import { describe, it, expect } from "vitest";
import type { Change } from "../../../shared/api-types";
import {
  groupChangesByStage,
  BOARD_STAGES,
} from "../lib/groupChangesByStage";

function makeChange(overrides: Partial<Change> = {}): Change {
  return {
    changeId: "01ABC",
    handle: "CH-01ABC",
    slug: "fix-thing",
    primitive: "fix",
    branch: "fix/thing",
    worktreePath: "/tmp/worktree",
    intent: "Fix the broken thing",
    baseBranch: "main",
    baseSha: "abc123",
    createdAt: "2026-05-26T11:00:00Z",
    updatedAt: "2026-05-26T11:55:00Z",
    stage: "implement",
    liveness: { status: "unknown", reason: "no session" },
    ...overrides,
  };
}

describe("BOARD_STAGES", () => {
  it("is the six lifecycle stages in recon→ship order (FR-01, ADR-005)", () => {
    expect(BOARD_STAGES).toEqual([
      "recon",
      "specify",
      "design",
      "implement",
      "review",
      "ship",
    ]);
  });
});

describe("groupChangesByStage", () => {
  it("returns a bucket for every one of the six stages, even when empty", () => {
    const grouped = groupChangesByStage([]);
    expect(grouped.map((g) => g.stage)).toEqual(BOARD_STAGES);
    for (const group of grouped) {
      expect(group.changes).toEqual([]);
    }
  });

  it("places each change in its own stage bucket", () => {
    const changes: Change[] = [
      makeChange({ changeId: "01R", stage: "recon" }),
      makeChange({ changeId: "01S", stage: "specify" }),
      makeChange({ changeId: "01I", stage: "implement" }),
    ];
    const grouped = groupChangesByStage(changes);
    const byStage = Object.fromEntries(
      grouped.map((g) => [g.stage, g.changes.map((c) => c.changeId)]),
    );
    expect(byStage.recon).toEqual(["01R"]);
    expect(byStage.specify).toEqual(["01S"]);
    expect(byStage.implement).toEqual(["01I"]);
    expect(byStage.design).toEqual([]);
    expect(byStage.review).toEqual([]);
    expect(byStage.ship).toEqual([]);
  });

  it("excludes shipped changes — they are not in-flight (FR-15)", () => {
    const changes: Change[] = [
      makeChange({ changeId: "01LIVE", stage: "review" }),
      makeChange({ changeId: "01DONE", stage: "shipped" }),
    ];
    const grouped = groupChangesByStage(changes);
    const allIds = grouped.flatMap((g) => g.changes.map((c) => c.changeId));
    expect(allIds).toContain("01LIVE");
    expect(allIds).not.toContain("01DONE");
    // No "shipped" column exists on the in-flight board.
    expect(grouped.map((g) => g.stage)).not.toContain("shipped");
  });

  it("keeps multiple changes within one stage, preserving input order", () => {
    const changes: Change[] = [
      makeChange({ changeId: "01A", stage: "implement" }),
      makeChange({ changeId: "01B", stage: "implement" }),
    ];
    const grouped = groupChangesByStage(changes);
    const impl = grouped.find((g) => g.stage === "implement");
    expect(impl?.changes.map((c) => c.changeId)).toEqual(["01A", "01B"]);
  });
});
