// WP-012 — useChangesWithLiveness test.
//
// The sibling-hook variant overrides refetchInterval on the same
// ["changes"] query key, so the dashboard + sidebar surfaces refresh
// their liveness dots every LIVENESS_POLL_MS without manual action.
// TanStack Query dedupes the shared key, so any other reader of
// useChanges benefits from the freshness automatically.

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { Change } from "../../../shared/api-types";
import { useChangesWithLiveness } from "../api/useChangesWithLiveness";
import { LIVENESS_POLL_MS } from "../config";

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

describe("useChangesWithLiveness", () => {
  beforeEach(() => {
    vi.spyOn(globalThis, "fetch").mockReset();
  });
  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it("hits /api/changes and shares the ['changes'] query key", async () => {
    const payload: Change[] = [];
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(jsonResponse(200, payload));

    function Probe() {
      const q = useChangesWithLiveness();
      return <div data-testid="probe">{q.isSuccess ? "ok" : q.status}</div>;
    }

    const { getByTestId } = render(
      <QueryClientProvider client={freshClient()}>
        <Probe />
      </QueryClientProvider>,
    );
    await waitFor(() => expect(getByTestId("probe").textContent).toBe("ok"));
    expect(fetchMock.mock.calls[0]![0]).toBe("/api/changes");
  });

  it("refetches at LIVENESS_POLL_MS cadence", async () => {
    vi.useFakeTimers();
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(jsonResponse(200, []));

    function Probe() {
      const q = useChangesWithLiveness();
      return <div data-testid="probe">{q.isSuccess ? "ok" : q.status}</div>;
    }

    render(
      <QueryClientProvider client={freshClient()}>
        <Probe />
      </QueryClientProvider>,
    );

    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    await vi.advanceTimersByTimeAsync(LIVENESS_POLL_MS + 50);
    await vi.waitFor(() =>
      expect(fetchMock.mock.calls.length).toBeGreaterThanOrEqual(2),
    );
  });
});
