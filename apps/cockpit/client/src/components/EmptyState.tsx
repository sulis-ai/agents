// WP-012 — <EmptyState> — what the dashboard shows when zero changes exist.
//
// Plain-English copy per TDD §6.2 + WP Contract. The command pointer is
// rendered inside <code> so the user can read it visually distinct from
// the prose.

import styles from "./EmptyState.module.css";

export function EmptyState() {
  return (
    <section className={styles.wrap} data-testid="dashboard-empty">
      <h2 className={styles.headline}>Nothing in flight.</h2>
      <p className={styles.body}>
        Run{" "}
        <code className={styles.command}>
          /sulis:change start &quot;&lt;intent&gt;&quot;
        </code>{" "}
        to begin one.
      </p>
    </section>
  );
}
