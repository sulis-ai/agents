// WP-008 — SettingsPage — the Products → Projects → Repo tree (read surface).
//
// The /settings page: the founder's one place to see their products, the
// projects inside them, and the local folders behind them. Built to the signed
// WP-VIS mockup. It renders the master tree with its three repo-states, the
// empty/implicit first-run state, and carried-over products (editable), all
// inside the WorkspaceShell.
//
// Data comes through the typed client (useSettings → getSettings → apiGet
// funnel) — never `fetch` in the component (WPF-02). The page renders the one
// async state-pattern set (ADR-005 / WPF-05): loading → error+retry → empty
// (first-run) → the tree.
//
// The create/edit/attach/remove FORMS + the confirm-remove DIALOG are a sibling
// WP (WP-009): this page renders the tree + the affordance buttons and wires
// them via callbacks; WP-009 owns the form/dialog components, and WP-010 wires
// them into the page. Until then the affordance callbacks are unset (the
// buttons render per the mockup; clicking is wired in WP-010).
//
// Render-failure error boundary (WPF-08): the cockpit has no app-wide error
// boundary today (no page mounts one — Board/ThreadView rely on the query
// layer's three states, the actual failure surface for a data page). Adding one
// is an app-wide, cross-cutting concern; introducing it only here would diverge
// from the established convention (CP-01). Captured as follow-up rather than an
// unbounded side-quest from this WP (EP-07 scope).
// TODO(deferred): wrap the app shell in a render-failure ErrorBoundary (WPF-08).
// REASON: app-wide cross-cutting concern; no page mounts one today — out of
//   this WP's single-page scope (EP-07).
// RESOLVE_BY: 2026-07-09

import type { SettingsProduct } from "../../../shared/api-types";
import { useSettings } from "../api/useSettings";
import { ProductRow } from "./settings/ProductRow";
import styles from "./settings/Settings.module.css";

export function SettingsPage() {
  const settings = useSettings();

  const products: SettingsProduct[] = settings.data?.products ?? [];
  // First-run / empty: a genuinely empty store, OR the synthesised implicit
  // single product with no real products to manage yet. Either way we lead with
  // "Add your first product" (IMMUTABLE_IMPLICIT).
  const isEmpty =
    settings.isSuccess &&
    (products.length === 0 || products.every((p) => !p.editable));

  return (
    <section className={styles.page} data-testid="page-settings">
      <div className={styles.pageHead}>
        <h1>Settings</h1>
        <p>
          The one place to manage your products, the projects inside them, and
          the local folders behind them. Changes save straight away and show up
          across the cockpit — no files to edit, no commands to run.
        </p>
      </div>

      {settings.isLoading && (
        <div
          className={styles.loading}
          data-testid="settings-loading"
          aria-busy="true"
          aria-label="Loading your settings"
        >
          <div className={styles.skeletonCard} />
          <div className={styles.skeletonCard} />
        </div>
      )}

      {settings.isError && (
        <div className={styles.errorBox} role="alert">
          <p className={styles.errorHeading}>
            Something went wrong loading your settings.
          </p>
          <p className={styles.errorMessage}>
            {settings.error instanceof Error
              ? settings.error.message
              : "Unknown error"}
          </p>
          <button
            type="button"
            className={`${styles.btn} ${styles.btnGhost}`}
            onClick={() => void settings.refetch()}
          >
            Retry
          </button>
        </div>
      )}

      {settings.isSuccess && (
        <div className={styles.section}>
          <div className={styles.sectionHead}>
            <h2>Products</h2>
            {!isEmpty && (
              <button
                type="button"
                className={`${styles.btn} ${styles.btnPrimary}`}
              >
                + Add product
              </button>
            )}
          </div>

          {isEmpty ? (
            <div className={styles.implicit}>
              <p>
                You haven’t set up a product yet. Add your first one to start
                managing its projects and folders here.
              </p>
              <button
                type="button"
                className={`${styles.btn} ${styles.btnPrimary}`}
              >
                + Add your first product
              </button>
            </div>
          ) : (
            products.map((product) => (
              <ProductRow key={product.productId} product={product} />
            ))
          )}
        </div>
      )}
    </section>
  );
}
