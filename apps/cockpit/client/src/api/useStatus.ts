// WP-004 — useStatus(changeId) — GET /api/changes/:id/status.
//
// The read-time plain-English status + needs-attention flag for one
// change (FR-05/12). Disabled when changeId is empty so the hook is safe
// to mount above the URL-binding boundary. Goes through the typed apiGet
// funnel only — never the raw browser primitive (WPF-02; the client
// inventory gate enforces apiGet is the sole network caller).

import { useQuery } from "@tanstack/react-query";
import type { ChangeStatus } from "../../../shared/api-types";
import { apiGet } from "./client";

export function useStatus(changeId: string) {
  return useQuery({
    queryKey: ["change-status", changeId],
    queryFn: () => apiGet<ChangeStatus>(`/api/changes/${changeId}/status`),
    enabled: changeId.length > 0,
  });
}
