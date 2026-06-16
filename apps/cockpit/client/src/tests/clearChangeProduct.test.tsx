// WP-004 — useClearChangeProduct test.
//
// The client half of the unassign seam (sibling to useAssignChangeProduct).
// The mutation hits DELETE /api/changes/:id/product through the typed funnel
// and, onSuccess, invalidates the two query keys the board + change detail
// read from (["changes"] and ["change", id]) so the Unassigned count + the
// product chip reflect the clear without a reload. The fetch-mock shape
// mirrors useChangesWithLiveness.test.tsx; the invalidation assertion mirrors
// the assign hook's documented onSuccess contract.

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

import type { ClearChangeProductResult } from "../../../shared/api-types";
import { useClearChangeProduct } from "../api/clearChangeProduct";

function freshClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, refetchOnWindowFocus: false, staleTime: 0 },
      mutations: { retry: false },
    },
  });
}

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

const CHANGE_ID = "dna:change:01KV883AJ0FNVQNNXZKX441KWT";

const CLEAR_RESULT: ClearChangeProductResult = {
  ok: true,
  id: CHANGE_ID,
  forProduct: null,
};

describe("useClearChangeProduct", () => {
  beforeEach(() => {
    vi.spyOn(globalThis, "fetch").mockReset();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("issues DELETE to /api/changes/:id/product through the funnel", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(jsonResponse(200, CLEAR_RESULT));

    const client = freshClient();
    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    );

    const { result } = renderHook(() => useClearChangeProduct(CHANGE_ID), {
      wrapper,
    });

    result.current.mutate();

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0]!;
    // The change id is encodeURIComponent-escaped in the path (parity with
    // assignChangeProduct — the id carries `:` segments).
    expect(url).toBe(`/api/changes/${encodeURIComponent(CHANGE_ID)}/product`);
    expect(init?.method).toBe("DELETE");
    expect(result.current.data).toEqual(CLEAR_RESULT);
  });

  it("invalidates ['changes'] and ['change', id] onSuccess", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(200, CLEAR_RESULT),
    );

    const client = freshClient();
    const invalidateSpy = vi.spyOn(client, "invalidateQueries");

    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    );

    const { result } = renderHook(() => useClearChangeProduct(CHANGE_ID), {
      wrapper,
    });

    result.current.mutate();

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    const invalidatedKeys = invalidateSpy.mock.calls.map(
      (call) => call[0]?.queryKey,
    );
    expect(invalidatedKeys).toContainEqual(["changes"]);
    expect(invalidatedKeys).toContainEqual(["change", CHANGE_ID]);
  });
});
