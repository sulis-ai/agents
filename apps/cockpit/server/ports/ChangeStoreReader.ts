// WP-003 — ChangeStoreReader port (TDD §2.3, §9, §12; ADR-008).
//
// This is the cockpit's one and only port to the change store. Lifting
// the cockpit later (per ADR-008) means rewriting only the adapter
// behind this interface, leaving the rest of the server unchanged. No
// other path in apps/cockpit/ reaches the change store.
//
// The port returns camelCase TypeScript shapes; the snake_case schema
// owned by _change_state.py stays inside the adapter (it does the
// translation). Consumers downstream see only the shape declared here.

// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits; the rule's `../../*` pattern is intended to block escapes out of apps/cockpit/, which `import/no-restricted-paths` already enforces correctly)
import type { WorkflowStage } from "../../shared/api-types";

export type { WorkflowStage };

/**
 * The camelCase shape of a change-store record, as the cockpit consumes
 * it. Mirrors the persisted change.json schema (snake_case) plus the
 * live-stage overlay from state.json (TDD §3 — change store row).
 *
 * Notable invariants the adapter must uphold:
 *   - `stage` always reflects the live overlay (state.json) when one
 *     exists; otherwise the seed value from change.json. The contract
 *     test enforces this.
 *   - `updatedAt` comes from state.json's `updated_at` when present,
 *     otherwise falls back to `createdAt` (a change with no overlay has
 *     never been transitioned, so its "last activity" is its creation).
 *   - `baseSha` is optional — legacy records may carry `null`.
 */
export type ChangeStoreRecord = {
  changeId: string;
  handle: string;
  slug: string;
  primitive: string;
  branch: string;
  worktreePath: string;
  intent: string;
  baseBranch: string;
  baseSha: string | null;
  /**
   * The commit a shipped change's worktree is recreated from once it has
   * been tidied (WP-004 / ADR-004). `null` for not-yet-shipped changes and
   * for legacy records that predate the field. It is one of the facts the
   * recreate-on-demand path reads off the record to decide recreatability
   * (ADR-003 — generic, never hard-wired).
   *
   * Optional on the port so existing consumers (and the wire-shape
   * `Change`, owned by the serving WP) are unaffected: the adapter
   * populates it when the store carries `shipped_sha`, and the
   * recreate-on-demand resolver reads it defensively (absent ⇒ treated
   * as `null` ⇒ not recreatable via a pin).
   */
  shippedSha?: string | null;
  /** ISO 8601 UTC */
  createdAt: string;
  /** ISO 8601 UTC (from state.json; may equal createdAt) */
  updatedAt: string;
  stage: WorkflowStage;
};

/**
 * The one port the cockpit talks to the change store through. Three
 * calls match the three reads the cockpit needs (TDD §9). Anything
 * richer goes through one of these — never around them.
 */
export interface ChangeStoreReader {
  /**
   * List every change in the store, sorted most-recent-first by
   * `createdAt`. Each record carries the live-overlay `stage`.
   * Returns `[]` for an empty store. Best-effort: never throws on
   * legitimate "no changes" or "no overlay" conditions.
   */
  listAllChanges(): Promise<ChangeStoreRecord[]>;

  /**
   * Read one change by id. Returns `null` for an unknown id. The
   * returned record carries the live-overlay `stage` (parity with
   * `listAllChanges`).
   */
  readChangeRecord(changeId: string): Promise<ChangeStoreRecord | null>;

  /**
   * Return the live stage for a change, or `null` if unknown. Parity
   * with `listAllChanges`: for any known id, this returns the same
   * stage `listAllChanges` reports for that id.
   */
  readChangeStage(changeId: string): Promise<WorkflowStage | null>;
}
