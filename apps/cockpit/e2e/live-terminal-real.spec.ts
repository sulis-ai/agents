// WP-007 — the load-bearing end-to-end proof against the REAL server endpoint.
//
// SUPERSEDES live-terminal.spec.ts (the harness-proxy e2e) as the PRODUCTION
// proof of the whole change. live-terminal.spec.ts drove the cockpit against the
// e2e harness's WS→AF_UNIX proxy (terminal-proxy.ts + terminal-backend.py); it
// proved CH-01KTGY's round-trip but NOT the production wiring. THIS spec drives
// the same founder acceptance journey against the REAL server endpoint produced
// by startProductionServer() — the production composition (WP-004): the cockpit
// server spawns the Python session-manager host (WP-001), attaches the terminal
// sidecar (WP-002/003) to the running HTTP server's /terminal WS upgrade, and the
// client reaches it via the WP-006 SAME-ORIGIN default (NO VITE_TERMINAL_WS_URL).
// MEA-09: real interface, real socket, real pty child, NO harness proxy in the
// round-trip. The harness-proxy spec stays intact (the proxy/backend may be
// retired in a later change — out of scope here).
//
// Each test maps 1:1 to a SPEC acceptance item (§5 / WP-007 DoD Red):
//   1. acceptance #1 — open change → Terminal view → the seeded scrollback token
//      renders (not blank, not the "not wired" fallback);
//   2. acceptance #2 — type a command → echoed output appears;
//   3. acceptance #3 — close + reopen → session alive, scrollback catches up;
//   4. acceptance #4 — a connection can only drive ITS OWN change; a cross-change
//      attach on the bound connection is refused (no foreign bytes) — the binding
//      guard is ON in production (WP-001);
//   5. acceptance #5 — read surfaces + the chat path still work; no session
//      starts on a read view.
//
// INDEPENDENCE (founder directive — MUST): the terminal works independently of
// chat. This spec drives the terminal round-trip WITHOUT the chat relay; the
// acceptance #5 chat assertion only confirms the chat surface is UNAFFECTED — it
// is not part of the terminal's round-trip (no shared transport, no dependency).
//
// xterm.js renders into a canvas; we assert on the accessible text layer (xterm's
// screen-reader live region exposes the rendered rows as text) — the a11y-correct
// read AND the deterministic, pixel-free assertion (mirrors live-terminal.spec.ts).
//
// UI selectors (truthful against ThreadView.tsx / LiveTerminal.tsx):
//   - the change page is /c/:id; the view is seeded from `?view=` (one of
//     conversation|files|provenance|preview|advanced|terminal) and then driven
//     by the `view-<id>` nav buttons;
//   - the terminal panel is `section-terminal`; the live card is `live-terminal`;
//   - the connection badge reads `connection status: connected`;
//   - the terminal viewport is role=region name="Live terminal output".

import { test, expect, type Page } from "@playwright/test";
import { WebSocket as NodeWebSocket } from "ws";

import {
  readRealTerminalHandoff,
  REAL_SCROLLBACK_TOKEN,
  type RealTerminalHandoff,
} from "./live-terminal-real-setup";

let fx: RealTerminalHandoff;

test.beforeAll(() => {
  fx = readRealTerminalHandoff();
});

/** Open the change's Terminal view (a fresh page load seeded on `?view=terminal`)
 *  and wait for the live card to mount. The WS rides the REAL server's
 *  same-origin /terminal endpoint via the WP-006 default. */
async function openTerminalView(page: Page): Promise<void> {
  await page.goto(`/c/${fx.changeId}?view=terminal`);
  await expect(page.getByTestId("page-thread")).toBeVisible();
  await expect(page.getByTestId("section-terminal")).toBeVisible();
  await expect(page.getByTestId("live-terminal")).toBeVisible();
}

/** Wait for the live attach to land — the badge reads "connected" and the
 *  connecting / no-terminal states are gone (NOT a blank pane). */
async function expectConnected(page: Page): Promise<void> {
  await expect(
    page.locator('[aria-label="connection status: connected"]'),
  ).toBeVisible({ timeout: 20_000 });
  await expect(page.getByTestId("live-terminal-no-terminal")).toHaveCount(0);
  await expect(page.getByTestId("live-terminal-connecting")).toHaveCount(0);
}

/** The rendered terminal text, read off xterm's accessible layer. */
async function terminalText(page: Page): Promise<string> {
  const host = page.getByTestId("live-terminal");
  return (await host.innerText()).replace(/ /g, " ");
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

test("acceptance #1 — open the terminal (real server) → live session + seeded scrollback (not blank)", async ({
  page,
}) => {
  await openTerminalView(page);

  // The live state is reached against the REAL sidecar — the WP-006 same-origin
  // default reaching the production sidecar with NO VITE_TERMINAL_WS_URL
  // configured (proves the production resolution path, not the no-op fallback).
  await expectConnected(page);

  // Scrollback rendered: the setup drove a REAL open+feed against the AF_UNIX
  // socket BEFORE the browser attached (the production host seeds NO banner — the
  // pre-seed is driven via a real write, matching production), so the snapshot
  // phase must render the token (the "render existing scrollback, not blank"
  // guarantee, acceptance #1).
  await expectTerminalContains(page, REAL_SCROLLBACK_TOKEN);
});

test("acceptance #2 — type a command → keystrokes reach the live session, output appears", async ({
  page,
}) => {
  await openTerminalView(page);
  await expectConnected(page);

  // Focus the terminal viewport and type the sentinel that makes the pty fake
  // child emit its deterministic PTY_PONG line (the two-way feed) — through the
  // REAL sidecar + REAL socket + REAL pty.
  const viewport = page.getByRole("region", { name: "Live terminal output" });
  await viewport.click();
  await page.keyboard.type("__PTY_PING__");
  await page.keyboard.press("Enter");

  await expectTerminalContains(page, "PTY_PONG");
});

test("acceptance #3 — close + reopen → session alive, scrollback catches up", async ({
  page,
}) => {
  await openTerminalView(page);
  await expectConnected(page);

  // Type a marker so it lands in the session's scrollback, then leave.
  const viewport = page.getByRole("region", { name: "Live terminal output" });
  await viewport.click();
  await page.keyboard.type("__PTY_PING__");
  await page.keyboard.press("Enter");
  await expectTerminalContains(page, "PTY_PONG");

  // "Close the terminal": navigate to the conversation view (unmount
  // <LiveTerminal/> → detach). Detach LEAVES THE SESSION RUNNING — the process +
  // scrollback survive on the host.
  await page.goto(`/c/${fx.changeId}?view=conversation`);
  await expect(page.getByTestId("section-conversation")).toBeVisible();
  await expect(page.getByTestId("live-terminal")).toHaveCount(0);

  // "Reopen": back to the Terminal view → a fresh attach against the REAL host.
  // The snapshot phase catches up with everything the session accumulated while
  // detached — nothing lost (the seeded token AND the PTY_PONG from before).
  await openTerminalView(page);
  await expectConnected(page);
  await expectTerminalContains(page, REAL_SCROLLBACK_TOKEN);
  await expectTerminalContains(page, "PTY_PONG");
});

test("acceptance #4 — a connection drives only its own change; cross-change attach refused", async () => {
  // Drive the REAL /terminal WS endpoint directly (a raw WS is the truthful way
  // to exercise the binding guard at the transport layer — the browser client
  // only ever speaks for its own mounted change, so a cross-change attempt has no
  // UI affordance; the guard is what protects against a hand-crafted client).
  //
  // The production host runs the binding guard ON (WP-001): a connection is bound
  // to the change `key` of its FIRST open; any later guarded method on a DIFFERENT
  // key is refused NOT_AUTHORIZED with ZERO foreign bytes. This complements the
  // WP-001 host unit test at the real transport layer (acceptance #4).
  const ws = new NodeWebSocket(`${fx.wsBaseUrl}/terminal`, {
    headers: { origin: fx.clientOrigin },
  });
  await new Promise<void>((resolve, reject) => {
    ws.once("open", () => resolve());
    ws.once("error", reject);
  });

  /** Send one NDJSON request and collect every response line for its id until a
   *  terminal line (end / error / unary reply) or a short quiet window. */
  function rpc(
    id: string,
    method: string,
    params: Record<string, unknown>,
    { stream = false }: { stream?: boolean } = {},
  ): Promise<Array<Record<string, unknown>>> {
    return new Promise((resolve) => {
      const lines: Array<Record<string, unknown>> = [];
      const onMessage = (data: NodeWebSocket.RawData): void => {
        for (const raw of data.toString().split("\n")) {
          const trimmed = raw.trim();
          if (!trimmed) continue;
          let obj: Record<string, unknown>;
          try {
            obj = JSON.parse(trimmed) as Record<string, unknown>;
          } catch {
            continue;
          }
          if (obj.id !== id) continue;
          lines.push(obj);
          // A unary reply or an error or an `end` terminates collection.
          const isError = obj.ok === false;
          const isEnd = obj.end === true;
          if (!stream || isError || isEnd) {
            ws.off("message", onMessage);
            resolve(lines);
            return;
          }
        }
      };
      ws.on("message", onMessage);
      ws.send(JSON.stringify({ id, method, params }));
      // Stream quiet-window safety net: if no terminal line lands, resolve with
      // whatever arrived (a guard refusal that yields zero lines must not hang).
      if (stream) {
        setTimeout(() => {
          ws.off("message", onMessage);
          resolve(lines);
        }, 4_000);
      }
    });
  }

  /** Decode the terminal bytes carried by a set of response lines. Raw PTY bytes
   *  ride in the NESTED `term.data` (base64) field per §2.13.1 — NOT a top-level
   *  `data` field. Concatenate every term chunk's decoded bytes. */
  function termBytes(lines: Array<Record<string, unknown>>): string {
    return lines
      .map((l) => {
        const term = l.term as { data?: unknown } | undefined;
        return typeof term?.data === "string"
          ? Buffer.from(term.data, "base64").toString()
          : "";
      })
      .join("");
  }

  try {
    // 1. open + attach for THIS change — binds the connection to fx.changeId and
    //    must yield the seeded token (proving the bound path actually works).
    const openOwn = await rpc("1", "open", { key: fx.changeId });
    expect(openOwn.at(-1)?.ok, JSON.stringify(openOwn)).toBe(true);

    const attachOwn = await rpc(
      "2",
      "attach",
      { key: fx.changeId },
      { stream: true },
    );
    expect(
      termBytes(attachOwn),
      "own-change attach should replay the seeded scrollback",
    ).toContain(REAL_SCROLLBACK_TOKEN);

    // 2. attach for a DIFFERENT change on the SAME (bound) connection → refused.
    const foreignChange = "01FOREIGNCHANGE000000000000";
    const attachForeign = await rpc(
      "3",
      "attach",
      { key: foreignChange },
      { stream: true },
    );

    // The guard refuses: an error line (NOT_AUTHORIZED), and crucially ZERO bytes
    // of the foreign change's terminal output (no `term` line carrying data).
    const refused = attachForeign.some((l) => l.ok === false);
    expect(
      refused,
      `expected a refusal, got ${JSON.stringify(attachForeign)}`,
    ).toBe(true);
    expect(
      termBytes(attachForeign),
      "cross-change attach must leak ZERO foreign bytes",
    ).toBe("");
  } finally {
    ws.close();
  }
});

test("acceptance #5 — read surfaces + the chat path are unaffected; no session on a read view", async ({
  page,
}) => {
  // The change's default view is the conversation (chat) surface — present and
  // mounted, UNAFFECTED by the terminal wiring (founder independence directive:
  // this asserts chat still works, NOT that the terminal depends on it).
  await page.goto(`/c/${fx.changeId}?view=conversation`);
  await expect(page.getByTestId("section-conversation")).toBeVisible();
  await expect(page.getByTestId("composer")).toBeVisible();
  // No terminal session is mounted on the chat view.
  await expect(page.getByTestId("live-terminal")).toHaveCount(0);

  // A read-only surface (the contract Preview view) renders with NO live-terminal
  // mount — no attach, no session start on a read view (ADR-010: the terminal is
  // the ONLY new write/attach path; read surfaces stay read-only). The preview
  // panel chrome mounts from the already-loaded change data, so this asserts the
  // read surface independently of any heavier per-view fetch.
  await page.goto(`/c/${fx.changeId}?view=preview`);
  await expect(page.getByTestId("section-preview")).toBeVisible();
  await expect(page.getByTestId("live-terminal")).toHaveCount(0);
});
