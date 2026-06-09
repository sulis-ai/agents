// WP-002 — Fake-specific guard tests (TDD §6; WPB-06 typed Result at the
// boundary).
//
// The shared contract (`SettingsStore.contract.ts`) pins the behaviour BOTH
// adapters share. These tests pin the FakeSettingsStore's typed-error guards
// for the not-found / unknown-id paths — the SettingsStoreError codes a route
// maps to 404 — which the happy-path contract does not exercise. Kept separate
// from the contract so the real adapter (WP-005) isn't forced to match the
// fake's exact in-memory error wording, only the port's NOT_FOUND code.

import { describe, it, expect } from "vitest";

import { FakeSettingsStore } from "../adapters/FakeSettingsStore";
import { SettingsStoreError } from "../ports/SettingsStore";

describe("FakeSettingsStore — typed not-found guards", () => {
  it("upsertProduct with an unknown id raises NOT_FOUND", async () => {
    const store = new FakeSettingsStore();
    await expect(
      store.upsertProduct({ productId: "fake-product-999", name: "Ghost" }),
    ).rejects.toMatchObject({ code: "NOT_FOUND" });
  });

  it("upsertProject with an unknown id raises NOT_FOUND", async () => {
    const store = new FakeSettingsStore();
    await expect(
      store.upsertProject({
        projectId: "fake-project-999",
        productId: "fake-product-1",
        name: "Ghost",
      }),
    ).rejects.toMatchObject({ code: "NOT_FOUND" });
  });

  it("upsertProject under an unknown product raises NOT_FOUND", async () => {
    const store = new FakeSettingsStore();
    await expect(
      store.upsertProject({ productId: "fake-product-999", name: "Web" }),
    ).rejects.toMatchObject({ code: "NOT_FOUND" });
  });

  it("removeProduct on an unknown id raises NOT_FOUND", async () => {
    const store = new FakeSettingsStore();
    await expect(store.removeProduct("nope")).rejects.toBeInstanceOf(
      SettingsStoreError,
    );
  });

  it("removeProject on an unknown id raises NOT_FOUND", async () => {
    const store = new FakeSettingsStore();
    await expect(store.removeProject("nope")).rejects.toMatchObject({
      code: "NOT_FOUND",
    });
  });

  it("removeProduct is idempotent-safe: a re-remove of a deleted product raises NOT_FOUND", async () => {
    const store = new FakeSettingsStore();
    const product = await store.upsertProduct({ name: "Acme" });
    await store.removeProduct(product.productId);
    await expect(store.removeProduct(product.productId)).rejects.toMatchObject({
      code: "NOT_FOUND",
    });
  });

  it("attachRepo on an unknown project raises NOT_FOUND", async () => {
    const store = new FakeSettingsStore();
    await expect(
      store.attachRepo({ projectId: "nope", localPath: "/tmp" }),
    ).rejects.toMatchObject({ code: "NOT_FOUND" });
  });

  it("unlinkRepo on an unknown project raises NOT_FOUND", async () => {
    const store = new FakeSettingsStore();
    await expect(store.unlinkRepo("nope")).rejects.toMatchObject({
      code: "NOT_FOUND",
    });
  });
});
