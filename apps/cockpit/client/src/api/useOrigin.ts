// WP-P09 — useOrigin(changeId) — GET /api/changes/:id/origin (ADR-012).
//
// Returns the change's per-file inferred origin list (a ChangeOriginView: one
// FileOrigin per changed file). `useFileOrigin(changeId, path)` fetches the
// `?path=<rel>` variant — one file's OriginView — and stays disabled until a
// path is chosen. Both are disabled until a changeId is known, and fetched
// through the typed client (apiGet funnel) — never `fetch` in a component
// (WPF-02). Every origin carries the honest `attribution` flag ("inferred" now;
// "recorded" once stamping lands — the badge flips with no UI change, ADR-012).

import { useQuery } from "@tanstack/react-query";
import type { ChangeOriginView, OriginView } from "../../../shared/api-types";
import { apiGet } from "./client";

export function useOrigin(changeId: string) {
  return useQuery({
    queryKey: ["origin", changeId],
    queryFn: () =>
      apiGet<ChangeOriginView>(`/api/changes/${changeId}/origin`),
    enabled: changeId.length > 0,
  });
}

export function useFileOrigin(changeId: string, path: string) {
  return useQuery({
    queryKey: ["origin", changeId, "path", path],
    queryFn: () =>
      apiGet<OriginView>(
        `/api/changes/${changeId}/origin?path=${encodeURIComponent(path)}`,
      ),
    enabled: changeId.length > 0 && path.length > 0,
  });
}
