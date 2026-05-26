// WP-014 — <FilesPanel /> — the "Files" tab of the thread view.
//
// Two-column layout: <FileTree> on the left (~280px) and <FilePane> on
// the right (fills). The selected file lives in the ?file= search param
// (driven by <FileTree>), so the selection is shareable within the same
// machine and survives refresh. <FilePane> reads the same param, so the
// two columns stay in sync through the URL with no shared state.
//
// References: WP-014 Contract (<FilesPanel> shape), ADR-001.

import { FileTree } from "./FileTree";
import { FilePane } from "./FilePane";
import styles from "../styles/FilesPanel.module.css";

interface Props {
  changeId: string;
}

export function FilesPanel({ changeId }: Props) {
  return (
    <div className={styles.filesPanel} data-testid="files-panel">
      <FileTree changeId={changeId} />
      <FilePane changeId={changeId} />
    </div>
  );
}
