// WP-012 — <Sidebar> tests.
//
// Coverage:
//   - Renders one <SidebarItem> per change.
//   - Currently-routed change is highlighted (data-active="true").
//   - Clicking an item navigates to /c/:changeId.
//   - Empty changes → renders a quiet placeholder (no error).

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { Change } from "../../../shared/api-types";
import { Sidebar } from "../components/Sidebar";

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
    liveness: { status: "running", pid: 1234 },
    ...overrides,
  };
}

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

// WP-008 — the Sidebar now also fetches GET /api/products (for the switcher).
// A URL-aware mock returns a ProductList for that endpoint and the supplied
// change list for GET /api/changes — so the existing change-list assertions
// stay valid while the product switcher has data to render.
function mockSidebarFetch(changes: Change[]) {
  return vi
    .spyOn(globalThis, "fetch")
    .mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/api/products")) {
        return Promise.resolve(
          jsonResponse(200, {
            products: [
              {
                productId: "dna:product:implicit-single",
                name: "Your product",
                active: true,
              },
            ],
            activeProductId: "dna:product:implicit-single",
          }),
        );
      }
      return Promise.resolve(jsonResponse(200, changes));
    });
}

function renderSidebar(initialEntries: string[]) {
  return render(
    <QueryClientProvider client={freshClient()}>
      <MemoryRouter initialEntries={initialEntries}>
        <Routes>
          <Route path="/" element={<Sidebar />} />
          <Route path="/c/:changeId" element={<Sidebar />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("<Sidebar>", () => {
  beforeEach(() => {
    vi.spyOn(globalThis, "fetch").mockReset();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders one item per change", async () => {
    const changes: Change[] = [
      makeChange({ changeId: "01AAA", handle: "CH-01AAA" }),
      makeChange({ changeId: "01BBB", handle: "CH-01BBB" }),
    ];
    mockSidebarFetch(changes);
    const { getAllByTestId } = renderSidebar(["/"]);
    await waitFor(() =>
      expect(getAllByTestId("sidebar-item")).toHaveLength(2),
    );
  });

  it("highlights the currently-routed change", async () => {
    const changes: Change[] = [
      makeChange({ changeId: "01AAA", handle: "CH-01AAA" }),
      makeChange({ changeId: "01BBB", handle: "CH-01BBB" }),
    ];
    mockSidebarFetch(changes);
    const { getAllByTestId } = renderSidebar(["/c/01BBB"]);
    const items = await waitFor(() => getAllByTestId("sidebar-item"));
    const active = items.filter((el) => el.getAttribute("data-active") === "true");
    expect(active).toHaveLength(1);
    expect(active[0]!.textContent).toContain("CH-01BBB");
  });

  it("clicking an item navigates to /c/:changeId", async () => {
    const changes: Change[] = [
      makeChange({ changeId: "01XYZ", handle: "CH-01XYZ" }),
    ];
    mockSidebarFetch(changes);
    const { getAllByTestId, getByRole } = renderSidebar(["/"]);
    await waitFor(() => expect(getAllByTestId("sidebar-item")).toHaveLength(1));
    const link = getByRole("link", { name: /CH-01XYZ/i });
    expect(link.getAttribute("href")).toBe("/c/01XYZ");
  });

  it("shows a quiet placeholder when there are zero changes", async () => {
    mockSidebarFetch([]);
    const { getByText } = renderSidebar(["/"]);
    await waitFor(() =>
      expect(getByText(/no changes yet/i)).toBeInTheDocument(),
    );
  });

  // #38: archive-on-ship — shipped changes go under a collapsed "Shipped"
  // section so they don't crowd active work, but everything stays accessible
  // (audit trail). The diff / file views work on them exactly like a live one.
  describe("shipped section", () => {
    it("does not render a Shipped section when no changes are shipped", async () => {
      const changes: Change[] = [
        makeChange({ changeId: "01AAA", handle: "CH-01AAA", stage: "implement" }),
      ];
      mockSidebarFetch(changes);
      const { queryByTestId, getAllByTestId } = renderSidebar(["/"]);
      await waitFor(() => expect(getAllByTestId("sidebar-item")).toHaveLength(1));
      expect(queryByTestId("sidebar-shipped")).toBeNull();
    });

    it("renders shipped changes under a separate, collapsed section", async () => {
      const changes: Change[] = [
        makeChange({ changeId: "01AAA", handle: "CH-01AAA", stage: "implement" }),
        makeChange({ changeId: "01BBB", handle: "CH-01BBB", stage: "shipped" }),
        makeChange({ changeId: "01CCC", handle: "CH-01CCC", stage: "shipped" }),
      ];
      mockSidebarFetch(changes);
      const { getByTestId, queryByTestId } = renderSidebar(["/"]);
      // Active section renders the one non-shipped change immediately.
      await waitFor(() => expect(getByTestId("sidebar-active")).toBeInTheDocument());
      const toggle = getByTestId("sidebar-shipped-toggle");
      expect(toggle.textContent).toContain("Shipped (2)");
      // Collapsed by default — the items are NOT in the DOM yet.
      expect(queryByTestId("sidebar-shipped-items")).toBeNull();
      expect(toggle.getAttribute("aria-expanded")).toBe("false");
    });

    it("expands shipped items on toggle click", async () => {
      const changes: Change[] = [
        makeChange({ changeId: "01BBB", handle: "CH-01BBB", stage: "shipped" }),
      ];
      mockSidebarFetch(changes);
      const { getByTestId, queryByTestId } = renderSidebar(["/"]);
      const toggle = await waitFor(() => getByTestId("sidebar-shipped-toggle"));
      expect(queryByTestId("sidebar-shipped-items")).toBeNull();
      fireEvent.click(toggle);
      expect(getByTestId("sidebar-shipped-items")).toBeInTheDocument();
      expect(toggle.getAttribute("aria-expanded")).toBe("true");
    });
  });
});
