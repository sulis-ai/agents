// End-to-end happy-path smoke (TDD §14.7, Spec §Acceptance).
//
// The full founder walkthrough, automated: boot the cockpit against the
// seeded fixture, land on the Board, open the change (its tab), read the
// conversation, reach the Files section, open a file (Monaco), copy its
// path, toggle the diff, and return to the file view. This is the sequence
// the MVP's acceptance criteria describe.
//
// #216 restructured the cockpit into a tabbed workspace. The old persistent
// sidebar + per-change "thread tabs" (?tab=chat / ?tab=files) are GONE. The
// navigation model is now:
//   Board (a tab in the top bar) → click a change card → the change opens in
//   its OWN tab (/c/:id) → ThreadView renders a change-scoped LEFT NAV
//   (<ChangeNav>) whose "Views" switch the main area between Conversation /
//   Files / Provenance / Preview / Terminal / Advanced.
//
// The view switch is local state seeded from the optional `?view=` param —
// there is no `?tab=` URL state anymore; the file SELECTION still lives in
// the URL (?file= / ?diff=1), which the file assertions below still use.
//
// The conversation is rendered as Turn Cards (<TurnCard>): the founder's
// message bubbles + one card per agent turn (a summary, with the recorded
// steps foldable). The old AssistantBlock / tool-use accordion testids
// (assistant-block-text, collapsed-block-body) belong to the concierge/
// onboarding chat, not the change conversation — so the "expandable agent
// detail" assertion is preserved here against the Turn Card's foldable
// steps (turn-steps-toggle → turn-steps), which is the equivalent
// progressive-disclosure affordance in the new UI.
//
// Selectors are the data-testid hooks the current components expose; we
// assert URL state where the URL is the source of truth (the change route,
// the file selection, the diff toggle).

import { test, expect } from "@playwright/test";
import { readHandoff, type Handoff } from "./global-setup";

let fx: Handoff;

test.beforeAll(async () => {
  fx = await readHandoff();
});

test("founder walkthrough: board → change → conversation → files → file → diff", async ({
  page,
}) => {
  // 1. The Board renders the seeded change card.
  await page.goto("/");
  await expect(page.getByTestId("page-board")).toBeVisible();
  const card = page.getByTestId("change-card");
  await expect(card).toBeVisible();
  await expect(card).toContainText(fx.handle);

  // 2. Click the card → the change opens in its own tab (/c/:id). The
  //    workspace top bar now carries a change tab, and the change's own
  //    left nav (ChangeNav) is present. Conversation is the default view.
  await card.click();
  await expect(page).toHaveURL(new RegExp(`/c/${fx.changeId}`));
  await expect(page.getByTestId("page-thread")).toBeVisible();
  await expect(page.getByTestId("tab-change")).toBeVisible();
  await expect(page.getByTestId("change-nav")).toBeVisible();
  await expect(page.getByTestId("section-conversation")).toBeVisible();

  // 3. The conversation shows the founder's message and the agent's turn.
  //    The user bubble carries the seeded prompt; the agent turn's summary
  //    carries the seeded reply text.
  await expect(page.getByTestId("chat-list")).toBeVisible();
  await expect(page.getByTestId("chat-message-user")).toContainText(
    "Walk me through the change.",
  );
  const turn = page.getByTestId("turn-card");
  await expect(turn).toBeVisible();
  // The agent's verbatim reply lives in the turn's "full reply", which is
  // foldable progressive disclosure. There are two display modes, depending
  // on whether a generated (Haiku) summary has landed:
  //   - no generated summary yet → the summary IS the verbatim first sentences
  //     of the reply, and the "full reply" toggle is hidden (nothing more to
  //     show);
  //   - generated summary landed → the summary is a paraphrase and the verbatim
  //     reply is behind the "Show the full reply" toggle.
  // The summary arrives asynchronously (a background poll), so the toggle can
  // appear at any time — a one-shot `count()` check would race that poll. We
  // poll instead: expand the full reply whenever the toggle is present, until
  // the verbatim seeded text is on screen. This is idempotent (an already-
  // expanded toggle stays expanded text-visible) and converges in either mode.
  // It's the progressive-disclosure equivalent of the old tool-use accordion.
  const fullToggle = turn.getByTestId("turn-full-toggle");
  await expect(async () => {
    if ((await fullToggle.count()) > 0 && (await fullToggle.getAttribute("aria-expanded")) === "false") {
      await fullToggle.click();
    }
    await expect(turn).toContainText("Here is what I changed.");
  }).toPass({ timeout: 15_000 });
  // The agent's recorded steps are folded by default (progressive
  // disclosure) and expand on click — the seeded turn has one step (the
  // Read of src/index.ts), so the steps toggle is present.
  await expect(page.getByTestId("turn-steps")).toHaveCount(0);
  await turn.getByTestId("turn-steps-toggle").click();
  await expect(page.getByTestId("turn-steps")).toBeVisible();

  // 4. Switch to the Files view via the change's left nav. There is no
  //    ?tab= URL state anymore; the view is local state.
  await page.getByTestId("view-files").click();
  await expect(page.getByTestId("section-files")).toBeVisible();
  await expect(page.getByTestId("files-panel")).toBeVisible();

  // 5. The file tree shows src/; expand it; index.ts appears.
  const srcNode = page.getByTestId("file-tree-node-src");
  await expect(srcNode).toBeVisible();
  await srcNode.getByRole("button").first().click();
  const fileNode = page.getByTestId("file-tree-node-src/index.ts");
  await expect(fileNode).toBeVisible();

  // 6. Click index.ts → ?file=src/index.ts; the read-only Monaco viewer
  //    renders the source. (A .ts file is non-renderable, so RenderedPreview
  //    falls back to the Monaco source viewer — data-testid="monaco-file".)
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

test("board refresh re-fetches without error", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  page.on("console", (msg) => {
    if (msg.type() === "error") errors.push(msg.text());
  });

  await page.goto("/");
  await expect(page.getByTestId("change-card")).toBeVisible();

  // The Refresh button on the Board header re-fetches the change list.
  await page.getByRole("button", { name: /refresh/i }).click();
  await expect(page.getByTestId("change-card")).toBeVisible();

  expect(errors, errors.join("\n")).toEqual([]);
});
