// WP-007 — <SearchBar> — the board toolbar (FR-10/11/12, ADR-005).
//
// One board toolbar hosts the content-search box + the stage filter chips
// + the needs-attention chip. They narrow the SAME board (ADR-005) — there
// is no separate results screen. Matches the SIGNED visual contract
// (sulis-app.html: a `role="search"` toolbar, a content-search box with a
// magnifier + "searches content" hint, neutral stage chips, and a
// "Needs attention" chip). Active chips take the neutral-inverse state from
// the contract (no brand fill).
//
// Controlled + presentational: the Board owns the filter state and passes
// it down with the change callbacks. Consumes tokens.css only — no raw hex
// (WPF / ADR-005 one design language).

import { useRef } from "react";
import type { WorkflowStage } from "../../../shared/api-types";
import { BOARD_STAGES } from "../lib/groupChangesByStage";
import styles from "./SearchBar.module.css";

/** Title-cased display name for each board stage (matches StageColumn). */
const STAGE_NAME: Record<(typeof BOARD_STAGES)[number], string> = {
  recon: "Recon",
  specify: "Specify",
  design: "Design",
  implement: "Implement",
  review: "Review",
  ship: "Ship",
};

// WP-008 — the two icons each appear in BOTH the desktop toolbar and the mobile
// switcher rail (the magnifier in the search box + the collapsed search button;
// the warning triangle in both "Needs attention" chips). Extracted to a single
// local presentational component each (2-consumer threshold, EP-03) so the SVG
// path lives in one place. Both are decorative (aria-hidden) — the control's
// label carries the meaning.

/** Magnifier glyph (decorative). The optional className lets the desktop search
 *  box size/colour it via .searchIcon while the mobile button uses its own. */
function SearchIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      aria-hidden="true"
    >
      <circle cx="11" cy="11" r="7" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  );
}

/** Warning triangle glyph (decorative) — the "Needs attention" mark. */
function WarningTriangleIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      aria-hidden="true"
    >
      <path d="M10.29 3.86 1.82 18a1 1 0 0 0 .86 1.5h18.64a1 1 0 0 0 .86-1.5L13.71 3.86a1 1 0 0 0-1.72 0z" />
      <line x1="12" y1="9" x2="12" y2="13" />
      <line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  );
}

/** Per-lane change counts shown on the mobile switcher's tab chips (WP-008). */
export type StageCounts = Partial<
  Record<(typeof BOARD_STAGES)[number], number>
>;

export interface SearchBarProps {
  query: string;
  stages: WorkflowStage[];
  needsAttention: boolean;
  onQueryChange: (q: string) => void;
  onToggleStage: (stage: WorkflowStage) => void;
  onToggleNeedsAttention: () => void;
  // ── WP-008 — mobile lane-switcher inputs (ADR-004) ──
  // The SAME chips gain a width-conditional second role as an ARIA tablist
  // lane switcher on mobile. These drive that role; they are optional so the
  // desktop-filter-only contract (Layer-1 callers) is unchanged. `counts` puts
  // each lane's size on its chip; `selectedStage` is the lane currently shown
  // (drives aria-selected); `onSelectStage` fires when a tab is activated so
  // the board can snap that lane into view.
  /** Per-lane counts shown on the switcher tab chips. */
  counts?: StageCounts;
  // The switcher only ever deals with the six BOARD stages (shipped is not a
  // lane, FR-15), so its selection type is the board-stage subset — not the
  // wider WorkflowStage (which includes "shipped").
  /** The stage whose lane is currently shown (the selected tab). */
  selectedStage?: (typeof BOARD_STAGES)[number];
  /** Activate a tab → show that stage's lane. */
  onSelectStage?: (stage: (typeof BOARD_STAGES)[number]) => void;
}

export function SearchBar({
  query,
  stages,
  needsAttention,
  onQueryChange,
  onToggleStage,
  onToggleNeedsAttention,
  counts,
  selectedStage,
  onSelectStage,
}: SearchBarProps) {
  const stageSet = new Set(stages);
  // The mobile rail's collapsed search icon focuses the (still-present) search
  // input rather than introducing a parallel mobile search surface — search
  // wiring is WP-007's; this WP only re-lays-out the controls (EP-03).
  const searchInputRef = useRef<HTMLInputElement>(null);

  return (
    <>
      <div
        className={styles.toolbar}
        role="search"
        aria-label="Search and filter changes"
      >
        <div className={styles.search}>
          <SearchIcon className={styles.searchIcon} />
          <input
            ref={searchInputRef}
            type="search"
            className={styles.input}
            aria-label="Search inside your changes — conversations and created items, not just titles"
            placeholder="Search inside your changes — conversations and created items, not just titles"
            value={query}
            onChange={(e) => onQueryChange(e.target.value)}
          />
          <span className={styles.hint}>searches content</span>
        </div>

        {BOARD_STAGES.map((stage) => {
          const active = stageSet.has(stage);
          return (
            <button
              key={stage}
              type="button"
              className={`${styles.chip} ${active ? styles.on : ""}`}
              aria-pressed={active}
              onClick={() => onToggleStage(stage)}
            >
              {STAGE_NAME[stage]}
            </button>
          );
        })}

        <button
          type="button"
          className={`${styles.chip} ${needsAttention ? styles.on : ""}`}
          aria-pressed={needsAttention}
          onClick={onToggleNeedsAttention}
        >
          <WarningTriangleIcon />
          Needs attention
        </button>
      </div>

      {/* WP-008 — the MOBILE lane switcher (ADR-004). The same Recon…Ship chips,
        reused as an ARIA tablist that picks which single full-width lane is
        shown. CSS shows this rail and hides the desktop .toolbar below 600px
        (and vice-versa) — it is ONE component with a width-conditional role,
        not a parallel mobile widget (EP-03). Only rendered when the board
        wires the switcher inputs (counts + onSelectStage); the desktop-only
        callers omit them and get just the .toolbar above.

        The search icon + "Needs attention" toggle sit in the rail but OUTSIDE
        the role="tablist" — a tablist may own only tabs (W3C ARIA
        aria-required-children), so the non-tab controls are siblings of it. */}
      {counts && onSelectStage && (
        <div className={styles.laneSwitcher} data-testid="lane-switcher">
          <button
            type="button"
            className={styles.switchSearch}
            aria-label="Search your changes"
            onClick={() => searchInputRef.current?.focus()}
          >
            <SearchIcon />
          </button>

          <div
            className={styles.switchTabs}
            role="tablist"
            aria-label="Pick a stage to view"
          >
            {BOARD_STAGES.map((stage) => {
              const isSelected = selectedStage === stage;
              return (
                <button
                  key={stage}
                  type="button"
                  role="tab"
                  id={`tab-${stage}`}
                  aria-selected={isSelected}
                  aria-controls={`lane-${stage}`}
                  className={`${styles.switchChip} ${styles[stage]} ${
                    isSelected ? styles.switchOn : ""
                  }`}
                  onClick={() => onSelectStage(stage)}
                >
                  <span className={styles.sdot} aria-hidden="true" />
                  {STAGE_NAME[stage]}
                  <span className={styles.switchCount}>
                    {counts[stage] ?? 0}
                  </span>
                </button>
              );
            })}
          </div>

          <button
            type="button"
            className={`${styles.switchChip} ${styles.attn} ${
              needsAttention ? styles.switchOn : ""
            }`}
            aria-pressed={needsAttention}
            onClick={onToggleNeedsAttention}
          >
            <WarningTriangleIcon />
            Needs attention
          </button>
        </div>
      )}
    </>
  );
}
