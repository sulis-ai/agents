// WP-008 — productScope: the change→Project→Product server-side roll-up
// (ADR-009, FR-37, NFR-ARCH-01).
//
// The seam owns Product scope: the board's change list is scoped to the
// active Product server-side so a client never receives another Product's
// changes (FR-37). A change rolls up to a Product via its Project
// (`change → Project → Product`); the roll-up is supplied as an explicit
// index (`ProductRollup`, built by `readProducts` from the brain), keeping
// this filter PURE and trivially testable with two seeded Products.
//
// HONEST single-Product reality (the real brain has no Products minted
// yet): the single-Product Tenant is the trivial case — one Product,
// implicitly active — so every change is in scope. This is what
// `scopeChangesToActiveProduct` (WP-003) modelled; this slice promotes it
// to the full roll-up while preserving that trivial case exactly.
//
// Read-only: returns a fresh array, never mutating the store's records.

import type { ChangeStoreRecord } from "../../ports/ChangeStoreReader";

/**
 * The `change → Project → Product` roll-up, resolved once per read:
 *   - `productIds`      — every Product the Tenant has (one for the trivial
 *                         single-Product case).
 *   - `changeToProduct` — change id → owning Product id, for the changes
 *                         whose Project could be resolved. A change absent
 *                         from this map rolls up to the single implicit
 *                         Product (the trivial case) — see below.
 */
export interface ProductRollup {
  productIds: string[];
  changeToProduct: Map<string, string>;
}

/**
 * Scope the full change set to the active Product (FR-37).
 *
 * The trivial single-Product case is preserved exactly: when the Tenant has
 * zero or one Product, every change is in scope regardless of the index
 * (there is nothing to disambiguate). Only when TWO OR MORE Products exist
 * does the roll-up index narrow the set to the active Product's changes — and
 * a change with no resolved Project is left OUT of a specific Product's scope
 * (it cannot be claimed by a Product it doesn't roll up to).
 *
 * An unknown `activeProductId` (not among `productIds`) yields an empty list:
 * the seam never leaks another Product's changes when asked for a Product it
 * doesn't recognise.
 */
export function scopeChangesToProduct(
  all: readonly ChangeStoreRecord[],
  activeProductId: string | null,
  rollup: ProductRollup,
): ChangeStoreRecord[] {
  // Trivial single-Product (or empty) Tenant: one implicit Product owns
  // everything. This is the WP-003 behaviour, preserved.
  if (rollup.productIds.length <= 1) {
    return all.slice();
  }

  // Multi-Product: scope to the active Product. With no active selection we
  // cannot disambiguate, so fall back to the full set (the board defaults to
  // showing everything rather than hiding changes) — the client always
  // supplies the active Product once it has read the Product list.
  if (activeProductId === null) {
    return all.slice();
  }

  // Unknown Product id ⇒ empty (no leak).
  if (!rollup.productIds.includes(activeProductId)) {
    return [];
  }

  return all.filter(
    (record) => rollup.changeToProduct.get(record.changeId) === activeProductId,
  );
}
