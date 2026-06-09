// WP-010 — GET /api/changes.
// WP-003 — scoped to the active Product server-side (ADR-009, FR-37).
// WP-008 — promoted to the full change→Project→Product roll-up: the optional
//   `?product=<id>` selects the active Product (the stateless all-GET scope
//   variant, ADR-009); the seam returns only that Product's changes. The
//   single-Product Tenant remains the trivial case (every change in scope).
// WP-002 — the feed is ENRICHED (ADR-002): each row now also carries the
//   FR-12 attention verdict, the new health verdict, and lastActivityAt —
//   gathered per record by the shared `gatherChangeEnrichment` helper (the
//   search route uses the same helper, so the board and search agree). The
//   gathering is best-effort / never-throws (BR-11): no record can 500 the
//   feed; a degraded record renders with honest unknown reads. The per-record
//   fan-out stays inside this ONE bounded Promise.all (MUC-2 / A-3) — no
//   per-card request, no second poll.
//
// Thin handler: list records → scope to the active Product (the shared
// _product-scope helper) → gather liveness + enrichment per record → shape
// into the wire `Change[]`.

import { Router } from "express";

// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits; the rule's `../../*` pattern is intended to block escapes out of apps/cockpit/, which `import/no-restricted-paths` already enforces correctly)
import type { Change } from "../../shared/api-types";
import type { ChangeStoreReader } from "../ports/ChangeStoreReader";
import { gatherChangeEnrichment } from "../lib/gatherChangeEnrichment";

import { asyncHandler } from "./_async";
import { toWireChange } from "./_change-lookup";
import { listScopedChanges, readProductQuery } from "./_product-scope";

export interface ChangesRouterDeps {
  changeStore: ChangeStoreReader;
  sulisStateDir: string;
  claudeProjectsDir: string;
}

export function createChangesRouter(deps: ChangesRouterDeps): Router {
  const router = Router();
  router.get(
    "/",
    asyncHandler(async (req, res) => {
      // The seam owns Product scope (ADR-009): the client never receives
      // another Product's changes. The single-Product Tenant is the trivial
      // case (every change in scope); the full roll-up scopes to the active
      // Product when two or more exist.
      const records = await listScopedChanges(
        deps.changeStore,
        deps.sulisStateDir,
        readProductQuery(req.query.product),
      );
      const enriched: Change[] = await Promise.all(
        records.map(async (record) => {
          const { liveness, enrichment } = await gatherChangeEnrichment(
            deps,
            record,
          );
          return toWireChange(record, liveness, enrichment);
        }),
      );
      res.json(enriched);
    }),
  );
  return router;
}
