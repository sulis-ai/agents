// WP-002 — <ProductControl> the one shared product vocabulary (ADR-002, EP-03).
//
// One presentation/interaction-only primitive — a value chip trigger + a
// searchable popover — placed identically in three homes:
//   1. the top-bar scope switcher  (mode="scope")
//   2. the change-nav product property (mode="assign")
//   3. the board card assign-in-context (mode="assign", compact)
//
// Build once, place three times (EP-03). The three homes are THIN placements
// that supply rows + handlers; the menu logic, keyboard model and a11y model
// live here. The primitive NEVER calls the network — each home injects its
// onSelect / mutation handler at the edge, so this stays a pure, testable
// component.
//
// Built to the SIGNED visual contract (.design/cockpit-product-experience/
// MOCKUP.html — .pswitch / .pmenu / .propChip / .pmitem) and consumes
// tokens.css custom properties only (no invented colours). The neutral
// two-letter monogram is the existing monogram() helper, REUSED (not
// re-implemented) from ProductSwitcher.tsx (the locked cockpit decision: the
// tile is chrome, not brand decoration).
//
// Accessibility (the founder's explicit ask; ADR-002's one shared model):
//   - never colour alone — every state is glyph + word (all-grid tile / dashed
//     unassigned tile / monogram; active row by tick + bold weight);
//   - trigger is a real <button> with aria-haspopup="menu" + aria-expanded;
//   - menu is role="menu" with role="menuitemradio" rows + aria-checked;
//   - labelled typeahead <input>; arrow/Enter/Escape keyboard parity;
//   - counts ride the row's accessible name ("Clinics, 6 changes");
//   - ≥44px targets; visible :focus-visible ring; reduced-motion fallback;
//   - aria-live="polite" announces "Saving…" then "Saved" (assign mode).

import { useEffect, useMemo, useRef, useState } from "react";
import { monogram } from "./ProductSwitcher";
import styles from "./ProductControl.module.css";

export type ProductControlMode = "scope" | "assign";

export type ProductGlyph = "monogram" | "all-grid" | "unassigned-dashed";

export interface ProductRow {
  /** A product id, or a synthetic "all" / "unassigned" sentinel in scope mode. */
  productId: string;
  name: string;
  /** Live count (scope mode); folded into the row's accessible name. */
  count?: number;
  /** Which tile glyph to render. Defaults to "monogram". */
  glyph?: ProductGlyph;
}

export interface ProductControlProps {
  mode: ProductControlMode;
  rows: ProductRow[];
  /** The ticked row id, or null when nothing is selected (unassigned). */
  selectedId: string | null;
  onSelect: (id: string | null) => void;
  /** Board-card placement — a quieter, denser chip. */
  compact?: boolean;
  /** Drives the aria-live announce (assign mode). */
  saveState?: "idle" | "saving" | "saved";
  onSetUpNew?: () => void;
  /** Scope-mode foot — routes to product settings (WP-007). */
  onManageProducts?: () => void;
  /** "Remove from product" (assign mode, only when assigned). */
  onRemove?: () => void;
  /** Explicit a11y name for the trigger (e.g. "Add this change to a product"). */
  triggerLabel?: string;
  /**
   * Override the trigger/menu `data-testid` prefix so the ONE primitive can be
   * placed in more than one home and still be addressed precisely (WP-003: the
   * agent picker reuses this primitive — no second popover — and aliases the
   * testids to "agent-picker-*"). Defaults to "product-control".
   */
  testIdPrefix?: string;
  /**
   * Which way the popover opens. `"down"` (default) keeps the historical
   * top-of-page behaviour (the scope switcher / change-nav / which-product all
   * open DOWNWARD). `"up"` is the drop-up variant for placements pinned to the
   * bottom of the viewport — the agent picker at the composer foot, where a
   * downward menu would fall off-screen (chat-ux Fix 1).
   */
  placement?: "down" | "up";
  /**
   * Placeholder + aria-label for the popover's search input. Defaults to the
   * product wording; the agent picker overrides it ("Find an agent…") since it
   * reuses this primitive (chat-ux: the agent picker showed "Find a product").
   */
  searchLabel?: string;
}

// ─── glyph tiles ────────────────────────────────────────────────────────────

function GridGlyph() {
  // The "everything" tile — a grid of dots, NOT two letters. Reads as "all".
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <circle cx="6" cy="6" r="1.6" />
      <circle cx="12" cy="6" r="1.6" />
      <circle cx="18" cy="6" r="1.6" />
      <circle cx="6" cy="12" r="1.6" />
      <circle cx="12" cy="12" r="1.6" />
      <circle cx="18" cy="12" r="1.6" />
      <circle cx="6" cy="18" r="1.6" />
      <circle cx="12" cy="18" r="1.6" />
      <circle cx="18" cy="18" r="1.6" />
    </svg>
  );
}

function PlusGlyph() {
  return (
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
  );
}

/** A glyph tile for a row / the trigger. Carries `data-glyph` for testing + the
 * never-colour-alone contract (the shape itself distinguishes the state). */
function Tile({
  glyph,
  name,
  compact,
}: {
  glyph: ProductGlyph;
  name: string;
  compact?: boolean;
}) {
  const cls = [
    glyph === "monogram"
      ? styles.mono
      : glyph === "all-grid"
        ? styles.tileAll
        : styles.tileNone,
    compact ? styles.sm : "",
  ]
    .filter(Boolean)
    .join(" ");
  return (
    <span className={cls} data-glyph={glyph} aria-hidden="true">
      {glyph === "monogram" ? (
        monogram(name)
      ) : glyph === "all-grid" ? (
        <GridGlyph />
      ) : (
        <PlusGlyph />
      )}
    </span>
  );
}

function Chevron() {
  return (
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
  );
}

function Tick() {
  return (
    <svg
      className={styles.pmcheck}
      data-testid="product-control-tick"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2.5}
      aria-hidden="true"
    >
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}

// ─── accessible names ─────────────────────────────────────────────────────────

/** "Clinics, 6 changes" — the count rides the accessible name so a screen
 * reader hears the shape of the work, not just the label. */
function rowLabel(row: ProductRow): string {
  if (typeof row.count === "number") {
    return `${row.name}, ${row.count} ${row.count === 1 ? "change" : "changes"}`;
  }
  return row.name;
}

const UNASSIGNED_TRIGGER_LABEL = "Add to a product";

export function ProductControl({
  mode,
  rows,
  selectedId,
  onSelect,
  compact,
  saveState = "idle",
  onSetUpNew,
  onManageProducts,
  onRemove,
  triggerLabel,
  testIdPrefix = "product-control",
  placement = "down",
  searchLabel = "Find a product…",
}: ProductControlProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(-1);
  const rootRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);

  // Close on outside click / Escape — the standard menu affordance, shared by
  // every home (matches the existing ProductSwitcher contract). The Escape
  // listener is document-level so the menu closes regardless of which element
  // inside the popover holds focus (the menu container's own onKeyDown also
  // refocuses the trigger when focus is within).
  useEffect(() => {
    if (!open) return;
    function onDocClick(e: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    function onDocKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onDocClick);
    document.addEventListener("keydown", onDocKey);
    return () => {
      document.removeEventListener("mousedown", onDocClick);
      document.removeEventListener("keydown", onDocKey);
    };
  }, [open]);

  // Reset the typeahead + active row each time the menu opens.
  useEffect(() => {
    if (open) {
      setQuery("");
      setActiveIndex(-1);
    }
  }, [open]);

  const selectedRow = rows.find((r) => r.productId === selectedId) ?? null;

  // Typeahead filter — case-insensitive substring over the visible rows.
  const filteredRows = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter((r) => r.name.toLowerCase().includes(q));
  }, [rows, query]);

  function commit(id: string | null) {
    setOpen(false);
    onSelect(id);
  }

  function closeAndRefocus() {
    setOpen(false);
    triggerRef.current?.focus();
  }

  // The foot actions (Remove / Set up / Manage) all close the menu then run
  // their injected handler — one shape, extracted so the three call sites stay
  // identical (EP-03: extract at the 2nd consumer).
  function closeThen(fn: () => void) {
    return () => {
      setOpen(false);
      fn();
    };
  }

  // Keyboard model on the menu container — arrow between rows, Enter commits the
  // active one, Escape closes + refocuses the trigger. Full parity with mouse.
  function onMenuKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Escape") {
      e.preventDefault();
      closeAndRefocus();
      return;
    }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex((i) => Math.min(i + 1, filteredRows.length - 1));
      return;
    }
    if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex((i) => Math.max(i - 1, 0));
      return;
    }
    if (e.key === "Enter") {
      e.preventDefault();
      const row = filteredRows[activeIndex];
      if (row) commit(row.productId);
    }
  }

  // Open from the trigger via Enter/Space (in addition to click).
  function onTriggerKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      setOpen((v) => !v);
    }
  }

  const isAssigned = mode === "assign" && selectedRow !== null;
  const triggerGlyph: ProductGlyph =
    selectedRow?.glyph ??
    (mode === "assign" ? "unassigned-dashed" : "monogram");
  const triggerName =
    selectedRow?.name ?? (mode === "assign" ? UNASSIGNED_TRIGGER_LABEL : "");

  const liveText =
    saveState === "saving" ? "Saving…" : saveState === "saved" ? "Saved" : "";

  const triggerClasses = [
    mode === "assign" ? styles.propChip : styles.pstrigger,
    mode === "assign" && !isAssigned ? styles.unassigned : "",
    compact ? styles.compact : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={styles.root} ref={rootRef}>
      <button
        type="button"
        ref={triggerRef}
        className={triggerClasses}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={
          triggerLabel ??
          (mode === "assign" && !isAssigned
            ? UNASSIGNED_TRIGGER_LABEL
            : undefined)
        }
        data-testid={`${testIdPrefix}-trigger`}
        onClick={() => setOpen((v) => !v)}
        onKeyDown={onTriggerKeyDown}
      >
        {mode === "assign" && !isAssigned ? (
          // #378 — the unassigned product chip leads with the signed mockup's
          // light inline "＋" icon (.plusIcon), not the dashed tile box, so the
          // chip reads as "＋ Add to a product" exactly as the visual contract
          // (.design/.../MOCKUP.html .propChip.unassigned) draws it.
          <span className={styles.plusIcon} data-glyph="plus" aria-hidden="true">
            <PlusGlyph />
          </span>
        ) : (
          <Tile glyph={triggerGlyph} name={triggerName} compact={compact} />
        )}
        {mode === "scope" ? (
          <span className={styles.pmeta}>
            <span className={styles.plabel}>Viewing</span>
            <span className={styles.pname}>{triggerName}</span>
          </span>
        ) : (
          <span className={styles.pcname}>{triggerName}</span>
        )}
        {isAssigned || mode === "scope" ? <Chevron /> : null}
      </button>

      {open && (
        <div
          className={`${styles.pmenu} ${placement === "up" ? styles.pmenuUp : ""}`}
          data-testid={`${testIdPrefix}-menu`}
          data-placement={placement}
          onKeyDown={onMenuKeyDown}
        >
          {/* The typeahead sits in the popover header, OUTSIDE role="menu": a
           * searchable menu's text input is not a permitted child of a menu
           * per WAI-ARIA (aria-required-children), so the menu wraps only its
           * menuitem rows + foot actions (WAI-ARIA APG searchable-menu shape). */}
          <div className={styles.pmsearch}>
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
              aria-hidden="true"
            >
              <circle cx="11" cy="11" r="7" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
            <input
              ref={searchRef}
              type="text"
              placeholder={searchLabel}
              aria-label={searchLabel.replace(/…$/, "")}
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setActiveIndex(-1);
              }}
            />
          </div>

          <div
            role="menu"
            aria-label={
              mode === "scope" ? "Switch scope" : "Assign to a product"
            }
          >
            {filteredRows.map((row, i) => {
              const isChecked = row.productId === selectedId;
              const isActive = i === activeIndex;
              const cls = [
                styles.pmitem,
                isChecked ? styles.active : "",
                isActive ? styles.keyactive : "",
              ]
                .filter(Boolean)
                .join(" ");
              return (
                <button
                  key={row.productId}
                  type="button"
                  className={cls}
                  role="menuitemradio"
                  aria-checked={isChecked}
                  aria-label={rowLabel(row)}
                  onClick={() => commit(row.productId)}
                  onMouseEnter={() => setActiveIndex(i)}
                >
                  <Tile
                    glyph={row.glyph ?? "monogram"}
                    name={row.name}
                    compact
                  />
                  <span className={styles.pmname}>{row.name}</span>
                  {typeof row.count === "number" && (
                    <span className={styles.pmcount} aria-hidden="true">
                      {row.count}
                    </span>
                  )}
                  {isChecked && <Tick />}
                </button>
              );
            })}

            {(isAssigned && onRemove) ||
            onSetUpNew ||
            (mode === "scope" && onManageProducts) ? (
              <div className={styles.pmsep} role="separator" />
            ) : null}

            {mode === "assign" && isAssigned && onRemove && (
              <button
                type="button"
                className={`${styles.pmitem} ${styles.pmRemove}`}
                role="menuitem"
                aria-label="Remove from product, set to unassigned"
                onClick={closeThen(onRemove)}
              >
                <span
                  className={`${styles.tileNone} ${styles.sm}`}
                  data-glyph="unassigned-dashed"
                  aria-hidden="true"
                >
                  <svg
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth={2}
                  >
                    <line x1="5" y1="12" x2="19" y2="12" />
                  </svg>
                </span>
                <span className={styles.pmname}>Remove from product</span>
              </button>
            )}

            {onSetUpNew && (
              <button
                type="button"
                className={styles.pmnew}
                role="menuitem"
                onClick={closeThen(onSetUpNew)}
              >
                <PlusGlyph />
                Set up a new product
              </button>
            )}

            {mode === "scope" && onManageProducts && (
              <button
                type="button"
                className={styles.pmmanage}
                role="menuitem"
                onClick={closeThen(onManageProducts)}
              >
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth={2}
                  aria-hidden="true"
                >
                  <circle cx="12" cy="12" r="3" />
                  <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
                </svg>
                Manage products
              </button>
            )}
          </div>
        </div>
      )}

      {mode === "assign" && (
        <div
          className={styles.savedTick}
          data-testid="product-control-live"
          role="status"
          aria-live="polite"
        >
          {liveText && (
            <>
              {saveState === "saved" && (
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth={2.5}
                  aria-hidden="true"
                >
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              )}
              {liveText}
            </>
          )}
        </div>
      )}
    </div>
  );
}
