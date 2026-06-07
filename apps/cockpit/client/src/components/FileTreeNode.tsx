// Files redesign (Direction B) — <FileTreeNode /> — one node in the
// worktree tree (recursive).
//
// A file row → selects the file (?file=). A directory row → toggles its
// expansion AND selects it as the overview target (?dir=), the
// repo-browser interaction: click a folder, see what's inside on the
// right; expand it to drill in the tree. Directories fetch their
// children lazily (useTree enabled only once expanded).
//
// Heroicons for the chevron + the file/folder glyph; a changed file
// carries a small status dot (the worded badge lives in the overview
// list + the breadcrumb). A name filter hides non-matching FILES at
// each loaded level; folders stay visible so drilling still works.
//
// References: WP-014 Contract (<FileTreeNode>), the signed files-B
// visual contract.

import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { ChevronRightIcon, ChevronDownIcon } from "@heroicons/react/20/solid";
import type { TreeNode, ChangedFile } from "../../../shared/api-types";
import { useTree } from "../api/useTree";
import { fileOriginQuery, fileQuery, treeQuery } from "../api/fileQueries";
import { NodeIcon } from "./fileIcons";
import styles from "../styles/FilesPanel.module.css";

export type ChangedMap = Map<string, ChangedFile["status"]>;

interface Props {
  changeId: string;
  node: TreeNode;
  /** Currently selected file path (?file=), for highlighting. */
  selectedPath: string;
  /** Currently selected directory path (?dir=), for highlighting. */
  selectedDir: string;
  onSelectFile: (path: string) => void;
  onSelectDir: (path: string) => void;
  /** path → changed status, for the per-file status dot. */
  changed: ChangedMap;
  /** Lower-cased name filter; "" = no filter. */
  filter: string;
  depth: number;
}

export function FileTreeNode({
  changeId,
  node,
  selectedPath,
  selectedDir,
  onSelectFile,
  onSelectDir,
  changed,
  filter,
  depth,
}: Props) {
  const [expanded, setExpanded] = useState(false);
  const isDirectory = node.kind === "directory";
  const queryClient = useQueryClient();

  const childrenActive = expanded && isDirectory;
  const childrenQuery = useTree(changeId, isDirectory ? node.path : "", {
    enabled: childrenActive,
  });

  const indent = { paddingLeft: `${depth * 12 + 8}px` };

  if (!isDirectory) {
    const isSelected = selectedPath === node.path;
    const status = changed.get(node.path);
    // Warm the file's contents + its "how this file came to be" panel on
    // hover/focus, so the click lands on a cache hit. Skip the already-open
    // file; prefetch is idempotent + staleTime-gated, so repeats are free.
    const prefetchFile = () => {
      if (isSelected) return;
      void queryClient.prefetchQuery(fileQuery(changeId, node.path));
      void queryClient.prefetchQuery(fileOriginQuery(changeId, node.path));
    };
    return (
      <button
        type="button"
        className={`${styles.tnode} ${isSelected ? styles.sel : ""}`}
        style={indent}
        onClick={() => onSelectFile(node.path)}
        onMouseEnter={prefetchFile}
        onFocus={prefetchFile}
        data-testid={`file-tree-node-${node.path}`}
        data-active={isSelected ? "true" : "false"}
      >
        <span className={styles.tw} aria-hidden="true" />
        <NodeIcon kind="file" path={node.path} className={styles.ti} />
        <span className={styles.tn}>{node.name}</span>
        {status && (
          <span
            className={`${styles.dot} ${styles[status]}`}
            title={status}
            aria-label={status}
          />
        )}
      </button>
    );
  }

  const isDirSelected = selectedDir === node.path && selectedPath === "";

  // Warm this folder's children on hover/focus so expanding it lands on a
  // cache hit. Skip an already-expanded folder (its children are loaded);
  // prefetch is idempotent + staleTime-gated, so repeats are free.
  const prefetchChildren = () => {
    if (expanded) return;
    void queryClient.prefetchQuery(treeQuery(changeId, node.path));
  };

  return (
    <div data-testid={`file-tree-node-${node.path}`}>
      <button
        type="button"
        className={`${styles.tnode} ${styles.folder} ${isDirSelected ? styles.sel : ""}`}
        style={indent}
        onClick={() => {
          onSelectDir(node.path);
          setExpanded((v) => !v);
        }}
        onMouseEnter={prefetchChildren}
        onFocus={prefetchChildren}
        aria-expanded={expanded}
        data-active={isDirSelected ? "true" : "false"}
      >
        <span className={styles.tw} aria-hidden="true">
          {expanded ? <ChevronDownIcon /> : <ChevronRightIcon />}
        </span>
        <NodeIcon
          kind="directory"
          path={node.path}
          expanded={expanded}
          className={styles.ti}
        />
        <span className={styles.tn}>{node.name}</span>
      </button>

      {childrenActive && childrenQuery.isError && (
        <div className={styles.nodeError} style={indent}>
          <span>couldn’t load this folder</span>
          <button
            type="button"
            className={styles.retryButton}
            onClick={() => childrenQuery.refetch()}
          >
            Try again
          </button>
        </div>
      )}

      {childrenActive && childrenQuery.data && (
        <div className={styles.tchildren} role="group">
          {filterNodes(sortNodes(childrenQuery.data), filter).map((child) => (
            <FileTreeNode
              key={child.path}
              changeId={changeId}
              node={child}
              selectedPath={selectedPath}
              selectedDir={selectedDir}
              onSelectFile={onSelectFile}
              onSelectDir={onSelectDir}
              changed={changed}
              filter={filter}
              depth={depth + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
}

/** Directories first, then files; alphabetical within each group. */
export function sortNodes(nodes: TreeNode[]): TreeNode[] {
  return [...nodes].sort((a, b) => {
    if (a.kind !== b.kind) return a.kind === "directory" ? -1 : 1;
    return a.name.localeCompare(b.name);
  });
}

/**
 * Apply the name filter: keep all directories (so the founder can still
 * drill to a deep match) and the files whose name matches. "" = no
 * filter (everything passes).
 */
export function filterNodes(nodes: TreeNode[], filter: string): TreeNode[] {
  if (filter === "") return nodes;
  return nodes.filter(
    (n) => n.kind === "directory" || n.name.toLowerCase().includes(filter),
  );
}
