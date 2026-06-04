// WP-008 — useProducts — GET /api/products (FR-38, ADR-009).
//
// Returns the Tenant's Products with the active one marked, for the product
// switcher. Read-only; the single-Product Tenant is the trivial case (one
// Product, shown active — synthesised server-side). Data is fetched through
// the typed funnel (apiGet) — never `fetch` directly (WPF-02).

import { useQuery } from "@tanstack/react-query";
import type { ProductList } from "../../../shared/api-types";
import { apiGet } from "./client";

export function useProducts() {
  return useQuery({
    queryKey: ["products"],
    queryFn: () => apiGet<ProductList>("/api/products"),
  });
}
