// WP-011 — <Shell /> layout: fixed-width sidebar on the left,
// route-rendered <Outlet /> on the right. Used by every route
// (TDD §6 — the sidebar is rendered in every view).
//
// The outlet region has `data-testid="shell-outlet"` so tests can
// assert structural containment without depending on rendered text.
//
// WP-004 — a minimal top-bar region (colours-only, no layout redesign of the
// existing regions) hosts the <ThemeToggle /> top-right, so the theme control
// is reachable from every route (ADR-001). The right pane is now a flex
// column: top bar above, outlet below. The outlet keeps its testid + role.

import { Outlet } from "react-router-dom";
import { Sidebar } from "../components/Sidebar";
import { ThemeToggle } from "../components/ThemeToggle";
import styles from "./Shell.module.css";

export function Shell() {
  return (
    <div className={styles.shell}>
      <Sidebar />
      <div className={styles.pane}>
        <header className={styles.topbar}>
          <ThemeToggle />
        </header>
        <main className={styles.main} data-testid="shell-outlet">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
