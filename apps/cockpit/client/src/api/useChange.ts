// WP-011 — useChange(changeId) — GET /api/changes/:id.
//
// One change's metadata + transcript paths. Disabled when changeId is
// empty so the hook is safe to mount above the URL-binding boundary.

import { useQuery } from "@tanstack/react-query";
import type { ChangeDetail } from "../../../shared/api-types";
import { apiGet } from "./client";

export function useChange(changeId: string) {
  return useQuery({
    queryKey: ["change", changeId],
    queryFn: () => apiGet<ChangeDetail>(`/api/changes/${changeId}`),
    enabled: changeId.length > 0,
  });
}
