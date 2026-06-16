// WP-008 — readProducts (the Tenant's Products + the change→Product roll-up;
// FR-38, ADR-009).
//
// Sources the Tenant's Products from the brain's `dna:product` entities and
// builds the `change → Project → Product` roll-up index a board/search read
// scopes with. HONEST single-Product reality: the real brain has no Product
// entities minted yet, so when none are found readProducts synthesises ONE
// implicit Product (the single-Product Tenant trivial case) — the board still
// renders a switcher showing that one Product, and every change is in scope.
//
// Reading is fail-soft (parallel to readBrain): a malformed product file is
// skipped, an absent brain yields the implicit single Product.

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { mkdtemp, mkdir, writeFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { readProducts, IMPLICIT_PRODUCT_ID } from "../lib/products/readProducts";
import type { ChangeStoreRecord } from "../ports/ChangeStoreReader";

let dir: string;

beforeEach(async () => {
  dir = await mkdtemp(join(tmpdir(), "wp008-products-"));
});

afterEach(async () => {
  await rm(dir, { recursive: true, force: true });
});

/** Write a product entity into the brain's product-development/product tree. */
async function seedProduct(
  stateDir: string,
  ulid: string,
  name: string,
): Promise<void> {
  await seedProductRaw(stateDir, ulid, { name, sys_status: "active" });
}

/**
 * Write a product entity with caller-controlled fields — used by the WP-003
 * sys_status filter tests to plant a `deleted` entity, or one with no
 * `sys_status` at all (legacy back-compat).
 */
async function seedProductRaw(
  stateDir: string,
  ulid: string,
  fields: Record<string, unknown>,
): Promise<void> {
  const productDir = join(
    stateDir,
    ".brain",
    "instances",
    "product-development",
    "product",
  );
  await mkdir(productDir, { recursive: true });
  await writeFile(
    join(productDir, `${ulid}.jsonld`),
    JSON.stringify({ id: `dna:product:${ulid}`, ...fields }),
    "utf8",
  );
}

describe("readProducts (FR-38 — list Products, mark active, build roll-up)", () => {
  it("synthesises ONE implicit Product when the brain has none (single-Product trivial case)", async () => {
    const result = await readProducts({ sulisStateDir: dir });
    expect(result.list.products).toHaveLength(1);
    expect(result.list.products[0]?.name.length).toBeGreaterThan(0);
    // The single implicit Product is active by default.
    expect(result.list.products[0]?.active).toBe(true);
    expect(result.list.activeProductId).toBe(result.list.products[0]?.productId);
    // Empty roll-up index ⇒ every change in scope (the trivial case).
    expect(result.rollup.changeToProduct.size).toBe(0);
    expect(result.rollup.productIds).toEqual([result.list.products[0]?.productId]);
  });

  it("lists the Tenant's Products from the brain, marking the active one", async () => {
    await seedProduct(dir, "01ACME00000000000000000000", "Acme Checkout");
    await seedProduct(dir, "01HELP00000000000000000000", "Helpdesk");

    const result = await readProducts({ sulisStateDir: dir });
    const names = result.list.products.map((p) => p.name).sort();
    expect(names).toEqual(["Acme Checkout", "Helpdesk"]);
    // Exactly one is active.
    const active = result.list.products.filter((p) => p.active);
    expect(active).toHaveLength(1);
    expect(result.list.activeProductId).toBe(active[0]?.productId);
  });

  it("honours the requested active Product when it exists", async () => {
    await seedProduct(dir, "01ACME00000000000000000000", "Acme Checkout");
    await seedProduct(dir, "01HELP00000000000000000000", "Helpdesk");

    const result = await readProducts({
      sulisStateDir: dir,
      activeProductId: "dna:product:01HELP00000000000000000000",
    });
    expect(result.list.activeProductId).toBe(
      "dna:product:01HELP00000000000000000000",
    );
    expect(
      result.list.products.find((p) => p.active)?.name,
    ).toBe("Helpdesk");
  });

  it("falls back to the first Product when the requested active id is unknown", async () => {
    await seedProduct(dir, "01ACME00000000000000000000", "Acme Checkout");
    const result = await readProducts({
      sulisStateDir: dir,
      activeProductId: "dna:product:01NOPE0000000000000000000000",
    });
    // Unknown requested id ⇒ default to a real Product, never null when one exists.
    expect(result.list.activeProductId).toBe(
      "dna:product:01ACME00000000000000000000",
    );
  });

  it("skips a malformed product file rather than throwing (fail-soft)", async () => {
    await seedProduct(dir, "01ACME00000000000000000000", "Acme Checkout");
    const productDir = join(
      dir,
      ".brain",
      "instances",
      "product-development",
      "product",
    );
    await writeFile(join(productDir, "broken.jsonld"), "{ not json", "utf8");
    const result = await readProducts({ sulisStateDir: dir });
    expect(result.list.products.map((p) => p.name)).toEqual(["Acme Checkout"]);
  });
});

// WP-003 (ADR-020) — Remove = soft-delete via sys_status. The read side must
// hide entities whose sys_status ∈ {deleted, purged, archived}, while a
// legacy entity with no sys_status stays active (absence ≠ deleted).
//
// Characterisation-test-first (EP-07 / Non-Negotiable 3): this is a behaviour
// change to a read path. `shows_deleted_entity_today_characterisation` pins
// today's behaviour (a deleted entity IS shown) and must pass against the code
// BEFORE the filter is added; `hides_sys_status_deleted_entity` asserts the new
// behaviour and fails before the change. After GREEN, the characterisation's
// job (pinning the old behaviour) is done and it is inverted to assert the
// post-change reality — keeping the suite green.
describe("readProducts sys_status filter (WP-003, ADR-020)", () => {
  it("characterisation (post-change): a lone deleted Product yields the implicit single Product, not the removed one", async () => {
    // CHARACTERISATION (EP-07): in RED this pinned today's UNFILTERED behaviour
    // (the deleted Product was returned, confirmed passing against pre-change
    // code). After the filter landed (GREEN) its job is done, so it is inverted
    // to the post-change reality: a brain whose only Product is soft-deleted
    // surfaces zero real Products — the read falls back to the implicit single
    // Product (the existing empty-brain branch), and the removed one is gone.
    await seedProductRaw(dir, "01GONE00000000000000000000", {
      name: "Removed Product",
      sys_status: "deleted",
    });

    const result = await readProducts({ sulisStateDir: dir });
    const names = result.list.products.map((p) => p.name);
    expect(names).not.toContain("Removed Product");
    expect(result.list.products).toHaveLength(1);
    expect(result.list.products[0]?.productId).toBe(IMPLICIT_PRODUCT_ID);
  });

  it("hides_sys_status_deleted_entity: a soft-deleted Product is NOT returned", async () => {
    await seedProduct(dir, "01ACME00000000000000000000", "Acme Checkout");
    await seedProductRaw(dir, "01GONE00000000000000000000", {
      name: "Removed Product",
      sys_status: "deleted",
    });

    const result = await readProducts({ sulisStateDir: dir });
    const names = result.list.products.map((p) => p.name);
    expect(names).toContain("Acme Checkout");
    expect(names).not.toContain("Removed Product");
  });

  it("hides purged and archived entities too (the full removed set)", async () => {
    await seedProduct(dir, "01ACME00000000000000000000", "Acme Checkout");
    await seedProductRaw(dir, "01PURG00000000000000000000", {
      name: "Purged Product",
      sys_status: "purged",
    });
    await seedProductRaw(dir, "01ARCH00000000000000000000", {
      name: "Archived Product",
      sys_status: "archived",
    });

    const result = await readProducts({ sulisStateDir: dir });
    const names = result.list.products.map((p) => p.name);
    expect(names).toEqual(["Acme Checkout"]);
  });

  it("treats_missing_sys_status_as_active: a legacy entity with no sys_status still appears", async () => {
    await seedProductRaw(dir, "01LEGACY000000000000000000", {
      name: "Legacy Product",
      // no sys_status field at all
    });

    const result = await readProducts({ sulisStateDir: dir });
    const names = result.list.products.map((p) => p.name);
    expect(names).toContain("Legacy Product");
  });

  it("allow-list hardening: a PRESENT but unrecognised sys_status is hidden (not shown)", async () => {
    // A crafted / typo'd status must NOT slip through as active — the read side
    // shows a present status only when it is exactly "active" (allow-list), so
    // an unknown value is treated as not-active and hidden.
    await seedProduct(dir, "01ACME00000000000000000000", "Acme Checkout");
    await seedProductRaw(dir, "01WEIRD0000000000000000000", {
      name: "Crafted Status Product",
      sys_status: "actiVe", // not the exact sentinel; a deny-list would leak it
    });

    const result = await readProducts({ sulisStateDir: dir });
    const names = result.list.products.map((p) => p.name);
    expect(names).toContain("Acme Checkout");
    expect(names).not.toContain("Crafted Status Product");
  });
});

// The explicit change→Product link: a change's brain Change entity carries an
// optional `for_product`. That assignment is authoritative — it must drive the
// roll-up regardless of where the change's worktree sits (worktrees live under
// ~/.sulis/changes, never under a Project's repo root, so the path heuristic
// can't claim them). This is the read half of per-change product assignment.
describe("readProducts — explicit change.for_product assignment drives the roll-up", () => {
  async function seedChange(
    stateDir: string,
    ulid: string,
    fields: Record<string, unknown>,
  ): Promise<void> {
    const changeDir = join(
      stateDir,
      ".brain",
      "instances",
      "product-development",
      "change",
    );
    await mkdir(changeDir, { recursive: true });
    await writeFile(
      join(changeDir, `${ulid}.jsonld`),
      JSON.stringify({ id: `dna:change:${ulid}`, sys_status: "active", ...fields }),
      "utf8",
    );
  }

  function changeRecord(changeId: string): ChangeStoreRecord {
    return {
      changeId,
      handle: `CH-${changeId.slice(-6)}`,
      slug: "some-change",
      primitive: "feat",
      branch: `change/feat-${changeId}`,
      // Deliberately NOT under any Project repo root — proves the explicit link,
      // not the path, is what assigns the change.
      worktreePath: `/Users/x/.sulis/changes/${changeId}/worktree`,
      intent: "do a thing",
      baseBranch: "main",
      baseSha: null,
      createdAt: "2026-06-16T00:00:00Z",
      updatedAt: "2026-06-16T00:00:00Z",
      stage: "recon",
    };
  }

  it("rolls a change up to the Product named by its for_product link", async () => {
    await seedProduct(dir, "01ACME00000000000000000000", "Acme Checkout");
    await seedProduct(dir, "01HELP00000000000000000000", "Helpdesk");
    await seedChange(dir, "01CHG0000000000000000000AA", {
      handle: "CH-0000AA",
      for_product: "dna:product:01HELP00000000000000000000",
    });

    const result = await readProducts({
      sulisStateDir: dir,
      changes: [changeRecord("01CHG0000000000000000000AA")],
    });
    expect(result.rollup.changeToProduct.get("01CHG0000000000000000000AA")).toBe(
      "dna:product:01HELP00000000000000000000",
    );
  });

  it("ignores a for_product link that names a Product the Tenant no longer has", async () => {
    await seedProduct(dir, "01ACME00000000000000000000", "Acme Checkout");
    await seedChange(dir, "01CHG0000000000000000000BB", {
      for_product: "dna:product:01GONE0000000000000000000000",
    });

    const result = await readProducts({
      sulisStateDir: dir,
      changes: [changeRecord("01CHG0000000000000000000BB")],
    });
    // Unknown Product ⇒ unassigned (left out of the index), never a phantom link.
    expect(result.rollup.changeToProduct.has("01CHG0000000000000000000BB")).toBe(false);
  });

  it("leaves a change with no for_product unassigned (shown under All)", async () => {
    await seedProduct(dir, "01ACME00000000000000000000", "Acme Checkout");
    await seedProduct(dir, "01HELP00000000000000000000", "Helpdesk");
    await seedChange(dir, "01CHG0000000000000000000CC", { handle: "CH-0000CC" });

    const result = await readProducts({
      sulisStateDir: dir,
      changes: [changeRecord("01CHG0000000000000000000CC")],
    });
    expect(result.rollup.changeToProduct.has("01CHG0000000000000000000CC")).toBe(false);
  });
});
