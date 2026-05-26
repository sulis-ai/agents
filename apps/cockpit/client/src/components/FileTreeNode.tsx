// WP-014 — <FileTreeNode /> — one node in the worktree tree (recursive).
//
// A node is either a file (clickable → sets ?file=) or a directory
// (clickable → toggles expansion). The recursion lives here, not in
// <FileTree>, so the tree component stays one screen (WP-014 Blue
// criterion).
//
// Directories fetch their children lazily: useTree(changeId, path) is
// only enabled once the directory is expanded. Per-directory loading
// shows an inline spinner on the expand triangle; per-directory errors
// show an inline "failed to load" with a retry control.
//
// References: WP-014 Contract (<FileTreeNode>), TDD §6.

import { useState } from "react";
import type { TreeNode } from "../../../shared/api-types";
import { useTree } from "../api/useTree";
import styles from "../styles/FilesPanel.module.css";

interface Props {
  changeId: string;
  node: TreeNode;
  /** Currently selected file path (?file=), for highlighting. */
  selectedPath: string;
  /** Called when a file node is clicked. */
  onSelectFile: (path: string) => void;
  /** Nesting depth, for indentation. */
  depth: number;
}

export function FileTreeNode({
  changeId,
  node,
  selectedPath,
  onSelectFile,
  depth,
}: Props) {
  const [expanded, setExpanded] = useState(false);
  const isDirectory = node.kind === "directory";

  // Children are only fetched once the directory is expanded.
  const childrenActive = expanded && isDirectory;
  // Mount the hook unconditionally (rules of hooks), but only fetch once
  // the directory is expanded. Keyed on the directory's own path so each
  // directory caches independently — a collapsed node never subscribes
  // to the root listing.
  const childrenQuery = useTree(changeId, isDirectory ? node.path : "", {
    enabled: childrenActive,
  });

  const indent = { paddingLeft: `${depth * 14 + 8}px` };

  if (!isDirectory) {
    const isSelected = selectedPath === node.path;
    return (
      <button
        type="button"
        className={isSelected ? styles.nodeFileActive : styles.nodeFile}
        style={indent}
        onClick={() => onSelectFile(node.path)}
        data-testid={`file-tree-node-${node.path}`}
        data-active={isSelected ? "true" : "false"}
      >
        <span className={styles.nodeIcon} aria-hidden="true">
          📄
        </span>
        <span className={styles.nodeLabel}>{node.name}</span>
      </button>
    );
  }

  return (
    <div data-testid={`file-tree-node-${node.path}`}>
      <button
        type="button"
        className={styles.nodeDir}
        style={indent}
        onClick={() => setExpanded((v) => !v)}
        aria-expanded={expanded}
      >
        <span className={styles.nodeTriangle} aria-hidden="true">
          {childrenActive && childrenQuery.isLoading
            ? "…"
            : expanded
              ? "▾"
              : "▸"}
        </span>
        <span className={styles.nodeIcon} aria-hidden="true">
          📁
        </span>
        <span className={styles.nodeLabel}>{node.name}</span>
      </button>

      {childrenActive && childrenQuery.isError && (
        <div className={styles.nodeError} style={indent}>
          <span>failed to load</span>
          <button
            type="button"
            className={styles.retryButton}
            onClick={() => childrenQuery.refetch()}
            title="Retry"
          >
            ↻
          </button>
        </div>
      )}

      {childrenActive && childrenQuery.data && (
        <div role="group">
          {sortNodes(childrenQuery.data).map((child) => (
            <FileTreeNode
              key={child.path}
              changeId={changeId}
              node={child}
              selectedPath={selectedPath}
              onSelectFile={onSelectFile}
              depth={depth + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
}

/**
 * Directories first, then files; alphabetical within each group. Shared
 * with <FileTree> for the root listing so ordering is consistent at
 * every level.
 */
export function sortNodes(nodes: TreeNode[]): TreeNode[] {
  return [...nodes].sort((a, b) => {
    if (a.kind !== b.kind) return a.kind === "directory" ? -1 : 1;
    return a.name.localeCompare(b.name);
  });
}
