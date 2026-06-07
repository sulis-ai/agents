// Files redesign (Direction B) — <FolderOverview /> — the folder level.
//
// The signature of the repo-browser direction: with a folder (or
// nothing) selected, the content column shows that folder's contents as
// a clean list (type icon · name · worded status badge for changed
// files), and if the folder has a README it renders BELOW the list,
// rendered the way it's meant to look (reusing <RenderedPreview>, so
// markdown defaults to rendered with a flip-to-raw switch).
//
// Clicking a folder row drills in (?dir=); a file row opens it (?file=).

import { useTree } from "../api/useTree";
import { useFile } from "../api/useFile";
import { sortNodes, type ChangedMap } from "./FileTreeNode";
import { NodeIcon } from "./fileIcons";
import { RenderedPreview } from "./RenderedPreview";
import styles from "../styles/FilesPanel.module.css";

interface Props {
  changeId: string;
  /** The folder to show; "" = the worktree root. */
  dirPath: string;
  changed: ChangedMap;
  onSelectFile: (path: string) => void;
  onSelectDir: (path: string) => void;
}

const STATUS_LETTER: Record<string, string> = {
  new: "N",
  edited: "E",
  removed: "R",
};

function StatusBadge({ status }: { status: "new" | "edited" | "removed" }) {
  return (
    <span className={`${styles.cstat} ${styles[status]}`}>
      <span className={styles.mk} aria-hidden="true">
        {STATUS_LETTER[status]}
      </span>
      <span className={styles.cw}>{status}</span>
    </span>
  );
}

export function FolderOverview({
  changeId,
  dirPath,
  changed,
  onSelectFile,
  onSelectDir,
}: Props) {
  const query = useTree(changeId, dirPath);
  const nodes = query.data ? sortNodes(query.data) : [];

  // A README in this folder renders below the list (rendered by default).
  const readme = nodes.find((n) => n.kind === "file" && /^readme(\.|$)/i.test(n.name));
  const readmeQuery = useFile(changeId, readme ? readme.path : "");

  if (query.isLoading) {
    return (
      <div className={styles.skwrap} role="status" aria-label="Loading folder">
        <div className={`${styles.sk} ${styles.skLine}`} style={{ width: "40%" }} />
        <div className={`${styles.sk} ${styles.skLine}`} />
        <div className={`${styles.sk} ${styles.skLine}`} />
        <div className={`${styles.sk} ${styles.skLine}`} style={{ width: "70%" }} />
      </div>
    );
  }
  if (query.isError) {
    return <p className={styles.fileMessage}>Couldn’t load this folder.</p>;
  }

  return (
    <div className={styles.ovwrap}>
      <div className={styles.ovsec}>
        {dirPath === "" ? "In this change" : dirPath}
      </div>
      <div className={styles.olist}>
        {nodes.length === 0 && (
          <div className={styles.orow}>
            <span className={styles.on}>This folder is empty.</span>
          </div>
        )}
        {nodes.map((n) => {
          const status = n.kind === "file" ? changed.get(n.path) : undefined;
          return (
            <button
              key={n.path}
              type="button"
              className={`${styles.orow} ${n.kind === "directory" ? styles.folder : ""}`}
              onClick={() =>
                n.kind === "directory"
                  ? onSelectDir(n.path)
                  : onSelectFile(n.path)
              }
              data-testid={`overview-row-${n.path}`}
            >
              <NodeIcon
                kind={n.kind}
                path={n.path}
                className={styles.oi}
              />
              <span className={styles.on}>{n.name}</span>
              {status && <StatusBadge status={status} />}
            </button>
          );
        })}
      </div>

      {readme && readmeQuery.data && !readmeQuery.data.binary && (
        <div className={styles.readmeWrap}>
          <RenderedPreview
            path={readme.path}
            content={readmeQuery.data.content ?? ""}
            language={readmeQuery.data.language}
          />
        </div>
      )}
    </div>
  );
}
