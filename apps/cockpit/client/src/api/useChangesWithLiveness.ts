// WP-012 — useChangesWithLiveness — GET /api/changes with 10s polling.
//
// Sibling hook to useChanges (WP-011). Shares the ["changes"] query
// key — TanStack Query dedupes, so every reader of the changes list
// benefits from the freshness automatically (TDD §6.1, ADR-007).
//
// This is the one polling exception ADR-007 permits.
//
// WP-008 — the board fetch is scoped to the active Product (ADR-009): when a
// Product is active the request carries `?product=<id>` and the query key
// includes it, so switching Products re-fetches the SAME board scoped to the
// new Product (ADR-005). A null product (the single-Product trivial case)
// keeps the original `/api/changes` request unchanged; the `["changes"]`
// key prefix still matches for invalidation (RefreshButton).

import { useQuery } from "@tanstack/react-query";
import type { Change } from "../../../shared/api-types";
import { apiGet } from "./client";
import { LIVENESS_POLL_MS } from "../config";
import { scopeToProductParam, type ProductScope } from "../lib/productCounts";

export function useChangesWithLiveness(activeProductId: ProductScope = null) {
  // WP-005 — the Unassigned scope is CLIENT-derived: the server scopes only by
  // ?product=<id> and has no "unassigned" value (TDD), so the sentinel is
  // stripped to null here (fetch the FULL list) and the Unassigned narrowing
  // happens client-side at the board (filterChangesByScope). All / a real
  // product behave exactly as before.
  const productParam = scopeToProductParam(activeProductId);
  return useQuery({
    queryKey: ["changes", productParam],
    queryFn: () =>
      apiGet<Change[]>(
        "/api/changes",
        productParam ? { product: productParam } : undefined,
      ),
    refetchInterval: LIVENESS_POLL_MS,
  });
}
