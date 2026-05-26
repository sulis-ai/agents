// WP-010 — GET /api/changes.
//
// Returns every change in the change store, each row enriched with
// liveness. Thin handler: list records → probe liveness per record →
// shape into the wire `Change[]`.

import { Router } from "express";

// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits; the rule's `../../*` pattern is intended to block escapes out of apps/cockpit/, which `import/no-restricted-paths` already enforces correctly)
import type { Change } from "../../shared/api-types";
import type { ChangeStoreReader } from "../ports/ChangeStoreReader";
import { probeLiveness } from "../lib/probeLiveness";

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
      const records = await deps.changeStore.listAllChanges();
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
