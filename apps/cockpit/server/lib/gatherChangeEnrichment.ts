// WP-002 — gatherChangeEnrichment: a change's board enrichment, gathered
// once (ADR-002). Both the list route (changes.ts) and the search route
// (search.ts) need the SAME per-record enrichment for the wire `Change`:
// the FR-12 attention verdict, the new health verdict, and lastActivityAt.
// 2-consumer threshold → extracted here (EP-03), so the board and search
// agree by construction.
//
// It composes existing reads — no new port:
//   - gatherChangeStatus → liveness + parsed transcript + the computed
//     ChangeStatus (whose needsAttention IS the FR-12 single source of
//     truth, reused not re-derived),
//   - readTestsState + readRigorForStage → computeHealth (ADR-001),
//   - deriveLastActivityAt over the already-parsed transcript (no extra I/O).
//
// Best-effort / never-throws (BR-11 / A-1): every underlying read fails soft
// to a safe default (unknown liveness, unknown health, not-flagged
// attention, null recency), so a change with a gone/malformed worktree
// degrades to honest unknown reads rather than throwing — the feed can never
// 500 because one record could not be enriched. The per-record fan-out stays
// inside the route's single bounded Promise.all (MUC-2 / A-3): no per-card
// request, no second poll.

import type { ChangeStoreRecord } from "../ports/ChangeStoreReader";
// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits; the rule's `../../*` pattern is intended to block escapes out of apps/cockpit/, which `import/no-restricted-paths` already enforces correctly)
import type { Liveness } from "../../shared/api-types";
import type { ChangeEnrichment } from "../routes/_change-lookup";
import {
  gatherChangeStatus,
  type GatherChangeStatusDeps,
} from "./gatherChangeStatus";
import { readTestsState } from "./readTestsState";
import { readRigorForStage } from "./readRigorForStage";
import { computeHealth } from "./computeHealth";
import { deriveLastActivityAt } from "./deriveLastActivityAt";

export type GatherChangeEnrichmentDeps = GatherChangeStatusDeps;

/** The enrichment + the liveness the route also needs for the wire row. */
export interface ChangeEnrichmentResult {
  liveness: Liveness;
  enrichment: ChangeEnrichment;
}

/**
 * Gather a change's board enrichment (attention + health + last-activity)
 * plus its liveness, best-effort. Never throws — see the module header.
 */
export async function gatherChangeEnrichment(
  deps: GatherChangeEnrichmentDeps,
  record: ChangeStoreRecord,
): Promise<ChangeEnrichmentResult> {
  // Liveness + transcript + the FR-12 attention verdict, gathered by the
  // shared helper (also used by status + search). Fail-soft already.
  const context = await gatherChangeStatus(deps, record);

  // The two new best-effort reads → the health verdict (ADR-001). Both
  // never-throw; computeHealth is pure.
  const [testsState, rigorForStage] = await Promise.all([
    readTestsState(record.worktreePath),
    readRigorForStage(record.worktreePath, record.stage),
  ]);
  const health = computeHealth({ testsState, rigorForStage });

  // Recency from the already-parsed transcript (no extra I/O), record's
  // updatedAt as the fallback, null when neither (FR-42).
  const lastActivityAt = deriveLastActivityAt(
    context.transcript,
    record.updatedAt,
  );

  return {
    liveness: context.liveness,
    enrichment: {
      needsAttention: context.status.needsAttention,
      health,
      lastActivityAt,
    },
  };
}
