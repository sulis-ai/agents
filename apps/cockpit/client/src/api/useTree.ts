// WP-011 — useTree(changeId) — GET /api/changes/:id/tree.
//
// Returns the worktree tree (one level at a time per TDD §5; the
// client expands directories lazily — that interaction lives in
// WP-014).

import { useQuery } from "@tanstack/react-query";
import type { TreeNode } from "../../../shared/api-types";
import { apiGet } from "./client";

export function useTree(changeId: string) {
  return useQuery({
    queryKey: ["tree", changeId],
    queryFn: () => apiGet<TreeNode[]>(`/api/changes/${changeId}/tree`),
    enabled: changeId.length > 0,
  });
}
