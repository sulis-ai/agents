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
import { MonacoFile } from "./MonacoFile";
import { MonacoDiff } from "./MonacoDiff";
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

  if (query.isLoading) {
    // No toolbar until data arrives: the absolute path (for copy-path)
    // only comes back with the payload, and the diff toggle is reachable
    // again the instant the load resolves. Matches WP-014's loading state.
    return message(diffMode ? "Loading diff..." : "Loading file...");
  }

  if (query.isError) {
    if (
      diffMode &&
      query.error instanceof ApiError &&
      query.error.code === "NO_BASE_SHA"
    ) {
      return pane(<NoBaseShaState />);
    }
    const reason =
      query.error instanceof ApiError ? query.error.message : "unknown error";
    return message(
      `Could not load ${diffMode ? "diff" : "file"}: ${reason}`,
    );
  }

  if (diffMode) {
    const diff = diffQuery.data!;
    return pane(
      <>
        <FileToolbar relativePath={diff.path} absolutePath={diff.absolutePath} />
        {diff.binary || diff.truncated ? (
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
        )}
      </>,
    );
  }

  const file = fileQuery.data!;
  return pane(
    <>
      <FileToolbar relativePath={file.path} absolutePath={file.absolutePath} />
      {file.binary ? (
        <FileBinaryState absolutePath={file.absolutePath} />
      ) : file.truncated ? (
        <FileTruncatedState absolutePath={file.absolutePath} />
      ) : (
        <Suspense
          fallback={<p className={styles.fileMessage}>Loading viewer...</p>}
        >
          <MonacoFile content={file.content ?? ""} language={file.language} />
        </Suspense>
      )}
    </>,
  );
}
