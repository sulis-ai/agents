// Files redesign (Direction B) — useChanged(changeId) —
// GET /api/changes/:id/changed
//
// The change's changed-files set (base commit → worktree): the data
// behind the "All files ↔ Changed · N" scope switch and the worded
// new/edited/removed status badges. Read-only; cached per change.

import { useQuery } from "@tanstack/react-query";
import type { ChangedFiles } from "../../../shared/api-types";
import { apiGet } from "./client";

export function useChanged(changeId: string) {
  return useQuery({
    queryKey: ["changed", changeId],
    queryFn: () => apiGet<ChangedFiles>(`/api/changes/${changeId}/changed`),
    enabled: changeId.length > 0,
  });
}
