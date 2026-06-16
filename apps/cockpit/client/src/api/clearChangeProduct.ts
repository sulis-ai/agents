// clearChangeProduct — clear a change's Product link (per-change un-assign).
//
// DELETE /api/changes/:id/product through the client fetch funnel. On success
// it invalidates the board feed (every product scope) and the change detail so
// the Unassigned count + the product chip reflect the cleared link without a
// reload. The un-assign sibling of assignChangeProduct.ts — same funnel, same
// invalidation shape (no divergent caching logic, EP-03 parity).

import { useMutation, useQueryClient } from "@tanstack/react-query";

import type { ClearChangeProductResult } from "../../../shared/api-types";

import { apiDelete } from "./client";

// The result shape is pinned ONCE in the shared wire contract (WP-001;
// shared/api-types.ts) and re-exported here for call sites — there is no
// second copy to drift (CF-02 / DRY). `forProduct` is explicitly `null` (the
// cleared sibling of the assign result; ADR-001 "explicit beats inferred").
export type { ClearChangeProductResult };

export function clearChangeProduct(
  changeId: string,
): Promise<ClearChangeProductResult> {
  return apiDelete<ClearChangeProductResult>(
    `/api/changes/${encodeURIComponent(changeId)}/product`,
  );
}

/** Mutation hook for the change-detail product picker's un-assign action. */
export function useClearChangeProduct(changeId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => clearChangeProduct(changeId),
    onSuccess: () => {
      // The board feed under any product scope (["changes", <scope>]) + the
      // change detail (["change", id]) both reflect the cleared link (mirrors
      // useAssignChangeProduct so assign + un-assign stay cache-consistent).
      void queryClient.invalidateQueries({ queryKey: ["changes"] });
      void queryClient.invalidateQueries({ queryKey: ["change", changeId] });
    },
  });
}
