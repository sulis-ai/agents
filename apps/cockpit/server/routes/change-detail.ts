// WP-010 — GET /api/changes/:id.
//
// Returns one ChangeDetail = Change (with liveness) + transcriptPaths.
// 404 if the change id is unknown.

import { Router } from "express";

// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits; the rule's `../../*` pattern is intended to block escapes out of apps/cockpit/, which `import/no-restricted-paths` already enforces correctly)
import type { ChangeDetail } from "../../shared/api-types";
import type { ChangeStoreReader } from "../ports/ChangeStoreReader";
import { locateTranscripts } from "../lib/locateTranscripts";
import { probeLiveness } from "../lib/probeLiveness";

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
      const [liveness, transcriptPaths] = await Promise.all([
        probeLiveness(deps.sulisStateDir, id),
        locateTranscripts(record.worktreePath, deps.claudeProjectsDir),
      ]);
      const body: ChangeDetail = {
        ...toWireChange(record, liveness),
        transcriptPaths,
      };
      res.json(body);
    }),
  );
  return router;
}
