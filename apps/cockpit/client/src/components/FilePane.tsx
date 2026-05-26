// WP-014 — <FilePane /> — the right-hand file viewer.
//
// Reads the selected file path from the ?file= search param (set by
// <FileTree>), fetches it via useFile(changeId, path), and renders one
// of:
//   - no selection      → a friendly "pick a file" prompt
//   - loading           → "Loading file..."
//   - error             → "Could not load file: <message>"
//   - binary            → <FileBinaryState> (no Monaco mount)
//   - truncated         → <FileTruncatedState> (no Monaco mount)
//   - text file         → <FileToolbar> + <MonacoFile content language />
//
// The toolbar (with its copy-path button + disabled diff stub) sits
// above the viewer for the text-file and the binary/truncated cases so
// the founder can always copy the path.
//
// References: WP-014 Contract (<FilePane>), ADR-001 (Monaco read-only),
// TDD §6.

import { Suspense } from "react";
import { useSearchParams } from "react-router-dom";
import { useFile } from "../api/useFile";
import { ApiError } from "../api/client";
import { FileToolbar } from "./FileToolbar";
import { FileBinaryState } from "./FileBinaryState";
import { FileTruncatedState } from "./FileTruncatedState";
import { MonacoFile } from "./MonacoFile";
import styles from "../styles/FilesPanel.module.css";

interface Props {
  changeId: string;
}

export function FilePane({ changeId }: Props) {
  const [params] = useSearchParams();
  const selected = params.get("file") ?? "";

  const query = useFile(changeId, selected);

  if (!selected) {
    return (
      <div className={styles.filePane} data-testid="file-pane">
        <p className={styles.fileMessage}>
          Pick a file from the tree to view it.
        </p>
      </div>
    );
  }

  if (query.isLoading) {
    return (
      <div className={styles.filePane} data-testid="file-pane">
        <p className={styles.fileMessage}>Loading file...</p>
      </div>
    );
  }

  if (query.isError) {
    const message =
      query.error instanceof ApiError ? query.error.message : "unknown error";
    return (
      <div className={styles.filePane} data-testid="file-pane">
        <p className={styles.fileMessage}>Could not load file: {message}</p>
      </div>
    );
  }

  const file = query.data!;

  return (
    <div className={styles.filePane} data-testid="file-pane">
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
    </div>
  );
}
