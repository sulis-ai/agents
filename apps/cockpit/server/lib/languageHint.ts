// WP-007 — extension-to-Monaco-language-id hint.
//
// The cockpit's read-only file viewer is Monaco (the same editor VS
// Code uses). Monaco accepts a language id (e.g. `"typescript"`) on
// `editor.create(...)` and applies the matching syntax highlighter.
// We don't try to *detect* the language from contents — that's a
// long-tail problem (shebangs, modeline strings, polyglot files); we
// just look up by extension. Unknown extensions return `null`, which
// the client treats as "plain text, no highlighting".
//
// References:
// - TDD §5.1 (FileContents.language: string | null).
// - WP-007 Contract (the baseline map below — adding entries is
//   opportunistic; removing one is a breaking change for the viewer).

import { extname } from "node:path";

/**
 * Lowercase-extension → Monaco language id. Keys include the leading
 * dot so lookup is by the unmodified output of `path.extname`
 * (lowercased).
 *
 * Exported because the unit tests assert the baseline shape, and
 * because a later iteration may want to merge in environment-specific
 * additions without re-declaring the map.
 */
export const LANGUAGE_HINTS: Record<string, string> = {
  ".ts": "typescript",
  ".tsx": "typescript",
  ".js": "javascript",
  ".jsx": "javascript",
  ".py": "python",
  ".json": "json",
  ".jsonl": "json",
  ".yaml": "yaml",
  ".yml": "yaml",
  ".md": "markdown",
  ".css": "css",
  ".html": "html",
  ".sh": "shell",
  ".sql": "sql",
  ".go": "go",
  ".rs": "rust",
  ".java": "java",
  ".rb": "ruby",
};

/**
 * Look up a Monaco language id for `filename`. Strips the directory
 * portion, lowercases the extension, and returns the mapped id or
 * `null` if the extension is not in `LANGUAGE_HINTS`. Files with no
 * extension (Makefile, .gitignore, .env, etc.) return `null`.
 *
 * The function takes a `filename` (a name with optional extension,
 * possibly with directory prefix). It does not touch the filesystem.
 */
export function languageHint(filename: string): string | null {
  const ext = extname(filename).toLowerCase();
  if (ext === "") {
    return null;
  }
  return LANGUAGE_HINTS[ext] ?? null;
}
