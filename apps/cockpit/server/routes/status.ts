// WP-004 — GET /api/changes/:id/status (FR-04/05/12).
//
// Returns a ChangeStatus computed at READ time (FR-05) — the plain-English
// "what's happening" headline + the needs-attention flag. Nothing is
// persisted; the status is derived fresh on every GET from:
//   - the change record (requireChange → 404 for an unknown id),
//   - the located + parsed transcript (the conversation shape),
//   - the liveness probe (is the session alive?),
//   - the read-time open-BLOCKER check.
//
// Composes existing reads — no new port (TDD §2.1). GET-only; the
// read-only gate proves no mutation verb or process start lives here.

import { Router } from "express";

// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits; the rule's `../../*` pattern is intended to block escapes out of apps/cockpit/, which `import/no-restricted-paths` already enforces correctly)
import type { ChangeStatus } from "../../shared/api-types";
import type { ChangeStoreReader } from "../ports/ChangeStoreReader";
import { locateTranscripts } from "../lib/locateTranscripts";
import { parseTranscripts } from "../lib/parseTranscripts";
import { probeLiveness } from "../lib/probeLiveness";
import { detectOpenBlocker } from "../lib/detectOpenBlocker";
import { computeStatus } from "../lib/computeStatus";

import { asyncHandler } from "./_async";
import { requireChange } from "./_change-lookup";

export interface StatusRouterDeps {
  changeStore: ChangeStoreReader;
  sulisStateDir: string;
  claudeProjectsDir: string;
}

export function createStatusRouter(deps: StatusRouterDeps): Router {
  const router = Router({ mergeParams: true });
  router.get(
    "/",
    asyncHandler(async (req, res) => {
      const { id } = req.params as { id: string };
      const record = await requireChange(deps.changeStore, id);

      const [liveness, transcriptPaths, hasOpenBlocker] = await Promise.all([
        probeLiveness(deps.sulisStateDir, id),
        locateTranscripts(record.worktreePath, deps.claudeProjectsDir),
        detectOpenBlocker(record.worktreePath),
      ]);
      const transcript = await parseTranscripts(transcriptPaths);

      const body: ChangeStatus = computeStatus({
        record,
        transcript,
        liveness,
        hasOpenBlocker,
      });
      res.json(body);
    }),
  );
  return router;
}
