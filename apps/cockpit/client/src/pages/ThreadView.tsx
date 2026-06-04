// WP-004 — <ThreadView /> — the one coherent thread shell (ADR-005).
//
// REORGANISE-Refactor: the thread is re-homed from disconnected tabs
// (Chat | Files) to the ONE coherent reading order the founder signed off:
//
//   ThreadHeader                         (handle · stage · liveness · intent)
//   StageTrack + StatusHeader            (top — the "where am I", FR-04/05/12)
//   ─────────────────────────────────────
//   Conversation · Files                 (named sections, not tabs, CL-02)
//
// The status (StageTrack + StatusHeader) is read at this moment from
// GET /api/changes/:id/status (FR-05 — never a stored post). The working
// area is named sections rather than a single-tab-at-a-time rail so
// "reading" and "driving" sit together (ADR-005). (The Brain section
// lands with WP-006 — its read route ships in that slice.)
//
// One state-pattern set (ADR-005): loading skeleton, 404-gone, and a
// generic error all reuse the shared framing.
//
// References: WP-004 Contract (coherent shell), ADR-005, TDD §6/§6.2.

import { useParams } from "react-router-dom";
import { useChange } from "../api/useChange";
import { useStatus } from "../api/useStatus";
import { ApiError } from "../api/client";
import { ThreadHeader } from "../components/ThreadHeader";
import { StageTrack } from "../components/StageTrack";
import { StatusHeader } from "../components/StatusHeader";
import { Chat } from "../components/Chat";
import { FilesPanel } from "../components/FilesPanel";
import { ContractLinks } from "../components/ContractLinks";
import styles from "../styles/Thread.module.css";

export function ThreadView() {
  const { changeId } = useParams<{ changeId: string }>();
  const id = changeId ?? "";
  const query = useChange(id);
  const statusQuery = useStatus(id);

  if (query.isLoading) {
    return (
      <section data-testid="page-thread" className={styles.page}>
        <p className={styles.status} data-testid="thread-loading">
          Loading...
        </p>
      </section>
    );
  }

  if (query.isError) {
    const isNotFound =
      query.error instanceof ApiError && query.error.status === 404;
    if (isNotFound) {
      return (
        <section data-testid="page-thread" className={styles.page}>
          <div
            className={styles.goneOrMoved}
            data-testid="thread-gone-or-moved"
          >
            <p>This change is gone or moved.</p>
            <p className={styles.goneOrMovedDetail}>
              Worktree path: <code>{id}</code>
            </p>
          </div>
        </section>
      );
    }
    return (
      <section data-testid="page-thread" className={styles.page}>
        <p className={styles.status}>Could not load this change.</p>
      </section>
    );
  }

  const change = query.data!;
  return (
    <section data-testid="page-thread" className={styles.page}>
      <ThreadHeader change={change} />

      {/* The "where am I" spine: stage track + read-time status (FR-04/05/12). */}
      <div className={styles.spine} data-testid="thread-spine">
        <StageTrack stage={change.stage} />
        {statusQuery.isSuccess && <StatusHeader status={statusQuery.data} />}
      </div>

      {/* WP-003 — per-change contract preview links. */}
      <ContractLinks change={change} />

      {/* The working area as named sections, not tabs (ADR-005, CL-02). */}
      <section
        className={styles.section}
        data-testid="section-conversation"
        aria-label="Conversation"
      >
        <h2 className={styles.sectionTitle}>Conversation</h2>
        <Chat changeId={id} />
      </section>

      <section
        className={styles.section}
        data-testid="section-files"
        aria-label="Files"
      >
        <h2 className={styles.sectionTitle}>Files</h2>
        <FilesPanel changeId={id} />
      </section>
    </section>
  );
}
