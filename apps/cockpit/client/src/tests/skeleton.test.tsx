// WP-011 — smoke test for <App />.
//
// Replaces WP-001's "cockpit booting" placeholder assertion now that
// WP-011 has landed the real Router + Shell + TanStack Query wiring.
// We assert <App /> mounts without throwing AND the dashboard route
// renders inside the persistent Shell. Detailed route + layout
// behaviour lives in routing.test.tsx + Shell.test.tsx.

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { AppRoutes } from "../App";

describe("App smoke", () => {
  it("mounts AppRoutes with a router + query client without throwing", () => {
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={["/"]}>
          <AppRoutes />
        </MemoryRouter>
      </QueryClientProvider>,
    );
    expect(screen.getByTestId("page-dashboard")).toBeInTheDocument();
    expect(screen.getByTestId("shell-sidebar")).toBeInTheDocument();
  });
});
