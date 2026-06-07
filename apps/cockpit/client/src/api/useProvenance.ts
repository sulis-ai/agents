// WP-P05 — useProvenance(changeId) — GET /api/changes/:id/provenance (ADR-011).
//
// Returns the change's Provenance read projection (a ProvenanceView: digest +
// run-log + coverage). `useFocusedTrace(changeId, requirementId)` fetches the
// `?focus=<reqId>` variant — one requirement's FocusedTrace — and stays
// disabled until a requirement is selected. Both are disabled until a changeId
// is known, and fetched through the typed client (apiGet funnel) — never
// `fetch` in a component (WPF-02).

import { useQuery } from "@tanstack/react-query";
import type { FocusedTrace } from "../../../shared/api-types";
import { apiGet } from "./client";
import { provenanceQuery } from "./fileQueries";

export function useProvenance(changeId: string) {
  return useQuery({
    ...provenanceQuery(changeId),
    enabled: changeId.length > 0,
  });
}

export function useFocusedTrace(changeId: string, requirementId: string) {
  return useQuery({
    queryKey: ["provenance", changeId, "focus", requirementId],
    queryFn: () =>
      apiGet<FocusedTrace>(
        `/api/changes/${changeId}/provenance?focus=${encodeURIComponent(
          requirementId,
        )}`,
      ),
    enabled: changeId.length > 0 && requirementId.length > 0,
  });
}
