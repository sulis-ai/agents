// Chat-redesign (chat-B2) — WorkspaceShell layout test.
//
// Asserts the tabbed-workspace layout renders:
//   - the workspace top bar (testid "workspace-topbar") with a Board tab,
//   - the <Outlet /> region (testid "shell-outlet"), into which the active
//     route's element is rendered.
//
// The top bar consumes products + changes (TanStack Query) and the open-tabs
// context, so the test wraps in QueryClientProvider + the providers and mocks
// fetch to keep the network out.

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ActiveProductProvider } from "../api/activeProduct";
import { OpenTabsProvider } from "../api/openTabs";
import { WorkspaceShell } from "../layouts/WorkspaceShell";
// CH-01KTHP — the workspace top bar now hosts the ThemeToggle (a useTheme()
// consumer), so the shell mount wraps in a ThemeProvider, mirroring App.tsx
// production composition.
import { ThemeProvider } from "../theme/ThemeProvider";

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

function renderShell(path = "/") {
  return render(
    <QueryClientProvider client={freshClient()}>
      <ThemeProvider>
        <ActiveProductProvider>
          <OpenTabsProvider>
            <MemoryRouter initialEntries={[path]}>
              <Routes>
                <Route element={<WorkspaceShell />}>
                  <Route
                    path="/"
                    element={<div data-testid="route-marker">child</div>}
                  />
                </Route>
              </Routes>
            </MemoryRouter>
          </OpenTabsProvider>
        </ActiveProductProvider>
      </ThemeProvider>
    </QueryClientProvider>,
  );
}

describe("<WorkspaceShell />", () => {
  beforeEach(() => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(200, []));
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the workspace top bar with the Board tab and the outlet region", () => {
    renderShell();
    expect(screen.getByTestId("workspace-topbar")).toBeInTheDocument();
    expect(screen.getByTestId("tab-board")).toBeInTheDocument();
    expect(screen.getByTestId("shell-outlet")).toBeInTheDocument();
  });

  it("renders the matched child route inside the outlet region", () => {
    renderShell();
    const marker = screen.getByTestId("route-marker");
    expect(marker).toBeInTheDocument();
    // The marker is a descendant of the outlet region.
    expect(screen.getByTestId("shell-outlet")).toContainElement(marker);
  });
});
