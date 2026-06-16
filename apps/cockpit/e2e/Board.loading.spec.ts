// WP-010 — loading → loaded with NO LAYOUT JUMP (S-34 part 2 / NFR-PERF-5 /
// BR-24).
//
// The MEASURED half of the no-jump contract (the structural half lives in the
// jsdom unit test Board.loading.test.tsx). jsdom computes no layout, so the
// "the card box does not move when the skeleton is replaced by the real card"
// guarantee can only be proven in a real browser — here, Chromium.
//
// We deliberately hold the feed PENDING so we can measure the skeleton board,
// then resolve it on demand and measure again across the same lane scaffold:
//   1. Route /api/changes to a deferred handler we resolve programmatically.
//   2. While pending: the board shows per-card skeletons; record the bounding
//      box of the FIRST skeleton card in the recon lane.
//   3. Install a longtask PerformanceObserver, then resolve the feed with a
//      real change whose card lands in that SAME lane/slot.
//   4. Once the real card is in: record ITS bounding box and assert it is at
//      the same top/left as the skeleton it replaced (no box move; CLS ≈ 0),
//      and that no main-thread long-task > 50 ms occurred during the swap.

import { test, expect, type Page, type Route } from "@playwright/test";

const LONG_FRAME_BUDGET_MS = 50;
// The skeleton occupies the same box as a real card, so a sub-pixel layout
// settle is tolerable but a genuine "card box moved" (a different slot) is not.
const BOX_MOVE_TOLERANCE_PX = 2;

function makeChange(id: string, stage: string) {
  return {
    changeId: id,
    handle: `CH-${id}`,
    slug: `change-${id.toLowerCase()}`,
    primitive: "feat",
    branch: `feat/${id}`,
    worktreePath: `/tmp/${id}`,
    intent: `Intent for ${id}`,
    baseBranch: "main",
    baseSha: "abc123",
    createdAt: "2026-06-01T10:00:00Z",
    updatedAt: "2026-06-01T11:00:00Z",
    stage,
    liveness: { status: "unknown", reason: "no session" },
    needsAttention: { flagged: false, reason: null },
    health: { state: "unknown", reason: "too early to tell" },
    lastActivityAt: null,
  };
}

test.describe("loading → loaded — no layout jump (S-34 / NFR-PERF-5)", () => {
  test("the real card lands in the same box the skeleton held, with no long-frame > 50 ms", async ({
    page,
  }: {
    page: Page;
  }) => {
    // A deferred /api/changes: we capture the route and fulfil it only once
    // we've measured the skeleton board, so the pending → resolved transition
    // is observable. (Search isn't used — no filter is active.)
    let resolveFeed: ((route: Route) => void) | null = null;
    const feedReady = new Promise<Route>((resolve) => {
      resolveFeed = (route) => resolve(route);
    });
    await page.route("**/api/changes**", async (route) => {
      resolveFeed?.(route);
    });

    await page.goto("/");
    await expect(page.getByTestId("page-board")).toBeVisible();

    // ── While PENDING: per-card skeletons in the real lane scaffold ──
    const loading = page.getByTestId("board-loading");
    await expect(loading).toBeVisible();
    await expect(loading).toHaveAttribute("aria-busy", "true");

    // The recon lane's first skeleton card — record its box (the slot the real
    // card will replace).
    const reconLane = loading.locator(
      '[data-testid="stage-column"][data-stage="recon"]',
    );
    const firstSkeleton = reconLane.getByTestId("skeleton-card").first();
    await expect(firstSkeleton).toBeVisible();
    const skeletonBox = await firstSkeleton.boundingBox();
    expect(skeletonBox).not.toBeNull();

    // Install a longtask observer in the page BEFORE we resolve the feed, so it
    // captures any jank during the skeleton → real-card swap.
    await page.evaluate(() => {
      (window as unknown as { __longTasks: number[] }).__longTasks = [];
      const obs = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          (window as unknown as { __longTasks: number[] }).__longTasks.push(
            entry.duration,
          );
        }
      });
      obs.observe({ entryTypes: ["longtask"] });
    });

    // ── Resolve the feed: one recon change → its card lands in recon ──
    const route = await feedReady;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([makeChange("01RECON", "recon")]),
    });

    // The real board renders; the skeletons are gone.
    await expect(page.getByTestId("board")).toBeVisible();
    const realCard = page
      .locator('[data-testid="stage-column"][data-stage="recon"]')
      .getByTestId("change-card")
      .first();
    await expect(realCard).toBeVisible();
    await expect(page.getByTestId("skeleton-card")).toHaveCount(0);

    // ── NO LAYOUT JUMP: the real card sits where the skeleton was ──
    const cardBox = await realCard.boundingBox();
    expect(cardBox).not.toBeNull();
    expect(Math.abs(cardBox!.x - skeletonBox!.x)).toBeLessThanOrEqual(
      BOX_MOVE_TOLERANCE_PX,
    );
    expect(Math.abs(cardBox!.y - skeletonBox!.y)).toBeLessThanOrEqual(
      BOX_MOVE_TOLERANCE_PX,
    );
    // Same width too (the skeleton shares the real card's box metrics).
    expect(Math.abs(cardBox!.width - skeletonBox!.width)).toBeLessThanOrEqual(
      BOX_MOVE_TOLERANCE_PX,
    );

    // ── No long-frame > 50 ms during the swap (NFR-PERF-5) ──
    const longestTaskMs = await page.evaluate(() => {
      const tasks =
        (window as unknown as { __longTasks: number[] }).__longTasks ?? [];
      return tasks.length ? Math.max(...tasks) : 0;
    });
    expect(longestTaskMs).toBeLessThanOrEqual(LONG_FRAME_BUDGET_MS);
  });
});
