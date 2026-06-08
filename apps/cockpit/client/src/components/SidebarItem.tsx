// WP-012 — <SidebarItem> — one row in the persistent sidebar.
//
// Leads with the human change NAME (the prettified slug — "deploy-founder-web"
// → "Deploy founder web") rather than the CH- handle, matching the signed
// mockup's sidebar (a readable name + a liveness dot, no identifiers). The
// handle stays in the accessible label so it's still reachable, just not the
// thing a non-technical founder reads. (CH-01KT50 copy fix.)
//
// The `data-active="true"` attribute marks the currently-routed change for
// both CSS styling and test selection.

import { Link } from "react-router-dom";
import type { Change } from "../../../shared/api-types";
import { LivenessDot } from "./LivenessDot";
import styles from "./SidebarItem.module.css";

export interface SidebarItemProps {
  change: Change;
  active: boolean;
}

/** "deploy-founder-web" → "Deploy founder web" — a readable row name. */
function changeName(change: Change): string {
  const words = change.slug.replace(/[-_]+/g, " ").trim();
  if (!words) return change.slug;
  return words.charAt(0).toUpperCase() + words.slice(1);
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
        <span className={styles.handle}>{changeName(change)}</span>
      </span>
      <LivenessDot liveness={change.liveness} />
    </Link>
  );
}
