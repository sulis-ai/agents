// WP-012 — Dashboard page.
//
// Lands the change-card grid (one per change), empty state, error
// state, loading skeleton, and the manual Refresh button. Uses
// useChangesWithLiveness so liveness dots refresh every 10s (ADR-007).
//
// State branches (TDD §6.2):
//   - isLoading           → skeleton placeholder grid
//   - isError             → error box + retry button
//   - isSuccess + empty   → <EmptyState />
//   - isSuccess + items   → grid of <ChangeCard>s

import { useChangesWithLiveness } from "../api/useChangesWithLiveness";
import { ChangeCard } from "../components/ChangeCard";
import { EmptyState } from "../components/EmptyState";
import { RefreshButton } from "../components/RefreshButton";
import styles from "./Dashboard.module.css";

const SKELETON_COUNT = 4;

export function Dashboard() {
  const query = useChangesWithLiveness();

  return (
    <section className={styles.page} data-testid="page-dashboard">
      <div className={styles.header}>
        <h1 className={styles.title}>Changes in flight</h1>
        <RefreshButton
          queryKey={["changes"]}
          isFetching={query.isFetching}
        />
      </div>

      {query.isLoading && (
        <div className={styles.skeleton} data-testid="dashboard-loading">
          {Array.from({ length: SKELETON_COUNT }).map((_, i) => (
            <div key={i} className={styles.skeletonCard} />
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
          <button
            type="button"
            onClick={() => query.refetch()}
          >
            Retry
          </button>
        </div>
      )}

      {query.isSuccess && query.data.length === 0 && <EmptyState />}

      {query.isSuccess && query.data.length > 0 && (
        <div className={styles.grid}>
          {query.data.map((change) => (
            <ChangeCard key={change.changeId} change={change} />
          ))}
        </div>
      )}
    </section>
  );
}
