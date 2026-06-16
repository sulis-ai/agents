// WP-010 (Blue refactor) — shared change-lookup + liveness shaping.
//
// Two duplications surfaced in Green:
//
//   1. `await deps.changeStore.readChangeRecord(id); if (record === null) throw NoSuchChangeError(id)`
//      — appears in change-detail, tree, file, diff, transcript (5 sites).
//      Extracted as `requireChange()` so every route gets identical
//      not-found behaviour.
//
//   2. Shaping a ChangeStoreRecord + Liveness into the wire-shape
//      `Change` — appears in changes.ts (list endpoint) and
//      change-detail.ts (single endpoint). Extracted as
//      `toWireChange()`. The single-record endpoint adds
//      `transcriptPaths` on top.
//
// 2-consumer threshold reached on both → extracted (EP-03).

// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits; the rule's `../../*` pattern is intended to block escapes out of apps/cockpit/, which `import/no-restricted-paths` already enforces correctly)
import type {
  Change,
  ChangeHealth,
  Liveness,
  NeedsAttention,
} from "../../shared/api-types";
import type {
  ChangeStoreReader,
  ChangeStoreRecord,
} from "../ports/ChangeStoreReader";

import { NoSuchChangeError } from "../middleware/errors";

/**
 * Read the change record for `changeId`. Throw `NoSuchChangeError`
 * (mapped to 404 NOT_FOUND by the error middleware) if the store
 * returns `null`.
 */
export async function requireChange(
  store: ChangeStoreReader,
  changeId: string,
): Promise<ChangeStoreRecord> {
  const record = await store.readChangeRecord(changeId);
  if (record === null) {
    throw new NoSuchChangeError(changeId);
  }
  return record;
}

/**
 * The derived enrichment a route gathers per record and hands to
 * `toWireChange` (WP-002 / ADR-002). Keeping these OUT of the shaper keeps
 * it a pure projection: the route does the best-effort reads (attention,
 * health, last-activity), the shaper just carries them onto the wire.
 */
export interface ChangeEnrichment {
  needsAttention: NeedsAttention;
  health: ChangeHealth;
  lastActivityAt: string | null;
  /** The change's assigned Product id, or null when unassigned (shown under
   *  All). Optional — only the board/detail enrichment populates it. */
  forProduct?: string | null;
}

/**
 * Project a ChangeStoreRecord + Liveness + derived enrichment into the
 * wire-shape `Change`. The single-record route (`/api/changes/:id`) extends
 * this with `transcriptPaths`; the list + search routes return the raw shape.
 *
 * Pure shaper: it derives NOTHING itself (the route gathers the enrichment
 * via `gatherChangeEnrichment`); it carries the values it is handed. This is
 * the REORGANISE invariant — gathering lives in the route, shaping here.
 */
export function toWireChange(
  record: ChangeStoreRecord,
  liveness: Liveness,
  enrichment: ChangeEnrichment,
): Change {
  return {
    changeId: record.changeId,
    handle: record.handle,
    slug: record.slug,
    primitive: record.primitive,
    branch: record.branch,
    worktreePath: record.worktreePath,
    intent: record.intent,
    baseBranch: record.baseBranch,
    baseSha: record.baseSha,
    createdAt: record.createdAt,
    updatedAt: record.updatedAt,
    stage: record.stage,
    liveness,
    needsAttention: enrichment.needsAttention,
    health: enrichment.health,
    lastActivityAt: enrichment.lastActivityAt,
    forProduct: enrichment.forProduct,
  };
}
