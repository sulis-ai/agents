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

export interface SearchBarProps {
  query: string;
  stages: WorkflowStage[];
  needsAttention: boolean;
  onQueryChange: (q: string) => void;
  onToggleStage: (stage: WorkflowStage) => void;
  onToggleNeedsAttention: () => void;
}

export function SearchBar({
  query,
  stages,
  needsAttention,
  onQueryChange,
  onToggleStage,
  onToggleNeedsAttention,
}: SearchBarProps) {
  const stageSet = new Set(stages);

  return (
    <div className={styles.toolbar} role="search" aria-label="Search and filter changes">
      <div className={styles.search}>
        <svg
          className={styles.searchIcon}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          aria-hidden="true"
        >
          <circle cx="11" cy="11" r="7" />
          <line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
        <input
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
        Needs attention
      </button>
    </div>
  );
}
