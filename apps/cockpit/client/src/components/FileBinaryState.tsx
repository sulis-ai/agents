// WP-014 — <FileBinaryState />.
//
// Shown when the server reports a file is binary (no text preview). The
// founder gets a friendly explanation and the copy-path affordance so
// they can open the file in a local app that understands it.
//
// References: WP-014 Contract (<FilePane> binary branch).

import { CopyPathButton } from "./CopyPathButton";
import styles from "../styles/FilesPanel.module.css";

interface Props {
  absolutePath: string;
}

export function FileBinaryState({ absolutePath }: Props) {
  return (
    <div className={styles.fileMessage} data-testid="file-binary-state">
      <p>Binary file — copy the path to open it locally.</p>
      <CopyPathButton absolutePath={absolutePath} />
    </div>
  );
}
