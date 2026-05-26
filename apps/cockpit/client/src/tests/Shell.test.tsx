// WP-011 — Shell layout test.
//
// Asserts the persistent two-pane layout renders:
//   - <Sidebar> on the left (testid "shell-sidebar")
//   - <Outlet /> region on the right (testid "shell-outlet"), into
//     which the active route's element is rendered.
//
// WP-012 made the Sidebar a TanStack-Query consumer (useChangesWithLiveness),
// so this test now needs a QueryClientProvider wrapper. The fetch mock
// keeps the network out of the test.

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Shell } from "../layouts/Shell";

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

function renderShellWith(_children: React.ReactNode, path = "/") {
  return render(
    <QueryClientProvider client={freshClient()}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route element={<Shell />}>
            <Route
              path="/"
              element={<div data-testid="route-marker">child</div>}
            />
          </Route>
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("<Shell />", () => {
  beforeEach(() => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(200, []));
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders sidebar and outlet regions", () => {
    renderShellWith(null);
    expect(screen.getByTestId("shell-sidebar")).toBeInTheDocument();
    expect(screen.getByTestId("shell-outlet")).toBeInTheDocument();
  });

  it("renders the matched child route inside the outlet region", () => {
    renderShellWith(null);
    const marker = screen.getByTestId("route-marker");
    expect(marker).toBeInTheDocument();
    // The marker is a descendant of the outlet region (TDD §6).
    expect(screen.getByTestId("shell-outlet")).toContainElement(marker);
  });
});
