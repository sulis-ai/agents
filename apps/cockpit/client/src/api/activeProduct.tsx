// WP-008 — active-Product UI scope (FR-37/38, ADR-009).
//
// The active Product is the founder's view scope — the read-side equivalent
// of a query parameter (ADR-009). It lives as client UI state and threads
// into every board/search read as `?product=<id>`; switching it re-scopes
// the SAME board (ADR-005). It is NOT persisted and writes nothing — picking
// a Product mints nothing and starts no session (FR-38 read-only).
//
// The default scope is `null` (no `?product=` → the single-Product trivial
// case / the server's default active Product), so a tree rendered WITHOUT a
// provider behaves exactly as it did before this slice — existing views are
// unaffected.

import { createContext, useContext, useMemo, useState, type ReactNode } from "react";
import type { ProductScope } from "../lib/productCounts";

export interface ActiveProductValue {
  /**
   * The active board scope: null = All, the UNASSIGNED_SCOPE sentinel, or a
   * product id. WP-005 widened this from a bare product id to the scope
   * vocabulary so "Unassigned" is a first-class, client-derived scope.
   */
  activeProductId: ProductScope;
  /** Re-scope (the switch): null = All, UNASSIGNED_SCOPE, or a product id. */
  setActiveProductId: (scope: ProductScope) => void;
}

const ActiveProductContext = createContext<ActiveProductValue>({
  activeProductId: null,
  setActiveProductId: () => {},
});

export function ActiveProductProvider({
  children,
  initialActiveProductId = null,
}: {
  children: ReactNode;
  initialActiveProductId?: ProductScope;
}) {
  const [activeProductId, setActiveProductId] = useState<ProductScope>(
    initialActiveProductId,
  );
  const value = useMemo<ActiveProductValue>(
    () => ({ activeProductId, setActiveProductId }),
    [activeProductId],
  );
  return (
    <ActiveProductContext.Provider value={value}>
      {children}
    </ActiveProductContext.Provider>
  );
}

/** Read (and set) the active-Product UI scope. */
export function useActiveProduct(): ActiveProductValue {
  return useContext(ActiveProductContext);
}
