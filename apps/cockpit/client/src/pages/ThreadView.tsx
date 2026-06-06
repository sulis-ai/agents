// <ThreadView /> — the open change's workspace (chat-B2 signed contract).
//
// The change owns the screen inside its tab: a change-scoped LEFT NAV
// (<ChangeNav>: name + vertical stage track + view switches) and a full-width
// MAIN area that renders the selected view. This REPLACES the old
// header + horizontal stage spine + right-hand rail — one navigation model.
//
//   ┌ ChangeNav ─┐ ┌ main ─────────────────────────────┐
//   │ name       │ │ Conversation = sticky status bar + │
//   │ stage      │ │   chat (Turn Cards) + composer     │
//   │ views      │ │ Files / Provenance / Preview swap  │
//   └────────────┘ └────────────────────────────────────┘
//
// One state-pattern set (ADR-005): loading skeleton, 404-gone, generic error.

import { useState } from "react";
import { useParams } from "react-router-dom";
import { useChange } from "../api/useChange";
import { useStatus } from "../api/useStatus";
import { ApiError } from "../api/client";
import { ChangeNav, type ChangeView } from "../components/ChangeNav";
import { stageLabel } from "../components/StageBadge";
import { Chat } from "../components/Chat";
import { Composer } from "../components/Composer";
import { FilesPanel } from "../components/FilesPanel";
import { ContractLinks } from "../components/ContractLinks";
import { ProvenanceSection } from "../components/ProvenanceSection";
import { AdvancedView } from "../components/AdvancedView";
import { REASON_WORD } from "../components/StatusHeader";
import ws from "../styles/ChangeWorkspace.module.css";

export function ThreadView() {
  const { changeId } = useParams<{ changeId: string }>();
  const id = changeId ?? "";
  const query = useChange(id);
  const statusQuery = useStatus(id);
  const [view, setView] = useState<ChangeView>("conversation");

  if (query.isLoading) {
    return (
      <section data-testid="page-thread" className={ws.main}>
        <p data-testid="thread-loading" style={{ padding: 32, textAlign: "center", color: "var(--muted-foreground)" }}>
          Loading...
        </p>
      </section>
    );
  }

  if (query.isError) {
    const isNotFound =
      query.error instanceof ApiError && query.error.status === 404;
    return (
      <section data-testid="page-thread" className={ws.main}>
        {isNotFound ? (
          <div
            data-testid="thread-gone-or-moved"
            style={{ margin: 32, padding: 24, background: "var(--bg-destructive)", border: "1px solid var(--bg-destructive-border)", borderRadius: "var(--radius-container)" }}
          >
            <p>This change is gone or moved.</p>
          </div>
        ) : (
          <p style={{ padding: 32, textAlign: "center" }}>
            Could not load this change.
          </p>
        )}
      </section>
    );
  }

  const change = query.data!;
  const status = statusQuery.isSuccess ? statusQuery.data : null;

  return (
    <div data-testid="page-thread" className={ws.change}>
      <ChangeNav change={change} activeView={view} onSelectView={setView} />

      <div className={ws.main}>
        {view === "conversation" && (
          <section
            className={ws.convocol}
            data-testid="section-conversation"
            aria-label="Conversation"
          >
            {/* slim sticky stage/status bar */}
            <div className={ws.stickybar} data-testid="thread-spine">
              <span className={ws.sd} aria-hidden="true" />
              <b>{stageLabel(change.stage)}</b>
              {status && (
                <>
                  <span className={ws.sep}>·</span>
                  <span className={ws.msg}>{status.headline}</span>
                </>
              )}
              {status?.needsAttention.flagged &&
              status.needsAttention.reason !== null ? (
                <span className={ws.needsAttn} data-testid="needs-attention">
                  {REASON_WORD[status.needsAttention.reason]}
                </span>
              ) : (
                <span className={ws.when}>live</span>
              )}
            </div>

            <div className={ws.scroll}>
              <div className={ws.measure}>
                <Chat changeId={id} />
              </div>
            </div>

            <Composer changeId={id} />
          </section>
        )}

        {view === "files" && (
          <div className={ws.viewfill} data-testid="section-files">
            <FilesPanel changeId={id} />
          </div>
        )}

        {view === "provenance" && (
          <div className={ws.viewfill} data-testid="section-provenance">
            <ProvenanceSection changeId={id} />
          </div>
        )}

        {view === "preview" && (
          <div className={ws.viewfill} data-testid="section-preview">
            <div className={ws.scroll}>
              <div className={ws.measure}>
                <ContractLinks change={change} />
              </div>
            </div>
          </div>
        )}

        {view === "advanced" && (
          <div className={ws.viewfill} data-testid="section-advanced">
            <div className={ws.scroll}>
              <div className={ws.measure}>
                <AdvancedView change={change} />
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
