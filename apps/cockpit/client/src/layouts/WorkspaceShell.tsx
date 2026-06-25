// Chat-redesign (chat-B2 signed contract) — the tabbed workspace shell.
//
// Top bar (product switcher + tab strip) over a full-width main region that
// renders the active route. Replaces the persistent left Sidebar: the Board
// is a tab, and each change opens in its OWN tab. Visiting /c/:id registers
// that change as an open tab so it appears in the strip.
//
// The main region keeps `data-testid="shell-outlet"` so existing structural
// assertions (route content lives inside the outlet) still hold.

import { useEffect } from "react";
import { Outlet, useMatch } from "react-router-dom";
import { WorkspaceTopBar } from "../components/WorkspaceTopBar";
import { ProductChatDock } from "../components/ProductChatDock";
import { useOpenTabs } from "../api/openTabs";
import { useProducts } from "../api/useProducts";
import { useStartHotkey } from "../api/useStartHotkey";
import styles from "./WorkspaceShell.module.css";

export function WorkspaceShell() {
  const match = useMatch("/c/:changeId");
  const activeChangeId = match?.params.changeId ?? null;
  const { openTab } = useOpenTabs();

  // WP-004 — the per-product chat dock reads the SAME product set the switcher
  // does (one source of truth), so one switch moves the board AND the chat
  // together (ADR-001). The dock keys off useActiveProduct() internally.
  const products = useProducts();
  const productList = products.data?.products ?? [];

  // The global ⌘N / ⌘K start accelerant, live on every workspace route
  // (ADR-003 / parked ADR-002). Same destination as the front-door button.
  useStartHotkey();

  // Opening a change (navigating to its route) gives it a tab in the strip.
  useEffect(() => {
    if (activeChangeId) openTab(activeChangeId);
  }, [activeChangeId, openTab]);

  return (
    <div className={styles.shell}>
      <WorkspaceTopBar activeChangeId={activeChangeId} />
      {/* The board is central; the per-product chat is docked right (ADR-001). */}
      <div className={styles.body}>
        <main className={styles.main} data-testid="shell-outlet">
          <Outlet />
        </main>
        <ProductChatDock products={productList} />
      </div>
    </div>
  );
}
