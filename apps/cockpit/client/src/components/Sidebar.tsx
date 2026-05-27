// WP-012 — Persistent <Sidebar>.
//
// Per TDD §2.2 + WP Contract: lists every change as a clickable item,
// highlights the currently-routed change, and lives on every page (via
// <Shell>). Uses useChangesWithLiveness so the dots refresh every 10s
// (ADR-007). When zero changes exist, shows a quiet placeholder rather
// than throwing or rendering an error — the founder may not have any
// changes yet.
//
// #38: shipped changes (stage='shipped') are the audit trail — the
// worktree, branch, and records all stay. They render under a separate
// "Shipped" section, collapsed by default so they don't crowd the active
// list. Every diff / file view keeps working on them exactly like a live
// change.

import { useState } from "react";
import { useParams } from "react-router-dom";
import { useChangesWithLiveness } from "../api/useChangesWithLiveness";
import { SidebarItem } from "./SidebarItem";
import styles from "./Sidebar.module.css";

export function Sidebar() {
  const { changeId: activeChangeId } = useParams<{ changeId: string }>();
  const query = useChangesWithLiveness();
  const [shippedOpen, setShippedOpen] = useState(false);

  const all = query.isSuccess ? query.data : [];
  const active = all.filter((c) => c.stage !== "shipped");
  const shipped = all.filter((c) => c.stage === "shipped");

  return (
    <aside className={styles.sidebar} data-testid="shell-sidebar">
      <h2 className={styles.heading}>Changes</h2>
      {query.isLoading && <p className={styles.placeholder}>Loading…</p>}
      {query.isError && (
        <p className={styles.error}>Failed to load changes.</p>
      )}
      {query.isSuccess && all.length === 0 && (
        <p className={styles.placeholder}>No changes yet.</p>
      )}
      {query.isSuccess && active.length > 0 && (
        <nav data-testid="sidebar-active">
          {active.map((change) => (
            <SidebarItem
              key={change.changeId}
              change={change}
              active={change.changeId === activeChangeId}
            />
          ))}
        </nav>
      )}
      {query.isSuccess && shipped.length > 0 && (
        <section data-testid="sidebar-shipped">
          <button
            type="button"
            className={styles.shippedToggle}
            aria-expanded={shippedOpen}
            data-testid="sidebar-shipped-toggle"
            onClick={() => setShippedOpen((v) => !v)}
          >
            {shippedOpen ? "▾" : "▸"} Shipped ({shipped.length})
          </button>
          {shippedOpen && (
            <nav data-testid="sidebar-shipped-items">
              {shipped.map((change) => (
                <SidebarItem
                  key={change.changeId}
                  change={change}
                  active={change.changeId === activeChangeId}
                />
              ))}
            </nav>
          )}
        </section>
      )}
    </aside>
  );
}
