// WP-010 — GET /api/changes/:id.
// WP-002 — the single-change detail carries the SAME enrichment the board
//   list does (ADR-002): liveness + the FR-12 attention verdict + the new
//   health verdict + lastActivityAt, gathered by the shared
//   `gatherChangeEnrichment` helper so list and detail agree. Best-effort /
//   never-throws (BR-11): a degraded change still returns its detail.
//
// Returns one ChangeDetail = enriched Change + transcriptPaths.
// 404 if the change id is unknown.

import { Router } from "express";

// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits; the rule's `../../*` pattern is intended to block escapes out of apps/cockpit/, which `import/no-restricted-paths` already enforces correctly)
import type { ChangeDetail } from "../../shared/api-types";
import type { ChangeStoreReader } from "../ports/ChangeStoreReader";
import { locateTranscripts } from "../lib/locateTranscripts";
import { gatherChangeEnrichment } from "../lib/gatherChangeEnrichment";

import { asyncHandler } from "./_async";
import { requireChange, toWireChange } from "./_change-lookup";

export interface ChangeDetailRouterDeps {
  changeStore: ChangeStoreReader;
  sulisStateDir: string;
  claudeProjectsDir: string;
}

export function createChangeDetailRouter(deps: ChangeDetailRouterDeps): Router {
  const router = Router({ mergeParams: true });
  router.get(
    "/",
    asyncHandler(async (req, res) => {
      const { id } = req.params as { id: string };
      const record = await requireChange(deps.changeStore, id);
      const [enriched, transcriptPaths] = await Promise.all([
        gatherChangeEnrichment(deps, record),
        locateTranscripts(record.worktreePath, deps.claudeProjectsDir),
      ]);
      const body: ChangeDetail = {
        ...toWireChange(record, enriched.liveness, enriched.enrichment),
        transcriptPaths,
      };
      res.json(body);
    }),
  );
  return router;
}
