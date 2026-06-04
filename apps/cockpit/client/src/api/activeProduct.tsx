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

export interface ActiveProductValue {
  /** The active Product id, or null for the default (single-Product) scope. */
  activeProductId: string | null;
  /** Re-scope to another Product (the switch). */
  setActiveProductId: (productId: string | null) => void;
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
  initialActiveProductId?: string | null;
}) {
  const [activeProductId, setActiveProductId] = useState<string | null>(
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
