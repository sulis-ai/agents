// WP-003 — Board page (was Dashboard; REORGANISE-Refactor).
//
// Journey A round-trip, client half: the founder opens the app and sees
// their real in-flight changes laid out in six lifecycle stage columns
// (recon→specify→design→implement→review→ship; FR-01, ADR-005). Each
// change is a <ChangeCard> in its stage column; shipped changes are NOT
// in-flight and never appear (FR-15). The behaviour the flat-grid
// Dashboard guaranteed is preserved (pinned by Dashboard.test.tsx, the
// characterisation test): the three async states, card-click navigation,
// the manual Refresh, and the 10s liveness poll.
//
// State branches (one state-pattern set, ADR-005) — driven by the presence of
// data (last-good OR current), not the raw success flag (see WP-007/EF-3):
//   - no data + loading     → six-column skeleton board
//   - no data + error       → error box + retry button (the INITIAL-load
//                             failure, EF-1 — no last-good to fall back to)
//   - data + no in-flight + unfiltered → <EmptyState /> (how to start one, FR-03)
//   - data (+ in-flight or filtered)   → the six-column board
//
// WP-007 — the enriched-feed integration seam + the board-level async
// behaviour. The real needsAttention / health / lastActivityAt fields flow
// Board → StageColumn → ChangeCard untouched (waiting XOR health foot; probe
// recency). The board OWNS its async-state behaviour against that wider shape:
//   - EF-1 (feed fails on initial load) → error box + Retry, no partial board.
//   - EF-3 / NFR-DEGRADE-3 (a background poll fails mid-session) → TanStack
//     Query keeps the last-good `data`; the board renders OFF that data, so it
//     never flickers to the error box; the next interval retries; manual
//     Refresh still works. This is why the render gates on `hasData`
//     (data !== undefined), not `isSuccess` — `isSuccess` flips false on the
//     failed poll and would drop the whole board.
//
// WP-007 — Journey D round-trip, client half: the board toolbar (search +
// stage filter + needs-attention filter) narrows the SAME board (ADR-005).
// When any filter is active the board renders the /api/search results in
// the same stage-column layout — never a separate results screen. When no
// filter is active the board shows the full active-Product list (WP-003).
// Clearing every filter restores the full board. A change re-seeded as
// shipped drops off the in-flight board on the next poll (AF-5 / FR-15).
//
// Data is fetched through the typed client (useChangesWithLiveness /
// useSearch → apiGet) — never `fetch` in the component (WPF-02), one feed
// poll, no per-card fetch (NFR-POLL-1). The seam scopes the list to the
// active Product server-side (ADR-009); the client groups the scoped set
// into columns.

import { useState } from "react";
import type { WorkflowStage } from "../../../shared/api-types";
import { useChangesWithLiveness } from "../api/useChangesWithLiveness";
import { hasActiveFilter, useSearch } from "../api/useSearch";
import { EmptyState } from "../components/EmptyState";
import { RefreshButton } from "../components/RefreshButton";
import { SearchBar } from "../components/SearchBar";
import { StageColumn } from "../components/StageColumn";
import { useActiveProduct } from "../api/activeProduct";
import { BOARD_STAGES, groupChangesByStage } from "../lib/groupChangesByStage";
import styles from "./Board.module.css";

export function Board() {
  // The board owns the filter state; the toolbar is controlled (ADR-005).
  const [query, setQuery] = useState("");
  const [stages, setStages] = useState<WorkflowStage[]>([]);
  const [needsAttention, setNeedsAttention] = useState(false);

  // WP-008 — the board (and its filters) are scoped to the active Product
  // (FR-37/38, ADR-009): the active-Product id threads into both reads as
  // `?product=`, so switching Products re-scopes the SAME board (ADR-005).
  const { activeProductId } = useActiveProduct();

  const searchArgs = { q: query, stages, needsAttention };
  const filtering = hasActiveFilter(searchArgs);

  const fullList = useChangesWithLiveness(activeProductId);
  const search = useSearch(searchArgs, activeProductId);

  // The active query: search when filtering, the full list otherwise. The
  // results render in the SAME stage-column board (ADR-005).
  const active = filtering ? search : fullList;

  function toggleStage(stage: WorkflowStage) {
    setStages((prev) =>
      prev.includes(stage) ? prev.filter((s) => s !== stage) : [...prev, stage],
    );
  }

  // EF-3 (NFR-DEGRADE-3) — render off the last-good data, not the success
  // flag. When a background poll fails, TanStack Query flips the query to
  // `isError` but KEEPS the last successful `data`; gating the board on
  // `isSuccess` would flicker the whole board to the error box on every failed
  // poll (the founder loses the board mid-session). So: whenever we have data
  // (current OR last-good) the board renders; the error box is reserved for the
  // INITIAL-load failure (EF-1), where there is no data to fall back to.
  const data = active.data;
  const hasData = data !== undefined;

  // Group into the six fixed columns; shipped is excluded (FR-15), so an
  // all-shipped store yields zero in-flight changes → the empty state.
  const columns = hasData ? groupChangesByStage(data) : [];
  const inFlightCount = columns.reduce((n, c) => n + c.changes.length, 0);

  return (
    <section className={styles.page} data-testid="page-board">
      <div className={styles.header}>
        <h1 className={styles.title}>Changes in flight</h1>
        <RefreshButton queryKey={["changes"]} isFetching={fullList.isFetching} />
      </div>

      <SearchBar
        query={query}
        stages={stages}
        needsAttention={needsAttention}
        onQueryChange={setQuery}
        onToggleStage={toggleStage}
        onToggleNeedsAttention={() => setNeedsAttention((v) => !v)}
      />

      {active.isLoading && (
        <div
          className={styles.board}
          data-testid="board-loading"
          aria-busy="true"
          aria-label="Loading changes"
        >
          {BOARD_STAGES.map((stage) => (
            <div key={stage} className={styles.skeletonCol}>
              <div className={styles.skeletonHead} />
              <div className={styles.skeletonCard} />
            </div>
          ))}
        </div>
      )}

      {/* EF-1 — the error box is the INITIAL-load failure only (no last-good
       * data to show). A failed background poll with last-good data (EF-3)
       * keeps the board and never reaches here. */}
      {active.isError && !hasData && (
        <div className={styles.errorBox} role="alert">
          <p className={styles.errorHeading}>
            Something went wrong loading your changes.
          </p>
          <p className={styles.errorMessage}>
            {active.error instanceof Error
              ? active.error.message
              : "Unknown error"}
          </p>
          <button type="button" onClick={() => void active.refetch()}>
            Retry
          </button>
        </div>
      )}

      {/* The "start a change" empty state only shows for the UNFILTERED board
       * (a genuinely empty store, FR-03). When filtering, zero matches still
       * renders the board — it has narrowed to nothing — so the founder sees
       * the same board, now empty, rather than a "start a change" prompt
       * (ADR-005: filters narrow the same board). */}
      {hasData && inFlightCount === 0 && !filtering && <EmptyState />}

      {hasData && (inFlightCount > 0 || filtering) && (
        <div className={styles.board} data-testid="board">
          {columns.map((col) => (
            <StageColumn
              key={col.stage}
              stage={col.stage}
              changes={col.changes}
            />
          ))}
        </div>
      )}
    </section>
  );
}
