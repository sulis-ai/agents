// WP-006 — GET /api/changes/:id/brain (FR-06/07).
//
// Returns a BrainView: the entities the agent created for a change, grouped
// by kind (empty groups omitted), computed at READ time off the change
// worktree's `.brain/instances` tree. A change with no brain entities yields
// `{ changeId, groups: [] }` (FR-06).
//
// Composes existing reads — no new port (TDD §2.1): `requireChange` gives the
// 404 for an unknown id (parity with status/file/tree); `resolveWorktreeRoot`
// realpaths the worktree (parity with file/tree/diff); `readBrain` does the
// pure read+group. GET-only; reading it starts no `claude` process (FR-N4) —
// the read-only gate proves no mutation verb or process start lives here.

import { Router } from "express";

// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits; the rule's `../../*` pattern is intended to block escapes out of apps/cockpit/, which `import/no-restricted-paths` already enforces correctly)
import type { BrainView } from "../../shared/api-types";
import type { ChangeStoreReader } from "../ports/ChangeStoreReader";
import { readBrain } from "../lib/readBrain";

import { asyncHandler } from "./_async";
import { requireChange } from "./_change-lookup";
import { resolveWorktreeRoot } from "./_worktree";

export interface BrainRouterDeps {
  changeStore: ChangeStoreReader;
}

export function createBrainRouter(deps: BrainRouterDeps): Router {
  const router = Router({ mergeParams: true });
  router.get(
    "/",
    asyncHandler(async (req, res) => {
      const { id } = req.params as { id: string };
      const record = await requireChange(deps.changeStore, id);
      const worktreeRoot = await resolveWorktreeRoot(record.worktreePath);
      const body: BrainView = await readBrain(worktreeRoot, id);
      res.json(body);
    }),
  );
  return router;
}
