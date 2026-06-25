// WP-003 — derive the wire `ChatScope` from the board's active product scope.
//
// The dock reads the SAME `useActiveProduct()` store the board reads (ADR-001:
// one switch moves both surfaces, no second active-product store). That store's
// value is a `ProductScope` (`string | null`, where `null` is the All-products
// overview and `UNASSIGNED_SCOPE` is the reserved triage scope). This single
// helper maps it to the `product:{...}` wire key the chat API speaks (ADR-002),
// reusing the ONE scope vocabulary in `shared/chatScope.ts` (no second source).

import type { ChatScope } from "../../../shared/api-types";
import { ALL_SCOPE, UNASSIGNED_SCOPE } from "../../../shared/chatScope";
import type { ProductScope } from "./productCounts";

/**
 * Map the board's active `ProductScope` to the chat's wire `ChatScope`:
 *   - `null`               → `product:__all__`        (the overview chat)
 *   - `UNASSIGNED_SCOPE`   → `product:__unassigned__` (reserved triage scope)
 *   - a product id         → `product:{id}`
 *
 * One switch, both surfaces: because the dock derives its scope from the same
 * store the board keys off, the board and the chat always move together.
 */
export function chatScopeForProduct(scope: ProductScope): ChatScope {
  if (scope === null) return `product:${ALL_SCOPE}`;
  if (scope === UNASSIGNED_SCOPE) return `product:${UNASSIGNED_SCOPE}`;
  return `product:${scope}`;
}

/** True for the cross-product overview scope (`product:__all__`), which must ask
 * which product new work belongs to before filing a card (ADR-004). */
export function isOverviewScope(scope: ProductScope): boolean {
  return scope === null;
}
