// WP-001 — wire-contract link assertions for the widened `Change` shape.
//
// This is a TYPE-LEVEL contract test (the sibling `.tsx` file tests the
// <ContractLinks> component — a different concern). The compiler is the
// failing test here (WP-001 DoD §Red): every assertion below is a
// compile-time check that the new wire fields exist with the right shape.
// At runtime the cases are trivial truthy/equality checks; the real gate is
// that `tsc` accepts the file at all.
//
// What it pins (source-of-truth in parentheses):
//   - `Change` carries `needsAttention`, `health`, `lastActivityAt`,
//     `liveness` (the board card's three new reads — FR-30/40/42, CF-02).
//   - `ChangeHealthState` has ALL FOUR members, including the first-class
//     `"unknown"` (a fresh/degraded change reads honestly, not on-track —
//     FR-31; "worth-a-look" stays deferred but is carried — ADR-001).
//   - `Liveness` carries the `"unknown"` member (the probe renders it
//     distinctly — FR-41).
//   - `lastActivityAt` is nullable (`null` ⇒ no-recency — FR-42).
//   - `NeedsAttention` is one shape, reused by both `Change.needsAttention`
//     and `ChangeStatus.needsAttention` (CF-02 / DRY).

import { describe, it, expect } from "vitest";
import type {
  Change,
  ChangeStatus,
  ChangeHealth,
  ChangeHealthState,
  NeedsAttention,
  Liveness,
} from "../../../shared/api-types";

// A `Change` literal that destructures every new field. If any field is
// missing or wrongly typed on `Change`, this object literal fails to compile
// — the WP's "the compiler is the failing test" RED.
const wired: Change = {
  changeId: "01ABC",
  handle: "CH-01ABC",
  slug: "demo",
  primitive: "create",
  branch: "change/demo",
  worktreePath: "/tmp/worktree",
  intent: "Demo change",
  baseBranch: "main",
  baseSha: "abc123",
  createdAt: "2026-06-09T11:00:00Z",
  updatedAt: "2026-06-09T11:55:00Z",
  stage: "design",
  liveness: { status: "not-running" },
  needsAttention: { flagged: false, reason: null },
  health: { state: "on-track", reason: "tests green" },
  lastActivityAt: "2026-06-09T11:55:00Z",
};

// Exhaustiveness probe: a switch over `ChangeHealthState` that the compiler
// only accepts as exhaustive when the union is EXACTLY the four members.
// Adding/removing a member breaks this at compile time.
function describeHealthState(state: ChangeHealthState): string {
  switch (state) {
    case "on-track":
      return "on track";
    case "off-track":
      return "off track";
    case "worth-a-look":
      return "worth a look";
    case "unknown":
      return "too early to tell";
    default: {
      // If a member is added without a case, `state` is not `never` here.
      const _exhaustive: never = state;
      return _exhaustive;
    }
  }
}

describe("WP-001 — widened `Change` wire contract", () => {
  it("`Change` carries needsAttention, health, lastActivityAt, and liveness", () => {
    expect(wired.needsAttention.flagged).toBe(false);
    expect(wired.health.state).toBe("on-track");
    expect(wired.lastActivityAt).toBe("2026-06-09T11:55:00Z");
    expect(wired.liveness.status).toBe("not-running");
  });

  it("`lastActivityAt` is nullable — null ⇒ no recency (FR-42)", () => {
    const noRecency: Change = { ...wired, lastActivityAt: null };
    expect(noRecency.lastActivityAt).toBeNull();
  });

  it("`ChangeHealthState` has all four members, including `unknown` (FR-31)", () => {
    const all: ChangeHealthState[] = [
      "on-track",
      "off-track",
      "worth-a-look",
      "unknown",
    ];
    expect(all.map(describeHealthState)).toEqual([
      "on track",
      "off track",
      "worth a look",
      "too early to tell",
    ]);
  });

  it("`ChangeHealth.state` may be `unknown` — a degraded change reads honestly (FR-31)", () => {
    const unknownHealth: ChangeHealth = {
      state: "unknown",
      reason: "too early to tell",
    };
    const degraded: Change = { ...wired, health: unknownHealth };
    expect(degraded.health.state).toBe("unknown");
  });

  it("`Liveness` carries the `unknown` member — the probe renders it distinctly (FR-41)", () => {
    const unknownLiveness: Liveness = {
      status: "unknown",
      reason: "could not probe the process",
    };
    const probed: Change = { ...wired, liveness: unknownLiveness };
    expect(probed.liveness.status).toBe("unknown");
  });

  it("`NeedsAttention` is one shape, reused by Change and ChangeStatus (CF-02 / DRY)", () => {
    // A single `NeedsAttention` value assigns to BOTH consumers — proving the
    // shape is lifted, not duplicated.
    const attention: NeedsAttention = {
      flagged: true,
      reason: "waiting-on-decision",
    };
    const onChange: Change = { ...wired, needsAttention: attention };
    const onStatus: ChangeStatus = {
      changeId: "01ABC",
      stage: "implement",
      headline: "Waiting on a decision.",
      needsAttention: attention,
    };
    expect(onChange.needsAttention.reason).toBe("waiting-on-decision");
    expect(onStatus.needsAttention.reason).toBe("waiting-on-decision");
  });
});
