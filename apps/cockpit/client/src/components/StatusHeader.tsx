// WP-004 — <StatusHeader> — the thread's plain-English status (FR-05/12).
//
// Renders the read-time "what's happening" headline from the status route,
// plus a needs-attention badge when the change is flagged. The badge
// follows the SIGNED visual contract's status-label readability rule: a
// warning-tint pill + an amber dot (decorative) + a worded reason — colour
// is never the sole cue; the WORD carries the meaning (WCAG 1.4.1).
//
// AI-07 transparency: the status is read at this moment, not a stored post.
// Consumes tokens.css only — no raw hex.

import type { ChangeStatus } from "../../../shared/api-types";
import styles from "./StatusHeader.module.css";

/** Worded reasons — the founder reads the word, never a colour. */
const REASON_WORD: Record<
  NonNullable<ChangeStatus["needsAttention"]["reason"]>,
  string
> = {
  blocked: "Blocked",
  "waiting-on-decision": "Waiting on you",
  "stopped-mid-reply": "Stopped mid-reply",
};

export interface StatusHeaderProps {
  status: ChangeStatus;
}

export function StatusHeader({ status }: StatusHeaderProps) {
  const { headline, needsAttention } = status;
  return (
    <div className={styles.wrap} data-testid="status-header">
      <p className={styles.headline}>{headline}</p>
      {needsAttention.flagged && needsAttention.reason !== null && (
        <span
          className={styles.attention}
          data-testid="needs-attention"
          data-reason={needsAttention.reason}
        >
          <span className={styles.attnDot} aria-hidden="true" />
          <span className={styles.attnWord}>
            {REASON_WORD[needsAttention.reason]}
          </span>
        </span>
      )}
    </div>
  );
}
