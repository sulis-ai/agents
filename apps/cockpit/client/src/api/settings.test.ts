// WP-007 — typed settings client fetcher (errors-are-values; WPF-02).
//
// The fetcher turns each settings route into a Promise<Result<T>> that NEVER
// throws for an EXPECTED settings error (a non-2xx carrying a SettingsErrorCode
// in the ApiError envelope) — it returns { ok:false, error } instead, so the
// page (WP-008) and forms (WP-009) render VALIDATION_FAILED / PATH_NOT_FOUND
// inline. Only a genuine TRANSPORT failure (the network rejects, no ApiError)
// rejects — the one throw path.
//
// The fetcher does NOT call fetch directly (the client inventory gate allow-
// lists only api/client.ts); it goes through the apiGet/apiPost/apiDelete
// funnel, which throws ApiError on non-2xx. We mock globalThis.fetch so the
// whole funnel + fetcher path is exercised against the WP-001 fixtures.
//
// References:
//   - WP-007 Contract (the seven typed methods + invariants).
//   - TDD §8 (Client design — errors are values).
//   - shared/__fixtures__/settings.fixtures.ts (WP-001 canonical stubs).

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import {
  happySettingsTree,
  settingsErrorFixtures,
} from "../../../shared/__fixtures__/settings.fixtures";
import {
  getSettings,
  writeProduct,
  removeProduct,
  writeProject,
  removeProject,
  attachRepo,
  unlinkRepo,
} from "./settings";

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

describe("settings fetcher — errors are values (WPF-02)", () => {
  beforeEach(() => {
    vi.spyOn(globalThis, "fetch").mockReset();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("getSettings_parses_tree_happy — returns ok:true with the typed tree", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(200, happySettingsTree),
    );

    const result = await getSettings();

    expect(result).toEqual({ ok: true, value: happySettingsTree });
  });

  it("returns_typed_result_not_thrown_on_VALIDATION_FAILED — a 422 ApiError becomes ok:false, no throw", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(422, settingsErrorFixtures.VALIDATION_FAILED),
    );

    // The promise RESOLVES (does not reject) with a typed error value.
    const result = await writeProduct({ name: "" });

    expect(result).toEqual({
      ok: false,
      error: {
        code: "VALIDATION_FAILED",
        message: settingsErrorFixtures.VALIDATION_FAILED.error,
      },
    });
  });

  it("maps_PATH_NOT_FOUND_from_attach — a 404 PATH_NOT_FOUND becomes ok:false", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(404, settingsErrorFixtures.PATH_NOT_FOUND),
    );

    const result = await attachRepo({
      projectId: "dna:project:01HAPPYPROJECT",
      localPath: "/does/not/exist",
    });

    expect(result).toEqual({
      ok: false,
      error: {
        code: "PATH_NOT_FOUND",
        message: settingsErrorFixtures.PATH_NOT_FOUND.error,
      },
    });
  });

  it("transport_failure_rejects — a network error rejects (the one throw path)", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(
      new TypeError("Failed to fetch"),
    );

    await expect(getSettings()).rejects.toThrow("Failed to fetch");
  });

  it("removeProduct — a 200 delete returns ok:true with void value", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(200, { ok: true }),
    );

    const result = await removeProduct("dna:product:01HAPPYPRODUCT");

    expect(result.ok).toBe(true);
  });

  it("removeProduct — a non-transport error (404 NOT_FOUND) returns ok:false, no throw", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(404, settingsErrorFixtures.NOT_FOUND),
    );

    const result = await removeProduct("dna:product:missing");

    expect(result).toEqual({
      ok: false,
      error: {
        code: "NOT_FOUND",
        message: settingsErrorFixtures.NOT_FOUND.error,
      },
    });
  });

  it("falls back to a WRITE_FAILED-shaped error when the body carries no recognised code", async () => {
    // A 500 with a non-JSON body: the funnel yields code:null. The fetcher must
    // still return a typed value (never throw for a server error) — it maps the
    // unknown code to WRITE_FAILED (the Internal-category settings code).
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response("upstream exploded", { status: 500 }),
    );

    const result = await writeProduct({ name: "Alpha" });

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.error.code).toBe("WRITE_FAILED");
    }
  });

  it("getSettings maps an expected ApiError to ok:false (IMMUTABLE_IMPLICIT path)", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(409, settingsErrorFixtures.IMMUTABLE_IMPLICIT),
    );

    const result = await getSettings();

    expect(result).toEqual({
      ok: false,
      error: {
        code: "IMMUTABLE_IMPLICIT",
        message: settingsErrorFixtures.IMMUTABLE_IMPLICIT.error,
      },
    });
  });

  it("writeProject returns ok:true with the typed project on 200", async () => {
    const project = happySettingsTree.products[0]!.projects[0]!;
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(200, project));

    const result = await writeProject({
      productId: "dna:product:01HAPPYPRODUCT",
      name: "Alpha web",
    });

    expect(result).toEqual({ ok: true, value: project });
  });

  it("writeProject maps a VALIDATION_FAILED to ok:false, no throw", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(422, settingsErrorFixtures.VALIDATION_FAILED),
    );

    const result = await writeProject({ productId: "p", name: "" });

    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error.code).toBe("VALIDATION_FAILED");
  });

  it("removeProject returns ok:true on a 200 delete", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(200, { ok: true }),
    );

    const result = await removeProject("dna:project:01HAPPYPROJECT");

    expect(result.ok).toBe(true);
  });

  it("unlinkRepo returns the updated project (repo cleared) on 200", async () => {
    const cleared: (typeof happySettingsTree.products)[0]["projects"][0] = {
      projectId: "dna:project:01HAPPYPROJECT",
      name: "Alpha web",
      repo: null,
    };
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(200, cleared));

    const result = await unlinkRepo("dna:project:01HAPPYPROJECT");

    expect(result).toEqual({ ok: true, value: cleared });
  });

  it("unlinkRepo maps a NOT_FOUND to ok:false, no throw", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(404, settingsErrorFixtures.NOT_FOUND),
    );

    const result = await unlinkRepo("dna:project:missing");

    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error.code).toBe("NOT_FOUND");
  });

  it("transport failure on a write rejects too (the one throw path applies to every method)", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(
      new TypeError("Failed to fetch"),
    );

    await expect(writeProject({ productId: "p", name: "x" })).rejects.toThrow(
      "Failed to fetch",
    );
  });
});
