// WP-015 — <NoBaseShaState />.
//
// Shown when the diff endpoint returns 422 NO_BASE_SHA — the change has
// no recorded starting point, so there is nothing to diff against. This
// happens for legacy change records created before the starting-point
// was tracked. We surface a clear message rather than a stack trace.
//
// References: WP-015 Contract (<FilePane> 422 NO_BASE_SHA branch),
// TDD §7.

import styles from "../styles/FilesPanel.module.css";

export function NoBaseShaState() {
  return (
    <div className={styles.fileMessage} data-testid="no-base-sha-state">
      <p>
        This change has no recorded starting point yet — start a new change to
        enable diffs.
      </p>
    </div>
  );
}
