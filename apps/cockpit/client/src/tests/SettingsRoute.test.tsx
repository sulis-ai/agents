// WP-008 — the /settings route is wired and reachable (WPF-11: done means
// routed/mounted + reachable in the running app).
//
// Mounts the real <AppRoutes> inside the same provider stack <App> uses
// (Theme / ActiveProduct / OpenTabs / QueryClient), at /settings, and asserts:
//   1. the SettingsPage content renders inside the WorkspaceShell outlet, and
//   2. a "Settings" tab is present in the workspace top bar (the gear/tab
//      affordance, right of the open-tabs strip per the signed mockup).
//
// Fetch is mocked by URL so the topbar's product/changes reads and the page's
// /api/settings read all resolve (the substrate every client test uses).

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ProductList, SettingsTree } from "../../../shared/api-types";
import { AppRoutes } from "../App";
import { ThemeProvider } from "../theme/ThemeProvider";
import { ActiveProductProvider } from "../api/activeProduct";
import { OpenTabsProvider } from "../api/openTabs";

const PRODUCTS: ProductList = {
  products: [{ productId: "pd-1", name: "Sulis Cockpit", active: true }],
  activeProductId: "pd-1",
};

const SETTINGS: SettingsTree = {
  products: [
    {
      productId: "pd-1",
      name: "Sulis Cockpit",
      editable: true,
      projects: [
        {
          projectId: "pr-1",
          name: "cockpit-app",
          repo: {
            localPath: "~/code/sulis/apps/cockpit",
            primaryBranch: "main",
            present: true,
          },
        },
      ],
    },
  ],
};

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

function mockFetchByUrl() {
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = typeof input === "string" ? input : (input as Request).url;
    if (url.includes("/api/settings")) {
      return Promise.resolve(jsonResponse(200, SETTINGS));
    }
    if (url.includes("/api/products")) {
      return Promise.resolve(jsonResponse(200, PRODUCTS));
    }
    if (url.includes("/api/changes") || url.includes("/api/search")) {
      return Promise.resolve(jsonResponse(200, []));
    }
    return Promise.resolve(jsonResponse(200, {}));
  });
}

function freshClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, refetchOnWindowFocus: false, staleTime: 0 },
    },
  });
}

function renderAt(path: string) {
  return render(
    <ThemeProvider>
      <QueryClientProvider client={freshClient()}>
        <ActiveProductProvider>
          <OpenTabsProvider>
            <MemoryRouter initialEntries={[path]}>
              <AppRoutes />
            </MemoryRouter>
          </OpenTabsProvider>
        </ActiveProductProvider>
      </QueryClientProvider>
    </ThemeProvider>,
  );
}

describe("/settings route", () => {
  beforeEach(() => {
    mockFetchByUrl();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("mounts SettingsPage inside the WorkspaceShell at /settings (reachable, WPF-11)", async () => {
    const { findByText, getByTestId } = renderAt("/settings");
    // The page heading renders inside the shell outlet.
    const outlet = getByTestId("shell-outlet");
    expect(outlet).toBeInTheDocument();
    expect(
      await findByText("Settings", { selector: "h1" }),
    ).toBeInTheDocument();
    // The tree content from /api/settings shows.
    expect(await findByText("Sulis Cockpit")).toBeInTheDocument();
  });

  it("shows a Settings tab/gear in the workspace top bar", async () => {
    const { findByTestId } = renderAt("/settings");
    expect(await findByTestId("tab-settings")).toBeInTheDocument();
  });
});
