// Files redesign (Direction B) — useChanged(changeId) —
// GET /api/changes/:id/changed
//
// The change's changed-files set (base commit → worktree): the data
// behind the "All files ↔ Changed · N" scope switch and the worded
// new/edited/removed status badges. Read-only; cached per change.

import { useQuery } from "@tanstack/react-query";
import { changedQuery } from "./fileQueries";

export function useChanged(changeId: string) {
  return useQuery({
    ...changedQuery(changeId),
    enabled: changeId.length > 0,
  });
}
