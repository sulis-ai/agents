// WP-011 — smoke test for <App />.
//
// Replaces WP-001's "cockpit booting" placeholder assertion now that
// WP-011 has landed the real Router + Shell + TanStack Query wiring.
// We assert <App /> mounts without throwing AND the dashboard route
// renders inside the persistent Shell. Detailed route + layout
// behaviour lives in routing.test.tsx + Shell.test.tsx.

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { AppRoutes } from "../App";
// WP-004 — the Shell now hosts the ThemeToggle (a useTheme() consumer), so the
// smoke mount wraps AppRoutes in a ThemeProvider, mirroring App.tsx production.
import { ThemeProvider } from "../theme/ThemeProvider";
import { stubMatchMedia } from "./helpers/stubMatchMedia";

describe("App smoke", () => {
  beforeEach(() => {
    stubMatchMedia(false);
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    delete document.documentElement.dataset.theme;
  });

  it("mounts AppRoutes with a router + query client without throwing", () => {
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <QueryClientProvider client={client}>
        <ThemeProvider>
          <MemoryRouter initialEntries={["/"]}>
            <AppRoutes />
          </MemoryRouter>
        </ThemeProvider>
      </QueryClientProvider>,
    );
    expect(screen.getByTestId("page-dashboard")).toBeInTheDocument();
    expect(screen.getByTestId("shell-sidebar")).toBeInTheDocument();
  });
});
