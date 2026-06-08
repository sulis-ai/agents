// Chat-redesign (chat-B2) — GET /api/changes/:id/turn-summaries.
//
// Returns `{ turnKey -> summary }` for the change's agent turns. Composes the
// same read path as the transcript route (locateTranscripts → parseTranscripts)
// then getTurnSummaries (cache-first; kicks off background Haiku generation for
// the most-recent uncached turns). Non-blocking: returns whatever's cached now.

import { Router } from "express";

import type { ChangeStoreReader } from "../ports/ChangeStoreReader";
import { locateTranscripts } from "../lib/locateTranscripts";
import { parseTranscripts } from "../lib/parseTranscripts";
import { getTurnSummaries } from "../lib/turnSummaries";

import { asyncHandler } from "./_async";
import { requireChange } from "./_change-lookup";

export interface TurnSummariesRouterDeps {
  changeStore: ChangeStoreReader;
  claudeProjectsDir: string;
}

export function createTurnSummariesRouter(deps: TurnSummariesRouterDeps): Router {
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
      const summaries = await getTurnSummaries(messages);
      res.json(summaries);
    }),
  );
  return router;
}
