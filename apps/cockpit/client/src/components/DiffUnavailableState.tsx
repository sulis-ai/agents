// WP-015 — <DiffUnavailableState />.
//
// Shown when a file's diff can't be displayed because the file is
// binary or larger than the 1 MiB cap (from WP-008). Mirrors
// <FileBinaryState> / <FileTruncatedState> (WP-014): a friendly
// explanation plus the copy-path affordance so the founder can open
// the file locally.
//
// References: WP-015 Contract (<FilePane> diff binary/truncated branch).

import { CopyPathButton } from "./CopyPathButton";
import styles from "../styles/FilesPanel.module.css";

interface Props {
  absolutePath: string;
}

export function DiffUnavailableState({ absolutePath }: Props) {
  return (
    <div className={styles.fileMessage} data-testid="diff-unavailable-state">
      <p>
        Diff not available for binary or large files — copy the path to open
        it locally.
      </p>
      <CopyPathButton absolutePath={absolutePath} />
    </div>
  );
}
