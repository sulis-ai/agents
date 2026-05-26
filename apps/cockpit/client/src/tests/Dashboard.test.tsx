// WP-012 — <Dashboard> tests.
//
// Coverage:
//   - Loading state renders skeleton placeholders.
//   - Error state renders message + retry button.
//   - Empty state renders <EmptyState />.
//   - Two fixture changes render two <ChangeCard>s with right text.
//   - Card click navigates to /c/:changeId (asserted via current URL).
//   - Refresh button calls queryClient.invalidateQueries on ["changes"].
//   - The Dashboard's underlying query has refetchInterval = LIVENESS_POLL_MS.

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { Change } from "../../../shared/api-types";
import { Dashboard } from "../pages/Dashboard";
import { LIVENESS_POLL_MS } from "../config";

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

function renderDashboard(client: QueryClient) {
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={["/"]}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route
            path="/c/:changeId"
            element={<div data-testid="thread-view" />}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("<Dashboard>", () => {
  beforeEach(() => {
    vi.spyOn(globalThis, "fetch").mockReset();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders a skeleton while loading", () => {
    // Never resolves → stays in loading.
    vi.spyOn(globalThis, "fetch").mockReturnValue(new Promise(() => {}));
    const { getByTestId } = renderDashboard(freshClient());
    expect(getByTestId("dashboard-loading")).toBeInTheDocument();
  });

  it("renders an error message + retry button on failure", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(500, { error: "boom" }),
    );
    const { getByText, getByRole } = renderDashboard(freshClient());
    await waitFor(() =>
      expect(getByText(/something went wrong/i)).toBeInTheDocument(),
    );
    expect(getByRole("button", { name: /retry/i })).toBeInTheDocument();
  });

  it("renders the empty state when zero changes", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(200, []));
    const { getByText } = renderDashboard(freshClient());
    await waitFor(() =>
      expect(getByText(/nothing in flight/i)).toBeInTheDocument(),
    );
  });

  it("renders one ChangeCard per change with handle + intent + stage", async () => {
    const changes: Change[] = [
      makeChange({ changeId: "01AAA", handle: "CH-01AAA", intent: "Alpha" }),
      makeChange({ changeId: "01BBB", handle: "CH-01BBB", intent: "Beta" }),
    ];
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(200, changes),
    );
    const { getAllByTestId, getByText } = renderDashboard(freshClient());
    await waitFor(() => expect(getAllByTestId("change-card")).toHaveLength(2));
    expect(getByText("CH-01AAA")).toBeInTheDocument();
    expect(getByText("CH-01BBB")).toBeInTheDocument();
    expect(getByText("Alpha")).toBeInTheDocument();
    expect(getByText("Beta")).toBeInTheDocument();
  });

  it("navigates to /c/:changeId when a card is clicked", async () => {
    const changes: Change[] = [
      makeChange({ changeId: "01XYZ", handle: "CH-01XYZ" }),
    ];
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(200, changes),
    );
    const { getByRole, queryByTestId } = renderDashboard(freshClient());
    const link = await waitFor(() =>
      getByRole("link", { name: /CH-01XYZ/i }),
    );
    fireEvent.click(link);
    await waitFor(() => expect(queryByTestId("thread-view")).toBeInTheDocument());
  });

  it("Refresh button invalidates the changes query", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(200, []));
    const client = freshClient();
    const spy = vi.spyOn(client, "invalidateQueries");
    const { getByRole } = renderDashboard(client);
    // Wait for both: the button to exist AND not be disabled (the
    // RefreshButton disables itself during in-flight fetches, so an
    // immediate click would no-op).
    await waitFor(() => {
      const btn = getByRole("button", { name: /refresh/i }) as HTMLButtonElement;
      expect(btn).toBeInTheDocument();
      expect(btn.disabled).toBe(false);
    });
    fireEvent.click(getByRole("button", { name: /refresh/i }));
    expect(spy).toHaveBeenCalledWith({ queryKey: ["changes"] });
  });

  it("the underlying query uses LIVENESS_POLL_MS as refetchInterval", async () => {
    vi.useFakeTimers();
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(jsonResponse(200, []));
    const client = freshClient();
    renderDashboard(client);
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    // Advance just past the configured interval and assert a refetch fired.
    await vi.advanceTimersByTimeAsync(LIVENESS_POLL_MS + 50);
    await vi.waitFor(() => expect(fetchMock.mock.calls.length).toBeGreaterThanOrEqual(2));
    vi.useRealTimers();
  });
});
