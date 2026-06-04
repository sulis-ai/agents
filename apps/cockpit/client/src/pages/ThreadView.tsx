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
import { Composer } from "../components/Composer";
import { FilesPanel } from "../components/FilesPanel";
import { ContractLinks } from "../components/ContractLinks";
import { BrainSection } from "../components/BrainSection";
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
        {/* WP-005 — the chat composer docked at the bottom of the thread: the
            app's one write/act path (ADR-003). Sending a message is always one
            glance from reading the change (signed contract). */}
        <Composer changeId={id} />
      </section>

      <section
        className={styles.section}
        data-testid="section-files"
        aria-label="Files"
      >
        <h2 className={styles.sectionTitle}>Files</h2>
        <FilesPanel changeId={id} />
      </section>

      {/* WP-006 — the Brain section: the entities the agent created for this
          change, grouped by kind with a readable detail per item (FR-06/07).
          Shares the thread's working-area section model (CL-02) — read its
          route ships in this slice. */}
      <section
        className={styles.section}
        data-testid="section-brain"
        aria-label="Brain"
      >
        <h2 className={styles.sectionTitle}>Brain</h2>
        <BrainSection changeId={id} />
      </section>
    </section>
  );
}
