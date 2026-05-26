// WP-014 — <FileToolbar />.
//
// The toolbar above the file viewer: the filename (truncated, full path
// in a tooltip), the copy-path button, and a diff-toggle button that is
// DISABLED in this WP. WP-015 enables the diff toggle — leaving the
// control present (but disabled) keeps the toolbar layout stable so
// WP-015 is a one-line wiring change rather than a layout shift.
//
// References: WP-014 Contract (<FileToolbar>, diff toggle stub), ADR-006
// (diff surface is WP-015).

import styles from "../styles/FilesPanel.module.css";
import { CopyPathButton } from "./CopyPathButton";

interface Props {
  /** Worktree-relative path (shown as the filename label). */
  relativePath: string;
  /** Absolute filesystem path (for copy-path). */
  absolutePath: string;
}

export function FileToolbar({ relativePath, absolutePath }: Props) {
  return (
    <div className={styles.toolbar} data-testid="file-toolbar">
      <span className={styles.filename} title={relativePath}>
        {relativePath}
      </span>
      <div className={styles.toolbarActions}>
        <CopyPathButton absolutePath={absolutePath} />
        <button
          type="button"
          className={styles.diffToggle}
          disabled
          title="Diff toggle lands in WP-015"
          data-testid="diff-toggle-stub"
        >
          Show diff
        </button>
      </div>
    </div>
  );
}
