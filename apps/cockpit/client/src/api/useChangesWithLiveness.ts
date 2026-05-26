// WP-012 — useChangesWithLiveness — GET /api/changes with 10s polling.
//
// Sibling hook to useChanges (WP-011). Shares the ["changes"] query
// key — TanStack Query dedupes, so every reader of the changes list
// benefits from the freshness automatically (TDD §6.1, ADR-007).
//
// This is the one polling exception ADR-007 permits.

import { useQuery } from "@tanstack/react-query";
import type { Change } from "../../../shared/api-types";
import { apiGet } from "./client";
import { LIVENESS_POLL_MS } from "../config";

export function useChangesWithLiveness() {
  return useQuery({
    queryKey: ["changes"],
    queryFn: () => apiGet<Change[]>("/api/changes"),
    refetchInterval: LIVENESS_POLL_MS,
  });
}
