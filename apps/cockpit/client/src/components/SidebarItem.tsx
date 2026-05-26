// WP-012 — <SidebarItem> — one row in the persistent sidebar.
//
// Shows handle + slug + liveness dot. The `data-active="true"`
// attribute marks the currently-routed change for both CSS styling
// and test selection.

import { Link } from "react-router-dom";
import type { Change } from "../../../shared/api-types";
import { LivenessDot } from "./LivenessDot";
import styles from "./SidebarItem.module.css";

export interface SidebarItemProps {
  change: Change;
  active: boolean;
}

export function SidebarItem({ change, active }: SidebarItemProps) {
  return (
    <Link
      to={`/c/${change.changeId}`}
      className={styles.item}
      data-testid="sidebar-item"
      data-active={active ? "true" : "false"}
      aria-current={active ? "page" : undefined}
      aria-label={`Open ${change.handle}: ${change.intent}`}
    >
      <span className={styles.label}>
        <span className={styles.handle}>{change.handle}</span>
        <span className={styles.slug}>{change.slug}</span>
      </span>
      <LivenessDot liveness={change.liveness} />
    </Link>
  );
}
