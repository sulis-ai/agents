// WP-007 — GET /api/search (FR-10/11/12).
//
// Journey D round-trip, server half: search + filter the active Product's
// changes by CONTENT (conversation + created entities — not just labels,
// FR-10), by stage (FR-11), and by needs-attention (FR-12). All filters
// narrow the SAME board (ADR-005) — the response is the same row shape as
// the board list (`{ results: Change[] }`).
//
// It composes existing reads — no new port (the same seam discipline as
// the status/brain reads):
//   - list → scope to the active Product (ADR-009; trivial = all),
//   - per change: gather the searchable content (transcript text + brain
//     entity text + the record's own labels) AND the attention verdict
//     (computeStatus → needsAttention, the FR-12 single source of truth —
//     NOT re-implemented here),
//   - hand the assembled rows to the pure `searchChanges` filter,
//   - shape the survivors to the wire `Change` with liveness.
//
// GET-only; reading it starts no `claude` process (FR-N4) — the read-only
// gate proves no mutation verb or process start lives here.

import { Router } from "express";

// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits; the rule's `../../*` pattern is intended to block escapes out of apps/cockpit/, which `import/no-restricted-paths` already enforces correctly)
import type { Change, WorkflowStage } from "../../shared/api-types";
import type { ChangeStoreReader, ChangeStoreRecord } from "../ports/ChangeStoreReader";
import { scopeChangesToActiveProduct } from "../lib/scopeChangesToActiveProduct";
import { probeLiveness } from "../lib/probeLiveness";
import { readBrain } from "../lib/readBrain";
import { gatherChangeStatus } from "../lib/gatherChangeStatus";
import { gatherChangeContent } from "../lib/gatherChangeContent";
import { searchChanges, type SearchableChange } from "../lib/searchChanges";

import { asyncHandler } from "./_async";
import { toWireChange } from "./_change-lookup";

export interface SearchRouterDeps {
  changeStore: ChangeStoreReader;
  sulisStateDir: string;
  claudeProjectsDir: string;
}

/** The valid board stages — guards the ?stage filter against junk values. */
const VALID_STAGES = new Set<WorkflowStage>([
  "recon",
  "specify",
  "design",
  "implement",
  "review",
  "ship",
  "shipped",
]);

export function createSearchRouter(deps: SearchRouterDeps): Router {
  const router = Router();
  router.get(
    "/",
    asyncHandler(async (req, res) => {
      const q = typeof req.query.q === "string" ? req.query.q : undefined;
      const stage = parseStages(req.query.stage);
      const needsAttention = req.query.needsAttention === "true";

      const allRecords = await deps.changeStore.listAllChanges();
      // The seam owns Product scope (ADR-009): search never surfaces another
      // Product's change. Trivial single-Product case = all (WP-008 promotes
      // this to the full roll-up).
      const records = scopeChangesToActiveProduct(allRecords);

      const items: SearchableChange[] = await Promise.all(
        records.map((record) => assembleSearchable(deps, record)),
      );

      const survivors = searchChanges(items, { q, stage, needsAttention });

      // Shape the survivors to the wire Change (with liveness), preserving
      // the filtered order.
      const results: Change[] = await Promise.all(
        survivors.map(async (record) => {
          const liveness = await probeLiveness(
            deps.sulisStateDir,
            record.changeId,
          );
          return toWireChange(record, liveness);
        }),
      );

      res.json({ results });
    }),
  );
  return router;
}

/**
 * Gather one change's searchable content + attention verdict from the
 * existing reads. Best-effort: a change whose worktree is gone still
 * appears (with just its labels as content + an unflagged verdict) rather
 * than sinking the whole search.
 */
async function assembleSearchable(
  deps: SearchRouterDeps,
  record: ChangeStoreRecord,
): Promise<SearchableChange> {
  // The read-time status context (liveness + transcript + computed status)
  // is gathered by the shared helper the status route also uses — the FR-12
  // attention verdict lives in ONE place (computeStatus → needsAttention).
  const [context, brain] = await Promise.all([
    gatherChangeStatus(deps, record),
    readBrain(record.worktreePath, record.changeId),
  ]);

  // Content scan covers conversation + created entities + the record's own
  // labels (FR-10 — not just handle/intent/stage).
  const content = gatherChangeContent(record, context.transcript, brain);

  return { record, content, attention: context.status.needsAttention };
}

/**
 * Normalise the `?stage` query param into a validated WorkflowStage[].
 * Express gives a string for one param and a string[] for repeated params
 * (the FR-11 repeated-param → array contract). Unknown values are dropped.
 */
function parseStages(raw: unknown): WorkflowStage[] {
  const candidates: string[] = Array.isArray(raw)
    ? raw.filter((v): v is string => typeof v === "string")
    : typeof raw === "string"
      ? [raw]
      : [];
  return candidates.filter((s): s is WorkflowStage =>
    VALID_STAGES.has(s as WorkflowStage),
  );
}
