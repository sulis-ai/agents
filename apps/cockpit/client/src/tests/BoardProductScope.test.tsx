// WP-008 — Board re-scopes to the active Product (the client round-trip;
// FR-37/38, UC-11, ADR-005/009).
//
// With the ActiveProductProvider supplying an active Product, the board's
// change fetch is scoped to it (?product=<id>). Switching the active Product
// re-fetches the SAME board scoped to the new Product — the first Product's
// changes disappear, only the second's remain (the journey-K observed
// round-trip, driven here in the component test; the OBSERVED gate drives it
// in the running app with two seeded Products).
//
// Data is fetched through the typed funnel (apiGet) — never `fetch` in the
// component (WPF-02); the test drives the real hooks against mocked global
// fetch.

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, waitFor, within, fireEvent } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { Change } from "../../../shared/api-types";
import type { Product } from "../../../shared/api-types";
import { Board } from "../pages/Board";
import { ActiveProductProvider, useActiveProduct } from "../api/activeProduct";
import { ProductSwitcher } from "../components/ProductSwitcher";

const ACME = "dna:product:01ACME00000000000000000000";
const HELP = "dna:product:01HELP00000000000000000000";

function makeChange(overrides: Partial<Change> = {}): Change {
  return {
    changeId: "01ABC",
    handle: "CH-01ABC",
    slug: "fix-thing",
    primitive: "fix",
    branch: "fix/thing",
    worktreePath: "/tmp/worktree",
    intent: "Fix the broken thing",
    baseBranch: "main",
    baseSha: "abc123",
    createdAt: "2026-05-26T11:00:00Z",
    updatedAt: "2026-05-26T11:55:00Z",
    stage: "implement",
    liveness: { status: "unknown", reason: "no session" },
    ...overrides,
  };
}

function freshClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, refetchOnWindowFocus: false, staleTime: 0 },
    },
  });
}

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

function renderBoardWithProduct(client: QueryClient, activeProductId: string) {
  return render(
    <QueryClientProvider client={client}>
      <ActiveProductProvider initialActiveProductId={activeProductId}>
        <MemoryRouter initialEntries={["/"]}>
          <Routes>
            <Route path="/" element={<Board />} />
          </Routes>
        </MemoryRouter>
      </ActiveProductProvider>
    </QueryClientProvider>,
  );
}

describe("Board re-scopes to the active Product (FR-37)", () => {
  beforeEach(() => {
    vi.spyOn(globalThis, "fetch").mockReset();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("fetches the board scoped to the active Product (?product=<id>)", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(jsonResponse(200, [makeChange({ changeId: "01A1", intent: "acme work" })]));

    const { getByTestId } = renderBoardWithProduct(freshClient(), ACME);
    await waitFor(() => expect(getByTestId("board")).toBeInTheDocument());

    const url = fetchMock.mock.calls[0]![0] as string;
    expect(url).toContain("/api/changes");
    expect(url).toContain(`product=${encodeURIComponent(ACME)}`);
  });

  it("re-scopes when the founder picks another Product in the switcher — the board re-fetches and the first Product's changes disappear (the journey-K round-trip)", async () => {
    // Acme returns one change; Helpdesk returns a DIFFERENT one. Picking
    // Helpdesk in the switcher re-scopes the SAME board to it (ADR-005).
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
      const url = String(input);
      if (url.includes(encodeURIComponent(HELP))) {
        return Promise.resolve(jsonResponse(200, [makeChange({ changeId: "01H1", intent: "help work" })]));
      }
      return Promise.resolve(jsonResponse(200, [makeChange({ changeId: "01A1", intent: "acme work" })]));
    });

    const products: Product[] = [
      { productId: ACME, name: "Acme Checkout", active: true },
      { productId: HELP, name: "Helpdesk" },
    ];

    // A harness that wires the real switcher to the real board through the
    // active-Product context (the production wiring): onSelect updates the
    // scope, the board re-fetches.
    function Harness() {
      const { activeProductId, setActiveProductId } = useActiveProduct();
      return (
        <>
          <ProductSwitcher
            products={products}
            activeProductId={activeProductId}
            onSelect={setActiveProductId}
          />
          <Board />
        </>
      );
    }

    const { getByTestId } = render(
      <QueryClientProvider client={freshClient()}>
        <ActiveProductProvider initialActiveProductId={ACME}>
          <MemoryRouter initialEntries={["/"]}>
            <Routes>
              <Route path="/" element={<Harness />} />
            </Routes>
          </MemoryRouter>
        </ActiveProductProvider>
      </QueryClientProvider>,
    );

    await waitFor(() =>
      expect(within(getByTestId("board")).getByText("acme work")).toBeInTheDocument(),
    );

    // Pick Helpdesk in the switcher — the switch.
    fireEvent.click(getByTestId("product-switcher-trigger"));
    fireEvent.click(
      within(getByTestId("product-switcher-menu")).getByText("Helpdesk"),
    );

    await waitFor(() =>
      expect(within(getByTestId("board")).getByText("help work")).toBeInTheDocument(),
    );
    // The first Product's change disappears (FR-37 — no other Product's change appears).
    expect(within(getByTestId("board")).queryByText("acme work")).not.toBeInTheDocument();
    expect(
      fetchMock.mock.calls.some((c) => String(c[0]).includes(encodeURIComponent(HELP))),
    ).toBe(true);
  });
});
