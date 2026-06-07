// Files redesign (Direction B · repo browser) — <FilesPanel />.
//
// The full-width Files view for a change. A ~280px TREE COLUMN (header,
// an All-files ↔ Changed · N switch, a search box, then the tree) + a
// CONTENT COLUMN that renders at two levels:
//   - a FOLDER OVERVIEW (the folder's contents as a list + its README
//     rendered below) — the default landing state, and whenever a folder
//     (or nothing) is selected;
//   - a SINGLE FILE (rendered/raw doc or read-only code, with a
//     current↔diff toggle) — whenever a file is selected.
//
// Selection lives in the URL: ?file= (a file) or ?dir= (a folder). The
// tree, the changed-list, the overview rows, and the breadcrumb all read
// and write those params, so every part stays in sync through the URL
// with no shared component state.
//
// References: the signed files-B-repo-browser visual contract.

import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  FolderIcon,
  ListBulletIcon,
  PencilSquareIcon,
  MagnifyingGlassIcon,
  ChevronRightIcon,
} from "@heroicons/react/20/solid";
import { useChanged } from "../api/useChanged";
import { FileTree } from "./FileTree";
import { ChangedList } from "./ChangedList";
import { FolderOverview } from "./FolderOverview";
import { FilePane } from "./FilePane";
import type { ChangeView } from "./ChangeNav";
import type { ChangedMap } from "./FileTreeNode";
import styles from "../styles/FilesPanel.module.css";

interface Props {
  changeId: string;
  /** Switch the change view (for the open-file provenance panel's jumps). */
  onSelectView?: (view: ChangeView) => void;
}

type Scope = "all" | "changed";

export function FilesPanel({ changeId, onSelectView }: Props) {
  const [params, setParams] = useSearchParams();
  const selectedFile = params.get("file") ?? "";
  const selectedDir = params.get("dir") ?? "";

  // Warm the heavy Monaco editor bundle as soon as the Files view mounts, so
  // it downloads during idle BEFORE the founder opens their first file — the
  // first open then renders with no chunk-download wait. The chunks are
  // code-split via React.lazy in MonacoFile/MonacoDiff; importing the inner
  // modules here kicks the same fetch early. Fire-and-forget, once per mount.
  useEffect(() => {
    void import("./MonacoFileInner");
    void import("./MonacoDiffInner");
  }, []);

  const [scope, setScope] = useState<Scope>("all");
  const [filterRaw, setFilterRaw] = useState("");
  const filter = filterRaw.trim().toLowerCase();

  const changedQuery = useChanged(changeId);
  const changedMap: ChangedMap = useMemo(() => {
    const m: ChangedMap = new Map();
    for (const f of changedQuery.data?.files ?? []) m.set(f.path, f.status);
    return m;
  }, [changedQuery.data]);
  const changedCount = changedQuery.data?.baseKnown
    ? changedQuery.data.files.length
    : null;

  function selectFile(path: string) {
    const next = new URLSearchParams(params);
    next.set("file", path);
    next.delete("dir");
    setParams(next, { replace: false });
  }
  function selectDir(path: string) {
    const next = new URLSearchParams(params);
    if (path === "") next.delete("dir");
    else next.set("dir", path);
    next.delete("file");
    setParams(next, { replace: false });
  }

  const fileSelected = selectedFile !== "";
  const dirSegments = selectedDir.split("/").filter((s) => s.length > 0);

  return (
    <div className={styles.filesPanel} data-testid="files-panel">
      {/* ---- TREE COLUMN ---- */}
      <div className={styles.tree}>
        <div className={styles.treeHead}>
          <FolderIcon className={styles.ti} aria-hidden="true" />
          <span className={styles.treeTitle}>Files in this change</span>
        </div>

        <div
          className={styles.scopeSwitch}
          role="tablist"
          aria-label="Which files to show"
        >
          <button
            type="button"
            role="tab"
            aria-selected={scope === "all"}
            className={scope === "all" ? styles.on : ""}
            onClick={() => setScope("all")}
          >
            <ListBulletIcon aria-hidden="true" />
            All files
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={scope === "changed"}
            className={scope === "changed" ? styles.on : ""}
            onClick={() => setScope("changed")}
          >
            <PencilSquareIcon aria-hidden="true" />
            Changed
            {changedCount !== null && changedCount > 0 && (
              <span className={styles.scopeCount}>{changedCount}</span>
            )}
          </button>
        </div>

        <div className={styles.treeSearch}>
          <MagnifyingGlassIcon className={styles.mg} aria-hidden="true" />
          <input
            type="search"
            value={filterRaw}
            onChange={(e) => setFilterRaw(e.target.value)}
            placeholder="Filter files…"
            aria-label="Filter files"
          />
        </div>

        <div className={styles.treebody}>
          {scope === "all" ? (
            <FileTree changeId={changeId} filter={filter} changed={changedMap} />
          ) : (
            <ChangedList
              changeId={changeId}
              changed={changedQuery.data}
              isLoading={changedQuery.isLoading}
              isError={changedQuery.isError}
              filter={filter}
            />
          )}
        </div>
      </div>

      {/* ---- CONTENT COLUMN ---- */}
      {fileSelected ? (
        <FilePane changeId={changeId} onSelectView={onSelectView} />
      ) : (
        <div className={styles.content} data-testid="file-pane">
          <div className={styles.cbar}>
            <nav className={styles.crumb} aria-label="Folder path">
              <button
                type="button"
                className={`${styles.seg} ${styles.crumblink} ${dirSegments.length === 0 ? styles.cur : ""}`}
                onClick={() => selectDir("")}
              >
                Files
              </button>
              {dirSegments.map((seg, i) => {
                const prefix = dirSegments.slice(0, i + 1).join("/");
                const isLast = i === dirSegments.length - 1;
                return (
                  <span
                    key={prefix}
                    style={{ display: "inline-flex", alignItems: "center", gap: 6, minWidth: 0 }}
                  >
                    <span className={styles.sep} aria-hidden="true">
                      <ChevronRightIcon />
                    </span>
                    <button
                      type="button"
                      className={`${styles.seg} ${styles.crumblink} ${isLast ? styles.cur : ""}`}
                      onClick={() => selectDir(prefix)}
                    >
                      {seg}
                    </button>
                  </span>
                );
              })}
            </nav>
          </div>
          <div className={styles.cbody}>
            <FolderOverview
              changeId={changeId}
              dirPath={selectedDir}
              changed={changedMap}
              onSelectFile={selectFile}
              onSelectDir={selectDir}
            />
          </div>
        </div>
      )}
    </div>
  );
}
