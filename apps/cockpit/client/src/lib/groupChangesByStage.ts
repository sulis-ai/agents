// WP-003 — groupChangesByStage (board read scope, client side).
//
// The board lays the active Product's in-flight changes into the six
// lifecycle stage columns in order (recon→specify→design→implement→
// review→ship; ADR-005 board IA, FR-01). Shipped changes are terminal —
// they are NOT in-flight and never appear on the board (FR-15). The six
// columns are fixed: a change in any other (unknown/terminal) stage does
// not create a seventh column.

import type { Change, WorkflowStage } from "../../../shared/api-types";

/** The six lifecycle stages, in board order (ADR-005). `shipped` is excluded. */
export const BOARD_STAGES = [
  "recon",
  "specify",
  "design",
  "implement",
  "review",
  "ship",
] as const satisfies readonly WorkflowStage[];

export type BoardStage = (typeof BOARD_STAGES)[number];

/** One stage column: the stage and the changes that sit in it. */
export interface StageGroup {
  stage: BoardStage;
  changes: Change[];
}

/**
 * Group changes into the six fixed stage columns, in order. Shipped
 * changes are excluded (FR-15); a change whose stage is not one of the
 * six lifecycle stages is dropped (it is not in-flight). Input order is
 * preserved within each column.
 */
export function groupChangesByStage(changes: readonly Change[]): StageGroup[] {
  const groups: StageGroup[] = BOARD_STAGES.map((stage) => ({
    stage,
    changes: [],
  }));
  const byStage = new Map(groups.map((g) => [g.stage, g]));
  for (const change of changes) {
    const group = byStage.get(change.stage as BoardStage);
    // Unknown / terminal (e.g. "shipped") stages are not in-flight (FR-15).
    if (group) group.changes.push(change);
  }
  return groups;
}
