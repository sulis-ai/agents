// WP-003 — useContractPreview(changeId) — GET /api/changes/:id/contract
//
// Returns the contract-preview availability summary for a change: whether
// its rendered data + UI contracts are reachable, and (when ready) what the
// manifest carries. The per-change "open data contract / open UI" links read
// this to decide what to render — present / no-UI note / unavailable.
//
// Data goes through the typed apiGet funnel (WPF-02 — never `fetch` in a
// component). Disabled for an empty id so a consumer can mount before a
// change is selected.

import { useQuery } from "@tanstack/react-query";
import type { ContractAvailability } from "../../../shared/api-types";
import { apiGet } from "./client";

export function useContractPreview(changeId: string) {
  return useQuery({
    queryKey: ["contract-preview", changeId],
    queryFn: () =>
      apiGet<ContractAvailability>(`/api/changes/${changeId}/contract`),
    enabled: changeId.length > 0,
  });
}
