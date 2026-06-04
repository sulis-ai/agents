// Chat-redesign (chat-B2) — useTurnSummaries(changeId).
//
// GET /api/changes/:id/turn-summaries → { turnKey -> summary }. The server
// generates summaries in the background (Haiku, cached), so this refetches on
// an interval to pick newly-generated ones up. The Turn Card falls back to the
// first few sentences for any turn whose summary isn't ready yet — so a missing
// entry is never an error, just "not generated yet".

import { useQuery } from "@tanstack/react-query";
import { apiGet } from "./client";

export interface TurnSummaries {
  /** turnKey -> generated summary. */
  summaries: Record<string, string>;
  /** turnKeys currently being generated (for the "summarising…" cue). */
  generating: string[];
}

export function useTurnSummaries(changeId: string) {
  return useQuery({
    queryKey: ["turn-summaries", changeId],
    queryFn: () =>
      apiGet<TurnSummaries>(`/api/changes/${changeId}/turn-summaries`),
    enabled: changeId.length > 0,
    // Background generation fills in over a few cycles; poll to pick it up.
    refetchInterval: 5000,
    staleTime: 0,
  });
}
