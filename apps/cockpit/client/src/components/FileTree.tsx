// WP-014 — <FileTree /> — the worktree file/folder tree.
//
// Fetches the root level via useTree(changeId, "") and renders one
// <FileTreeNode> per entry (directories first). All recursion +
// per-directory lazy fetching lives in <FileTreeNode>, so this
// component stays one screen (WP-014 Blue criterion).
//
// Selecting a file sets the ?file= search param, making the selection
// shareable within the same machine and durable across refresh.
//
// References: WP-014 Contract (<FileTree>), TDD §6.

import { useSearchParams } from "react-router-dom";
import { useTree } from "../api/useTree";
import { FileTreeNode, sortNodes } from "./FileTreeNode";
import styles from "../styles/FilesPanel.module.css";

interface Props {
  changeId: string;
}

export function FileTree({ changeId }: Props) {
  const [params, setParams] = useSearchParams();
  const selectedPath = params.get("file") ?? "";
  const query = useTree(changeId, "");

  function selectFile(path: string) {
    const next = new URLSearchParams(params);
    next.set("file", path);
    setParams(next, { replace: false });
  }

  return (
    <nav className={styles.fileTree} data-testid="file-tree" aria-label="Files">
      {query.isLoading && <p className={styles.treeMessage}>Loading files…</p>}
      {query.isError && (
        <p className={styles.treeMessage}>Could not load the file tree.</p>
      )}
      {query.data &&
        sortNodes(query.data).map((node) => (
          <FileTreeNode
            key={node.path}
            changeId={changeId}
            node={node}
            selectedPath={selectedPath}
            onSelectFile={selectFile}
            depth={0}
          />
        ))}
    </nav>
  );
}
