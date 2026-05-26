// WP-011 — useDiff(changeId, path) — GET /api/changes/:id/diff?path=...
//
// Returns { base, current } strings (or null markers per TDD §7) for
// the file's base-vs-current diff. Disabled when path is empty.

import { useQuery } from "@tanstack/react-query";
import type { FileDiff } from "../../../shared/api-types";
import { apiGet } from "./client";

export function useDiff(changeId: string, path: string) {
  return useQuery({
    queryKey: ["diff", changeId, path],
    queryFn: () =>
      apiGet<FileDiff>(`/api/changes/${changeId}/diff`, { path }),
    enabled: changeId.length > 0 && path.length > 0,
  });
}
