// WP-014 — <FileTruncatedState />.
//
// Shown when the server reports a file is too large for preview (over
// the 1 MiB cap from WP-007). The founder gets a friendly explanation
// and the copy-path affordance so they can open the full file locally.
//
// References: WP-014 Contract (<FilePane> truncated branch).

import { CopyPathButton } from "./CopyPathButton";
import styles from "../styles/FilesPanel.module.css";

interface Props {
  absolutePath: string;
}

export function FileTruncatedState({ absolutePath }: Props) {
  return (
    <div className={styles.fileMessage} data-testid="file-truncated-state">
      <p>File too large for preview — copy the path to open it locally.</p>
      <CopyPathButton absolutePath={absolutePath} />
    </div>
  );
}
