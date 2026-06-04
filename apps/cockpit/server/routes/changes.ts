// WP-010 — GET /api/changes.
// WP-003 — scoped to the active Product server-side (ADR-009, FR-37).
//
// Returns the active Product's in-flight change set, each row enriched
// with liveness. Thin handler: list records → scope to active Product →
// probe liveness per record → shape into the wire `Change[]`. For this
// slice the single-Product Tenant is the trivial case, so the scope helper
// returns every change; the shape is unchanged.

import { Router } from "express";

// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits; the rule's `../../*` pattern is intended to block escapes out of apps/cockpit/, which `import/no-restricted-paths` already enforces correctly)
import type { Change } from "../../shared/api-types";
import type { ChangeStoreReader } from "../ports/ChangeStoreReader";
import { probeLiveness } from "../lib/probeLiveness";
import { scopeChangesToActiveProduct } from "../lib/scopeChangesToActiveProduct";

import { asyncHandler } from "./_async";
import { toWireChange } from "./_change-lookup";

export interface ChangesRouterDeps {
  changeStore: ChangeStoreReader;
  sulisStateDir: string;
}

export function createChangesRouter(deps: ChangesRouterDeps): Router {
  const router = Router();
  router.get(
    "/",
    asyncHandler(async (_req, res) => {
      const allRecords = await deps.changeStore.listAllChanges();
      // The seam owns Product scope (ADR-009): the client never receives
      // another Product's changes. Trivial single-Product case = all.
      const records = scopeChangesToActiveProduct(allRecords);
      const enriched: Change[] = await Promise.all(
        records.map(async (record) => {
          const liveness = await probeLiveness(
            deps.sulisStateDir,
            record.changeId,
          );
          return toWireChange(record, liveness);
        }),
      );
      res.json(enriched);
    }),
  );
  return router;
}
