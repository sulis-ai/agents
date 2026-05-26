// WP-012 — Persistent <Sidebar>.
//
// Per TDD §2.2 + WP Contract: lists every change as a clickable item,
// highlights the currently-routed change, and lives on every page (via
// <Shell>). Uses useChangesWithLiveness so the dots refresh every 10s
// (ADR-007). When zero changes exist, shows a quiet placeholder rather
// than throwing or rendering an error — the founder may not have any
// changes yet.

import { useParams } from "react-router-dom";
import { useChangesWithLiveness } from "../api/useChangesWithLiveness";
import { SidebarItem } from "./SidebarItem";
import styles from "./Sidebar.module.css";

export function Sidebar() {
  const { changeId: activeChangeId } = useParams<{ changeId: string }>();
  const query = useChangesWithLiveness();

  return (
    <aside className={styles.sidebar} data-testid="shell-sidebar">
      <h2 className={styles.heading}>Changes</h2>
      {query.isLoading && <p className={styles.placeholder}>Loading…</p>}
      {query.isError && (
        <p className={styles.error}>Failed to load changes.</p>
      )}
      {query.isSuccess && query.data.length === 0 && (
        <p className={styles.placeholder}>No changes yet.</p>
      )}
      {query.isSuccess && query.data.length > 0 && (
        <nav>
          {query.data.map((change) => (
            <SidebarItem
              key={change.changeId}
              change={change}
              active={change.changeId === activeChangeId}
            />
          ))}
        </nav>
      )}
    </aside>
  );
}
