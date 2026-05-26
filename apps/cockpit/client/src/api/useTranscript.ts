// WP-011 — useTranscript(changeId) — GET /api/changes/:id/transcript.
//
// Returns the chronologically-merged transcript messages (TDD §4 /
// ADR-004 association heuristic). The rendering of the messages is
// owned by WP-013; this hook just supplies the array.

import { useQuery } from "@tanstack/react-query";
import type { TranscriptMessage } from "../../../shared/api-types";
import { apiGet } from "./client";

export function useTranscript(changeId: string) {
  return useQuery({
    queryKey: ["transcript", changeId],
    queryFn: () =>
      apiGet<TranscriptMessage[]>(`/api/changes/${changeId}/transcript`),
    enabled: changeId.length > 0,
  });
}
