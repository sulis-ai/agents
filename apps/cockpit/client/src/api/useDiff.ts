// WP-011 — useDiff(changeId, path) — GET /api/changes/:id/diff?path=...
//
// Returns { base, current } strings (or null markers per TDD §7) for
// the file's base-vs-current diff. Disabled when path is empty.

import { useQuery } from "@tanstack/react-query";
import { diffQuery } from "./fileQueries";

export function useDiff(changeId: string, path: string) {
  return useQuery({
    ...diffQuery(changeId, path),
    enabled: changeId.length > 0 && path.length > 0,
  });
}
