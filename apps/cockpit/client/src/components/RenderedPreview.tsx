// WP-006 — <RenderedPreview /> (FR-08/09).
//
// The rendered-preview wrapper used by the Files section. For a RENDERABLE
// document it shows a RENDERED view with a one-click Rendered ↔ Raw toggle
// (FR-08/09), matching the SIGNED visual contract panel 6 (`.previewbar` +
// `.toggle` Rendered/Raw, `.rendered`, `.raw`):
//
//   - .md / .markdown → rendered via the shared renderMarkdown() (the app's
//     ONE markdown renderer — EP-03, not a fork); raw view is the exact
//     source in a `.raw` <pre>.
//   - .html / .htm    → rendered inside a SANDBOXED, script-free iframe
//     (`sandbox=""`, srcdoc) — the same "show it the way it's meant to look"
//     intent as the contract-preview renderer, with no execution; raw view
//     is the source.
//
// A CODE file is NOT renderable: it stays read-only source, delegated to
// <MonacoFile> (the existing viewer — EP-03), with no toggle.
//
// Consumes tokens.css only — no raw hex.

import { Suspense, useState } from "react";
import { renderMarkdown } from "../lib/renderMarkdown";
import { MonacoFile } from "./MonacoFile";
import styles from "../styles/RenderedPreview.module.css";

interface Props {
  /** Worktree-relative path (drives renderability + the filename label). */
  path: string;
  /** The file's text content. */
  content: string;
  /** Monaco's language hint (used for the code fallback). */
  language: string | null;
}

type Renderable = "markdown" | "html" | null;

/** Decide how a file renders from its extension (the language hint backs it up). */
function renderableKind(path: string, language: string | null): Renderable {
  const lower = path.toLowerCase();
  if (lower.endsWith(".md") || lower.endsWith(".markdown")) return "markdown";
  if (lower.endsWith(".html") || lower.endsWith(".htm")) return "html";
  // Fall back to the language hint for extension-less names.
  if (language === "markdown") return "markdown";
  if (language === "html") return "html";
  return null;
}

export function RenderedPreview({ path, content, language }: Props) {
  const kind = renderableKind(path, language);
  const [showRaw, setShowRaw] = useState(false);

  // Non-renderable → read-only source via the existing Monaco viewer. No
  // toggle: code is always shown as source (the contract: "code is read-only
  // mono").
  if (kind === null) {
    return (
      <div className={styles.preview} data-testid="preview-code">
        <Suspense fallback={<p className={styles.loading}>Loading viewer…</p>}>
          <MonacoFile content={content} language={language} />
        </Suspense>
      </div>
    );
  }

  return (
    <div className={styles.preview} data-testid="preview">
      <div className={styles.bar}>
        <span className={styles.filename} title={path}>
          {path.split("/").pop()}
        </span>
        <span className={styles.toggle} role="group" aria-label="View as">
          <button
            type="button"
            className={!showRaw ? styles.on : undefined}
            aria-pressed={!showRaw}
            onClick={() => setShowRaw(false)}
          >
            Rendered
          </button>
          <button
            type="button"
            className={showRaw ? styles.on : undefined}
            aria-pressed={showRaw}
            onClick={() => setShowRaw(true)}
          >
            Raw
          </button>
        </span>
      </div>

      {showRaw ? (
        <pre className={styles.raw} data-testid="preview-raw">
          {content}
        </pre>
      ) : kind === "markdown" ? (
        <div
          className={styles.rendered}
          data-testid="preview-rendered"
          // Safe: renderMarkdown HTML-escapes all source before emitting any
          // tag, and the rendered output is a bounded, audited tag subset
          // (see renderMarkdown.ts safety model). No document content can
          // inject markup or script.
          dangerouslySetInnerHTML={{ __html: renderMarkdown(content) }}
        />
      ) : (
        <iframe
          className={styles.htmlFrame}
          data-testid="preview-html-frame"
          title={`Rendered ${path}`}
          // Empty sandbox = maximum restriction: no scripts, no forms, no
          // same-origin. The document renders for reading only.
          sandbox=""
          srcDoc={content}
        />
      )}
    </div>
  );
}
