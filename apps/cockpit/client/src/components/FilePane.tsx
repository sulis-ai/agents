// Files redesign (Direction B) — <FilePane /> — the single-file level of
// the content column.
//
// Reads the selected file path from ?file= and the diff toggle from
// ?diff=1. The breadcrumb-and-actions bar (<FileToolbar>) renders ABOVE
// the body in EVERY state so the founder can always copy the path and
// flip the diff toggle — even when diff mode errors (NO_BASE_SHA).
//
// Body modes (by ?diff):
//   - file mode → useFile → binary/truncated states, or <RenderedPreview>
//     (docs render by default, code stays read-only source).
//   - diff mode → useDiff → binary/truncated → <DiffUnavailableState>;
//     422 NO_BASE_SHA → <NoBaseShaState>; else <MonacoDiff>.
//
// A genuine read failure → the calm, worded couldn't-load state (heading
// + a "couldn't read the file" chip + the reason + Try again + Copy
// path) — the signed honest-failure treatment, never a blank pane or a
// destructive-red banner.
//
// References: WP-014/WP-015 Contract, ADR-001/006, the signed files-B
// visual contract (state 7 — couldn't-load).

import { Suspense, type ReactNode } from "react";
import { useSearchParams } from "react-router-dom";
import {
  ExclamationTriangleIcon,
  ArrowPathIcon,
  ClipboardIcon,
} from "@heroicons/react/20/solid";
import { DocumentMagnifyingGlassIcon } from "@heroicons/react/24/outline";
import { useFile } from "../api/useFile";
import { useDiff } from "../api/useDiff";
import { ApiError } from "../api/client";
import { FileToolbar } from "./FileToolbar";
import { FileBinaryState } from "./FileBinaryState";
import { FileTruncatedState } from "./FileTruncatedState";
import { DiffUnavailableState } from "./DiffUnavailableState";
import { NoBaseShaState } from "./NoBaseShaState";
import { MonacoDiff } from "./MonacoDiff";
import { RenderedPreview } from "./RenderedPreview";
import { HowThisFileCameToBe } from "./HowThisFileCameToBe";
import type { ChangeView } from "./ChangeNav";
import styles from "../styles/FilesPanel.module.css";

interface Props {
  changeId: string;
  /** Switch the change view (for the file-provenance panel's trace jumps). */
  onSelectView?: (view: ChangeView) => void;
}

function content(children: ReactNode) {
  return (
    <div className={styles.content} data-testid="file-pane">
      {children}
    </div>
  );
}

/** The calm, worded couldn't-load state (signed contract, state 7). */
function CouldNotLoad({
  reason,
  absolutePath,
  onRetry,
}: {
  reason: string;
  absolutePath: string;
  onRetry: () => void;
}) {
  async function copyPath() {
    const clip = navigator.clipboard;
    if (clip && typeof clip.writeText === "function" && absolutePath) {
      try {
        await clip.writeText(absolutePath);
      } catch {
        /* copy is a convenience; never surface an error for it */
      }
    }
  }
  return (
    <div className={styles.state} role="alert" data-testid="file-load-error">
      <DocumentMagnifyingGlassIcon className={styles.ic} aria-hidden="true" />
      <h3>Couldn’t load this file</h3>
      <span className={styles.why}>
        <ExclamationTriangleIcon aria-hidden="true" />
        Couldn’t read the file
      </span>
      {/* Keep the literal phrase the contract's body uses. */}
      <p>Could not load file — {reason}</p>
      <div className={styles.actions}>
        <button type="button" className={styles.retry} onClick={onRetry}>
          <ArrowPathIcon aria-hidden="true" />
          Try again
        </button>
        {absolutePath && (
          <button type="button" className={styles.copybtn} onClick={copyPath}>
            <ClipboardIcon aria-hidden="true" />
            Copy path
          </button>
        )}
      </div>
    </div>
  );
}

export function FilePane({ changeId, onSelectView }: Props) {
  const [params] = useSearchParams();
  const selected = params.get("file") ?? "";
  const diffMode = params.get("diff") === "1";

  // Only the active query fetches: the inactive hook gets an empty path,
  // which disables it (so diff mode never hits /file, and vice-versa).
  const fileQuery = useFile(changeId, diffMode ? "" : selected);
  const diffQuery = useDiff(changeId, diffMode ? selected : "");
  const query = diffMode ? diffQuery : fileQuery;

  if (!selected) {
    return content(
      <div className={styles.cbody}>
        <p className={styles.fileMessage}>Pick a file from the tree to view it.</p>
      </div>,
    );
  }

  const absolutePath =
    query.data && "absolutePath" in query.data ? query.data.absolutePath : "";

  function body(): ReactNode {
    if (query.isLoading) {
      return (
        <div className={styles.loadnote} role="status" aria-live="polite">
          <span className={styles.spin} aria-hidden="true" />
          {diffMode ? "Loading diff…" : "Loading file…"}
        </div>
      );
    }

    if (query.isError) {
      if (
        diffMode &&
        query.error instanceof ApiError &&
        query.error.code === "NO_BASE_SHA"
      ) {
        return <NoBaseShaState />;
      }
      const reason =
        query.error instanceof ApiError ? query.error.message : "unknown error";
      return (
        <CouldNotLoad
          reason={reason}
          absolutePath={absolutePath}
          onRetry={() => void query.refetch()}
        />
      );
    }

    if (diffMode) {
      const diff = diffQuery.data!;
      return diff.binary || diff.truncated ? (
        <DiffUnavailableState absolutePath={diff.absolutePath} />
      ) : (
        <Suspense
          fallback={<p className={styles.fileMessage}>Loading viewer…</p>}
        >
          <MonacoDiff
            base={diff.base}
            current={diff.current}
            language={diff.language}
          />
        </Suspense>
      );
    }

    const file = fileQuery.data!;
    return file.binary ? (
      <FileBinaryState absolutePath={file.absolutePath} />
    ) : file.truncated ? (
      <FileTruncatedState absolutePath={file.absolutePath} />
    ) : (
      <RenderedPreview
        path={selected}
        content={file.content ?? ""}
        language={file.language}
      />
    );
  }

  return content(
    <>
      <FileToolbar relativePath={selected} absolutePath={absolutePath} />
      <div className={styles.cbody}>
        <div className={styles.fileFill}>{body()}</div>
      </div>
      {/* WP-P10/P11 — "How this file came to be": the per-file origin badge +
          trace, beneath the content (progressive disclosure). */}
      <HowThisFileCameToBe
        changeId={changeId}
        path={selected}
        onSelectView={onSelectView}
      />
    </>,
  );
}
