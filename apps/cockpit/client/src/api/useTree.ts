// WP-011 — useTree(changeId, path) — GET /api/changes/:id/tree?path=...
//
// Returns one level of the worktree tree. `path` selects which
// directory to list ("" = the worktree root). The client expands
// directories lazily by mounting one useTree per expanded directory
// (the interaction WP-014 delivers); the server route (WP-010) and
// reader (WP-006) already accept the `path` query parameter, so the
// lazy-expansion wiring is purely client-side.
//
// `path` defaults to "" so existing single-arg root callers are
// unchanged. The query key includes `path` so each directory caches
// independently.
//
// `enabled` lets a caller defer loading until ready — e.g. a collapsed
// directory node mounts the hook for React's rules-of-hooks but must not
// request its children until the founder expands it. It defaults to
// `true`, so root callers are unchanged; it is AND-ed with the changeId
// guard.

import { useQuery } from "@tanstack/react-query";
import type { TreeNode } from "../../../shared/api-types";
import { apiGet } from "./client";

interface Options {
  /** Defer the fetch until the caller is ready (default true). */
  enabled?: boolean;
}

export function useTree(changeId: string, path = "", options: Options = {}) {
  const { enabled = true } = options;
  return useQuery({
    queryKey: ["tree", changeId, path],
    queryFn: () =>
      apiGet<TreeNode[]>(
        `/api/changes/${changeId}/tree`,
        path ? { path } : undefined,
      ),
    enabled: enabled && changeId.length > 0,
  });
}
