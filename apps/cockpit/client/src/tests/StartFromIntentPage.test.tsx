// CH-01KTPF — <StartFromIntentPage /> must hand the EFFECTIVE active product
// to <StartFromIntent />, never an empty id.
//
// The bug this pins: the page read only the client-side useActiveProduct()
// context, which defaults to `null` until the founder explicitly switches
// product. On null it passed `productId=""` downstream — so even with a real
// product set up (and shown active in the top bar, which falls back to the
// server's activeProductId), the start request carried "" and the server
// couldn't resolve the Project repo → 502 "I couldn't find that product's
// repository". The page must apply the SAME fallback the top bar does
// (client activeProductId ?? server activeProductId) so the start always
// carries a real id.

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";

import { ActiveProductProvider } from "../api/activeProduct";
import { freshQueryClient } from "./_renderWithClient";

// Capture the productId the page hands to <StartFromIntent />.
vi.mock("../components/StartFromIntent", () => ({
  StartFromIntent: ({ productId }: { productId: string }) => (
    <div data-testid="sfi-productid">{productId}</div>
  ),
}));

// Control the server's active product (the /api/products read).
const mockUseProducts = vi.fn();
vi.mock("../api/useProducts", () => ({
  useProducts: () => mockUseProducts(),
}));

import { StartFromIntentPage } from "../pages/StartFromIntentPage";

function renderPage(opts: {
  clientActive?: string | null;
  serverActive: string | null;
}) {
  mockUseProducts.mockReturnValue({
    data:
      opts.serverActive !== null
        ? {
            products: [
              { productId: opts.serverActive, name: "P", active: true },
            ],
            activeProductId: opts.serverActive,
          }
        : { products: [], activeProductId: null },
  });
  return render(
    <QueryClientProvider client={freshQueryClient()}>
      <MemoryRouter>
        <ActiveProductProvider
          initialActiveProductId={opts.clientActive ?? null}
        >
          <StartFromIntentPage />
        </ActiveProductProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function passedProductId(): string {
  return screen.getByTestId("sfi-productid").textContent ?? "";
}

describe("StartFromIntentPage — effective active product", () => {
  beforeEach(() => mockUseProducts.mockReset());

  it("falls back to the server's active product when the client context is null (the 502 bug)", () => {
    renderPage({ clientActive: null, serverActive: "dna:product:SERVER" });
    expect(passedProductId()).toBe("dna:product:SERVER");
  });

  it("prefers an explicitly-selected client product over the server default", () => {
    renderPage({
      clientActive: "dna:product:CLIENT",
      serverActive: "dna:product:SERVER",
    });
    expect(passedProductId()).toBe("dna:product:CLIENT");
  });

  it("passes empty only when neither client nor server has a product", () => {
    renderPage({ clientActive: null, serverActive: null });
    expect(passedProductId()).toBe("");
  });
});
