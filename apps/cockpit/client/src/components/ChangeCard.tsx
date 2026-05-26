// WP-012 — <ChangeCard> — one card per change on the dashboard grid.
//
// Per WP Contract + TDD §1.1: handle + slug + intent + stage badge +
// relative-time + liveness dot. Click navigates to /c/:changeId.
// A11y: rendered as a <Link> with an aria-label describing what opens.

import { Link } from "react-router-dom";
import type { Change } from "../../../shared/api-types";
import { StageBadge } from "./StageBadge";
import { LivenessDot } from "./LivenessDot";
import { RelativeTime } from "./RelativeTime";
import styles from "./ChangeCard.module.css";

export interface ChangeCardProps {
  change: Change;
  /** Optional pidKind from the session record (TDD §8); when present
   *  and equal to "terminal", the liveness dot renders amber. */
  pidKind?: string | null;
}

export function ChangeCard({ change, pidKind }: ChangeCardProps) {
  return (
    <Link
      to={`/c/${change.changeId}`}
      className={styles.card}
      data-testid="change-card"
      aria-label={`Open ${change.handle}: ${change.intent}`}
    >
      <div className={styles.headerRow}>
        <span className={styles.handle}>{change.handle}</span>
        <StageBadge stage={change.stage} />
      </div>
      <p className={styles.intent}>{change.intent}</p>
      <div className={styles.footerRow}>
        <span className={styles.slug}>{change.slug}</span>
        <span className={styles.livenessGroup}>
          <RelativeTime iso={change.updatedAt} />
          <LivenessDot liveness={change.liveness} pidKind={pidKind} />
        </span>
      </div>
    </Link>
  );
}
