// Chat-redesign follow-on — the change "Advanced" (operator) view.
//
//   GET  /api/changes/:id/advanced            → { branchUrl, processes }
//   POST /api/changes/:id/reveal              → reveal a folder (default: the
//                                                worktree) in the file manager
//   POST /api/changes/:id/processes/:pid/stop → stop a linked process (guarded)
//
// The client already has the worktree path + branch (from the change record);
// this supplies the things it can't compute (the GitHub link, the live process
// list) and performs the two OS-side actions.

import { Router } from "express";

import type { ChangeStoreReader } from "../ports/ChangeStoreReader";
import {
  branchUrl,
  listChangeProcesses,
  revealInFileManager,
  stopProcess,
} from "../lib/changeAdvanced";

import { asyncHandler } from "./_async";
import { requireChange } from "./_change-lookup";

export interface AdvancedRouterDeps {
  changeStore: ChangeStoreReader;
}

export function createAdvancedRouter(deps: AdvancedRouterDeps): Router {
  const router = Router({ mergeParams: true });

  router.get(
    "/advanced",
    asyncHandler(async (req, res) => {
      const { id } = req.params as { id: string };
      const record = await requireChange(deps.changeStore, id);
      const [url, processes] = await Promise.all([
        branchUrl(record.worktreePath, record.branch),
        listChangeProcesses(id, record.worktreePath),
      ]);
      res.json({ branchUrl: url, processes });
    }),
  );

  router.post(
    "/reveal",
    asyncHandler(async (req, res) => {
      const { id } = req.params as { id: string };
      const record = await requireChange(deps.changeStore, id);
      const body = (req.body ?? {}) as { path?: unknown };
      const target =
        typeof body.path === "string" && body.path.trim()
          ? body.path
          : record.worktreePath;
      const result = await revealInFileManager(target);
      res.status(result.ok ? 200 : 400).json(result);
    }),
  );

  router.post(
    "/processes/:pid/stop",
    asyncHandler(async (req, res) => {
      const { id, pid } = req.params as { id: string; pid: string };
      // Resolve the change so an unknown id 404s consistently with the rest.
      await requireChange(deps.changeStore, id);
      const result = stopProcess(Number(pid));
      res.status(result.ok ? 200 : 400).json(result);
    }),
  );

  return router;
}
