// WP-011 — useChanges — GET /api/changes.
//
// Returns the full set of changes visible to the founder. Liveness
// re-polling lives in a sibling hook in WP-012 (it overrides
// refetchInterval on the same query key).

import { useQuery } from "@tanstack/react-query";
import type { Change } from "../../../shared/api-types";
import { apiGet } from "./client";

export function useChanges() {
  return useQuery({
    queryKey: ["changes"],
    queryFn: () => apiGet<Change[]>("/api/changes"),
  });
}
