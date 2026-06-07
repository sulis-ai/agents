// Shared queryKey + queryFn definitions for the change's LEFT-NAV view reads.
//
// One definition per read so the React Query HOOK and the hover-PREFETCH share
// exactly the same key + queryFn (DRY/EP-03 — no duplicated request logic).
// Each builder returns `{ queryKey, queryFn }` ready to spread into
// `useQuery(...)` or `queryClient.prefetchQuery(...)`.
//
// These cover the LIVE view reads (transcript / turn-summaries / contract /
// advanced) that back the Conversation, Preview, and Advanced views. Unlike the
// static worktree reads in fileQueries.ts, these carry the QueryClient's short
// defaults (no longer staleTime baked in) — the consuming hooks add their own
// `enabled` / `refetchInterval`. The static file-tree reads
// (tree/changed/provenance) live in fileQueries.ts and are reused as-is.

import type {
  ContractAvailability,
  TranscriptMessage,
} from "../../../shared/api-types";
import { apiGet } from "./client";
import type { AdvancedData } from "./useAdvanced";
import type { TurnSummaries } from "./useTurnSummaries";

export function transcriptQuery(changeId: string) {
  return {
    queryKey: ["transcript", changeId] as const,
    queryFn: () =>
      apiGet<TranscriptMessage[]>(`/api/changes/${changeId}/transcript`),
  };
}

export function turnSummariesQuery(changeId: string) {
  return {
    queryKey: ["turn-summaries", changeId] as const,
    queryFn: () =>
      apiGet<TurnSummaries>(`/api/changes/${changeId}/turn-summaries`),
  };
}

export function contractPreviewQuery(changeId: string) {
  return {
    queryKey: ["contract-preview", changeId] as const,
    queryFn: () =>
      apiGet<ContractAvailability>(`/api/changes/${changeId}/contract`),
  };
}

export function advancedQuery(changeId: string) {
  return {
    queryKey: ["advanced", changeId] as const,
    queryFn: () => apiGet<AdvancedData>(`/api/changes/${changeId}/advanced`),
  };
}
