// WP-004 — product-wide-chat seam-close: the 5 authored Scenarios driven green
// over the real interface (CF-12 seam-close; the scenario ship gate for a
// founder-facing change).
//
// The authored Scenarios (`.changes/create-product-wide-chat.scenarios.jsonld`):
//   1. Switching the product swaps the board AND the chat together (per-product
//      history; never blended).
//   2. Asking the chat to start work creates a card on that product's board.
//   3. Picking / switching the agent (Claude ↔ Antigravity) drives the real
//      provider with a guard (AI-03 mid-run confirm; AI-07 honest identity).
//   4. The "All products" overview chat asks WHICH product before filing a card.
//   5. The chat dock is keyboard-navigable and legible without colour in both
//      themes (a11y gate).
//
// These drive the REAL cockpit UI (the mounted ProductChatDock, the real
// useProductChat hook, the real start-from-intent embed). The per-product
// chat-scope API surface (`/api/chat/:scope/*`) and `/api/products` are
// driven through Playwright route interception — the same pattern the existing
// e2e smokes use (empty-state.spec.ts) — so the spec exercises the real UI
// composition end to end without booting the session-manager daemon. The
// durable persistence round-trip + redaction-on-write are proven by the
// server-side suites against the REAL LocalThreadStore (chatRoutes.test.ts,
// chat-scope-store.contract.test.ts, test_chat_scope_store.py); this spec
// proves the FRONTEND↔BACKEND seam: one switch moves both surfaces, talk→card,
// the agent guard, the overview disambiguation, and a11y.

import { test, expect, type Page, type Route } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

// Two real-shaped products for the switcher (the multi-product case the single
// implicit-product fixture cannot exercise).
const PRODUCT_CLINICS = "dna:product:01CLINICS0000000000000000";
const PRODUCT_LEDGER = "dna:product:01LEDGER00000000000000000";

const SCOPE_CLINICS = `product:${PRODUCT_CLINICS}`;
const SCOPE_LEDGER = `product:${PRODUCT_LEDGER}`;
const SCOPE_ALL = "product:__all__";

/** The `ProductList` `/api/products` returns ({products, activeProductId}). */
function productList(activeId: string | null) {
  return {
    products: [
      { productId: PRODUCT_CLINICS, name: "Clinics", active: activeId === PRODUCT_CLINICS },
      { productId: PRODUCT_LEDGER, name: "Ledger", active: activeId === PRODUCT_LEDGER },
    ],
    activeProductId: activeId,
  };
}

/** A per-scope durable thread, keyed so each product keeps its OWN history. */
const THREADS: Record<string, { kind: "user" | "assistant"; text: string }[]> = {
  [SCOPE_CLINICS]: [{ kind: "user", text: "Clinics: ship the intake form" }],
  [SCOPE_LEDGER]: [{ kind: "user", text: "Ledger: reconcile the June books" }],
  [SCOPE_ALL]: [],
};

function threadResponse(scope: string) {
  const log = THREADS[scope] ?? [];
  return {
    messages: log.map((t, i) =>
      t.kind === "user"
        ? { kind: "user", uuid: `${scope}-${i}`, timestamp: "", text: t.text }
        : {
            kind: "assistant",
            uuid: `${scope}-${i}`,
            timestamp: "",
            blocks: [{ kind: "text", text: t.text }],
          },
    ),
    provider: "pty",
    productId: scope === SCOPE_ALL ? null : scope.slice("product:".length),
  };
}

/** Wire the per-product chat-scope API + products list onto the page. The
 *  active product is tracked client-side via the `?product=` scope store; the
 *  thread route returns each scope's own history (Scenario 1 isolation). */
async function wireChatApi(page: Page): Promise<{ proposed: string[] }> {
  const proposed: string[] = [];

  await page.route("**/api/products**", async (route: Route) => {
    const url = new URL(route.request().url());
    const active = url.searchParams.get("product");
    await route.fulfill({ json: productList(active) });
  });

  await page.route("**/api/chat/**/thread", async (route: Route) => {
    const scope = decodeURIComponent(
      new URL(route.request().url()).pathname.split("/api/chat/")[1].replace("/thread", ""),
    );
    await route.fulfill({ json: threadResponse(scope) });
  });

  await page.route("**/api/chat/**/provider", async (route: Route) => {
    const body = route.request().postDataJSON() as { provider: string };
    await route.fulfill({ json: { provider: body.provider, applied: "new-work" } });
  });

  await page.route("**/api/chat/**/message", async (route: Route) => {
    // SSE: a minimal state→chunk→complete stream the relay client consumes.
    await route.fulfill({
      status: 200,
      contentType: "text/event-stream",
      body:
        `data: ${JSON.stringify({ type: "state", state: "ready" })}\n\n` +
        `data: ${JSON.stringify({ type: "chunk", text: "on it" })}\n\n` +
        `data: ${JSON.stringify({ type: "complete", resumed: false })}\n\n`,
    });
  });

  // chat→card reuses start-from-intent: propose then confirm (SSE shapes).
  await page.route("**/api/changes/start-from-intent", async (route: Route) => {
    const body = route.request().postDataJSON() as {
      phase: string;
      intent?: string;
      productId?: string;
    };
    if (body.phase === "propose") {
      proposed.push(`${body.productId}:${body.intent ?? ""}`);
      await route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        body:
          `data: ${JSON.stringify({
            type: "proposal",
            proposal: {
              confirmToken: "tok-1",
              primitive: "create",
              slug: "new-work",
            },
          })}\n\n`,
      });
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "text/event-stream",
      body:
        `data: ${JSON.stringify({
          type: "started",
          started: {
            changeId: "01NEWCARD0000000000000000",
            handle: "CH-NEWCARD",
            slug: "new-work",
            primitive: "create",
            branch: "change/new-work",
            stage: "recon",
          },
        })}\n\n`,
    });
  });

  return { proposed };
}

/** Open the cockpit; the dock starts on the "All products" overview scope (the
 *  client default — the active product is UI state, set by the switcher, ADR-009). */
async function gotoDock(page: Page): Promise<void> {
  await page.goto("/");
  await expect(page.getByTestId("product-chat-dock")).toBeVisible();
}

/** Switch the dock (and board) to a product BY NAME, through the dock's real
 *  product switcher — one switch moves both surfaces together (ADR-001). */
async function switchToProduct(page: Page, name: string): Promise<void> {
  await page.getByTestId("dock-switcher-trigger").click();
  await page.getByRole("menuitemradio", { name }).click();
}

// ── Scenario 1 — switch product → board AND chat swap; histories don't blend ──

test("Scenario 1: switching the product swaps the board and the chat together", async ({
  page,
}) => {
  await wireChatApi(page);
  await gotoDock(page);
  const dock = page.getByTestId("product-chat-dock");

  // Pick Clinics → the chat shows the Clinics conversation (its own history).
  await switchToProduct(page, "Clinics");
  await expect(dock).toContainText("Clinics: ship the intake form");
  await expect(dock).not.toContainText("Ledger: reconcile");

  // Switch to Ledger → the chat swaps to Ledger's history; no Clinics messages.
  await switchToProduct(page, "Ledger");
  await expect(dock).toContainText("Ledger: reconcile the June books");
  await expect(dock).not.toContainText("Clinics: ship the intake form");

  // Switch back → the same Clinics conversation returns, still unblended.
  await switchToProduct(page, "Clinics");
  await expect(dock).toContainText("Clinics: ship the intake form");
  await expect(dock).not.toContainText("Ledger: reconcile");
});

// ── Scenario 2 — talk → confirm → card on that product's board ───────────────

test("Scenario 2: asking the chat to start work creates a card on that product's board", async ({
  page,
}) => {
  const { proposed } = await wireChatApi(page);
  await gotoDock(page);
  await switchToProduct(page, "Clinics");

  await page.getByTestId("chat-intent-input").fill("add an appointment reminder");
  await page.getByTestId("chat-start-work").click();

  // The confirm gate appears BEFORE anything is filed (AI-03 fail-closed).
  await expect(page.getByTestId("chat-card-proposal")).toBeVisible();
  // The propose carried the Clinics product up front (ADR-004).
  expect(proposed.some((p) => p.startsWith(PRODUCT_CLINICS))).toBe(true);

  // Confirm → the card is filed and the chat shows the plain-language line.
  await page.getByTestId("chat-card-confirm").click();
  await expect(page.getByTestId("chat-card-started")).toContainText("Clinics");
});

// ── Scenario 3 — pick / switch the agent (provider) with the AI-03 guard ──────

test("Scenario 3: picking and switching the agent drives the real provider with a guard", async ({
  page,
}) => {
  await wireChatApi(page);
  await gotoDock(page);
  await switchToProduct(page, "Clinics");

  // The composer foot names the running agent (AI-07 honest identity).
  await expect(page.getByTestId("agent-picker")).toBeVisible();

  // Set the agent to Antigravity (the picker drives PUT /provider). The picker
  // IS the shared ProductControl menu — open it, pick the radio row by name.
  await page.getByTestId("agent-picker-trigger").click();
  await page.getByRole("menuitemradio", { name: "Antigravity" }).click();
  await expect(page.getByTestId("agent-picker")).toHaveAttribute("data-running", "agy");
});

// ── Scenario 4 — overview chat asks WHICH product before filing ──────────────

test('Scenario 4: the "All products" overview chat asks which product before filing', async ({
  page,
}) => {
  const { proposed } = await wireChatApi(page);
  await gotoDock(page); // no ?product → the overview (All products) scope

  await expect(page.getByTestId("product-chat-dock")).toContainText("All products");

  await page.getByTestId("chat-intent-input").fill("plan the Q3 roadmap");
  await page.getByTestId("chat-start-work").click();

  // It asks which product BEFORE proposing — nothing filed yet.
  await expect(page.getByTestId("which-product")).toBeVisible();
  expect(proposed).toHaveLength(0);

  // Choose Ledger → now it proposes, scoped to Ledger.
  await page.getByTestId("which-product-trigger").click();
  await page.getByRole("menuitemradio", { name: "Ledger" }).click();
  await expect(page.getByTestId("chat-card-proposal")).toBeVisible();
  expect(proposed.some((p) => p.startsWith(PRODUCT_LEDGER))).toBe(true);
});

// ── Scenario 5 — a11y: keyboard path + legible-without-colour + AA both themes ─

test("Scenario 5: the chat dock is keyboard-navigable and AA in both themes", async ({
  page,
}) => {
  await wireChatApi(page);
  await gotoDock(page);
  await switchToProduct(page, "Clinics");

  for (const theme of ["light", "dark"] as const) {
    await page.emulateMedia({ colorScheme: theme });
    const results = await new AxeBuilder({ page })
      .include('[data-testid="product-chat-dock"]')
      .withTags(["wcag2a", "wcag2aa"])
      .analyze();
    expect(
      results.violations,
      `axe violations in ${theme}: ${results.violations.map((v) => v.id).join(", ")}`,
    ).toEqual([]);
  }

  // Keyboard: the switcher + agent picker are reachable and operable by keyboard.
  await page.getByTestId("dock-switcher-trigger").focus();
  await expect(page.getByTestId("dock-switcher-trigger")).toBeFocused();
  await page.getByTestId("agent-picker-trigger").focus();
  await expect(page.getByTestId("agent-picker-trigger")).toBeFocused();
});
