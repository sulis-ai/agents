// WP-014 → WP-015 — <FileToolbar />.
//
// The toolbar above the file viewer: the filename (truncated, full path
// in a tooltip), the copy-path button, and the diff toggle.
//
// WP-014 shipped the diff toggle as a disabled stub. WP-015 makes it
// live: the toggle flips the `?diff=1` search param on/off, and its
// label + pressed state derive from that param — so the URL fully
// describes the view (TDD §6.1) and the back button works. The label
// strings live in a single constant (diffToolbarCopy) per the WP-015
// Blue requirement.
//
// References: WP-014 Contract (<FileToolbar>), WP-015 Contract
// (<FileToolbar> change), ADR-006.

import { useSearchParams } from "react-router-dom";
import styles from "../styles/FilesPanel.module.css";
import { CopyPathButton } from "./CopyPathButton";
import { DIFF_TOGGLE_LABELS } from "./diffToolbarCopy";

interface Props {
  /** Worktree-relative path (shown as the filename label). */
  relativePath: string;
  /** Absolute filesystem path (for copy-path). */
  absolutePath: string;
}

export function FileToolbar({ relativePath, absolutePath }: Props) {
  const [params, setParams] = useSearchParams();
  const diffOn = params.get("diff") === "1";

  function toggleDiff() {
    const next = new URLSearchParams(params);
    if (diffOn) {
      next.delete("diff");
    } else {
      next.set("diff", "1");
    }
    setParams(next, { replace: false });
  }

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
          aria-pressed={diffOn}
          onClick={toggleDiff}
          data-testid="diff-toggle"
        >
          {diffOn ? DIFF_TOGGLE_LABELS.showCurrent : DIFF_TOGGLE_LABELS.showDiff}
        </button>
      </div>
    </div>
  );
}
