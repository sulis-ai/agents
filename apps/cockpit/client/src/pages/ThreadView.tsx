// WP-013 — <ThreadView /> — per-thread page at /c/:changeId.
//
// Hosts the thread header, the URL-driven Chat | Files tab switcher,
// the Chat panel, and (WP-014) the Files panel — the worktree tree +
// Monaco read-only viewer + copy-path button.
//
// Empty states:
//   - useChange loading → "Loading..." status.
//   - useChange 404 → "This change is gone or moved." rendered in the
//     page body. The Shell's sidebar continues to render (because this
//     page returns a normal node rather than throwing).
//
// References: WP-013 Contract (<ThreadView>), TDD §6.2 (empty/error
// states), ADR-007 (TanStack Query for server data).

import { useParams } from "react-router-dom";
import { useChange } from "../api/useChange";
import { ApiError } from "../api/client";
import { ThreadHeader } from "../components/ThreadHeader";
import { ThreadTabs } from "../components/ThreadTabs";
import { Chat } from "../components/Chat";
import { FilesPanel } from "../components/FilesPanel";
import { ContractLinks } from "../components/ContractLinks";
import styles from "../styles/Thread.module.css";

export function ThreadView() {
  const { changeId } = useParams<{ changeId: string }>();
  const id = changeId ?? "";
  const query = useChange(id);

  if (query.isLoading) {
    return (
      <section data-testid="page-thread" className={styles.page}>
        <p className={styles.status}>Loading...</p>
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
      {/* WP-003 — per-change contract preview: each change surfaces its OWN
          rendered data + UI contracts (generic resolution, ADR-003). */}
      <ContractLinks change={change} />
      <ThreadTabs
        chat={<Chat changeId={id} />}
        files={<FilesPanel changeId={id} />}
      />
    </section>
  );
}
