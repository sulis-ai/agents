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
import { useParams, NavLink, useNavigate } from "react-router-dom";
import { useChangesWithLiveness } from "../api/useChangesWithLiveness";
import { useProducts } from "../api/useProducts";
import { useActiveProduct } from "../api/activeProduct";
import { ProductSwitcher } from "./ProductSwitcher";
import { SidebarItem } from "./SidebarItem";
import styles from "./Sidebar.module.css";

export function Sidebar() {
  const { changeId: activeChangeId } = useParams<{ changeId: string }>();
  // WP-008 — the product switcher sits top-left in the sidebar's brand row,
  // above the nav, so the active Product is always in view (FR-38, ADR-009).
  // Switching re-scopes the board + per-product views via the active-Product
  // context; the sidebar's own change list follows the same active Product.
  // The single-Product Tenant is the trivial case (one Product, shown active
  // — synthesised server-side).
  const { activeProductId, setActiveProductId } = useActiveProduct();
  const navigate = useNavigate();
  const products = useProducts();
  const query = useChangesWithLiveness(activeProductId);
  const [shippedOpen, setShippedOpen] = useState(false);

  const all = query.isSuccess ? query.data : [];
  const active = all.filter((c) => c.stage !== "shipped");
  const shipped = all.filter((c) => c.stage === "shipped");
  // The switcher reflects the server-resolved active Product until the founder
  // picks another (which updates the context scope the board/sidebar fetch on).
  const productList = products.isSuccess ? products.data.products : [];
  const serverActiveProductId = products.isSuccess
    ? products.data.activeProductId
    : null;

  return (
    <aside className={styles.sidebar} data-testid="shell-sidebar">
      {productList.length > 0 && (
        <ProductSwitcher
          products={productList}
          activeProductId={activeProductId ?? serverActiveProductId}
          onSelect={setActiveProductId}
          onSetUpNew={() => navigate("/settings?new=product")}
        />
      )}
      {/* WP-009 — the concierge front door: the plain-English way to find a
          change, ask about your world, or start something new (FR-33/34). */}
      <nav className={styles.topnav} aria-label="Primary">
        <NavLink
          to="/"
          end
          className={styles.navlink}
          data-testid="nav-board"
        >
          Board
        </NavLink>
        <NavLink
          to="/concierge"
          className={styles.navlink}
          data-testid="nav-concierge"
        >
          Concierge
        </NavLink>
      </nav>
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
