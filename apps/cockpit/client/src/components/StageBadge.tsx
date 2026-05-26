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
};

export interface StageBadgeProps {
  stage: WorkflowStage;
}

export function StageBadge({ stage }: StageBadgeProps) {
  const cls = STAGE_CLASS[stage] ?? styles.unknown;
  return <span className={`${styles.badge} ${cls}`}>{stage}</span>;
}
