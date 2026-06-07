// WP-011 — Routing test.
//
// Asserts the three routes per the WP Contract:
//   /              → <Board>      (WP-003 stage-column board; was Dashboard)
//   /c/:changeId   → <ThreadView> placeholder
//   /garbage       → <NotFound>
//
// Pages are rendered inside <Shell />, so the sidebar testid is also
// present in every case (the layout wraps every route).
//
// WP-012 made the Sidebar a TanStack-Query consumer and turned the
// Dashboard into a query-driven page; this test wraps in a
// QueryClientProvider and mocks fetch.

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AppRoutes } from "../App";

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

function renderAt(path: string) {
  // Since WP-013, the ThreadView route calls useChange/useTranscript;
  // wrap routes in a QueryClientProvider so any route is renderable.
  // freshClient() gives test-friendly defaults (retry off, focus-refetch off).
  return render(
    <QueryClientProvider client={freshClient()}>
      <MemoryRouter initialEntries={[path]}>
        <AppRoutes />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("App routes", () => {
  beforeEach(() => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(200, []));
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the Board at /", () => {
    renderAt("/");
    expect(screen.getByTestId("page-board")).toBeInTheDocument();
    expect(screen.getByTestId("workspace-topbar")).toBeInTheDocument();
  });

  it("renders ThreadView at /c/:changeId", () => {
    renderAt("/c/CH-01KSJA");
    expect(screen.getByTestId("page-thread")).toBeInTheDocument();
    expect(screen.getByTestId("workspace-topbar")).toBeInTheDocument();
  });

  it("renders NotFound for an unknown path", () => {
    renderAt("/garbage");
    expect(screen.getByTestId("page-not-found")).toBeInTheDocument();
    expect(screen.getByTestId("workspace-topbar")).toBeInTheDocument();
  });
});
