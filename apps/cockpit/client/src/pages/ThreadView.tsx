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

import { useCallback, useEffect, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useChange } from "../api/useChange";
import { useStatus } from "../api/useStatus";
import {
  ApiError,
  fetchChangeProvider as defaultFetchChangeProvider,
  putChangeProvider as defaultPutChangeProvider,
  type FetchChangeProviderFn,
  type PutChangeProviderFn,
} from "../api/client";
import { changedQuery, provenanceQuery, treeQuery } from "../api/fileQueries";
import {
  advancedQuery,
  contractPreviewQuery,
  transcriptQuery,
  turnSummariesQuery,
} from "../api/viewQueries";
import { ChangeNav, type ChangeView, CHANGE_VIEWS } from "../components/ChangeNav";
import { stageLabel } from "../components/StageBadge";
import { Chat } from "../components/Chat";
import { Composer } from "../components/Composer";
import { FilesPanel } from "../components/FilesPanel";
import { LiveTerminal } from "../components/LiveTerminal";
import { AgentPicker } from "../components/AgentPicker";
import { ContractLinks } from "../components/ContractLinks";
import { ProvenanceSection } from "../components/ProvenanceSection";
import { AdvancedView } from "../components/AdvancedView";
import { REASON_WORD } from "../components/StatusHeader";
import type { ChatProvider } from "../../../shared/api-types";
import ws from "../styles/ChangeWorkspace.module.css";

export interface ThreadViewProps {
  /** Read the change's remembered provider (CH-R5EE44 Fix 3). Injectable for
   *  tests; defaults to the real per-change provider funnel. */
  fetchChangeProvider?: FetchChangeProviderFn;
  /** Persist the per-change picker's choice (CH-R5EE44 Fix 3). Injectable for
   *  tests; defaults to the real per-change provider funnel. */
  putChangeProvider?: PutChangeProviderFn;
}

export function ThreadView({
  fetchChangeProvider = defaultFetchChangeProvider,
  putChangeProvider = defaultPutChangeProvider,
}: ThreadViewProps = {}) {
  const { changeId } = useParams<{ changeId: string }>();
  const id = changeId ?? "";
  const query = useChange(id);
  const statusQuery = useStatus(id);
  // The initial view is seeded from the optional `?view=` query param (WP-009:
  // "open this change's terminal" navigates to /c/:id?view=terminal so the page
  // lands ON the terminal). It is validated against the known views and falls
  // back to "conversation" for any absent/unknown value. After mount the view
  // is plain local state — the nav drives it, the URL is the entry seed only.
  const [searchParams] = useSearchParams();
  const initialView: ChangeView = (() => {
    const requested = searchParams.get("view");
    return requested && (CHANGE_VIEWS as readonly string[]).includes(requested)
      ? (requested as ChangeView)
      : "conversation";
  })();
  const [view, setView] = useState<ChangeView>(initialView);
  const queryClient = useQueryClient();

  // CH-R5EE44 Fix 3 — the change's remembered (running) provider for the per-
  // change AgentPicker. Keyed by change id so each change keeps its own choice.
  const providerQuery = useQuery({
    queryKey: ["change-provider", id],
    queryFn: () => fetchChangeProvider(id),
    enabled: id.length > 0,
  });
  // Optimistic overlay: reflect the chosen provider immediately, clearing it
  // whenever the authoritative running provider (re)loads — so the picker never
  // shadows the server's value across a refetch (AI-07 honest identity).
  const [pendingProvider, setPendingProvider] = useState<ChatProvider | null>(
    null,
  );
  useEffect(() => {
    setPendingProvider(null);
  }, [id, providerQuery.dataUpdatedAt]);
  const runningProvider: ChatProvider =
    pendingProvider ?? providerQuery.data ?? "pty";

  const onSwitchProvider = useCallback(
    (next: ChatProvider) => {
      // AI-03: applies to the change's NEXT session-open (never a hot-swap). The
      // optimistic overlay reflects the choice; a server rejection rolls back.
      setPendingProvider(next);
      void putChangeProvider(id, next)
        .then(() => {
          void queryClient.invalidateQueries({
            queryKey: ["change-provider", id],
          });
        })
        .catch(() => setPendingProvider(null));
    },
    [id, putChangeProvider, queryClient],
  );

  // Warm a view's primary read(s) on nav hover/focus so the click lands on a
  // cache hit and the switch is instant. Each view maps to the SAME query
  // definitions its hook consumes (fileQueries / viewQueries — DRY/EP-03), so
  // there's one fetch definition per read. Skip the already-active view.
  //
  // The static file reads (tree/changed/provenance) carry their own staleTime
  // (FILE_QUERY_CACHE), so repeated hovers are free. The live reads (transcript
  // / turn-summaries / contract / advanced) default to staleTime 0, which would
  // refire on every hover — so the prefetch passes a short HOVER_STALE_TIME to
  // gate repeats without touching the hooks' own polling cadence.
  const prefetchView = useCallback(
    (target: ChangeView) => {
      if (target === view || id.length === 0) return;
      const HOVER_STALE_TIME = 10_000;
      switch (target) {
        case "conversation":
          void queryClient.prefetchQuery({
            ...transcriptQuery(id),
            staleTime: HOVER_STALE_TIME,
          });
          void queryClient.prefetchQuery({
            ...turnSummariesQuery(id),
            staleTime: HOVER_STALE_TIME,
          });
          break;
        case "files":
          void queryClient.prefetchQuery(treeQuery(id, ""));
          void queryClient.prefetchQuery(changedQuery(id));
          break;
        case "provenance":
          void queryClient.prefetchQuery(provenanceQuery(id));
          break;
        case "preview":
          void queryClient.prefetchQuery({
            ...contractPreviewQuery(id),
            staleTime: HOVER_STALE_TIME,
          });
          break;
        case "advanced":
          void queryClient.prefetchQuery({
            ...advancedQuery(id),
            staleTime: HOVER_STALE_TIME,
          });
          break;
        case "terminal":
          // The terminal has no react-query read to warm — <LiveTerminal/>
          // opens its pty session over the socket bridge on mount. Nothing to
          // prefetch; the case exists for switch exhaustiveness.
          break;
      }
    },
    [queryClient, id, view],
  );

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
      <ChangeNav
        change={change}
        activeView={view}
        onSelectView={setView}
        onPrefetchView={prefetchView}
      />

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
            <FilesPanel changeId={id} onSelectView={setView} />
          </div>
        )}

        {view === "provenance" && (
          <div className={ws.viewfill} data-testid="section-provenance">
            <ProvenanceSection changeId={id} onSelectView={setView} />
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

        {/* The change's live terminal (WP-008): the in-cockpit xterm.js view
            backed by the session manager's pty-mode session. Mirrors the files
            view's viewfill mount; <LiveTerminal/> owns its own chrome,
            scrollback, and connecting/disconnected/no-terminal states. */}
        {view === "terminal" && (
          <div className={ws.viewfill} data-testid="section-terminal">
            {/* CH-R5EE44 Fix 3 — the per-change agent picker (the SAME
                <AgentPicker> the product-wide chat uses). It names the change's
                remembered RUNNING provider; switching applies to the change's
                NEXT session-open (AI-03 "new work"), never a hot-swap of the live
                PTY — the AI-03 confirm fires while the change session is live. */}
            <div className={ws.terminalAgentBar} data-testid="change-agent-bar">
              <AgentPicker
                running={runningProvider}
                selected={runningProvider}
                sessionRunning={change.liveness.status === "running"}
                onSwitch={onSwitchProvider}
              />
            </div>
            <LiveTerminal changeId={id} />
          </div>
        )}
      </div>
    </div>
  );
}
