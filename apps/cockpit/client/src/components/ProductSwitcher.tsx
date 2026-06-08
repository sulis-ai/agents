// WP-008 — <ProductSwitcher> (FR-38, UC-11; ADR-009).
//
// Journey K, client half: a top-left active-Product control — a NEUTRAL
// two-letter monogram tile + the active Product's name + a chevron — opening
// a menu that lists the Tenant's Products (active one ticked) plus "set up a
// new product". Selecting another Product re-scopes the board + search/filters
// to it (the parent owns the active-product state; the switcher emits
// `onSelect`).
//
// Matches the SIGNED visual contract (sulis-app.html .pswitch/.pmenu): the
// avatar is a neutral monogram tile (deliberately NOT brand-coloured — chrome,
// not decoration; a locked decision), consumes tokens.css only.
//
// Read-only (FR-38): selecting a Product fires only `onSelect` — it mints
// nothing, starts no session, and performs no write. The seam re-scoping is
// the parent's data refetch, not a mutation.

import { useEffect, useRef, useState } from "react";
import type { Product } from "../../../shared/api-types";
import styles from "./ProductSwitcher.module.css";

export interface ProductSwitcherProps {
  products: Product[];
  /** The active Product id (the current board scope). */
  activeProductId: string | null;
  /** Re-scope to another Product (the switch). */
  onSelect: (productId: string) => void;
  /** Optional "set up a new product" action (deferred surface; UC-07). */
  onSetUpNew?: () => void;
}

/**
 * The neutral two-letter monogram for a Product name: the initials of the
 * first two words, else the first two letters. Always upper-case; never empty.
 */
export function monogram(name: string): string {
  const words = name.trim().split(/\s+/).filter((w) => w.length > 0);
  if (words.length >= 2) {
    return (words[0]![0]! + words[1]![0]!).toUpperCase();
  }
  const first = words[0] ?? "";
  return (first.slice(0, 2) || "?").toUpperCase();
}

export function ProductSwitcher({
  products,
  activeProductId,
  onSelect,
  onSetUpNew,
}: ProductSwitcherProps) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  // Close on outside click / Escape — standard menu affordance.
  useEffect(() => {
    if (!open) return;
    function onDocClick(e: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onDocClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDocClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const active =
    products.find((p) => p.productId === activeProductId) ??
    products.find((p) => p.active) ??
    products[0] ??
    null;

  if (active === null) return null;

  function choose(productId: string) {
    setOpen(false);
    if (productId !== active?.productId) onSelect(productId);
  }

  return (
    <div className={styles.pswitch} ref={rootRef}>
      <button
        type="button"
        className={styles.pstrigger}
        aria-haspopup="menu"
        aria-expanded={open}
        data-testid="product-switcher-trigger"
        onClick={() => setOpen((v) => !v)}
      >
        <span
          className={styles.pavatar}
          aria-hidden="true"
          data-testid="product-switcher-avatar"
        >
          {monogram(active.name)}
        </span>
        <span className={styles.pmeta}>
          <span className={styles.plabel}>Product</span>
          <span className={styles.pname}>{active.name}</span>
        </span>
        <svg
          className={styles.pchev}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
          aria-hidden="true"
        >
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>

      {open && (
        <div
          className={styles.pmenu}
          role="menu"
          aria-label="Switch product"
          data-testid="product-switcher-menu"
        >
          <div className={styles.pmlabel}>Your products</div>
          {products.map((p) => {
            const isActive = p.productId === active.productId;
            return (
              <button
                key={p.productId}
                type="button"
                className={isActive ? `${styles.pmitem} ${styles.active}` : styles.pmitem}
                role="menuitemradio"
                aria-checked={isActive}
                onClick={() => choose(p.productId)}
              >
                <span className={styles.pavatar} aria-hidden="true">
                  {monogram(p.name)}
                </span>
                <span className={styles.pmname}>{p.name}</span>
                {isActive && (
                  <svg
                    className={styles.pmcheck}
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth={2.5}
                    aria-hidden="true"
                  >
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                )}
              </button>
            );
          })}
          <div className={styles.pmsep} role="separator" />
          <button
            type="button"
            className={styles.pmnew}
            role="menuitem"
            onClick={() => {
              setOpen(false);
              onSetUpNew?.();
            }}
          >
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
              aria-hidden="true"
            >
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            Set up a new product
          </button>
        </div>
      )}
    </div>
  );
}
