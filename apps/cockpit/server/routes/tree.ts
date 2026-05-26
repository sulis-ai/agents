// WP-010 — GET /api/changes/:id/tree?path=...
//
// Reads one level of the worktree's file/folder tree under `path`
// (default `""` = the worktree root). Delegates path-sanitisation +
// directory listing to `readWorktreeTree` (WP-006); the route layer
// only validates inputs, picks the right error class, and shapes JSON.

import { Router } from "express";

import type { ChangeStoreReader } from "../ports/ChangeStoreReader";
import { readWorktreeTree } from "../lib/readWorktreeTree";

import { asyncHandler } from "./_async";
import { requireChange } from "./_change-lookup";
import { resolveWorktreeRoot } from "./_worktree";

export interface TreeRouterDeps {
  changeStore: ChangeStoreReader;
}

export function createTreeRouter(deps: TreeRouterDeps): Router {
  const router = Router({ mergeParams: true });
  router.get(
    "/",
    asyncHandler(async (req, res) => {
      const { id } = req.params as { id: string };
      const record = await requireChange(deps.changeStore, id);
      const worktreeRoot = await resolveWorktreeRoot(record.worktreePath);
      const rawPath = (req.query.path as string | undefined) ?? "";
      const nodes = await readWorktreeTree(worktreeRoot, rawPath);
      res.json(nodes);
    }),
  );
  return router;
}
