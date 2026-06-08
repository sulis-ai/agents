// WP-011 — useFile(changeId, path) — GET /api/changes/:id/file?path=...
//
// Returns one file's contents (or a binary/truncated marker per
// TDD §5). Disabled when path is empty so the consumer can mount the
// hook before a file is selected.

import { useQuery } from "@tanstack/react-query";
import { fileQuery } from "./fileQueries";

export function useFile(changeId: string, path: string) {
  return useQuery({
    ...fileQuery(changeId, path),
    enabled: changeId.length > 0 && path.length > 0,
  });
}
