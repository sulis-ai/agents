// WP-003 — scopeChangesToActiveProduct (server-side read scope; ADR-009).
//
// The seam owns Product scope (NFR-ARCH-01): the board's change list is
// scoped to the active Product server-side so a client never receives
// another Product's changes (FR-37). For this slice the single-Product
// Tenant is the trivial case — one Product, implicitly active — so every
// change in the store IS the active Product's change set. The full
// change→Project→Product roll-up and the switcher ship in journey K
// (WP-008, ADR-009); this is the seam they extend.
//
// It returns a fresh array (read-only scope: never mutate the store's
// records in place).

import type { ChangeStoreRecord } from "../ports/ChangeStoreReader";

/**
 * Scope the full change set to the active Product. Trivial single-Product
 * case: returns every change (a shallow copy). When WP-008 lands the
 * `change → Project → Product` roll-up, this is where the active-Product
 * filter is applied — callers (the board/search reads) are unchanged.
 */
export function scopeChangesToActiveProduct(
  all: readonly ChangeStoreRecord[],
): ChangeStoreRecord[] {
  // Trivial case: one implicit Product → all changes are in scope.
  return all.slice();
}
