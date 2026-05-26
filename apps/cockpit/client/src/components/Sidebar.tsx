// WP-011 — Sidebar placeholder.
//
// Persistent across every route (TDD §2.2: "Sidebar of every change,
// visible everywhere"). WP-012 replaces the body with the change
// thread list + 10-second liveness poll; WP-011 only lands the shell.

import styles from "./Sidebar.module.css";

export function Sidebar() {
  return (
    <aside className={styles.sidebar} data-testid="shell-sidebar">
      <h2 className={styles.heading}>Changes</h2>
      <p className={styles.placeholder}>
        Change thread list lands in WP-012.
      </p>
    </aside>
  );
}
