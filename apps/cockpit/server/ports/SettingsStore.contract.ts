// WP-002 — Shared contract test for the SettingsStore port (TDD §5.3, §6;
// ADR-019/020; MEA-08).
//
// This file defines the behaviour EVERY implementation of the SettingsStore
// port must satisfy. Both adapters import `settingsStoreContract` and supply
// their own factory: the in-memory `FakeSettingsStore` (WP-002) and the real
// `SpineSettingsAdapter` (WP-005). Same assertions, two implementations — that
// is the boundary-parity guarantee (MEA-08) the real adapter must also pass.
//
// It is a `.contract.ts` (not a `.test.ts`): it exports a function and carries
// no top-level `describe`, so the vitest server glob never collects it on its
// own. Each adapter's runnable `*.contract.test.ts` calls it with a factory.
//
// The factory is `() => Promise<SettingsStore>` per the WP Contract: each call
// yields a FRESH, empty store, so tests do not bleed state into one another.

import { describe, it, expect, beforeEach } from "vitest";

import type { SettingsStore } from "./SettingsStore";

/**
 * A folder path that is guaranteed not to exist on disk, used to drive the
 * `attachRepo` PATH_NOT_FOUND assertion. Kept here so both adapters exercise
 * the same input.
 */
export const MISSING_PATH =
  "/nonexistent/settings-store-contract/missing-folder";

/**
 * Run the shared behaviour contract against an implementation of
 * `SettingsStore`. `makeStore` returns a fresh, empty store per invocation.
 *
 * @param name      label distinguishing the implementation under test
 * @param makeStore factory yielding a fresh `SettingsStore`
 * @param opts      per-adapter hooks. `existingFolderNoGit` MUST resolve to a
 *                  real on-disk folder that has NO `.git` child — the fake
 *                  supplies an in-memory stand-in, the real adapter an
 *                  `mkdtemp` dir — so the "attach a non-repo folder" case is
 *                  exercised identically without hard-wiring a path here.
 */
export function settingsStoreContract(
  name: string,
  makeStore: () => Promise<SettingsStore>,
  opts: { existingFolderNoGit: () => Promise<string> },
): void {
  describe(`SettingsStore contract — ${name}`, () => {
    let store: SettingsStore;

    beforeEach(async () => {
      store = await makeStore();
    });

    describe("upsertProduct", () => {
      it("upsert_without_id_mints_new — a create (no id) mints a fresh id", async () => {
        const created = await store.upsertProduct({ name: "Acme" });
        expect(created.productId).toBeTruthy();
        expect(created.name).toBe("Acme");

        const tree = await store.readTree();
        expect(tree.products.map((p) => p.productId)).toContain(
          created.productId,
        );
      });

      it("upsert_with_id_overwrites_in_place — an edit (with id) overwrites, never grows the tree", async () => {
        const created = await store.upsertProduct({ name: "Acme" });

        const edited = await store.upsertProduct({
          productId: created.productId,
          name: "Acme Renamed",
        });
        expect(edited.productId).toBe(created.productId);
        expect(edited.name).toBe("Acme Renamed");

        const tree = await store.readTree();
        // Idempotent on the id: re-upsert overwrites in place; the tree holds
        // exactly one product.
        expect(tree.products).toHaveLength(1);
        const only = tree.products[0];
        expect(only?.productId).toBe(created.productId);
        expect(only?.name).toBe("Acme Renamed");
      });
    });

    describe("readTree", () => {
      it("returns active products sorted by name", async () => {
        await store.upsertProduct({ name: "Zeta" });
        await store.upsertProduct({ name: "Alpha" });
        await store.upsertProduct({ name: "Mu" });

        const tree = await store.readTree();
        expect(tree.products.map((p) => p.name)).toEqual([
          "Alpha",
          "Mu",
          "Zeta",
        ]);
      });

      it("returns active projects under a product sorted by name", async () => {
        const product = await store.upsertProduct({ name: "Acme" });
        await store.upsertProject({
          productId: product.productId,
          name: "Yak",
        });
        await store.upsertProject({
          productId: product.productId,
          name: "Bee",
        });

        const tree = await store.readTree();
        const acme = tree.products.find(
          (p) => p.productId === product.productId,
        );
        expect(acme?.projects.map((pr) => pr.name)).toEqual(["Bee", "Yak"]);
      });
    });

    describe("remove", () => {
      it("removed_entity_absent_from_next_readTree — removeProduct soft-deletes; the product is gone from the next readTree", async () => {
        const keep = await store.upsertProduct({ name: "Keep" });
        const drop = await store.upsertProduct({ name: "Drop" });

        await store.removeProduct(drop.productId);

        const tree = await store.readTree();
        const ids = tree.products.map((p) => p.productId);
        expect(ids).toContain(keep.productId);
        expect(ids).not.toContain(drop.productId);
      });

      it("removed_entity_absent_from_next_readTree — removeProject soft-deletes; the project is gone from the next readTree", async () => {
        const product = await store.upsertProduct({ name: "Acme" });
        const keep = await store.upsertProject({
          productId: product.productId,
          name: "Keep",
        });
        const drop = await store.upsertProject({
          productId: product.productId,
          name: "Drop",
        });

        await store.removeProject(drop.projectId);

        const tree = await store.readTree();
        const acme = tree.products.find(
          (p) => p.productId === product.productId,
        );
        const projectIds = acme?.projects.map((pr) => pr.projectId) ?? [];
        expect(projectIds).toContain(keep.projectId);
        expect(projectIds).not.toContain(drop.projectId);
      });
    });

    describe("attachRepo / unlinkRepo", () => {
      it("attach_missing_path_raises_PATH_NOT_FOUND — attaching a non-existent folder raises a PATH_NOT_FOUND coded error", async () => {
        const product = await store.upsertProduct({ name: "Acme" });
        const project = await store.upsertProject({
          productId: product.productId,
          name: "Web",
        });

        await expect(
          store.attachRepo({
            projectId: project.projectId,
            localPath: MISSING_PATH,
          }),
        ).rejects.toMatchObject({ code: "PATH_NOT_FOUND" });
      });

      it("attach_non_repo_folder_attaches_present_false — a folder without .git still attaches, with present:false", async () => {
        const product = await store.upsertProduct({ name: "Acme" });
        const project = await store.upsertProject({
          productId: product.productId,
          name: "Web",
        });

        const folder = await opts.existingFolderNoGit();
        const attached = await store.attachRepo({
          projectId: project.projectId,
          localPath: folder,
        });

        expect(attached.repo).not.toBeNull();
        expect(attached.repo?.localPath).toBe(folder);
        expect(attached.repo?.present).toBe(false);
      });

      it("unlinkRepo clears the repo link without erroring", async () => {
        const product = await store.upsertProduct({ name: "Acme" });
        const project = await store.upsertProject({
          productId: product.productId,
          name: "Web",
        });

        const folder = await opts.existingFolderNoGit();
        await store.attachRepo({
          projectId: project.projectId,
          localPath: folder,
        });

        const unlinked = await store.unlinkRepo(project.projectId);
        expect(unlinked.repo).toBeNull();
      });
    });
  });
}
