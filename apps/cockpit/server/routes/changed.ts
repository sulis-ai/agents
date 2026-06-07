// Files redesign (Direction B) — GET /api/changes/:id/changed
//
// Returns the change's changed-files set (base commit → worktree) for
// the repo-browser's "All files ↔ Changed · N" scope. Read-only:
// delegates the diff to `readChangedFiles` (which composes the
// sanctioned git boundary); the route layer only looks up the change,
// resolves the worktree root, and shapes JSON.

import { Router } from "express";

import type { ChangeStoreReader } from "../ports/ChangeStoreReader";
import { readChangedFiles } from "../lib/readChangedFiles";

import { asyncHandler } from "./_async";
import { requireChange } from "./_change-lookup";
import { resolveWorktreeRoot } from "./_worktree";

export interface ChangedRouterDeps {
  changeStore: ChangeStoreReader;
  /** Override the 5 s git timeout (tests). */
  gitTimeoutMs?: number;
}

export function createChangedRouter(deps: ChangedRouterDeps): Router {
  const router = Router({ mergeParams: true });
  router.get(
    "/",
    asyncHandler(async (req, res) => {
      const { id } = req.params as { id: string };
      const record = await requireChange(deps.changeStore, id);
      const worktreeRoot = await resolveWorktreeRoot(record.worktreePath);
      const changed = await readChangedFiles(worktreeRoot, record.baseSha, {
        ...(deps.gitTimeoutMs !== undefined
          ? { timeoutMs: deps.gitTimeoutMs }
          : {}),
      });
      res.json(changed);
    }),
  );
  return router;
}
