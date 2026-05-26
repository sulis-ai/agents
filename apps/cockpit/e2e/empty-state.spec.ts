// WP-016 — empty-state end-to-end (Spec §Acceptance, TDD §6.2).
//
// The dashboard's empty branch: when the change store has zero changes,
// the dashboard renders <EmptyState> with the exact spec copy and the
// sidebar is empty.
//
// Rather than boot a second server against an empty SULIS_STATE_DIR (more
// processes, more flake surface), we intercept the /api/changes response
// and return an empty array. This exercises the real Dashboard rendering
// the real empty branch — the network shape is the only thing stubbed.

import { test, expect } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  // Force the change list empty for this spec, regardless of the seeded
  // fixture the shared server is serving.
  await page.route("**/api/changes", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: "[]",
    });
  });
});

test("empty store renders the EmptyState with the spec copy", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  page.on("console", (msg) => {
    if (msg.type() === "error") errors.push(msg.text());
  });

  await page.goto("/");

  const empty = page.getByTestId("dashboard-empty");
  await expect(empty).toBeVisible();
  // Exact copy (TDD §6.2): headline + the change-start command pointer.
  await expect(empty).toContainText("Nothing in flight.");
  await expect(empty).toContainText('/sulis:change start "<intent>"');

  // No change cards.
  await expect(page.getByTestId("change-card")).toHaveCount(0);

  // Sidebar is present but holds no items.
  await expect(page.getByTestId("shell-sidebar")).toBeVisible();
  await expect(page.getByTestId("sidebar-item")).toHaveCount(0);

  // No console errors.
  expect(errors, errors.join("\n")).toEqual([]);
});
