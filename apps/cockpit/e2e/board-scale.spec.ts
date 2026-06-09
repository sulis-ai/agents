// WP-013 — Lane scale: a single lane holds up to 200 cards and scrolls at
// 60fps via its INTERNAL scroll, with no long-frame jank (S-15 / NFR-PERF-2
// / AF-6).
//
// The mechanism is WP-004's full-height lane (the `.laneList` internal-scroll
// container); this spec PROVES the perf budget at the 200-card threshold and
// fixes the contract so it can't silently regress. Virtualisation is NOT
// built unless this budget is breached (Q-6, boring-code) — so the default
// assertion is: the plain internal scroll absorbs 200 cards without jank.
//
// We seed 200 changes into ONE lane (recon) by intercepting /api/changes and
// returning a synthetic list — the same network-shape stub the empty-state
// spec uses, inverted from [] to a 200-element array. This exercises the real
// Board → StageColumn lane render against a large count without standing up a
// 200-change fixture on disk.
//
// The budget is measured with a PerformanceObserver on `longtask` entries
// installed BEFORE a programmatic scroll of the lane: the scroll is driven in
// fixed steps to the bottom, and we assert no single main-thread long-task
// exceeded 50 ms during that window (NFR-PERF-2's "no long-frame > 50 ms").
// The header count is asserted to read the TRUE total (200), not a windowed
// subset, in both the plain-scroll and (hypothetical) virtualised case.

import { test, expect, type Page } from "@playwright/test";
import type { Change } from "../shared/api-types";

const LANE_CARD_COUNT = 200;
const LONG_FRAME_BUDGET_MS = 50;

/** A minimal-but-conformant Change in the recon lane, indexed for uniqueness. */
function makeChange(i: number): Change {
  const id = `01SCALE${String(i).padStart(18, "0")}`;
  return {
    changeId: id,
    handle: `CH-SCALE${String(i).padStart(3, "0")}`,
    slug: `scale-change-${i}`,
    primitive: "fix",
    branch: `fix/scale-${i}`,
    worktreePath: `/tmp/scale/${i}`,
    intent: `Synthetic scale change number ${i}`,
    baseBranch: "main",
    baseSha: "abc123",
    createdAt: "2026-06-09T11:00:00Z",
    updatedAt: "2026-06-09T11:55:00Z",
    stage: "recon",
    liveness: { status: "unknown", reason: "no session" },
    needsAttention: { flagged: false, reason: null },
    health: { state: "unknown", reason: "too early to tell" },
    lastActivityAt: null,
  };
}

/** Seed 200 changes, all in the recon lane, via /api/changes interception. */
async function seedLargeLane(page: Page): Promise<void> {
  const changes = Array.from({ length: LANE_CARD_COUNT }, (_, i) =>
    makeChange(i),
  );
  await page.route("**/api/changes**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(changes),
    });
  });
}

test.describe("lane scale — 200 cards scroll at 60fps via internal scroll (S-15)", () => {
  test("the recon lane holds all 200 cards, the header count reads 200, and the internal scroll reaches the last card", async ({
    page,
  }) => {
    await seedLargeLane(page);
    await page.goto("/");

    // The board renders (not the empty state — there are 200 in-flight).
    await expect(page.getByTestId("page-board")).toBeVisible();
    await expect(page.getByTestId("board")).toBeVisible();

    // The recon lane is the labelled region; its header count reads the TRUE
    // total (200), not a windowed subset.
    const lane = page.locator('[data-testid="stage-column"][data-stage="recon"]');
    await expect(lane).toBeVisible();
    await expect(lane).toHaveAttribute("aria-label", /Recon — 200 changes/);
    // The count pill in the sticky header carries the TRUE total (200) — the
    // contract's truthfulness invariant, which holds whether the lane plain-
    // scrolls all 200 or virtualises a window of them (the header never reads
    // a windowed subset).
    await expect(lane.locator("header")).toContainText("200");

    // The list — not the page — is the lane's internal scroll container: it
    // has real overflow sized for the full 200-card count (scrollHeight far
    // exceeds clientHeight), so all 200 are reachable by scrolling, not just
    // the ones currently in the DOM window.
    const list = page.getByTestId("stage-column-recon");
    await expect(list).toBeVisible();
    const overflow = await list.evaluate(
      (el) => el.scrollHeight - el.clientHeight,
    );
    expect(overflow).toBeGreaterThan(0);

    // The FIRST change is reachable at the top (scroll to 0), identified by
    // its handle — this works for both plain-scroll and virtualised lanes.
    await list.evaluate((el) => {
      el.scrollTop = 0;
    });
    await expect(list.getByText("CH-SCALE000")).toBeVisible();

    // The LAST change is reachable by scrolling to the bottom — proving the
    // internal scroll absorbs the FULL count (not a truncated window). Under
    // virtualisation the last card mounts only once scrolled into range, so
    // we drive the scroll to the end and wait for its handle to appear.
    await list.evaluate((el) => {
      el.scrollTop = el.scrollHeight;
    });
    await expect(list.getByText(`CH-SCALE${String(LANE_CARD_COUNT - 1).padStart(3, "0")}`)).toBeVisible();
  });

  test("scrolling the 200-card lane produces no long-frame > 50 ms (NFR-PERF-2)", async ({
    page,
  }) => {
    await seedLargeLane(page);
    await page.goto("/");
    await expect(page.getByTestId("board")).toBeVisible();

    const list = page.getByTestId("stage-column-recon");
    // Ready when the lane has mounted its first card and sized its full scroll
    // height (works for both plain-scroll and virtualised lanes).
    await expect(list.getByText("CH-SCALE000")).toBeVisible();

    // Install a longtask observer, then drive a programmatic step-scroll of
    // the lane to the bottom and back, and collect the longest main-thread
    // task observed during that window. `longtask` entries are tasks ≥ 50 ms,
    // so ANY entry is already a budget breach; we still capture the max for
    // diagnostics.
    const longestTaskMs = await list.evaluate(async (el: HTMLElement) => {
      const durations: number[] = [];
      const obs = new PerformanceObserver((listEntries) => {
        for (const entry of listEntries.getEntries()) {
          durations.push(entry.duration);
        }
      });
      obs.observe({ entryTypes: ["longtask"] });

      const sleep = (ms: number) =>
        new Promise<void>((r) => setTimeout(r, ms));
      const step = Math.max(1, Math.floor(el.clientHeight * 0.8));
      const max = el.scrollHeight - el.clientHeight;

      // Scroll down to the bottom in steps, then back to the top, letting the
      // browser paint between steps (rAF) so any per-frame jank is observable.
      for (let y = 0; y <= max; y += step) {
        el.scrollTop = y;
        await new Promise<void>((r) => requestAnimationFrame(() => r()));
      }
      for (let y = max; y >= 0; y -= step) {
        el.scrollTop = y;
        await new Promise<void>((r) => requestAnimationFrame(() => r()));
      }

      // Give the observer a tick to flush, then disconnect.
      await sleep(50);
      obs.disconnect();

      return durations.length ? Math.max(...durations) : 0;
    });

    expect(longestTaskMs).toBeLessThanOrEqual(LONG_FRAME_BUDGET_MS);
  });

  test("scrolling the lane triggers no per-card network request (NFR-POLL-1, no N+1 on scroll)", async ({
    page,
  }) => {
    await seedLargeLane(page);

    // Record every /api request AFTER the initial board load, so we can prove
    // that scrolling adds no per-card fetch (the feed is one 10s poll; more
    // cards on screen must not trigger N+1 fetches).
    await page.goto("/");
    await expect(page.getByTestId("board")).toBeVisible();
    const list = page.getByTestId("stage-column-recon");
    await expect(list.getByText("CH-SCALE000")).toBeVisible();

    const apiCallsDuringScroll: string[] = [];
    page.on("request", (req) => {
      const url = req.url();
      if (url.includes("/api/")) apiCallsDuringScroll.push(url);
    });

    // Drive a full scroll of the lane.
    await list.evaluate((el) => {
      el.scrollTop = el.scrollHeight;
    });
    await list.getByTestId("change-card").last().scrollIntoViewIfNeeded();
    // A short settle window for any (forbidden) lazy fetch to fire.
    await page.waitForTimeout(300);

    // No per-card request was triggered by the scroll. The only /api traffic
    // permitted in this window is the periodic 10s poll of /api/changes — and
    // 300 ms is far below that interval, so we expect zero.
    expect(
      apiCallsDuringScroll,
      `scroll triggered unexpected /api calls:\n${apiCallsDuringScroll.join("\n")}`,
    ).toEqual([]);
  });
});
