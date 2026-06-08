// Empty-state end-to-end (Spec §Acceptance, TDD §6.2).
//
// The Board's empty branch: when the change store has zero in-flight
// changes, the Board renders <EmptyState> with the exact spec copy.
//
// #216 restructured the cockpit into a tabbed workspace: the persistent
// left Sidebar is GONE. The dashboard is now the "Board" (a tab in the top
// bar), and there is no per-change sidebar list to assert on — the Board IS
// the surface, and its empty branch is what the founder sees. This spec was
// updated for that layout: it asserts the empty Board (EmptyState copy +
// zero change cards) and the workspace top bar with its Board tab, and drops
// the removed shell-sidebar / sidebar-item assertions (those DOM nodes no
// longer exist in the new UI).
//
// Rather than boot a second server against an empty SULIS_STATE_DIR (more
// processes, more flake surface), we intercept the /api/changes response
// and return an empty array. This exercises the real Board rendering its
// real empty branch — the network shape is the only thing stubbed.

import { test, expect } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  // Force the change list empty for this spec, regardless of the seeded
  // fixture the shared server is serving. The Board reads the active-Product
  // change list through /api/changes (and /api/search when filtering); with
  // no filter active the empty list drives the EmptyState branch.
  await page.route("**/api/changes**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: "[]",
    });
  });
});

test("empty store renders the EmptyState with the spec copy on the Board", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  page.on("console", (msg) => {
    if (msg.type() === "error") errors.push(msg.text());
  });

  await page.goto("/");

  // The Board is the landing surface (its tab is active in the top bar).
  await expect(page.getByTestId("workspace-topbar")).toBeVisible();
  await expect(page.getByTestId("tab-board")).toBeVisible();
  await expect(page.getByTestId("page-board")).toBeVisible();

  // The empty branch: <EmptyState> with the exact spec copy (TDD §6.2):
  // headline + the change-start command pointer.
  const empty = page.getByTestId("dashboard-empty");
  await expect(empty).toBeVisible();
  await expect(empty).toContainText("Nothing in flight.");
  await expect(empty).toContainText('/sulis:change start "<intent>"');

  // No change cards on the empty board, and no board grid rendered (the
  // EmptyState replaces it).
  await expect(page.getByTestId("change-card")).toHaveCount(0);
  await expect(page.getByTestId("board")).toHaveCount(0);

  // No console errors.
  expect(errors, errors.join("\n")).toEqual([]);
});
