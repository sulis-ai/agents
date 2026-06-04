// WP-007 — useSearch — GET /api/search (FR-10/11/12).
//
// Journey D round-trip, client data hook: given the active filters
// (q / stage[] / needsAttention), fetch the matching changes. The board
// (WP-003) renders the results in the SAME stage-column layout when any
// filter is active (ADR-005 — never a separate results screen).
//
// The query is built here (not via apiGet's Record<string,string> params)
// because the stage filter is a REPEATED param (?stage=design&stage=ship,
// the FR-11 array contract) which a flat record can't express.
//
// The hook is `enabled` only when a filter is active; with no filter the
// board falls back to the full `useChangesWithLiveness` list. Data is
// fetched through the typed client funnel (apiGet) — never `fetch` here
// (WPF-02). The query key carries the filter args so TanStack Query
// caches per distinct filter set.

import { useQuery } from "@tanstack/react-query";
import type { Change, WorkflowStage } from "../../../shared/api-types";
import { apiGet } from "./client";

export interface SearchArgs {
  /** Free-text content query (FR-10). */
  q: string;
  /** Stage allow-list (FR-11). */
  stages: WorkflowStage[];
  /** Needs-attention filter (FR-12). */
  needsAttention: boolean;
}

/** True when at least one filter is active (so the board should search). */
export function hasActiveFilter(args: SearchArgs): boolean {
  return (
    args.q.trim().length > 0 ||
    args.stages.length > 0 ||
    args.needsAttention
  );
}

/**
 * Build `/api/search?…` with repeated `stage` params (the FR-11 array). WP-008:
 * when a Product is active the search is scoped to it (`?product=<id>`, ADR-009)
 * so a filter can never surface another Product's change (FR-37).
 */
function buildSearchPath(args: SearchArgs, activeProductId: string | null): string {
  const params = new URLSearchParams();
  if (activeProductId) params.set("product", activeProductId);
  const q = args.q.trim();
  if (q.length > 0) params.set("q", q);
  for (const stage of args.stages) params.append("stage", stage);
  if (args.needsAttention) params.set("needsAttention", "true");
  const qs = params.toString();
  return qs.length > 0 ? `/api/search?${qs}` : "/api/search";
}

export function useSearch(args: SearchArgs, activeProductId: string | null = null) {
  return useQuery({
    queryKey: [
      "search",
      activeProductId,
      args.q.trim(),
      [...args.stages].sort(),
      args.needsAttention,
    ],
    queryFn: () =>
      apiGet<{ results: Change[] }>(buildSearchPath(args, activeProductId)).then(
        (r) => r.results,
      ),
    enabled: hasActiveFilter(args),
  });
}
