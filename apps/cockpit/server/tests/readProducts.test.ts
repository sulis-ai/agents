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
import { readProducts } from "../lib/products/readProducts";

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
    JSON.stringify({ id: `dna:product:${ulid}`, name, sys_status: "active" }),
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
