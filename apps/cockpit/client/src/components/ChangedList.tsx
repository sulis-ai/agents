// Files redesign (Direction B) — <ChangedList /> — the tree column in
// the "Changed" scope.
//
// Shows every file that differs between the change's base commit and its
// worktree (from useChanged) as an EXPAND/COLLAPSE TREE — the same
// pattern as the All-files tree, but pruned to only the changed files
// and the folders that contain them. The whole changed set is already
// known client-side, so the tree is built in memory (no lazy fetch):
// folders toggle open/closed, files show their worded status dot and
// select on click (?file=, clearing ?dir=). The name filter prunes to
// matching files (and auto-expands so matches are visible).
//
// Honest empty states: a change with no recorded baseline says so; a
// clean change (nothing changed) says so too — neither implies an error.

import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { ChevronRightIcon, ChevronDownIcon } from "@heroicons/react/20/solid";
import type { ChangedFile, ChangedFiles } from "../../../shared/api-types";
import { NodeIcon } from "./fileIcons";
import styles from "../styles/FilesPanel.module.css";

interface Props {
  changed: ChangedFiles | undefined;
  isLoading: boolean;
  isError: boolean;
  filter: string;
}

interface TNode {
  name: string;
  path: string;
  kind: "dir" | "file";
  status?: ChangedFile["status"];
  children: TNode[];
  /** Number of changed files within this folder (descendants); dirs only. */
  count?: number;
  /** Added lines: per-file from numstat (null = binary); per-folder = rolled-up sum of descendants (nulls skipped). */
  added?: number | null;
  /** Removed lines: per-file from numstat (null = binary); per-folder = rolled-up sum of descendants (nulls skipped). */
  removed?: number | null;
}

/** Build a nested dir/file tree from the flat changed-file list. */
function buildTree(files: ChangedFile[]): TNode[] {
  const root: TNode = { name: "", path: "", kind: "dir", children: [] };
  for (const f of files) {
    const segs = f.path.split("/").filter((s) => s.length > 0);
    let cur = root;
    segs.forEach((seg, i) => {
      const isLeaf = i === segs.length - 1;
      const p = segs.slice(0, i + 1).join("/");
      let child = cur.children.find(
        (c) => c.name === seg && (isLeaf ? c.kind === "file" : c.kind === "dir"),
      );
      if (!child) {
        child = {
          name: seg,
          path: p,
          kind: isLeaf ? "file" : "dir",
          children: [],
          ...(isLeaf ? { status: f.status, added: f.added, removed: f.removed } : {}),
        };
        cur.children.push(child);
      }
      cur = child;
    });
  }
  sortRec(root);
  rollUp(root);
  return root.children;
}

/**
 * Tag each directory with the number of changed files it contains AND the
 * rolled-up sum of its descendants' added/removed lines (binary files —
 * null counts — are skipped, never coerced to 0). One bottom-up pass.
 */
function rollUp(node: TNode): { files: number; added: number; removed: number } {
  if (node.kind === "file") {
    return {
      files: 1,
      added: node.added ?? 0,
      removed: node.removed ?? 0,
    };
  }
  const acc = node.children.reduce(
    (sum, c) => {
      const r = rollUp(c);
      return {
        files: sum.files + r.files,
        added: sum.added + r.added,
        removed: sum.removed + r.removed,
      };
    },
    { files: 0, added: 0, removed: 0 },
  );
  node.count = acc.files;
  node.added = acc.added;
  node.removed = acc.removed;
  return acc;
}

/** Directories first, then files; alphabetical within each group. */
function sortRec(node: TNode): void {
  node.children.sort((a, b) => {
    if (a.kind !== b.kind) return a.kind === "dir" ? -1 : 1;
    return a.name.localeCompare(b.name);
  });
  node.children.forEach(sortRec);
}

/**
 * The +N −N line counts for one node. `+N` reads in the positive token,
 * `−N` in the destructive token — worded/number-led, never colour-alone
 * (the sign character carries the meaning without colour). Mono numerals.
 *
 * A binary file (both counts null) shows a calm "binary" word instead of
 * numbers. A folder whose descendants are all binary rolls up to 0/0 and
 * shows +0 −0 (it still changed); we only suppress numbers for the binary
 * *file* case where there is genuinely nothing to count.
 */
function DiffCounts({
  added,
  removed,
  isFile,
}: {
  added: number | null | undefined;
  removed: number | null | undefined;
  isFile: boolean;
}) {
  if (isFile && added == null && removed == null) {
    return (
      <span className={styles.tdiff} title="binary file — no line count">
        <span className={styles.binary}>binary</span>
      </span>
    );
  }
  const add = added ?? 0;
  const rm = removed ?? 0;
  return (
    <span
      className={styles.tdiff}
      aria-label={`${add} added, ${rm} removed`}
    >
      <span className={styles.add}>+{add}</span>
      <span className={styles.del}>−{rm}</span>
    </span>
  );
}

function ChangedTreeNode({
  node,
  depth,
  defaultExpanded,
  selectedPath,
  onSelectFile,
}: {
  node: TNode;
  depth: number;
  defaultExpanded: boolean;
  selectedPath: string;
  onSelectFile: (path: string) => void;
}) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const indent = { paddingLeft: `${depth * 12 + 8}px` };

  if (node.kind === "file") {
    const isSelected = selectedPath === node.path;
    return (
      <button
        type="button"
        className={`${styles.tnode} ${isSelected ? styles.sel : ""}`}
        style={indent}
        onClick={() => onSelectFile(node.path)}
        data-testid={`changed-row-${node.path}`}
        data-active={isSelected ? "true" : "false"}
      >
        <span className={styles.tw} aria-hidden="true" />
        <NodeIcon kind="file" path={node.path} className={styles.ti} />
        <span className={styles.tn} title={node.path}>
          {node.name}
        </span>
        <span className={styles.statWrap}>
          <DiffCounts added={node.added} removed={node.removed} isFile />
          {node.status && (
            <span
              className={`${styles.dot} ${styles[node.status]}`}
              title={node.status}
              aria-label={node.status}
            />
          )}
        </span>
      </button>
    );
  }

  return (
    <div>
      <button
        type="button"
        className={`${styles.tnode} ${styles.folder}`}
        style={indent}
        onClick={() => setExpanded((v) => !v)}
        aria-expanded={expanded}
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
        <span className={styles.tn} title={node.path}>
          {node.name}
        </span>
        <span
          className={styles.folderStats}
          title={`${node.count} changed file${node.count === 1 ? "" : "s"}`}
        >
          <DiffCounts
            added={node.added}
            removed={node.removed}
            isFile={false}
          />
        </span>
      </button>
      {expanded && (
        <div className={styles.tchildren} role="group">
          {node.children.map((child) => (
            <ChangedTreeNode
              key={child.path}
              node={child}
              depth={depth + 1}
              defaultExpanded={defaultExpanded}
              selectedPath={selectedPath}
              onSelectFile={onSelectFile}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export function ChangedList({ changed, isLoading, isError, filter }: Props) {
  const [params, setParams] = useSearchParams();
  const selectedPath = params.get("file") ?? "";
  const filtering = filter !== "";

  const tree = useMemo(() => {
    const files = (changed?.files ?? []).filter(
      (f) => filter === "" || f.path.toLowerCase().includes(filter),
    );
    return buildTree(files);
  }, [changed, filter]);

  function selectFile(path: string) {
    const next = new URLSearchParams(params);
    next.set("file", path);
    next.delete("dir");
    setParams(next, { replace: false });
  }

  if (isLoading) {
    return <p className={styles.treeMessage}>Loading what changed…</p>;
  }
  if (isError) {
    return <p className={styles.treeMessage}>Couldn’t work out what changed.</p>;
  }
  if (changed && !changed.baseKnown) {
    return (
      <p className={styles.treeMessage}>
        No baseline recorded for this change, so there’s nothing to compare
        against yet.
      </p>
    );
  }

  if (tree.length === 0) {
    return (
      <p className={styles.treeMessage}>
        {filter === "" ? "Nothing’s changed yet." : "No changed files match."}
      </p>
    );
  }

  return (
    // Keyed on the filter so toggling the filter resets the expand state
    // (a filtered tree auto-expands so matches are visible).
    <nav data-testid="changed-list" aria-label="Changed files" key={filter}>
      {tree.map((node) => (
        <ChangedTreeNode
          key={node.path}
          node={node}
          depth={0}
          defaultExpanded={filtering}
          selectedPath={selectedPath}
          onSelectFile={selectFile}
        />
      ))}
    </nav>
  );
}
