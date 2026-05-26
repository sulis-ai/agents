// WP-014 — <MonacoFileInner /> — the actual Monaco wrapper.
//
// This module is the lazy chunk: it is the only client module that
// imports @monaco-editor/react, so Monaco's bundle is split out and
// loaded only when the founder opens a file (never on the dashboard
// route). <MonacoFile> (in MonacoFile.tsx) is the React.lazy() wrapper
// that points here.
//
// The editor is configured read-only per ADR-001 — the cockpit never
// writes files. `options.readOnly === true` is the load-bearing
// client-side read-only guarantee (asserted in MonacoFile.test.tsx).
//
// References: WP-014 Contract (<MonacoFile>), ADR-001 (Monaco
// read-only).

import Editor from "@monaco-editor/react";
import styles from "../styles/FilesPanel.module.css";

export interface MonacoFileProps {
  /** File contents to display. */
  content: string;
  /** Monaco language id (e.g. "typescript"); null → plaintext. */
  language: string | null;
}

export default function MonacoFileInner({
  content,
  language,
}: MonacoFileProps) {
  return (
    <div className={styles.monaco} data-testid="monaco-file">
      <Editor
        theme="vs-dark"
        defaultLanguage={language ?? "plaintext"}
        value={content}
        options={{
          readOnly: true,
          minimap: { enabled: false },
          scrollBeyondLastLine: false,
          wordWrap: "on",
          fontSize: 13,
        }}
      />
    </div>
  );
}
