// WP-008 — useSettings hook tests.
//
// The page's read source unwraps the WP-007 errors-are-values fetcher: an
// EXPECTED settings error ({ ok:false }) is raised into the query as a typed
// SettingsQueryError so the page's isError branch engages and the typed code is
// available; a successful Result resolves to the tree. Drives the real fetcher
// + funnel against the mocked global network call — the substrate every client
// test uses.

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import type { SettingsTree } from "../../../shared/api-types";
import {
  useSettings,
  SettingsQueryError,
  SETTINGS_QUERY_KEY,
  PRODUCTS_QUERY_KEY,
} from "./useSettings";

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

function wrapper() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
}

describe("useSettings", () => {
  beforeEach(() => {
    vi.spyOn(globalThis, "fetch").mockReset();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("pins the shared cache keys (the settings tree + the product switcher)", () => {
    expect(SETTINGS_QUERY_KEY).toEqual(["settings"]);
    expect(PRODUCTS_QUERY_KEY).toEqual(["products"]);
  });

  it("resolves the tree on success", async () => {
    const tree: SettingsTree = { products: [] };
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(200, tree));
    const { result } = renderHook(() => useSettings(), { wrapper: wrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(tree);
  });

  it("raises an expected settings error as a typed SettingsQueryError (isError)", async () => {
    // A non-2xx with a settings error code travels in the ApiError envelope →
    // the fetcher returns { ok:false } → the hook throws SettingsQueryError.
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(404, { code: "NOT_FOUND", message: "no settings" }),
    );
    const { result } = renderHook(() => useSettings(), { wrapper: wrapper() });
    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error).toBeInstanceOf(SettingsQueryError);
    expect((result.current.error as SettingsQueryError).code).toBe("NOT_FOUND");
  });
});
