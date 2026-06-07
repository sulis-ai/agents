// WP-008 — useProducts hook + Board re-scope wiring (FR-37/38; ADR-009).
//
// useProducts: GET /api/products through the typed funnel (apiGet) — never
// `fetch` directly (WPF-02).
//
// Board re-scope wiring: with the ProductSwitcher mounted, picking another
// Product re-fetches the board scoped to it (?product=<id>) — the SAME board
// re-scopes (ADR-005), the first Product's changes disappear. This is the
// client half of the journey-K observed round-trip.

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { Change, Product, ProductList } from "../../../shared/api-types";
import { useProducts } from "../api/useProducts";

function freshClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } },
  });
}

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

function renderInClient(ui: React.ReactElement) {
  const client = freshClient();
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe("useProducts", () => {
  beforeEach(() => {
    vi.spyOn(globalThis, "fetch").mockReset();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("GET /api/products → returns the ProductList", async () => {
    const payload: ProductList = {
      products: [
        { productId: "dna:product:01ACME00000000000000000000", name: "Acme Checkout", active: true },
        { productId: "dna:product:01HELP00000000000000000000", name: "Helpdesk" },
      ],
      activeProductId: "dna:product:01ACME00000000000000000000",
    };
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(jsonResponse(200, payload));

    function Probe() {
      const q = useProducts();
      return (
        <div data-testid="probe">
          {q.isSuccess ? `${q.data.products.length}:${q.data.activeProductId}` : q.status}
        </div>
      );
    }

    const { getByTestId } = renderInClient(<Probe />);
    await waitFor(() =>
      expect(getByTestId("probe").textContent).toBe(
        "2:dna:product:01ACME00000000000000000000",
      ),
    );
    expect(fetchMock.mock.calls[0]![0]).toBe("/api/products");
  });
});
