// WP-013 — <EmptyTranscript /> — the "no Claude session yet" empty
// state (TDD §6.2, WP-013 Contract).

import styles from "../styles/Chat.module.css";

export function EmptyTranscript() {
  return (
    <div className={styles.empty} data-testid="empty-transcript">
      <p className={styles.emptyText}>
        This change hasn&apos;t had a Claude session yet.
      </p>
    </div>
  );
}
