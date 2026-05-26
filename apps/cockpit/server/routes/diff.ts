// WP-010 — GET /api/changes/:id/diff?path=...
//
// Returns { base, current } strings for Monaco's DiffEditor to render
// (ADR-006). Reads via `readFileDiff` (WP-008). 422 when the change
// has no baseSha (legacy records); 504 if the underlying `git show`
// times out; 400 on path-traversal or git error; 404 on unknown id.

import { Router } from "express";

import type { ChangeStoreReader } from "../ports/ChangeStoreReader";
import { readFileDiff } from "../lib/readFileDiff";

import { asyncHandler } from "./_async";
import { requireChange } from "./_change-lookup";
import { resolveWorktreeRoot } from "./_worktree";
import { BadRequestError, NoBaseShaError } from "../middleware/errors";

export interface DiffRouterDeps {
  changeStore: ChangeStoreReader;
  gitTimeoutMs?: number;
  fileMaxBytes?: number;
}

export function createDiffRouter(deps: DiffRouterDeps): Router {
  const router = Router({ mergeParams: true });
  router.get(
    "/",
    asyncHandler(async (req, res) => {
      const { id } = req.params as { id: string };
      const record = await requireChange(deps.changeStore, id);
      if (record.baseSha === null) {
        throw new NoBaseShaError(id);
      }
      const rawPath = req.query.path;
      if (typeof rawPath !== "string" || rawPath.length === 0) {
        throw new BadRequestError("missing required query parameter: path");
      }
      const worktreeRoot = await resolveWorktreeRoot(record.worktreePath);
      const diff = await readFileDiff(worktreeRoot, record.baseSha, rawPath, {
        maxBytes: deps.fileMaxBytes,
        timeoutMs: deps.gitTimeoutMs,
      });
      res.json(diff);
    }),
  );
  return router;
}
