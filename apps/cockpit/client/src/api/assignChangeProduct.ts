// assignChangeProduct — set a change's Product (per-change assignment).
//
// PUT /api/changes/:id/product through the client fetch funnel. On success it
// invalidates the board feed (every product scope) and the change detail so the
// product filter + the picker reflect the new assignment without a reload.

import { useMutation, useQueryClient } from "@tanstack/react-query";

import type { AssignChangeProductResult } from "../../../shared/api-types";

import { apiPut } from "./client";

// The result shape is pinned ONCE in the shared wire contract (WP-001;
// shared/api-types.ts) and re-exported here for existing call sites — there is
// no second copy to drift (CF-02 / DRY). The new un-assign sibling lives next
// to it as `ClearChangeProductResult`.
export type { AssignChangeProductResult };

export function assignChangeProduct(
  changeId: string,
  productId: string,
): Promise<AssignChangeProductResult> {
  return apiPut<AssignChangeProductResult>(
    `/api/changes/${encodeURIComponent(changeId)}/product`,
    { productId },
  );
}

/** Mutation hook for the change-detail product picker. */
export function useAssignChangeProduct(changeId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (productId: string) => assignChangeProduct(changeId, productId),
    onSuccess: () => {
      // The board feed under any product scope (["changes", <scope>]) + the
      // change detail (["change", id]) both reflect the new link.
      void queryClient.invalidateQueries({ queryKey: ["changes"] });
      void queryClient.invalidateQueries({ queryKey: ["change", changeId] });
    },
  });
}
