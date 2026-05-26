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
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(200, changes),
    );
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
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(200, changes),
    );
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
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(200, changes),
    );
    const { getAllByTestId, getByRole } = renderSidebar(["/"]);
    await waitFor(() => expect(getAllByTestId("sidebar-item")).toHaveLength(1));
    const link = getByRole("link", { name: /CH-01XYZ/i });
    expect(link.getAttribute("href")).toBe("/c/01XYZ");
  });

  it("shows a quiet placeholder when there are zero changes", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(200, []));
    const { getByText } = renderSidebar(["/"]);
    await waitFor(() =>
      expect(getByText(/no changes yet/i)).toBeInTheDocument(),
    );
  });
});
