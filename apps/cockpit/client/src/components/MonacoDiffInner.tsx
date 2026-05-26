// WP-015 — <MonacoDiffInner /> — the actual Monaco DiffEditor wrapper.
//
// This module is the lazy chunk for the diff view: alongside
// MonacoFileInner it imports @monaco-editor/react, so Monaco's bundle
// stays code-split and loads only when the founder opens the diff.
// <MonacoDiff> (in MonacoDiff.tsx) is the React.lazy() wrapper that
// points here — same pattern as <MonacoFile> (WP-014).
//
// Both panes are read-only per ADR-006 — the cockpit never writes
// files. `options.readOnly === true` is the load-bearing client-side
// read-only guarantee (asserted in MonacoDiff.test.tsx). The server
// has already computed `base` (the change's starting point) and
// `current` (the worktree now); we hand the two strings to Monaco's
// DiffEditor and it renders the visual diff.
//
// A null `base` means the file did not exist at the change's start →
// empty original pane (Monaco renders it as fully added). A null
// `current` means the file was deleted → empty modified pane (fully
// removed). See TDD §7.
//
// References: WP-015 Contract (<MonacoDiff>), ADR-006 (server computes,
// DiffEditor displays, both panes read-only).

import { DiffEditor } from "@monaco-editor/react";
import styles from "../styles/FilesPanel.module.css";

export interface MonacoDiffProps {
  /** File contents at the change's starting point; null = did not exist. */
  base: string | null;
  /** Current worktree contents; null = file deleted. */
  current: string | null;
  /** Monaco language id (e.g. "typescript"); null → plaintext. */
  language: string | null;
}

export default function MonacoDiffInner({
  base,
  current,
  language,
}: MonacoDiffProps) {
  const lang = language ?? "plaintext";
  return (
    <div className={styles.monaco} data-testid="monaco-diff">
      <DiffEditor
        theme="vs-dark"
        original={base ?? ""}
        modified={current ?? ""}
        originalLanguage={lang}
        modifiedLanguage={lang}
        options={{
          readOnly: true,
          renderSideBySide: true,
          minimap: { enabled: false },
          scrollBeyondLastLine: false,
          fontSize: 13,
        }}
      />
    </div>
  );
}
