// WP-P05 — GET /api/changes/:id/provenance (ADR-011).
//
// Returns the Provenance read PROJECTION over the change's brain tree: the
// digest dashboard + the run-log lens + the coverage map (one `ProvenanceView`,
// one round-trip — ADR-011). The `?focus=<requirementId>` variant returns a
// single requirement's `FocusedTrace` instead (edge resolve stays server-side).
//
// Composes existing reads — no new port (mirrors routes/brain.ts): `requireChange`
// gives the 404 for an unknown id; `resolveWorktreeRoot` realpaths the worktree;
// `readProvenance` / `readFocusedTrace` do the pure read+project. GET-only;
// reading it starts NO `claude` process (NFR-SEC-05 parity) — the read-only gate
// proves no mutation verb or process start lives here.

import { Router } from "express";

// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits; the rule's `../../*` pattern blocks escapes out of apps/cockpit/, which import/no-restricted-paths enforces)
import type { FocusedTrace, ProvenanceView } from "../../shared/api-types";
import type { ChangeStoreReader } from "../ports/ChangeStoreReader";
import { NotFoundError } from "../lib/errors";
import { readFocusedTrace, readProvenance } from "../lib/readProvenance";

import { asyncHandler } from "./_async";
import { requireChange } from "./_change-lookup";
import { resolveWorktreeRoot } from "./_worktree";

export interface ProvenanceRouterDeps {
  changeStore: ChangeStoreReader;
}

export function createProvenanceRouter(deps: ProvenanceRouterDeps): Router {
  const router = Router({ mergeParams: true });
  router.get(
    "/",
    asyncHandler(async (req, res) => {
      const { id } = req.params as { id: string };
      const focus =
        typeof req.query.focus === "string" ? req.query.focus : null;

      const record = await requireChange(deps.changeStore, id);
      const worktreeRoot = await resolveWorktreeRoot(record.worktreePath);

      if (focus !== null) {
        const trace = await readFocusedTrace(worktreeRoot, id, focus);
        if (trace === null) {
          throw new NotFoundError(`requirement not in brain: ${focus}`);
        }
        const body: FocusedTrace = trace;
        res.json(body);
        return;
      }

      const body: ProvenanceView = await readProvenance(worktreeRoot, id);
      res.json(body);
    }),
  );
  return router;
}
