// WP-009 — conciergeRead unit test (FR-33 / FR-34 / FR-N8 / FR-N9; ADR-006).
//
// The concierge's read path composes the EXISTING ChangeStoreReader + brain
// read into a read-only nav/status/Q&A context (no new write path), and
// detects when the founder's intent is CONSEQUENTIAL (start work / investigate)
// so the route can emit a `route` hint instead of acting inline (FR-N9).
//
// Two pure surfaces, both read-only:
//   - detectRoute(question)  → "onboarding" | "start-from-intent" | null
//   - buildConciergeContext({changeStore, …}) → a read-only context summary
//     the concierge prompt is grounded in (zero writes/mints/starts/signals).
//
// We use the in-memory FakeChangeStoreReader (the same fake the board/thread
// reads use) so the composition is exercised without shelling out.

import { describe, it, expect, vi } from "vitest";

import {
  detectRoute,
  buildConciergeContext,
} from "../lib/concierge/conciergeRead";
import { FakeChangeStoreReader } from "../adapters/FakeChangeStoreReader";
import type { ChangeStoreRecord } from "../ports/ChangeStoreReader";

function record(over: Partial<ChangeStoreRecord> = {}): ChangeStoreRecord {
  return {
    changeId: "01CHANGE",
    handle: "fix-login-redirect",
    slug: "fix-login-redirect",
    primitive: "fix",
    branch: "change/fix-login-redirect",
    worktreePath: "/tmp/wt/fix-login-redirect",
    intent: "Fix login redirect loop",
    baseBranch: "main",
    baseSha: "abc123",
    createdAt: "2026-06-01T00:00:00Z",
    updatedAt: "2026-06-02T00:00:00Z",
    stage: "implement",
    ...over,
  };
}

describe("detectRoute — consequential intent routes, read-only Q&A does not (FR-34/N9)", () => {
  it("returns null for a navigation / find-a-change question (read-only)", () => {
    expect(
      detectRoute("which change was I doing the login fix in?"),
    ).toBeNull();
    expect(detectRoute("find the change about the hanging login page")).toBeNull();
  });

  it("returns null for a status question (read-only)", () => {
    expect(detectRoute("what needs my attention?")).toBeNull();
    expect(detectRoute("where's the checkout change up to?")).toBeNull();
  });

  it("returns null for a plain Q&A question over the world (read-only)", () => {
    expect(detectRoute("what have I got in flight?")).toBeNull();
    expect(detectRoute("how many changes are in Implement?")).toBeNull();
  });

  it("routes an INVESTIGATION request to start-from-intent (FR-34/N9 — never inline)", () => {
    expect(detectRoute("can you look into why sign-ups dropped last week?")).toBe(
      "start-from-intent",
    );
    expect(detectRoute("investigate the slow checkout")).toBe(
      "start-from-intent",
    );
    expect(detectRoute("dig into the failing payment webhook")).toBe(
      "start-from-intent",
    );
  });

  it("routes a START-WORK request to start-from-intent (FR-34)", () => {
    expect(detectRoute("start a change to add saved cards")).toBe(
      "start-from-intent",
    );
    expect(detectRoute("I want to build a weekly digest email")).toBe(
      "start-from-intent",
    );
    expect(detectRoute("fix the login redirect loop")).toBe(
      "start-from-intent",
    );
  });

  it("routes an empty-world SET-UP request to onboarding (UC-09→UC-07)", () => {
    expect(detectRoute("set me up", { worldIsEmpty: true })).toBe("onboarding");
    expect(detectRoute("help me get started", { worldIsEmpty: true })).toBe(
      "onboarding",
    );
  });

  it("does not route a question with no consequential verb even on an empty world", () => {
    // A bare question on an empty world is still read-only Q&A; only an
    // explicit set-up / start intent routes.
    expect(detectRoute("what is this?", { worldIsEmpty: true })).toBeNull();
  });
});

// ─── Fix-forward: deterministic investigation-intent table (FR-N9) ───────────
//
// The live concierge let investigation phrasings slip to the inline-answer path
// because detection was LLM-classified. These tables PIN the deterministic
// pre-classifier so investigation-phrased requests ALWAYS route (never inline)
// and genuine read-only questions ALWAYS stay inline (route null). Both live
// examples that drove this fix are included verbatim.

describe("detectRoute — investigation phrasings ALWAYS route (FR-N9, deterministic)", () => {
  const INVESTIGATION_PHRASINGS = [
    // ── the two live examples that drove the fix ──
    "Look into why sign-ups dropped last week.",
    "Can you look into why the deploy keeps failing?",
    // ── the common investigation patterns the founder named ──
    "investigate the slow checkout",
    "dig into the failing payment webhook",
    "diagnose the timeout on the dashboard",
    "debug the broken email digest",
    "find out why the build is red",
    "figure out why customers are churning",
    "what's the root cause of the 500s?",
    "what's going wrong with the signup flow?",
    "whats going wrong with billing",
    // ── "why is/are/does/do … <symptom>" interrogatives ──
    "why is the deploy failing?",
    "why are sign-ups dropping?",
    "why does checkout keep erroring?",
    "why do payments fail intermittently?",
    "why is the dashboard so slow?",
    "why is login broken?",
    // ── case-insensitivity / leading punctuation ──
    "INVESTIGATE the flaky test suite",
    "  Dig into the latency spike  ",
  ];

  it.each(INVESTIGATION_PHRASINGS)(
    "routes to start-from-intent (never inline): %s",
    (phrasing) => {
      expect(detectRoute(phrasing)).toBe("start-from-intent");
    },
  );
});

describe("detectRoute — genuine read-only questions STAY inline (route null)", () => {
  const READ_ONLY_QUESTIONS = [
    "what needs my attention?",
    "what have I got in flight?",
    "where's the checkout change up to?",
    "which change was the login fix in?",
    "find the change about the hanging login page",
    "how many changes are in Implement?",
    "show me the changes in review",
    "what's the status of the billing change?",
    "what is this?",
    // A noun that merely CONTAINS a symptom word must not trip the symptom
    // interrogative (no leading "why … fail" pattern → read-only).
    "which change fixed the failing webhook?",
    "where did the slow checkout investigation end up?",
  ];

  it.each(READ_ONLY_QUESTIONS)("stays inline (route null): %s", (question) => {
    expect(detectRoute(question)).toBeNull();
  });
});

describe("buildConciergeContext — read-only composition over the seam (FR-33/N8)", () => {
  it("composes the change list into a read-only context summary", async () => {
    const reader = new FakeChangeStoreReader([
      record({ changeId: "01A", handle: "fix-login-redirect", stage: "implement" }),
      record({ changeId: "01B", handle: "add-checkout-flow", stage: "design" }),
    ]);

    const ctx = await buildConciergeContext({ changeStore: reader });

    expect(ctx.changes).toHaveLength(2);
    expect(ctx.changes.map((c) => c.handle)).toContain("fix-login-redirect");
    expect(ctx.changes.map((c) => c.handle)).toContain("add-checkout-flow");
    // The summary carries the live stage so the concierge can answer "where's
    // it up to" without a second read.
    const login = ctx.changes.find((c) => c.handle === "fix-login-redirect");
    expect(login?.stage).toBe("implement");
  });

  it("reports an EMPTY world (nothing minted) so the UI can prompt onboarding", async () => {
    const reader = new FakeChangeStoreReader([]);
    const ctx = await buildConciergeContext({ changeStore: reader });
    expect(ctx.changes).toHaveLength(0);
    expect(ctx.worldIsEmpty).toBe(true);
  });

  it("scopes to a Product when productId is given (ADR-009 read-only scope)", async () => {
    const reader = new FakeChangeStoreReader([
      record({ changeId: "01A", handle: "fix-login-redirect" }),
    ]);
    const ctx = await buildConciergeContext({
      changeStore: reader,
      productId: "prod-1",
    });
    expect(ctx.productId).toBe("prod-1");
  });

  it("performs ZERO writes / mints / session-starts (read-only; FR-N8)", async () => {
    // The composition uses ONLY the reader's read methods — never a write,
    // never a process start. We assert no unexpected method is invoked.
    const reader = new FakeChangeStoreReader([record()]);
    const listSpy = vi.spyOn(reader, "listAllChanges");
    await buildConciergeContext({ changeStore: reader });
    expect(listSpy).toHaveBeenCalledTimes(1);
    // FakeChangeStoreReader has no write method to spy on — the port itself is
    // read-only (listAllChanges / readChangeRecord / readChangeStage). The
    // route-level read-only-inventory test proves the route starts no process.
  });
});
