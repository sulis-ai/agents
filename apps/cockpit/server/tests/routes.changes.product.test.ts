// PUT /api/changes/:id/product — per-change product assignment route.
//
// Isolated route test: mount createChangesRouter with a MOCK ChangeProductWriter
// (the real write goes through the allow-listed SpineSettingsAdapter, exercised
// by its own pytest). This pins the route's parse + delegate + envelope shape.

import { describe, it, expect, vi } from "vitest";
import request from "supertest";
import express from "express";

import {
  createChangesRouter,
  type ChangeProductWriter,
} from "../routes/changes";
import { FakeChangeStoreReader } from "../adapters/FakeChangeStoreReader";

function appWith(writer: Partial<ChangeProductWriter>) {
  const app = express();
  app.use(express.json());
  // Fill any unprovided method with a never-called stub: each test supplies
  // only the method under test (assign for the PUT cases, clear for DELETE), so
  // the `not.toHaveBeenCalled()` assertions still target the supplied mock.
  const changeProductWriter: ChangeProductWriter = {
    assignChangeProduct: vi.fn(),
    clearChangeProduct: vi.fn(),
    ...writer,
  };
  app.use(
    "/api/changes",
    createChangesRouter({
      changeStore: new FakeChangeStoreReader([]),
      sulisStateDir: "/tmp/cockpit-test-nostate",
      claudeProjectsDir: "/tmp/cockpit-test-noprojects",
      changeProductWriter,
    }),
  );
  return app;
}

const CHANGE_ID = "01ABC0000000000000000000AA";
const PRODUCT_ID = "dna:product:01XYZ000000000000000000000";

describe("PUT /api/changes/:id/product", () => {
  it("delegates to the writer and returns the saved link", async () => {
    const assignChangeProduct = vi.fn().mockResolvedValue({
      id: `dna:change:${CHANGE_ID}`,
      forProduct: PRODUCT_ID,
    });
    const res = await request(appWith({ assignChangeProduct }))
      .put(`/api/changes/${CHANGE_ID}/product`)
      .send({ productId: PRODUCT_ID });

    expect(res.status).toBe(200);
    expect(res.body).toMatchObject({ ok: true, forProduct: PRODUCT_ID });
    expect(assignChangeProduct).toHaveBeenCalledWith(CHANGE_ID, PRODUCT_ID);
  });

  it("400s when productId is missing — and never calls the writer", async () => {
    const assignChangeProduct = vi.fn();
    const res = await request(appWith({ assignChangeProduct }))
      .put(`/api/changes/${CHANGE_ID}/product`)
      .send({});

    expect(res.status).toBe(400);
    expect(res.body.ok).toBe(false);
    expect(assignChangeProduct).not.toHaveBeenCalled();
  });

  it("surfaces a writer validation error (the adapter rejects a bad id)", async () => {
    const assignChangeProduct = vi
      .fn()
      .mockRejectedValue(new Error("invalid product id"));
    const res = await request(appWith({ assignChangeProduct }))
      .put(`/api/changes/${CHANGE_ID}/product`)
      .send({ productId: "not-a-product" });
    // The route delegates; the adapter's throw becomes a non-2xx (error handler).
    expect(res.status).toBeGreaterThanOrEqual(400);
  });
});

describe("DELETE /api/changes/:id/product (un-assign — WP-003)", () => {
  it("delegates to clearChangeProduct and returns forProduct: null", async () => {
    const assignChangeProduct = vi.fn();
    const clearChangeProduct = vi.fn().mockResolvedValue({
      id: `dna:change:${CHANGE_ID}`,
      forProduct: null,
    });
    const res = await request(
      appWith({ assignChangeProduct, clearChangeProduct }),
    ).delete(`/api/changes/${CHANGE_ID}/product`);

    expect(res.status).toBe(200);
    expect(res.body).toEqual({
      ok: true,
      id: `dna:change:${CHANGE_ID}`,
      forProduct: null,
    });
    expect(clearChangeProduct).toHaveBeenCalledWith(CHANGE_ID);
    expect(assignChangeProduct).not.toHaveBeenCalled();
  });

  it("400s on a blank id — and never calls the writer (parity with PUT guard)", async () => {
    const assignChangeProduct = vi.fn();
    const clearChangeProduct = vi.fn();
    const res = await request(
      appWith({ assignChangeProduct, clearChangeProduct }),
    ).delete(`/api/changes/${encodeURIComponent("  ")}/product`);

    expect(res.status).toBe(400);
    expect(res.body.ok).toBe(false);
    expect(clearChangeProduct).not.toHaveBeenCalled();
  });

  it("surfaces a writer error as a non-2xx (the adapter rejects a bad id)", async () => {
    const assignChangeProduct = vi.fn();
    const clearChangeProduct = vi
      .fn()
      .mockRejectedValue(new Error("invalid change id"));
    const res = await request(
      appWith({ assignChangeProduct, clearChangeProduct }),
    ).delete(`/api/changes/${CHANGE_ID}/product`);
    expect(res.status).toBeGreaterThanOrEqual(400);
  });
});
