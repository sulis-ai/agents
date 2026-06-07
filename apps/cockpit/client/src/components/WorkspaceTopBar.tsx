// Chat-redesign (chat-B2 signed contract) — the workspace top bar.
//
// The product switcher (far left) + a tab strip: a Board tab plus one
// closable tab per open change, each with a stage-coloured dot. Clicking a
// tab navigates; closing removes it and lands on a neighbour (or the Board).
// Global controls (product switcher, Board) live here at the workspace level;
// a change's own nav lives inside the change (ThreadView), not here.

import { NavLink, useNavigate } from "react-router-dom";
import { Squares2X2Icon } from "@heroicons/react/24/outline";
import { XMarkIcon } from "@heroicons/react/20/solid";
import type { Change } from "../../../shared/api-types";
import { useProducts } from "../api/useProducts";
import { useActiveProduct } from "../api/activeProduct";
import { useChangesWithLiveness } from "../api/useChangesWithLiveness";
import { useOpenTabs } from "../api/openTabs";
import { ProductSwitcher } from "./ProductSwitcher";
import styles from "../layouts/WorkspaceShell.module.css";

/** "deploy-founder-web" → "Deploy founder web" — a readable tab name. */
function changeName(change: Change): string {
  const words = change.slug.replace(/[-_]+/g, " ").trim();
  if (!words) return change.slug;
  return words.charAt(0).toUpperCase() + words.slice(1);
}

interface Props {
  /** The change currently routed to (its tab is active), or null on Board. */
  activeChangeId: string | null;
}

export function WorkspaceTopBar({ activeChangeId }: Props) {
  const navigate = useNavigate();
  const { activeProductId, setActiveProductId } = useActiveProduct();
  const products = useProducts();
  const changesQuery = useChangesWithLiveness(activeProductId);
  const { openChangeIds, closeTab } = useOpenTabs();

  const productList = products.data?.products ?? [];
  const serverActiveProductId = products.data?.activeProductId ?? null;

  const byId = new Map<string, Change>(
    (changesQuery.isSuccess ? changesQuery.data : []).map((c) => [c.changeId, c]),
  );

  function onCloseTab(changeId: string, e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    const next = closeTab(changeId);
    // If we closed the active tab, follow it to the neighbour (or the Board).
    if (changeId === activeChangeId) {
      navigate(next ? `/c/${next}` : "/");
    }
  }

  return (
    <header className={styles.topbar} data-testid="workspace-topbar">
      {productList.length > 0 && (
        <div className={styles.brand}>
          <ProductSwitcher
            products={productList}
            activeProductId={activeProductId ?? serverActiveProductId}
            onSelect={setActiveProductId}
            onSetUpNew={() => navigate("/onboarding")}
          />
        </div>
      )}

      <nav className={styles.tabs} aria-label="Open tabs">
        <NavLink
          to="/"
          end
          data-testid="tab-board"
          className={({ isActive }) =>
            isActive ? `${styles.tab} ${styles.tabActive}` : styles.tab
          }
        >
          <span className={styles.tabIcon}>
            <Squares2X2Icon aria-hidden="true" />
          </span>
          <span className={styles.tabLabel}>Board</span>
        </NavLink>

        {openChangeIds.map((id) => {
          const change = byId.get(id);
          const label = change ? changeName(change) : id;
          return (
            <NavLink
              key={id}
              to={`/c/${id}`}
              data-testid="tab-change"
              data-change-id={id}
              className={({ isActive }) =>
                isActive ? `${styles.tab} ${styles.tabActive}` : styles.tab
              }
            >
              <span
                className={styles.tabDot}
                data-stage={change?.stage}
                aria-hidden="true"
              />
              <span className={styles.tabLabel}>{label}</span>
              <button
                type="button"
                className={styles.tabClose}
                aria-label={`Close ${label}`}
                onClick={(e) => onCloseTab(id, e)}
              >
                <XMarkIcon aria-hidden="true" />
              </button>
            </NavLink>
          );
        })}
      </nav>
    </header>
  );
}
