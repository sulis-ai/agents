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
// The editor theme follows the active app theme (WP-005 / ADR-002):
// Monaco does not read CSS variables, so we pass it the matching built-in
// theme id derived from useTheme() via monacoThemeFor(). Flipping the app
// toggle re-renders this wrapper and Monaco restyles live (no remount).
//
// References: WP-014 Contract (<MonacoFile>), ADR-001 (Monaco
// read-only), WP-005 / ADR-002 (Monaco theme binds to the app theme).

import Editor from "@monaco-editor/react";
import styles from "../styles/FilesPanel.module.css";
import { useTheme } from "../theme/ThemeProvider";
import { monacoThemeFor } from "../theme/monacoThemeFor";

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
  const { theme } = useTheme();
  return (
    <div className={styles.monaco} data-testid="monaco-file">
      <Editor
        theme={monacoThemeFor(theme)}
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
