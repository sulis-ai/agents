// Files redesign (Direction B) — <FileTree /> — the worktree tree
// (All-files scope).
//
// Fetches the root level via useTree(changeId, "") and renders one
// <FileTreeNode> per entry (directories first, name filter applied).
// Selection lives in the URL — a file sets ?file= (and clears ?dir=); a
// folder sets ?dir= (and clears ?file=). The content column reads the
// same params, so the two columns stay in sync through the URL with no
// shared state (the original WP-014 contract, extended for folder
// selection).
//
// `filter` + `changed` are optional so the tree still renders standalone
// (its unit test mounts <FileTree changeId=… />); FilesPanel passes them
// from the scope switch + search box + changed-files set.
//
// References: WP-014 Contract (<FileTree>), the signed files-B contract.

import { useSearchParams } from "react-router-dom";
import { useTree } from "../api/useTree";
import {
  FileTreeNode,
  sortNodes,
  filterNodes,
  type ChangedMap,
} from "./FileTreeNode";
import styles from "../styles/FilesPanel.module.css";

interface Props {
  changeId: string;
  /** Lower-cased name filter from the search box; default "". */
  filter?: string;
  /** path → changed status for the per-file status dot; default empty. */
  changed?: ChangedMap;
}

export function FileTree({ changeId, filter = "", changed }: Props) {
  const [params, setParams] = useSearchParams();
  const selectedPath = params.get("file") ?? "";
  const selectedDir = params.get("dir") ?? "";
  const changedMap: ChangedMap = changed ?? new Map();
  const query = useTree(changeId, "");

  function selectFile(path: string) {
    const next = new URLSearchParams(params);
    next.set("file", path);
    next.delete("dir");
    setParams(next, { replace: false });
  }

  function selectDir(path: string) {
    const next = new URLSearchParams(params);
    next.set("dir", path);
    next.delete("file");
    setParams(next, { replace: false });
  }

  return (
    <nav className={styles.treebody} data-testid="file-tree" aria-label="Files">
      {query.isLoading && <p className={styles.treeMessage}>Loading files…</p>}
      {query.isError && (
        <p className={styles.treeMessage}>Couldn’t load the file tree.</p>
      )}
      {query.data &&
        filterNodes(sortNodes(query.data), filter).map((node) => (
          <FileTreeNode
            key={node.path}
            changeId={changeId}
            node={node}
            selectedPath={selectedPath}
            selectedDir={selectedDir}
            onSelectFile={selectFile}
            onSelectDir={selectDir}
            changed={changedMap}
            filter={filter}
            depth={0}
          />
        ))}
    </nav>
  );
}
