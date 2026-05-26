// WP-010 — GET /api/changes/:id/transcript.
//
// Returns the chronologically-merged TranscriptMessage[] for a change.
// Compose: locateTranscripts (WP-009) → parseTranscripts (WP-009).
// Empty when no transcripts match the change's worktree (e.g. the
// change never had a Claude session yet).

import { Router } from "express";

import type { ChangeStoreReader } from "../ports/ChangeStoreReader";
import { locateTranscripts } from "../lib/locateTranscripts";
import { parseTranscripts } from "../lib/parseTranscripts";

import { asyncHandler } from "./_async";
import { requireChange } from "./_change-lookup";

export interface TranscriptRouterDeps {
  changeStore: ChangeStoreReader;
  claudeProjectsDir: string;
}

export function createTranscriptRouter(deps: TranscriptRouterDeps): Router {
  const router = Router({ mergeParams: true });
  router.get(
    "/",
    asyncHandler(async (req, res) => {
      const { id } = req.params as { id: string };
      const record = await requireChange(deps.changeStore, id);
      const paths = await locateTranscripts(
        record.worktreePath,
        deps.claudeProjectsDir,
      );
      const messages = await parseTranscripts(paths);
      res.json(messages);
    }),
  );
  return router;
}
