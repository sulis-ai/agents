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
// Data is loaded through the typed client (useChangesWithLiveness /
// useSearch → apiGet) — never a direct network call in the component
// (WPF-02), one feed poll, no per-card request (NFR-POLL-1). The seam
// scopes the list to the
// active Product server-side (ADR-009); the client groups the scoped set
// into columns.

import { useCallback, useEffect, useRef, useState } from "react";
import { useMatch } from "react-router-dom";
import type { WorkflowStage } from "../../../shared/api-types";
import { useChangesWithLiveness } from "../api/useChangesWithLiveness";
import { hasActiveFilter, useSearch } from "../api/useSearch";
import { EmptyState } from "../components/EmptyState";
import { RefreshButton } from "../components/RefreshButton";
import { SearchBar } from "../components/SearchBar";
import { SkeletonCard } from "../components/SkeletonCard";
import { StageColumn } from "../components/StageColumn";
import { useActiveProduct } from "../api/activeProduct";
import {
  BOARD_STAGES,
  type BoardStage,
  groupChangesByStage,
} from "../lib/groupChangesByStage";
import styles from "./Board.module.css";

/** How many skeleton placeholder cards each lane shows while the feed loads. A
 *  small fixed count (FR-53 — per-card, not one block per column): enough to
 *  read as "a lane of cards is coming", not so many it implies a count. */
const SKELETON_CARDS_PER_LANE = 3;

export function Board() {
  // WP-009 — the SELECTED card is route-derived (CS-1 / FR-50). Read the active
  // change the SAME way the shell does — useMatch("/c/:changeId") → activeChangeId
  // (WorkspaceShell.tsx) — and thread it to each lane → card, so the card whose
  // change is the open route marks itself selected. Never stored on the feed, so
  // it survives a re-poll (carry-over of EF-3's last-good discipline). On a
  // non-change route the match is null → no card is selected.
  const changeRouteMatch = useMatch("/c/:changeId");
  const activeChangeId = changeRouteMatch?.params.changeId ?? null;

  // The board owns the filter state; the toolbar is controlled (ADR-005).
  const [query, setQuery] = useState("");
  const [stages, setStages] = useState<WorkflowStage[]>([]);
  const [needsAttention, setNeedsAttention] = useState(false);

  // WP-008 — the mobile lane switcher's selected lane (the one full-width lane
  // shown < 600px). Tapping a switcher tab scroll-snaps that lane into view;
  // swiping the board updates the selection so the rail always reflects the
  // landed lane (S-8). The board grid is the horizontal-snap scroll container.
  const [selectedStage, setSelectedStage] = useState<BoardStage>("recon");
  const boardRef = useRef<HTMLDivElement>(null);

  // Activate a switcher tab → snap its lane into view. (CSS scroll-snap also
  // lets the founder swipe directly; the scroll handler below keeps the
  // selected tab in sync either way — one source of truth: which lane is
  // centred in the board's viewport.)
  const onSelectStage = useCallback((stage: BoardStage) => {
    setSelectedStage(stage);
    const lane = boardRef.current?.querySelector<HTMLElement>(`#lane-${stage}`);
    lane?.scrollIntoView({
      behavior: "smooth",
      inline: "start",
      block: "nearest",
    });
  }, []);

  // Swipe → keep the selected chip in sync with the lane nearest the viewport
  // centre (the rail reflects position). rAF-coalesced so a fling doesn't spam
  // state. No-op above the mobile breakpoint (the board doesn't snap-scroll
  // there), so it's cheap on desktop.
  useEffect(() => {
    const board = boardRef.current;
    if (!board) return;
    let raf: number | null = null;
    const onScroll = () => {
      if (raf !== null) return;
      raf = requestAnimationFrame(() => {
        raf = null;
        const mid = board.scrollLeft + board.clientWidth / 2;
        let nearest: BoardStage | null = null;
        let best = Infinity;
        for (const stage of BOARD_STAGES) {
          const lane = board.querySelector<HTMLElement>(`#lane-${stage}`);
          if (!lane) continue;
          const centre = lane.offsetLeft + lane.offsetWidth / 2;
          const d = Math.abs(centre - mid);
          if (d < best) {
            best = d;
            nearest = stage;
          }
        }
        if (nearest) setSelectedStage(nearest);
      });
    };
    board.addEventListener("scroll", onScroll, { passive: true });
    return () => {
      board.removeEventListener("scroll", onScroll);
      if (raf !== null) cancelAnimationFrame(raf);
    };
  }, []);

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

  // WP-008 — per-lane counts for the mobile switcher's tab chips (the count
  // does double duty as a "how full is this stage" read). Derived from the
  // same grouped columns the board renders — one feed, no extra request.
  const stageCounts = Object.fromEntries(
    columns.map((c) => [c.stage, c.changes.length]),
  ) as Record<BoardStage, number>;

  return (
    <section className={styles.page} data-testid="page-board">
      <div className={styles.header}>
        <h1 className={styles.title}>Changes in flight</h1>
        <RefreshButton
          queryKey={["changes"]}
          isFetching={fullList.isFetching}
        />
      </div>

      <SearchBar
        query={query}
        stages={stages}
        needsAttention={needsAttention}
        onQueryChange={setQuery}
        onToggleStage={toggleStage}
        onToggleNeedsAttention={() => setNeedsAttention((v) => !v)}
        // WP-008 — the mobile lane-switcher inputs. The chips become an ARIA
        // tablist < 600px (ADR-004); the counts + selected lane + select
        // callback drive that role. (Hidden by CSS at wider widths.)
        counts={stageCounts}
        selectedStage={selectedStage}
        onSelectStage={onSelectStage}
      />

      {/* LOADING ≠ EMPTY (FR-52). While the feed is unresolved the board shows
       * PER-CARD skeletons (FR-53) inside the SAME six-lane scaffold a loaded
       * board uses — so the swap to real data is in-place with no layout jump
       * (BR-24 / NFR-PERF-5). The region is a live `status` (a valid role, so
       * its aria-label/aria-busy are permitted) carrying an SR "Loading your
       * changes…" line; the skeleton cards are inert (aria-hidden, not
       * focusable — §7c precedence, no real card exists yet). The skeleton path
       * is the INITIAL load only: a background poll keeps last-good data and
       * never re-enters here (EF-3, gated on `isLoading` not `isFetching`). */}
      {active.isLoading && (
        <div
          className={styles.board}
          data-testid="board-loading"
          role="status"
          aria-busy="true"
          aria-label="Loading changes"
        >
          <span className={styles.srOnly}>Loading your changes…</span>
          {BOARD_STAGES.map((stage) => (
            <section
              key={stage}
              id={`lane-${stage}`}
              className={styles.skeletonLane}
              data-testid="stage-column"
              data-stage={stage}
            >
              {/* The lane scaffold (a quiet sticky header band + an internal
               * list) mirrors the loaded lane's metrics so the board shape is
               * identical loading vs loaded. The header is intentionally bare —
               * no stage name yet — but holds the same height as the real
               * laneHead so the cards below sit at the same y. */}
              <div className={styles.skeletonHead} aria-hidden="true" />
              <div className={styles.skeletonList}>
                {Array.from({ length: SKELETON_CARDS_PER_LANE }, (_, i) => (
                  <SkeletonCard key={i} />
                ))}
              </div>
            </section>
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
        <div className={styles.board} data-testid="board" ref={boardRef}>
          {columns.map((col) => (
            <StageColumn
              key={col.stage}
              stage={col.stage}
              changes={col.changes}
              activeChangeId={activeChangeId}
            />
          ))}
        </div>
      )}
    </section>
  );
}
