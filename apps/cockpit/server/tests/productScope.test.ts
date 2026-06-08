// WP-008 — productScope (the change→Project→Product server-side roll-up; ADR-009, FR-37).
//
// This is the slice that PROMOTES WP-003's trivial single-Product scope to
// the full roll-up. The board's change list is scoped to the active Product
// server-side so a client never receives another Product's changes (FR-37,
// NFR-ARCH-01). A change rolls up to a Product via its Project
// (`change → Project → Product`); the roll-up is supplied as an explicit
// index (built by readProducts from the brain), keeping this filter pure
// and testable with two seeded Products.
//
// Honest-observability invariant (the real brain has no Products minted
// yet): the single-Product Tenant is the trivial case — one Product,
// implicitly active — so every change is in scope.

import { describe, it, expect } from "vitest";
import {
  scopeChangesToProduct,
  type ProductRollup,
} from "../lib/products/productScope";
import type { ChangeStoreRecord } from "../ports/ChangeStoreReader";

function record(overrides: Partial<ChangeStoreRecord> = {}): ChangeStoreRecord {
  return {
    changeId: "01ABC",
    handle: "CH-01ABC",
    slug: "demo",
    primitive: "create",
    branch: "change/demo",
    worktreePath: "/tmp/x",
    intent: "demo",
    baseBranch: "main",
    baseSha: "deadbeef",
    createdAt: "2026-05-01T00:00:00Z",
    updatedAt: "2026-05-01T00:00:00Z",
    stage: "specify",
    ...overrides,
  };
}

// Two seeded Products, each owning two changes (the multi-product case the
// observed-acceptance gate drives).
const ACME = "dna:product:01ACME00000000000000000000";
const HELP = "dna:product:01HELP00000000000000000000";

function twoProductRollup(): ProductRollup {
  return {
    productIds: [ACME, HELP],
    changeToProduct: new Map<string, string>([
      ["01A1", ACME],
      ["01A2", ACME],
      ["01H1", HELP],
      ["01H2", HELP],
    ]),
  };
}

const twoProductChanges: ChangeStoreRecord[] = [
  record({ changeId: "01A1" }),
  record({ changeId: "01H1" }),
  record({ changeId: "01A2" }),
  record({ changeId: "01H2" }),
];

describe("scopeChangesToProduct (the change→Project→Product roll-up; FR-37)", () => {
  it("returns ONLY the active Product's changes when two Products are seeded", () => {
    const scoped = scopeChangesToProduct(twoProductChanges, ACME, twoProductRollup());
    expect(scoped.map((c) => c.changeId)).toEqual(["01A1", "01A2"]);
  });

  it("re-scopes to the OTHER Product — the first Product's changes disappear (the switch)", () => {
    const scoped = scopeChangesToProduct(twoProductChanges, HELP, twoProductRollup());
    expect(scoped.map((c) => c.changeId)).toEqual(["01H1", "01H2"]);
    // No Acme change ever leaks across the seam (FR-37 "no other Product's change appears").
    expect(scoped.some((c) => c.changeId.startsWith("01A"))).toBe(false);
  });

  it("preserves the input order within the active Product's set", () => {
    // 01A2 appears after 01H1 in the input; scoping must keep 01A1 before 01A2.
    const scoped = scopeChangesToProduct(twoProductChanges, ACME, twoProductRollup());
    expect(scoped.map((c) => c.changeId)).toEqual(["01A1", "01A2"]);
  });

  it("returns an empty list for an unknown active Product id (no leak)", () => {
    const scoped = scopeChangesToProduct(
      twoProductChanges,
      "dna:product:01NOPE0000000000000000000000",
      twoProductRollup(),
    );
    expect(scoped).toEqual([]);
  });

  // ── The honest single-Product trivial case ───────────────────────────────
  it("returns ALL changes for the single-Product trivial case (one implicit Product)", () => {
    const rollup: ProductRollup = { productIds: [ACME], changeToProduct: new Map() };
    const all = [record({ changeId: "01A" }), record({ changeId: "01B" })];
    // With a single Product, every change is in scope regardless of the index.
    const scoped = scopeChangesToProduct(all, ACME, rollup);
    expect(scoped.map((c) => c.changeId)).toEqual(["01A", "01B"]);
  });

  it("returns ALL changes when there is no active Product yet (activeProductId null) and one implicit Product", () => {
    const rollup: ProductRollup = { productIds: [ACME], changeToProduct: new Map() };
    const all = [record({ changeId: "01A" }), record({ changeId: "01B" })];
    const scoped = scopeChangesToProduct(all, null, rollup);
    expect(scoped.map((c) => c.changeId)).toEqual(["01A", "01B"]);
  });

  it("returns ALL changes when no Products are known at all (empty Tenant — degrade to single implicit scope)", () => {
    const rollup: ProductRollup = { productIds: [], changeToProduct: new Map() };
    const all = [record({ changeId: "01A" })];
    expect(scopeChangesToProduct(all, null, rollup).map((c) => c.changeId)).toEqual([
      "01A",
    ]);
  });

  it("does not mutate the input array (read-only scope)", () => {
    const all = twoProductChanges;
    const before = all.length;
    const scoped = scopeChangesToProduct(all, ACME, twoProductRollup());
    expect(scoped).not.toBe(all);
    expect(all).toHaveLength(before);
  });
});
