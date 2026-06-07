// Shared queryKey + queryFn definitions for the static file-tree reads.
//
// One definition per read so the React Query HOOK and the hover-PREFETCH
// share exactly the same key + queryFn (DRY/EP-03 — no duplicated request
// logic). Each builder returns `{ queryKey, queryFn }` ready to spread into
// `useQuery(...)` or `queryClient.prefetchQuery(...)`.
//
// These cover the worktree's STATIC reads — the worktree is unchanging
// within a session, so they also carry a longer `staleTime`/`gcTime`
// (FILE_QUERY_CACHE) so re-navigation and repeated hovers don't refetch.
// Live data (chat / transcript / turn-summaries / liveness) is NOT routed
// through here and keeps the QueryClient's short defaults.

import type {
  ChangeOriginView,
  ChangedFiles,
  FileContents,
  FileDiff,
  OriginView,
  ProvenanceView,
  TreeNode,
} from "../../../shared/api-types";
import { apiGet } from "./client";

/**
 * Cache policy for the static worktree reads. The worktree is fixed within
 * a session, so:
 *   - staleTime 60s — re-navigating to a folder/file already fetched is a
 *     cache hit, no refetch; hover-prefetch is gated by this (a second hover
 *     within 60s won't refire).
 *   - gcTime 5min — cached folders/files stay warm long after they leave
 *     the screen, so drilling back in is instant.
 */
export const FILE_QUERY_CACHE = {
  staleTime: 60_000,
  gcTime: 5 * 60_000,
} as const;

export function treeQuery(changeId: string, path = "") {
  return {
    queryKey: ["tree", changeId, path] as const,
    queryFn: () =>
      apiGet<TreeNode[]>(
        `/api/changes/${changeId}/tree`,
        path ? { path } : undefined,
      ),
    ...FILE_QUERY_CACHE,
  };
}

export function fileQuery(changeId: string, path: string) {
  return {
    queryKey: ["file", changeId, path] as const,
    queryFn: () =>
      apiGet<FileContents>(`/api/changes/${changeId}/file`, { path }),
    ...FILE_QUERY_CACHE,
  };
}

export function diffQuery(changeId: string, path: string) {
  return {
    queryKey: ["diff", changeId, path] as const,
    queryFn: () => apiGet<FileDiff>(`/api/changes/${changeId}/diff`, { path }),
    ...FILE_QUERY_CACHE,
  };
}

export function changedQuery(changeId: string) {
  return {
    queryKey: ["changed", changeId] as const,
    queryFn: () => apiGet<ChangedFiles>(`/api/changes/${changeId}/changed`),
    ...FILE_QUERY_CACHE,
  };
}

export function originQuery(changeId: string) {
  return {
    queryKey: ["origin", changeId] as const,
    queryFn: () => apiGet<ChangeOriginView>(`/api/changes/${changeId}/origin`),
    ...FILE_QUERY_CACHE,
  };
}

export function fileOriginQuery(changeId: string, path: string) {
  return {
    queryKey: ["origin", changeId, "path", path] as const,
    queryFn: () =>
      apiGet<OriginView>(
        `/api/changes/${changeId}/origin?path=${encodeURIComponent(path)}`,
      ),
    ...FILE_QUERY_CACHE,
  };
}

export function provenanceQuery(changeId: string) {
  return {
    queryKey: ["provenance", changeId] as const,
    queryFn: () =>
      apiGet<ProvenanceView>(`/api/changes/${changeId}/provenance`),
    ...FILE_QUERY_CACHE,
  };
}
