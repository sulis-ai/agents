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

// WP-001 placeholder enrichment defaults. The wire now carries
// `needsAttention` / `health` / `lastActivityAt`, but DERIVING them (the
// open-blocker probe, the health computation, the last-activity read) is
// WP-002's scope. Until WP-002 lands, `toWireChange` emits the honest
// absence-defaults the never-throw degradation discipline already mandates
// (A-1): not-flagged attention, `unknown` health ("too early to tell"), and
// no recorded recency. WP-002 replaces these with the derived values.
const PLACEHOLDER_NEEDS_ATTENTION: NeedsAttention = {
  flagged: false,
  reason: null,
};
const PLACEHOLDER_HEALTH: ChangeHealth = {
  state: "unknown",
  reason: "too early to tell",
};

/**
 * Project a ChangeStoreRecord + Liveness into the wire-shape `Change`.
 * The single-record route (`/api/changes/:id`) extends this with
 * `transcriptPaths`; the list route returns the raw shape.
 *
 * The attention/health/last-activity fields carry WP-001 placeholder
 * defaults; WP-002 enriches them from the per-record signals.
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
    // WP-001 placeholder enrichment (WP-002 derives these — see above).
    needsAttention: PLACEHOLDER_NEEDS_ATTENTION,
    health: PLACEHOLDER_HEALTH,
    lastActivityAt: null,
  };
}
