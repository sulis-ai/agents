// WP-014 → WP-015 — <FilePane /> — the right-hand file viewer.
//
// Reads the selected file path from the ?file= search param (set by
// <FileTree>) and the diff toggle from the ?diff=1 param (set by
// <FileToolbar>). One toolbar always renders above the body so the
// founder can copy the path and flip the diff toggle in every state.
//
// The body has two modes, selected by ?diff:
//   - file mode (?diff absent)  → useFile  → <MonacoFile> (WP-014)
//   - diff mode (?diff=1)       → useDiff  → <MonacoDiff>  (WP-015)
// Both modes share one rendering path: loading / error / a
// "not previewable" state / Monaco. Only the active query fetches —
// the inactive hook is called with an empty path, which disables it
// (so diff mode never hits /file, and vice-versa).
//
// Mode-specific states:
//   - file: binary → <FileBinaryState>; truncated → <FileTruncatedState>
//   - diff: binary/truncated → <DiffUnavailableState>;
//           422 NO_BASE_SHA  → <NoBaseShaState>
//
// References: WP-014 Contract (<FilePane>), WP-015 Contract (<FilePane>
// diff behaviour), ADR-001 + ADR-006 (Monaco read-only), TDD §6, §7.

import { Suspense, type ReactNode } from "react";
import { useSearchParams } from "react-router-dom";
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
import styles from "../styles/FilesPanel.module.css";

interface Props {
  changeId: string;
}

function pane(children: ReactNode) {
  return (
    <div className={styles.filePane} data-testid="file-pane">
      {children}
    </div>
  );
}

function message(text: string) {
  return pane(<p className={styles.fileMessage}>{text}</p>);
}

export function FilePane({ changeId }: Props) {
  const [params] = useSearchParams();
  const selected = params.get("file") ?? "";
  const diffMode = params.get("diff") === "1";

  // Only the active query fetches: the inactive hook gets an empty
  // path, which disables it (useFile/useDiff are `enabled` on a
  // non-empty path). This is what keeps diff mode off the /file route.
  const fileQuery = useFile(changeId, diffMode ? "" : selected);
  const diffQuery = useDiff(changeId, diffMode ? selected : "");
  const query = diffMode ? diffQuery : fileQuery;

  if (!selected) {
    return message("Pick a file from the tree to view it.");
  }

  // The toolbar — and crucially the diff toggle — renders ABOVE the body
  // in EVERY state (loading / error / no-base-sha / success). This is the
  // documented contract: the founder must always be able to flip the diff
  // toggle back, even when diff mode errors (e.g. NO_BASE_SHA). Earlier the
  // error branches returned without the toolbar, stranding the user in diff
  // mode with no way back. The filename comes from the selected path
  // (always known); the absolute path (for copy) only fills once data
  // arrives — CopyPathButton disables itself until then.
  const absolutePath =
    query.data && "absolutePath" in query.data ? query.data.absolutePath : "";

  function body(): ReactNode {
    if (query.isLoading) {
      return (
        <p className={styles.fileMessage}>
          {diffMode ? "Loading diff..." : "Loading file..."}
        </p>
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
        <p className={styles.fileMessage}>
          Could not load {diffMode ? "diff" : "file"}: {reason}
        </p>
      );
    }

    if (diffMode) {
      const diff = diffQuery.data!;
      return diff.binary || diff.truncated ? (
        <DiffUnavailableState absolutePath={diff.absolutePath} />
      ) : (
        <Suspense
          fallback={<p className={styles.fileMessage}>Loading viewer...</p>}
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
      // WP-006 — renderable docs (.md/.html) show RENDERED with a
      // rendered/raw toggle; code stays read-only source (RenderedPreview
      // delegates to <MonacoFile>, the existing viewer — EP-03). The Suspense
      // boundary for the lazy Monaco bundle lives inside RenderedPreview.
      <RenderedPreview
        path={selected}
        content={file.content ?? ""}
        language={file.language}
      />
    );
  }

  return pane(
    <>
      <FileToolbar relativePath={selected} absolutePath={absolutePath} />
      {body()}
    </>,
  );
}
