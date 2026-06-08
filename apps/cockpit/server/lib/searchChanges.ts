// WP-007 — searchChanges: the pure search/filter predicate (FR-10/11/12).
//
// The single content + stage + needs-attention filter the search route
// drives. It is PURE — no I/O. The route does the gathering: for each
// change in the active Product's set it assembles the searchable
// `content` (the conversation text + the created-entity text, NOT just
// the handle/intent — FR-10) and the `attention` verdict (from WP-004's
// `needsAttention` predicate — the single source of truth, never
// re-implemented here). searchChanges then decides which changes survive
// the active filters.
//
// The three filters compose with AND semantics; an absent/empty filter
// is a no-op (so "no filters" returns the full board). Input order is
// preserved — the route hands rows in the board's most-recent-first
// order and the surviving subset keeps it.

import type { ChangeStoreRecord } from "../ports/ChangeStoreReader";
import type { AttentionVerdict } from "./needsAttention";

// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits; the rule's `../../*` pattern is intended to block escapes out of apps/cockpit/, which `import/no-restricted-paths` already enforces correctly)
import type { WorkflowStage } from "../../shared/api-types";

/**
 * One change ready to be filtered: its record, its gathered searchable
 * content (conversation + created-entity text + the record's own labels),
 * and its precomputed attention verdict (FR-12, from WP-004's predicate).
 */
export interface SearchableChange {
  record: ChangeStoreRecord;
  /** Conversation + created-entity text + labels, folded into one string. */
  content: string;
  attention: AttentionVerdict;
}

/** The active filters. Each is optional; absent/empty = not applied. */
export interface SearchFilters {
  /** Free-text content match (FR-10). Trimmed; empty = no text filter. */
  q?: string;
  /** Stage allow-list (FR-11). Empty/absent = all stages. */
  stage?: WorkflowStage[];
  /** When true, only changes that need attention (FR-12). */
  needsAttention?: boolean;
}

/**
 * Filter the changes by the active content/stage/needs-attention filters.
 * Pure; AND semantics across filters; preserves input order. Returns the
 * surviving records (the route shapes them to the wire `Change`).
 */
export function searchChanges(
  items: readonly SearchableChange[],
  filters: SearchFilters,
): ChangeStoreRecord[] {
  const needle = (filters.q ?? "").trim().toLowerCase();
  const stages = filters.stage ?? [];
  const stageFilterActive = stages.length > 0;
  const stageSet = new Set<WorkflowStage>(stages);
  const attentionFilterActive = filters.needsAttention === true;

  const out: ChangeStoreRecord[] = [];
  for (const item of items) {
    if (needle !== "" && !item.content.toLowerCase().includes(needle)) {
      continue;
    }
    if (stageFilterActive && !stageSet.has(item.record.stage)) {
      continue;
    }
    if (attentionFilterActive && !item.attention.flagged) {
      continue;
    }
    out.push(item.record);
  }
  return out;
}
