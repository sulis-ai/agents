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
// State branches (one state-pattern set, ADR-005):
//   - isLoading              → six-column skeleton board
//   - isError                → error box + retry button
//   - isSuccess + no in-flight → <EmptyState /> (guides how to start one, FR-03)
//   - isSuccess + in-flight  → the six-column board
//
// Data is fetched through the typed client (useChangesWithLiveness →
// apiGet) — never `fetch` in the component (WPF-02). The seam scopes the
// list to the active Product server-side (ADR-009); the client groups the
// scoped set into columns.

import { useChangesWithLiveness } from "../api/useChangesWithLiveness";
import { EmptyState } from "../components/EmptyState";
import { RefreshButton } from "../components/RefreshButton";
import { StageColumn } from "../components/StageColumn";
import { BOARD_STAGES, groupChangesByStage } from "../lib/groupChangesByStage";
import styles from "./Board.module.css";

export function Board() {
  const query = useChangesWithLiveness();

  // Group into the six fixed columns; shipped is excluded (FR-15), so an
  // all-shipped store yields zero in-flight changes → the empty state.
  const columns = query.isSuccess
    ? groupChangesByStage(query.data)
    : [];
  const inFlightCount = columns.reduce((n, c) => n + c.changes.length, 0);

  return (
    <section className={styles.page} data-testid="page-board">
      <div className={styles.header}>
        <h1 className={styles.title}>Changes in flight</h1>
        <RefreshButton queryKey={["changes"]} isFetching={query.isFetching} />
      </div>

      {query.isLoading && (
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

      {query.isError && (
        <div className={styles.errorBox} role="alert">
          <p className={styles.errorHeading}>
            Something went wrong loading your changes.
          </p>
          <p className={styles.errorMessage}>
            {query.error instanceof Error
              ? query.error.message
              : "Unknown error"}
          </p>
          <button type="button" onClick={() => query.refetch()}>
            Retry
          </button>
        </div>
      )}

      {query.isSuccess && inFlightCount === 0 && <EmptyState />}

      {query.isSuccess && inFlightCount > 0 && (
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
