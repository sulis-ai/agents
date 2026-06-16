// WP-008 — shared Product-scope helpers for the board/search/products reads
// (FR-37/38, ADR-009).
//
// Three routes consume the active-Product scope (products, changes, search),
// so the `?product=` parse and the change→Product roll-up application live
// here once (DRY; EP-03 / WPB-12) rather than being copied into each handler.
//
// DECISION (ADR-009 builder's choice): the active Product arrives as the
// optional `?product=<id>` query param — the stateless all-GET variant. The
// seam stays read-only (no POST /api/products/active), so the read-only gate
// needs no scope-selection classification.

import type { ChangeStoreReader, ChangeStoreRecord } from "../ports/ChangeStoreReader";
import { readProducts } from "../lib/products/readProducts";
import { scopeChangesToProduct } from "../lib/products/productScope";

/**
 * Normalise the `?product=` query value into an active-Product id or null.
 * Express gives a string for one value, a string[] for repeated params (we
 * take the first), or undefined when absent.
 */
export function readProductQuery(raw: unknown): string | null {
  if (typeof raw === "string" && raw.length > 0) return raw;
  if (Array.isArray(raw)) {
    const first = raw.find((v): v is string => typeof v === "string" && v.length > 0);
    return first ?? null;
  }
  return null;
}

/**
 * List the full change set, then scope it to the active Product server-side
 * (FR-37). The roll-up (`change → Project → Product`) is computed at the seam
 * so a client never receives another Product's changes. The single-Product
 * Tenant is the trivial case — every change is in scope.
 */
export async function listScopedChanges(
  changeStore: ChangeStoreReader,
  sulisStateDir: string,
  requestedProduct: string | null,
): Promise<ChangeStoreRecord[]> {
  const allRecords = await changeStore.listAllChanges();
  const { rollup } = await readProducts({
    sulisStateDir,
    activeProductId: requestedProduct,
    changes: allRecords,
  });
  // "All" scope: when no specific Product is requested (`requestedProduct` is
  // null), show EVERY change — a Product is a filter layered on top of All,
  // never a default that hides changes. scopeChangesToProduct already returns
  // the full set for a null scope; we pass the raw request through rather than
  // the resolved first Product, which previously hid every change the moment a
  // second Product existed (a change's worktree never lives under a Project's
  // repo root, so the roll-up could match nothing). A real Product id still
  // filters to that Product's changes.
  return scopeChangesToProduct(allRecords, requestedProduct, rollup);
}
