// WP-003 — chat→card; the overview chat asks which product first (ADR-004).
//
// Per-product chat already knows the product (the dock's chat_scope), so "start
// work" calls propose() with that productId directly. The overview chat
// (product:__all__) has no product, so it MUST ask which product the new work
// belongs to BEFORE propose — it never files a card without a product. Both
// paths then drive the SAME start-from-intent propose→confirm lifecycle (one
// source of truth, no second creation path).

import { describe, it, expect, vi, afterEach } from "vitest";
import { within, fireEvent, waitFor } from "@testing-library/react";
import type {
  StartFromIntentRequest,
  StartFromIntentStreamEvent,
} from "../../../shared/api-types";
import { ProductChatDock } from "../components/ProductChatDock";
import { renderWithClient } from "./_renderWithClient";
import { ActiveProductProvider } from "../api/activeProduct";

const CLINICS = "dna:product:01CLINIC0000000000000000000";
const BAKERY = "dna:product:01BAKERY0000000000000000000";

const PRODUCTS = [
  { productId: CLINICS, name: "Clinics", active: true },
  { productId: BAKERY, name: "Bakery Ops" },
];

const PROPOSAL: StartFromIntentStreamEvent[] = [
  { type: "state", state: "proposing" },
  { type: "proposal", proposal: { confirmToken: "tok-1", primitive: "fix", slug: "x" } },
];

function makeDock(initialScope: string | null) {
  const calls: StartFromIntentRequest[] = [];
  const streamStartFromIntent = vi.fn(
    async (req: StartFromIntentRequest, onEvent: (e: StartFromIntentStreamEvent) => void) => {
      calls.push(req);
      if (req.phase === "propose") for (const e of PROPOSAL) onEvent(e);
    },
  );
  const utils = renderWithClient(
    <ActiveProductProvider initialActiveProductId={initialScope}>
      <ProductChatDock
        products={PRODUCTS}
        fetchChatThread={async () => ({ messages: [], provider: "pty", productId: initialScope })}
        streamProductChat={async () => {}}
        putChatProvider={async () => ({ provider: "pty", applied: "new-work" })}
        streamStartFromIntent={streamStartFromIntent}
      />
    </ActiveProductProvider>,
  );
  return { ...utils, calls, streamStartFromIntent };
}

function startWork(getByTestId: (id: string) => HTMLElement, intent: string) {
  fireEvent.change(getByTestId("chat-intent-input"), { target: { value: intent } });
  fireEvent.click(getByTestId("chat-start-work"));
}

afterEach(() => {
  delete document.documentElement.dataset.theme;
});

describe("chat→card · per-product chat skips the which-product ask", () => {
  it("calls propose with the active productId directly (no disambiguation)", async () => {
    const { getByTestId, queryByTestId, calls } = makeDock(CLINICS);
    startWork(getByTestId, "fix the booking bug");

    // No "which product?" menu — the product is already known.
    expect(queryByTestId("which-product-menu")).toBeNull();
    await waitFor(() => expect(calls.some((c) => c.phase === "propose")).toBe(true));
    const propose = calls.find((c) => c.phase === "propose")!;
    expect(propose.productId).toBe(CLINICS);
  });
});

describe("chat→card · overview chat asks which product before filing", () => {
  it("shows the which-product chooser and does NOT propose until a product is chosen", async () => {
    // initialActiveProductId null === the All-products overview scope.
    const { getByTestId, calls } = makeDock(null);
    startWork(getByTestId, "set up onboarding emails");

    // The overview chat asks which product before any propose fires.
    expect(getByTestId("which-product")).toBeTruthy();
    expect(calls.some((c) => c.phase === "propose")).toBe(false);
  });

  it("after picking a product, proposes with THAT productId", async () => {
    const { getByTestId, calls } = makeDock(null);
    startWork(getByTestId, "set up onboarding emails");

    // Open the ONE menu primitive placed under the which-product home, pick Bakery.
    fireEvent.click(getByTestId("which-product-trigger"));
    const menu = getByTestId("which-product-menu");
    const bakery = within(menu)
      .getAllByRole("menuitemradio")
      .find((r) => /bakery/i.test(r.getAttribute("aria-label") ?? r.textContent ?? ""))!;
    fireEvent.click(bakery);

    await waitFor(() => expect(calls.some((c) => c.phase === "propose")).toBe(true));
    const propose = calls.find((c) => c.phase === "propose")!;
    expect(propose.productId).toBe(BAKERY);
  });
});
