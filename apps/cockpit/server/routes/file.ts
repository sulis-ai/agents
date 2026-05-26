// WP-010 — GET /api/changes/:id/file?path=...
//
// Reads one file's contents (capped at 1 MiB by `readFileContents`).
// `path` is required; missing → 400 BAD_REQUEST.

import { Router } from "express";

import type { ChangeStoreReader } from "../ports/ChangeStoreReader";
import { readFileContents } from "../lib/readFileContents";

import { asyncHandler } from "./_async";
import { requireChange } from "./_change-lookup";
import { resolveWorktreeRoot } from "./_worktree";
import { BadRequestError } from "../middleware/errors";

export interface FileRouterDeps {
  changeStore: ChangeStoreReader;
  fileMaxBytes?: number;
}

export function createFileRouter(deps: FileRouterDeps): Router {
  const router = Router({ mergeParams: true });
  router.get(
    "/",
    asyncHandler(async (req, res) => {
      const { id } = req.params as { id: string };
      const record = await requireChange(deps.changeStore, id);
      const rawPath = req.query.path;
      if (typeof rawPath !== "string" || rawPath.length === 0) {
        throw new BadRequestError("missing required query parameter: path");
      }
      const worktreeRoot = await resolveWorktreeRoot(record.worktreePath);
      const contents = await readFileContents(worktreeRoot, rawPath, {
        maxBytes: deps.fileMaxBytes,
      });
      res.json(contents);
    }),
  );
  return router;
}
