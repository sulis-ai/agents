// WP-003 — scopeChangesToActiveProduct helper (server-side read scope).
//
// The seam owns Product scope (ADR-009, NFR-ARCH-01): the board's change
// list is scoped to the active Product server-side so a client never
// receives another Product's changes. For this slice the single-Product
// Tenant is the trivial case (one Product, implicitly active) → the
// helper returns every change. The full change→Project→Product roll-up
// and the switcher ship in journey K (WP-008); this helper is the seam
// it extends.

import { describe, it, expect } from "vitest";
import { scopeChangesToActiveProduct } from "../lib/scopeChangesToActiveProduct";
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

describe("scopeChangesToActiveProduct", () => {
  it("returns all changes for the trivial single-Product case (FR-37 trivial)", () => {
    const all = [record({ changeId: "01A" }), record({ changeId: "01B" })];
    const scoped = scopeChangesToActiveProduct(all);
    expect(scoped.map((c) => c.changeId)).toEqual(["01A", "01B"]);
  });

  it("returns an empty list unchanged", () => {
    expect(scopeChangesToActiveProduct([])).toEqual([]);
  });

  it("does not mutate the input array (read-only scope)", () => {
    const all = [record({ changeId: "01A" })];
    const scoped = scopeChangesToActiveProduct(all);
    expect(scoped).not.toBe(all);
    expect(all).toHaveLength(1);
  });
});
