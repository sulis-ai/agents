// WP-006 — the change-nav product property (ADR-002, SUBSTITUTE-Replace).
//
// The raw native <select> (ProductPicker) is replaced by a labelled "Product"
// property in the change's left nav, rendered via the shared <ProductControl
// mode="assign"> primitive (WP-002). This file pins the PLACEMENT behaviour:
//   - the assigned trigger shows the monogram chip + product name + chevron;
//   - the unassigned trigger shows "＋ Add to a product" with an accessible name;
//   - picking a product commits via useAssignChangeProduct (PUT) → chip swaps in
//     place + a "Saved" tick announce;
//   - the in-flight request shows "Saving…";
//   - "Remove from product" commits via useClearChangeProduct (DELETE) → the
//     chip returns to the "＋ Add" state;
//   - ChangeNav no longer renders a native <select> (the raw picker is gone).
//
// The primitive's own a11y model (axe, keyboard, aria-live, ≥44px) is exercised
// on the primitive (ProductControl.axe.test.tsx) + at this placement
// (ChangeNavProduct.axe.test.tsx). Here we pin the wiring + the two scenarios
// "Assign an unassigned change to a product" and "Remove a change from a
// product (un-assign)". Network is fetch-mocked through the typed funnel —
// the placement injects the hooks at the edge, never calling fetch directly.

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, fireEvent, waitFor, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

import { ChangeProductProperty } from "../components/ChangeProductProperty";
import { ChangeNav } from "../components/ChangeNav";
import type { Change } from "../../../shared/api-types";

const ACME = "dna:product:01ACME00000000000000000000";
const HELP = "dna:product:01HELP00000000000000000000";
const CHANGE_ID = "01CHG0000000000000000000AA";

function jsonRes(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "content-type": "application/json" },
  });
}

function client() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } },
  });
}

function wrap(ui: ReactNode) {
  return render(<QueryClientProvider client={client()}>{ui}</QueryClientProvider>);
}

/** A products feed mock; assign/clear default to a resolved write. */
function mockFetch(opts: {
  products?: { productId: string; name: string }[];
  onWrite?: (url: string, init?: RequestInit) => Response | Promise<Response>;
} = {}) {
  const products = opts.products ?? [
    { productId: ACME, name: "Acme Checkout" },
    { productId: HELP, name: "Helpdesk" },
  ];
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (url, init) => {
    const u = String(url);
    if (u.includes("/api/products")) {
      return jsonRes({ products, activeProductId: null });
    }
    if (u.includes(`/api/changes/`) && init?.method === "PUT") {
      if (opts.onWrite) return opts.onWrite(u, init as RequestInit);
      return jsonRes({ ok: true, id: `dna:change:${CHANGE_ID}`, forProduct: HELP });
    }
    if (u.includes(`/api/changes/`) && init?.method === "DELETE") {
      if (opts.onWrite) return opts.onWrite(u, init as RequestInit);
      return jsonRes({ ok: true, id: `dna:change:${CHANGE_ID}`, forProduct: null });
    }
    return jsonRes({});
  });
}

function change(overrides: Partial<Change> = {}): Change {
  return {
    changeId: CHANGE_ID,
    handle: "CH-01CHG",
    slug: "refine-product",
    primitive: "refactor",
    branch: "feat/x",
    worktreePath: "/tmp/wt",
    intent: "Refine the product experience",
    baseBranch: "main",
    baseSha: "abc123",
    createdAt: "2026-06-16T11:00:00Z",
    updatedAt: "2026-06-16T11:55:00Z",
    stage: "implement",
    liveness: { status: "unknown", reason: "no session" },
    needsAttention: { flagged: false, reason: null },
    health: { state: "unknown", reason: "too early to tell" },
    lastActivityAt: null,
    ...overrides,
  };
}

describe("<ChangeProductProperty> — change-nav product property (ADR-002)", () => {
  beforeEach(() => {
    vi.spyOn(globalThis, "fetch").mockReset();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows the assigned product's monogram chip + name + chevron when assigned", async () => {
    mockFetch();
    const { findByTestId } = wrap(
      <ChangeProductProperty changeId={CHANGE_ID} currentProductId={ACME} />,
    );
    const trigger = await findByTestId("product-control-trigger");
    await waitFor(() => expect(trigger.textContent).toContain("Acme Checkout"));
    // The neutral two-letter monogram tile (chrome, not colour-alone).
    expect(trigger.querySelector("[data-glyph='monogram']")?.textContent).toBe("AC");
    // A chevron is present on the assigned trigger.
    expect(trigger.querySelector("svg")).toBeTruthy();
  });

  it("shows the '＋ Add to a product' trigger with an accessible name when unassigned", async () => {
    mockFetch();
    const { findByTestId } = wrap(
      <ChangeProductProperty changeId={CHANGE_ID} currentProductId={null} />,
    );
    const trigger = await findByTestId("product-control-trigger");
    expect(trigger.textContent).toMatch(/add to a product/i);
    // The accessible name survives even when the visible text folds at narrow
    // width (triggerLabel carried through the primitive).
    expect(trigger.getAttribute("aria-label")).toMatch(/product/i);
    // #378 — never colour alone: the unassigned chip leads with the signed
    // mockup's inline "＋" icon (data-glyph="plus") + a dashed chip border.
    expect(trigger.querySelector("[data-glyph='plus']")).toBeTruthy();
  });

  it("commits an assignment via PUT when a product is picked (assign scenario)", async () => {
    const fetchMock = mockFetch();
    const { findByTestId, getByTestId } = wrap(
      <ChangeProductProperty changeId={CHANGE_ID} currentProductId={null} />,
    );
    fireEvent.click(await findByTestId("product-control-trigger"));
    const menu = getByTestId("product-control-menu");
    fireEvent.click(within(menu).getByText("Helpdesk"));
    await waitFor(() => {
      const put = fetchMock.mock.calls.find(
        ([u, i]) =>
          String(u).includes(`/api/changes/${CHANGE_ID}/product`) &&
          (i as RequestInit | undefined)?.method === "PUT",
      );
      expect(put).toBeTruthy();
    });
  });

  it("swaps the chip in place + announces 'Saved' after a successful assign", async () => {
    mockFetch();
    const { findByTestId, getByTestId, rerender } = wrap(
      <ChangeProductProperty changeId={CHANGE_ID} currentProductId={null} />,
    );
    fireEvent.click(await findByTestId("product-control-trigger"));
    fireEvent.click(within(getByTestId("product-control-menu")).getByText("Helpdesk"));
    // The "Saved" tick announces in the live region after the write resolves.
    await waitFor(() =>
      expect(getByTestId("product-control-live").textContent).toMatch(/saved/i),
    );
    // The parent re-renders with the new assignment (board feed invalidation →
    // refetch in the live app) — the chip swaps to the new product in place.
    rerender(
      <QueryClientProvider client={client()}>
        <ChangeProductProperty changeId={CHANGE_ID} currentProductId={HELP} />
      </QueryClientProvider>,
    );
    await waitFor(() =>
      expect(getByTestId("product-control-trigger").textContent).toContain(
        "Helpdesk",
      ),
    );
  });

  it("shows 'Saving…' while the assign write is in flight", async () => {
    // Hold the write open so the in-flight state is observable.
    let resolveWrite: (r: Response) => void = () => {};
    const pending = new Promise<Response>((res) => {
      resolveWrite = res;
    });
    mockFetch({ onWrite: () => pending });
    const { findByTestId, getByTestId } = wrap(
      <ChangeProductProperty changeId={CHANGE_ID} currentProductId={null} />,
    );
    fireEvent.click(await findByTestId("product-control-trigger"));
    fireEvent.click(within(getByTestId("product-control-menu")).getByText("Helpdesk"));
    await waitFor(() =>
      expect(getByTestId("product-control-live").textContent).toMatch(/saving/i),
    );
    resolveWrite(jsonRes({ ok: true, id: `dna:change:${CHANGE_ID}`, forProduct: HELP }));
  });

  it("commits an un-assign via DELETE from 'Remove from product' (un-assign scenario)", async () => {
    const fetchMock = mockFetch();
    const { findByTestId, getByTestId } = wrap(
      <ChangeProductProperty changeId={CHANGE_ID} currentProductId={ACME} />,
    );
    fireEvent.click(await findByTestId("product-control-trigger"));
    const menu = getByTestId("product-control-menu");
    fireEvent.click(within(menu).getByText(/remove from product/i));
    await waitFor(() => {
      const del = fetchMock.mock.calls.find(
        ([u, i]) =>
          String(u).includes(`/api/changes/${CHANGE_ID}/product`) &&
          (i as RequestInit | undefined)?.method === "DELETE",
      );
      expect(del).toBeTruthy();
    });
  });

  it("returns to the '＋ Add to a product' state after a successful un-assign", async () => {
    mockFetch();
    const { findByTestId, getByTestId, rerender } = wrap(
      <ChangeProductProperty changeId={CHANGE_ID} currentProductId={ACME} />,
    );
    fireEvent.click(await findByTestId("product-control-trigger"));
    fireEvent.click(
      within(getByTestId("product-control-menu")).getByText(/remove from product/i),
    );
    await waitFor(() =>
      expect(getByTestId("product-control-live").textContent).toMatch(/saved/i),
    );
    // The live app re-renders with forProduct cleared (invalidation → refetch).
    rerender(
      <QueryClientProvider client={client()}>
        <ChangeProductProperty changeId={CHANGE_ID} currentProductId={null} />
      </QueryClientProvider>,
    );
    await waitFor(() =>
      expect(getByTestId("product-control-trigger").textContent).toMatch(
        /add to a product/i,
      ),
    );
  });

  it("renders nothing when there are no products to assign to", async () => {
    mockFetch({ products: [] });
    const { queryByTestId } = wrap(
      <ChangeProductProperty changeId={CHANGE_ID} currentProductId={null} />,
    );
    await waitFor(() =>
      expect(queryByTestId("product-control-trigger")).toBeNull(),
    );
  });
});

describe("<ChangeNav> — product property replaces the raw <select>", () => {
  beforeEach(() => {
    vi.spyOn(globalThis, "fetch").mockReset();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the ProductControl property and NO native <select>", async () => {
    mockFetch();
    const { container, findByTestId } = wrap(
      <ChangeNav
        change={change({ forProduct: ACME })}
        activeView="conversation"
        onSelectView={() => {}}
      />,
    );
    // The shared primitive's trigger is present...
    await findByTestId("product-control-trigger");
    // ...and the old raw <select> picker is gone entirely.
    expect(container.querySelector("select")).toBeNull();
    expect(container.querySelector("[data-testid='change-product-picker']")).toBeNull();
  });

  it("labels the property with a 'Product' section heading at the identity position", async () => {
    mockFetch();
    const { findByText } = wrap(
      <ChangeNav
        change={change({ forProduct: ACME })}
        activeView="conversation"
        onSelectView={() => {}}
      />,
    );
    await findByText(/^product$/i);
  });
});
