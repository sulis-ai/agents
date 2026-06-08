// Files redesign (Direction B) — <FileToolbar /> — the breadcrumb +
// actions bar for a single open file.
//
// Renders the file's path as a breadcrumb (folder segments + the
// filename, the way a code host shows where you are), then the actions:
// Copy path and the current↔diff toggle. The diff toggle is one button
// whose label + pressed state derive from the ?diff=1 search param, so
// the URL fully describes the view (TDD §6.1) and the back button works.
//
// References: WP-014/WP-015 Contract (<FileToolbar>), the signed
// files-B visual contract (the .cbar breadcrumb bar).

import { useSearchParams } from "react-router-dom";
import { ChevronRightIcon, ArrowsRightLeftIcon } from "@heroicons/react/20/solid";
import styles from "../styles/FilesPanel.module.css";
import { CopyPathButton } from "./CopyPathButton";
import { DIFF_TOGGLE_LABELS } from "./diffToolbarCopy";

interface Props {
  /** Worktree-relative path (rendered as the breadcrumb). */
  relativePath: string;
  /** Absolute filesystem path (for copy-path). */
  absolutePath: string;
}

export function FileToolbar({ relativePath, absolutePath }: Props) {
  const [params, setParams] = useSearchParams();
  const diffOn = params.get("diff") === "1";
  const segments = relativePath.split("/").filter((s) => s.length > 0);

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
    <div className={styles.cbar} data-testid="file-toolbar">
      <nav className={styles.crumb} aria-label="File path">
        {segments.map((seg, i) => {
          const isLast = i === segments.length - 1;
          return (
            <span key={i} style={{ display: "inline-flex", alignItems: "center", gap: 6, minWidth: 0 }}>
              {i > 0 && (
                <span className={styles.sep} aria-hidden="true">
                  <ChevronRightIcon />
                </span>
              )}
              <span className={`${styles.seg} ${isLast ? styles.cur : ""}`}>
                {seg}
              </span>
            </span>
          );
        })}
      </nav>
      <span className={styles.spacer} />
      <div className={styles.cbarActions}>
        <CopyPathButton absolutePath={absolutePath} />
        <button
          type="button"
          className={styles.act}
          aria-pressed={diffOn}
          onClick={toggleDiff}
          data-testid="diff-toggle"
        >
          <ArrowsRightLeftIcon aria-hidden="true" />
          {diffOn ? DIFF_TOGGLE_LABELS.showCurrent : DIFF_TOGGLE_LABELS.showDiff}
        </button>
      </div>
    </div>
  );
}
