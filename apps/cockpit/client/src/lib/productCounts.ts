// WP-005 — the one client-side product count + scope helper (ADR-002, TDD
// "Counts & the 'Unassigned' scope — client-derived").
//
// The switcher's per-row counts and the board's Unassigned view are BOTH
// derived from the already-fetched (All-scoped) change list — no new endpoint
// (TDD). This module is the SINGLE home for that derivation (the WP's Blue
// 2-consumer extraction: the switcher's row counts AND the board's scope
// filter both call here, so the predicate lives in exactly one place).
//
// The scope vocabulary is a small superset of the existing `string | null`
// (null = All, a product id = that product). WP-005 adds a first-class
// "Unassigned" scope as a CLIENT sentinel: the server scopes only by
// `?product=<id>` and has no "unassigned" value, so the sentinel must never
// reach the wire. `scopeToProductParam` strips it (both All and Unassigned
// fetch the full list) and `filterChangesByScope` applies the Unassigned
// predicate (forProduct == null) on the client.

import type { Change } from "../../../shared/api-types";
// The scope sentinels live ONCE in `shared/chatScope.ts` (the single vocabulary
// home — the per-product chat scope and these board sentinels share one token,
// WP-001 / CL-05). Re-exported here so existing client importers keep working.
import { ALL_SCOPE, UNASSIGNED_SCOPE } from "../../../shared/chatScope";

export { ALL_SCOPE, UNASSIGNED_SCOPE };

/**
 * The active board scope: `null` = All products (every change), a product id =
 * that product (scoped server-side), or the `UNASSIGNED_SCOPE` sentinel =
 * changes with no product (filtered client-side).
 */
export type ProductScope = string | null;

/** True when the change has no product (null or undefined `forProduct`). */
function isUnassigned(change: Change): boolean {
  return change.forProduct == null;
}

/**
 * The count of changes in a scope, over the already-fetched (All-scoped) list:
 *   - All (`null`)            → total changes;
 *   - Unassigned (sentinel)   → changes with no product;
 *   - a product id            → changes assigned to that product.
 */
export function countForScope(changes: Change[], scope: ProductScope): number {
  if (scope === null) return changes.length;
  if (scope === UNASSIGNED_SCOPE) return changes.filter(isUnassigned).length;
  return changes.filter((c) => c.forProduct === scope).length;
}

/**
 * The `?product=` value to send for a scope, or `null` for none. The All scope
 * and the Unassigned sentinel both return `null` (the full list is fetched and
 * — for Unassigned — narrowed client-side), so the server contract is never
 * widened with a synthetic scope value.
 */
export function scopeToProductParam(scope: ProductScope): string | null {
  if (scope === null || scope === UNASSIGNED_SCOPE) return null;
  return scope;
}

/**
 * Narrow a fetched change list to a scope on the client. For All and a real
 * product scope this is a pass-through (the server already scoped, or there's
 * nothing to narrow); for Unassigned it keeps only the changes with no product.
 */
export function filterChangesByScope(
  changes: Change[],
  scope: ProductScope,
): Change[] {
  if (scope === UNASSIGNED_SCOPE) return changes.filter(isUnassigned);
  return changes;
}
