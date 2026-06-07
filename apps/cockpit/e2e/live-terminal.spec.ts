// WP-010 — end-to-end live-terminal round-trip (Spec §Acceptance #1/#2/#3,
// TDD §3 / §6.4, contract §2.12–§2.13).
//
// THE proof of the whole change: the founder's acceptance journey, driven
// through the REAL interface (Playwright clicking the cockpit) against a REAL
// AF_UNIX socket served over a REAL SessionManager + a REAL pty-backed fake
// child (MEA-09 — no mocks in integration; WPF/WPB-09 done = wired). The
// browser↔socket gap is bridged by the e2e harness's WS→AF_UNIX terminal proxy
// (e2e/terminal-proxy.ts, started by run-server.ts) — the live-socket transport
// WP-008 left as `notYetWiredTransport` for this WP to replace. The read-only
// Express app is untouched (the read-only-inventory gate stays green): the WS
// proxy is harness-only.
//
// The four UI cases (WP-010 DoD Red):
//   1. open the change's Terminal tab → see the running session + scrollback
//      (NOT a blank pane; not the "no terminal here" state) — acceptance #1.
//   2. type a command → keystrokes reach the live session, output appears —
//      acceptance #2.
//   3. close the tab + reopen → the session is still alive, scrollback catches
//      up — acceptance #3.
//   4. Playwright-axe clean on the live terminal surface — WPF-10.
//
// RED first: with WP-008's default `notYetWiredTransport`, the Terminal tab
// renders the "no terminal here" state (NOT_PTY_SESSION), so every assertion
// that the live terminal shows real output FAILS until WP-010 wires the live
// transport + proxy.
//
// xterm.js renders into a canvas; we assert on the accessible text layer
// (xterm's screen-reader live region exposes the rendered rows as text), which
// is both the a11y-correct read AND the deterministic, pixel-free assertion.

import { test, expect, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

import {
  readTerminalHandoff,
  type TerminalHandoff,
} from "./live-terminal-setup";

let fx: TerminalHandoff;

test.beforeAll(() => {
  fx = readTerminalHandoff();
});

/** Navigate to the change's Terminal tab and wait for the live attach to land
 *  (the "connected" badge + the live input hint replace the connecting/
 *  no-terminal states). Returns once the terminal is live. */
async function openTerminalTab(page: Page): Promise<void> {
  await page.goto(`/c/${fx.changeId}?tab=terminal`);
  await expect(page.getByTestId("thread-tabs")).toBeVisible();
  await expect(page.getByTestId("tab-panel-terminal")).toBeVisible();
  await expect(page.getByTestId("live-terminal")).toBeVisible();
}

/** The rendered terminal text, read off xterm's accessible layer. xterm.js
 *  mirrors the screen into a `.xterm-accessibility` live region; we read its
 *  text content so the assertion is on what a screen-reader (and the founder)
 *  perceives — never on canvas pixels. */
async function terminalText(page: Page): Promise<string> {
  const host = page.getByTestId("live-terminal");
  return (await host.innerText()).replace(/ /g, " ");
}

/** Wait until the terminal's rendered text contains `needle`. */
async function expectTerminalContains(
  page: Page,
  needle: string,
): Promise<void> {
  await expect
    .poll(async () => await terminalText(page), {
      timeout: 15_000,
      message: `terminal never rendered ${JSON.stringify(needle)}`,
    })
    .toContain(needle);
}

test("acceptance #1 — open the terminal → see the live session + scrollback (not blank)", async ({
  page,
}) => {
  await openTerminalTab(page);

  // The live state is reached: the connection badge reads "connected" and the
  // "no terminal here" / connecting states are gone (NOT a blank pane).
  await expect(
    page.locator('[aria-label="connection status: connected"]'),
  ).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("live-terminal-no-terminal")).toHaveCount(0);
  await expect(page.getByTestId("live-terminal-connecting")).toHaveCount(0);

  // Scrollback rendered: the harness seeds the pty session with a known banner
  // line BEFORE the browser attaches, so the snapshot phase must render it
  // (the "render existing scrollback, not a blank pane" guarantee, §2.12.2).
  await expectTerminalContains(page, "WP010_SCROLLBACK_BANNER");
});

test("acceptance #2 — type a command → keystrokes reach the session, output appears", async ({
  page,
}) => {
  await openTerminalTab(page);
  await expect(
    page.locator('[aria-label="connection status: connected"]'),
  ).toBeVisible({ timeout: 15_000 });

  // Focus the terminal viewport and type the sentinel that makes the pty fake
  // child emit its deterministic PTY_PONG line (the two-way feed, §2.12.4).
  const viewport = page.getByRole("region", { name: "Live terminal output" });
  await viewport.click();
  await page.keyboard.type("__PTY_PING__");
  await page.keyboard.press("Enter");

  // The keystrokes reached the live session and its output came back.
  await expectTerminalContains(page, "PTY_PONG");
});

test("acceptance #3 — close the tab + reopen → session alive, scrollback catches up", async ({
  page,
}) => {
  await openTerminalTab(page);
  await expect(
    page.locator('[aria-label="connection status: connected"]'),
  ).toBeVisible({ timeout: 15_000 });

  // Type a marker so it lands in the session's scrollback, then leave.
  const viewport = page.getByRole("region", { name: "Live terminal output" });
  await viewport.click();
  await page.keyboard.type("__PTY_PING__");
  await page.keyboard.press("Enter");
  await expectTerminalContains(page, "PTY_PONG");

  // "Close the tab": navigate away (unmount <LiveTerminal/> → detach). Detach
  // LEAVES THE SESSION RUNNING (§2.12.3) — the process + scrollback survive.
  await page.goto(`/c/${fx.changeId}`);
  await expect(page.getByTestId("tab-panel-chat")).toBeVisible();

  // "Reopen": back to the Terminal tab → a fresh attach. The snapshot phase
  // catches up with everything the session accumulated while detached —
  // nothing lost (the banner AND the PTY_PONG from before the close).
  await openTerminalTab(page);
  await expect(
    page.locator('[aria-label="connection status: connected"]'),
  ).toBeVisible({ timeout: 15_000 });
  await expectTerminalContains(page, "WP010_SCROLLBACK_BANNER");
  await expectTerminalContains(page, "PTY_PONG");
});

test("WPF-10 — the live terminal surface is Playwright-axe clean", async ({
  page,
}) => {
  await openTerminalTab(page);
  await expect(
    page.locator('[aria-label="connection status: connected"]'),
  ).toBeVisible({ timeout: 15_000 });

  // Scan the live-terminal region for WCAG A/AA violations. The terminal
  // CONTENT canvas is xterm's own surface (it ships its own screen-reader
  // affordance); we scope the scan to the surrounding chrome region the WP
  // owns (WP-VISUAL §5.1 — chrome meets AA; content is xterm's).
  const results = await new AxeBuilder({ page })
    .include('[data-testid="live-terminal"]')
    .withTags(["wcag2a", "wcag2aa"])
    .analyze();

  expect(
    results.violations,
    JSON.stringify(results.violations, null, 2),
  ).toEqual([]);
});
