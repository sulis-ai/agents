// WP-011 — <Shell /> layout: fixed-width sidebar on the left,
// route-rendered <Outlet /> on the right. Used by every route
// (TDD §6 — the sidebar is rendered in every view).
//
// The outlet region has `data-testid="shell-outlet"` so tests can
// assert structural containment without depending on rendered text.

import { Outlet } from "react-router-dom";
import { Sidebar } from "../components/Sidebar";
import styles from "./Shell.module.css";

export function Shell() {
  return (
    <div className={styles.shell}>
      <Sidebar />
      <main className={styles.main} data-testid="shell-outlet">
        <Outlet />
      </main>
    </div>
  );
}
