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
import type { Change, Liveness } from "../../shared/api-types";
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
 * Project a ChangeStoreRecord + Liveness into the wire-shape `Change`.
 * The single-record route (`/api/changes/:id`) extends this with
 * `transcriptPaths`; the list route returns the raw shape.
 */
export function toWireChange(
  record: ChangeStoreRecord,
  liveness: Liveness,
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
  };
}
