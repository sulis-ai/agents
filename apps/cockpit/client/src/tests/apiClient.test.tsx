// WP-011 — apiGet + ApiError tests.
//
// Per the WP Contract:
//   - apiGet<T>(path, params?) calls fetch with method GET, parses JSON,
//     returns typed body.
//   - On non-2xx, throws ApiError populated from { error, code } JSON
//     (best-effort; if body is not JSON, code is null and message is
//     a generic "HTTP <status>" string).
//   - query string serialised from params (omitted when no params).

import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { apiGet, ApiError } from "../api/client";

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

describe("apiGet", () => {
  beforeEach(() => {
    vi.spyOn(globalThis, "fetch").mockReset();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("calls fetch with method GET and returns parsed body on 200", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(jsonResponse(200, { hello: "world" }));

    const body = await apiGet<{ hello: string }>("/api/changes");

    expect(fetchMock).toHaveBeenCalledOnce();
    const [url, init] = fetchMock.mock.calls[0]!;
    expect(url).toBe("/api/changes");
    expect((init as RequestInit | undefined)?.method ?? "GET").toBe("GET");
    expect(body).toEqual({ hello: "world" });
  });

  it("appends query-string params when supplied", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(jsonResponse(200, []));

    await apiGet<unknown>("/api/changes/abc/file", { path: "src/main.tsx" });

    const [url] = fetchMock.mock.calls[0]!;
    expect(url).toBe("/api/changes/abc/file?path=src%2Fmain.tsx");
  });

  it("throws ApiError with status + code + message on 404 JSON body", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(404, { error: "no such change", code: "NOT_FOUND" }),
    );

    await expect(apiGet("/api/changes/xyz")).rejects.toMatchObject({
      name: "ApiError",
      status: 404,
      code: "NOT_FOUND",
      message: "no such change",
    });
    await expect(apiGet("/api/changes/xyz")).rejects.toBeInstanceOf(ApiError);
  });

  it("throws ApiError with null code when response body is not JSON", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response("oops", { status: 500 }),
    );

    await expect(apiGet("/api/changes")).rejects.toMatchObject({
      status: 500,
      code: null,
    });
  });
});
