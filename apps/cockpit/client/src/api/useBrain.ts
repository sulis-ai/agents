// WP-006 — useBrain(changeId) — GET /api/changes/:id/brain (FR-06/07).
//
// Returns the change's brain entities grouped by kind (a BrainView).
// Disabled until a changeId is known. Fetched through the typed client
// (apiGet funnel) — never `fetch` in a component (WPF-02).

import { useQuery } from "@tanstack/react-query";
import type { BrainView } from "../../../shared/api-types";
import { apiGet } from "./client";

export function useBrain(changeId: string) {
  return useQuery({
    queryKey: ["brain", changeId],
    queryFn: () => apiGet<BrainView>(`/api/changes/${changeId}/brain`),
    enabled: changeId.length > 0,
  });
}
