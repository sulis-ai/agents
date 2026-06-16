// WP-005 — <ProductSwitcher> the board scope switcher (ADR-002, EP-03).
//
// REORGANISE-Refactor: the switcher now renders the shared <ProductControl
// mode="scope"> primitive (WP-002) rather than its own bespoke menu — one
// product vocabulary across the three homes (switcher, change-nav property,
// board card). The refinement (signed design, Concerns A1 + C1):
//   - "All products" is the resting default + the explicit top item, rendered
//     with an everything (grid) tile — NOT a product called "All";
//   - "Unassigned" is a first-class scope (dashed tile) just under All — a
//     CLIENT-derived scope (the server has no "unassigned" value; it's the
//     All feed filtered to forProduct == null, TDD);
//   - every row carries a LIVE count, derived client-side from the already-
//     fetched (All-scoped) change list (productCounts; no new endpoint);
//   - the header echoes the active scope ("Viewing <scope> · N changes") with
//     a one-tap "× clear" back to All when scoped away from it.
//
// Read-only (FR-38): selecting a scope fires only `onSelect` — it mints
// nothing, starts no session, performs no write. The board re-scope is the
// parent's data refetch (or, for Unassigned, a client filter), not a mutation.
//
// The neutral two-letter monogram() is still exported here (the locked cockpit
// decision: the tile is chrome, not brand decoration) and reused by
// ProductControl + OnboardingChat (EP-03) — never re-implemented.

import type { Change, Product } from "../../../shared/api-types";
import { ProductControl, type ProductRow } from "./ProductControl";
import {
  UNASSIGNED_SCOPE,
  countForScope,
  type ProductScope,
} from "../lib/productCounts";
import styles from "./ProductSwitcher.module.css";

// The All-products row id. A client sentinel that maps to the `null` scope
// (every change); kept distinct from a product id and from UNASSIGNED_SCOPE so
// the synthetic + real rows never collide.
const ALL_SCOPE_ROW_ID = "__all__";

export interface ProductSwitcherProps {
  products: Product[];
  /** The active scope: null = All, UNASSIGNED_SCOPE, or a product id. */
  activeProductId: ProductScope;
  /** Re-scope: null = All, UNASSIGNED_SCOPE = unassigned, else a product id. */
  onSelect: (scope: ProductScope) => void;
  /**
   * The already-fetched (All-scoped) change list, for the live per-row counts +
   * the header echo. Derived client-side (TDD); defaults to none.
   */
  changes?: Change[];
  /** "Set up a new product" foot action (routes to settings). */
  onSetUpNew?: () => void;
  /** "Manage products" foot action (WP-007 wires it; optional here). */
  onManageProducts?: () => void;
}

/**
 * The neutral two-letter monogram for a Product name: the initials of the
 * first two words, else the first two letters. Always upper-case; never empty.
 */
export function monogram(name: string): string {
  const words = name.trim().split(/\s+/).filter((w) => w.length > 0);
  if (words.length >= 2) {
    return (words[0]![0]! + words[1]![0]!).toUpperCase();
  }
  const first = words[0] ?? "";
  return (first.slice(0, 2) || "?").toUpperCase();
}

/** The human label for the active scope, for the header echo. */
function scopeName(scope: ProductScope, products: Product[]): string {
  if (scope === null) return "All products";
  if (scope === UNASSIGNED_SCOPE) return "Unassigned";
  return products.find((p) => p.productId === scope)?.name ?? "All products";
}

export function ProductSwitcher({
  products,
  activeProductId,
  onSelect,
  changes = [],
  onSetUpNew,
  onManageProducts,
}: ProductSwitcherProps) {
  // Nothing to switch when the Tenant has no Products at all.
  if (products.length === 0) return null;

  // An activeProductId that matches no known scope reads as "All" (safe
  // fallback — never a blank header), preserving the old switcher's behaviour.
  const knownProduct =
    typeof activeProductId === "string" &&
    activeProductId !== UNASSIGNED_SCOPE &&
    products.some((p) => p.productId === activeProductId);
  const scope: ProductScope =
    activeProductId === null ||
    activeProductId === UNASSIGNED_SCOPE ||
    knownProduct
      ? activeProductId
      : null;

  // The scope rows: All (everything-tile) → Unassigned (dashed) → each product
  // (monogram). Each carries a live count derived from the All-scoped feed.
  const rows: ProductRow[] = [
    {
      productId: ALL_SCOPE_ROW_ID,
      name: "All products",
      glyph: "all-grid",
      count: countForScope(changes, null),
    },
    {
      productId: UNASSIGNED_SCOPE,
      name: "Unassigned",
      glyph: "unassigned-dashed",
      count: countForScope(changes, UNASSIGNED_SCOPE),
    },
    ...products.map<ProductRow>((p) => ({
      productId: p.productId,
      name: p.name,
      glyph: "monogram",
      count: countForScope(changes, p.productId),
    })),
  ];

  // ProductControl uses a string `selectedId`; the All scope maps to the All
  // row sentinel, and a row select maps back to the scope vocabulary.
  const selectedId = scope === null ? ALL_SCOPE_ROW_ID : scope;

  function onRowSelect(rowId: string | null) {
    onSelect(rowId === ALL_SCOPE_ROW_ID || rowId === null ? null : rowId);
  }

  const scopeLabel = scopeName(scope, products);
  const scopeCount = countForScope(changes, scope);
  // "× clear" only appears when scoped away from All (there's somewhere to go
  // back to). At the All scope there is nothing to clear.
  const showClear = scope !== null;
  // The trigger's accessible name always carries the active scope + its count
  // ("Viewing All products, 23 changes"), so a screen reader announces the
  // scope even at narrow widths where the visible "Viewing <scope>" text folds
  // to the monogram tile + chevron (IDEAS.md §5 — the name folds, but stays on
  // the accessible name).
  const triggerLabel = `Viewing ${scopeLabel}, ${scopeCount} ${
    scopeCount === 1 ? "change" : "changes"
  }`;

  return (
    <div className={styles.pswitch}>
      <ProductControl
        mode="scope"
        rows={rows}
        selectedId={selectedId}
        triggerLabel={triggerLabel}
        onSelect={onRowSelect}
        onSetUpNew={onSetUpNew}
        onManageProducts={onManageProducts}
      />

      {/* The header echo — the active scope is always named in the chrome so
          the founder never wonders what they're looking at (Concern A1). The
          count rides the text; "× clear" returns to All when scoped. */}
      <div className={styles.scopeHeader} data-testid="product-scope-header">
        <span>
          Viewing <strong>{scopeLabel}</strong> · {scopeCount}{" "}
          {scopeCount === 1 ? "change" : "changes"}
        </span>
        {showClear && (
          <button
            type="button"
            className={styles.clearScope}
            aria-label="Clear scope, view all products"
            onClick={() => onSelect(null)}
          >
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
              aria-hidden="true"
            >
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
            All products
          </button>
        )}
      </div>
    </div>
  );
}
