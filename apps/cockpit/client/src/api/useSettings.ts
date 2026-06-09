// WP-008 — useSettings — GET /api/settings (ADR-019/020).
//
// The Settings page's read source: the whole editable store (active entities
// only) as the Products → Projects → Repo tree. Data is fetched through the
// WP-007 typed client (getSettings → apiGet funnel) — never `fetch` directly
// (WPF-02). getSettings() is errors-are-values: it returns a typed Result, so
// here we unwrap it inside the queryFn — an `{ ok:false }` becomes a thrown
// SettingsQueryError so TanStack Query's `isError` branch (the page's generic
// retry state) engages; a genuine transport failure already rejects and is
// surfaced the same way (WP-007 contract).
//
// SETTINGS_QUERY_KEY is the ONE shared cache key for this seam (WP-008 Contract
// "query key shared and documented here"). A mutation from WP-009 invalidates
// this key to refresh the tree, and invalidates ["products"] so the board's
// product switcher (useProducts) reflects a product rename/remove.

import { useQuery } from "@tanstack/react-query";
import type { SettingsTree } from "../../../shared/api-types";
import { getSettings, type SettingsError } from "./settings";

/** The shared cache key for the settings tree (WP-008). */
export const SETTINGS_QUERY_KEY = ["settings"] as const;

/** The product-switcher cache key a settings write must also invalidate. */
export const PRODUCTS_QUERY_KEY = ["products"] as const;

/** A typed settings error raised into the query so `isError` engages. */
export class SettingsQueryError extends Error {
  readonly code: SettingsError["code"];
  constructor(error: SettingsError) {
    super(error.message);
    this.name = "SettingsQueryError";
    this.code = error.code;
  }
}

export function useSettings() {
  return useQuery<SettingsTree, Error>({
    queryKey: SETTINGS_QUERY_KEY,
    queryFn: async () => {
      const result = await getSettings();
      if (!result.ok) throw new SettingsQueryError(result.error);
      return result.value;
    },
  });
}
