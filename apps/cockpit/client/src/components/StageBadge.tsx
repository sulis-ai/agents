// WP-012 — <StageBadge> — colour-coded workflow stage pill.
//
// Maps WorkflowStage enum (recon/specify/design/implement/review/ship)
// to a CSS-module class. Unknown stages fall back to a neutral class.

import type { WorkflowStage } from "../../../shared/api-types";
import styles from "./StageBadge.module.css";

const STAGE_CLASS: Record<WorkflowStage, string> = {
  recon: styles.recon!,
  specify: styles.specify!,
  design: styles.design!,
  implement: styles.implement!,
  review: styles.review!,
  ship: styles.ship!,
  // #38: shipped is a terminal stage past the six-stage workflow. Muted on
  // purpose — the badge signals "archived", not "active step".
  shipped: styles.shipped!,
};

// The six-stage workflow, in order. Used to render a stage as its
// position in the journey ("Review · 5/6") so it reads as a recognisable
// step rather than a bare enum the reader might think is invalid.
const STAGE_ORDER: WorkflowStage[] = [
  "recon",
  "specify",
  "design",
  "implement",
  "review",
  "ship",
];

const STAGE_NAME: Record<WorkflowStage, string> = {
  recon: "Recon",
  specify: "Specify",
  design: "Design",
  implement: "Implement",
  review: "Review",
  ship: "Ship",
  shipped: "Shipped",
};

/** "Review · 5/6" — title-cased stage name + its position in the six-stage
 *  workflow. Terminal stages (e.g. "Shipped") read as just the name — they
 *  are *past* the workflow, not a position within it (#38). */
export function stageLabel(stage: WorkflowStage): string {
  const i = STAGE_ORDER.indexOf(stage);
  const name = STAGE_NAME[stage] ?? stage;
  return i >= 0 ? `${name} · ${i + 1}/6` : name;
}

export interface StageBadgeProps {
  stage: WorkflowStage;
}

export function StageBadge({ stage }: StageBadgeProps) {
  const cls = STAGE_CLASS[stage] ?? styles.unknown;
  return <span className={`${styles.badge} ${cls}`}>{stageLabel(stage)}</span>;
}
