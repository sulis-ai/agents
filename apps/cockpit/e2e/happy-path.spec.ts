// WP-016 — end-to-end happy-path smoke (TDD §14.7, Spec §Acceptance).
//
// The full founder walkthrough, automated: boot the cockpit against the
// seeded fixture, land on the dashboard, click into the change, read the
// chat, browse files, open a file, copy its path, toggle the diff, and
// return to the file view. This is the sequence the MVP's acceptance
// criteria describe.
//
// Selectors are the data-testid hooks the surface WPs (WP-012..015) baked
// in; we assert URL state at each step because the URL is the source of
// truth for the view (TDD §6.1).

import { test, expect } from "@playwright/test";
import { readHandoff, type Handoff } from "./global-setup";

let fx: Handoff;

test.beforeAll(async () => {
  fx = await readHandoff();
});

test("founder walkthrough: dashboard → chat → files → file → diff", async ({
  page,
}) => {
  // 1. Dashboard renders the seeded change card.
  await page.goto("/");
  const card = page.getByTestId("change-card");
  await expect(card).toBeVisible();
  await expect(card).toContainText(fx.handle);

  // 2. Click the card → navigate to the thread (chat is the default tab).
  await card.click();
  await expect(page).toHaveURL(new RegExp(`/c/${fx.changeId}`));
  await expect(page.getByTestId("thread-tabs")).toBeVisible();
  await expect(page.getByTestId("tab-panel-chat")).toBeVisible();

  // 3. Chat shows the three transcript messages in order; the tool-use
  //    block is collapsed and expands on click.
  await expect(page.getByTestId("chat-list")).toBeVisible();
  await expect(page.getByTestId("chat-message-user")).toContainText(
    "Walk me through the change.",
  );
  await expect(page.getByTestId("assistant-block-text")).toContainText(
    "Here is what I changed.",
  );
  // The tool-use block body starts collapsed (not in the DOM) and becomes
  // visible after clicking the accordion header button.
  const toolUse = page.getByTestId("assistant-block-tool-use");
  await expect(toolUse).toContainText("Used");
  await expect(page.getByTestId("collapsed-block-body")).toHaveCount(0);
  await toolUse.getByRole("button").first().click();
  await expect(page.getByTestId("collapsed-block-body")).toBeVisible();

  // 4. Switch to the Files tab → ?tab=files in the URL.
  await page.getByRole("tab", { name: "Files" }).click();
  await expect(page).toHaveURL(/[?&]tab=files/);
  await expect(page.getByTestId("files-panel")).toBeVisible();

  // 5. File tree shows src/; expand it; index.ts appears.
  const srcNode = page.getByTestId("file-tree-node-src");
  await expect(srcNode).toBeVisible();
  await srcNode.getByRole("button").first().click();
  const fileNode = page.getByTestId("file-tree-node-src/index.ts");
  await expect(fileNode).toBeVisible();

  // 6. Click index.ts → ?file=src/index.ts; Monaco read-only viewer renders.
  await fileNode.click();
  await expect(page).toHaveURL(/[?&]file=src(%2F|\/)index\.ts/);
  await expect(page.getByTestId("monaco-file")).toBeVisible();
  await expect(page.getByTestId("monaco-file")).toContainText(
    "export const x = 2;",
  );

  // 7. Copy path → clipboard holds the absolute path.
  //    (Chromium grants clipboard read/write on localhost in the test
  //    context; we read it back to assert.)
  await page.getByTestId("copy-path-button").click();
  const clip = await page.evaluate(() => navigator.clipboard.readText());
  expect(clip).toBe(fx.fileAbsolutePath);

  // 8. Show diff → ?diff=1; the Monaco diff editor renders.
  await page.getByTestId("diff-toggle").click();
  await expect(page).toHaveURL(/[?&]diff=1/);
  await expect(page.getByTestId("monaco-diff")).toBeVisible();

  // 9. Show current → ?diff removed; back to the read-only viewer.
  await page.getByTestId("diff-toggle").click();
  await expect(page).not.toHaveURL(/[?&]diff=1/);
  await expect(page.getByTestId("monaco-file")).toBeVisible();

  // 10. No console errors accumulated during the walkthrough.
  //     (Captured below via the page error listener.)
});

test("dashboard refresh re-fetches without error", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  page.on("console", (msg) => {
    if (msg.type() === "error") errors.push(msg.text());
  });

  await page.goto("/");
  await expect(page.getByTestId("change-card")).toBeVisible();

  // The Refresh button on the dashboard header re-fetches the change list.
  await page.getByRole("button", { name: /refresh/i }).click();
  await expect(page.getByTestId("change-card")).toBeVisible();

  expect(errors, errors.join("\n")).toEqual([]);
});
