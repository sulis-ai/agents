// WP-007 — read a file inside a worktree and shape it into a FileContents.
//
// TDD §5 (`/api/changes/:id/file`), §5.1 (FileContents shape), §5.2
// (1 MiB server-side cap), §13.6 (binary detection). The function
// composes:
//
//   safeJoin       — sanitise the relative path (WP-004, single
//                    chokepoint for path traversal defence).
//   fs.stat        — discover the file size WITHOUT reading the bytes,
//                    so a 2 GiB file does not blow the heap. Per the WP
//                    Green spec.
//   fs.readFile    — only when size ≤ MAX_BYTES; reads the whole file.
//   detectBinary   — NUL byte in the first 8 KiB → binary.
//   languageHint   — extension → Monaco language id (or null).
//
// Returns the FileContents shape declared in shared/api-types.ts; the
// route layer (WP-010) wraps this in the HTTP envelope.

import { readFile, stat } from "node:fs/promises";

// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits; the rule's `../../*` pattern is intended to block escapes out of apps/cockpit/, which `import/no-restricted-paths` already enforces correctly)
import type { FileContents } from "../../shared/api-types";

import { detectBinary } from "./detectBinary";
import { IsADirectoryError, NotFoundError } from "./errors";
import { languageHint } from "./languageHint";
import { safeJoin } from "./safeJoin";

/**
 * Maximum file size the cockpit will inline-serve, in bytes. Per
 * TDD §5.2 and §13.6 this is **1 MiB**. Files larger than this are
 * returned with `content: null, truncated: true`; the UI shows
 * "file too large for preview — copy path".
 *
 * Exported as a named constant so WP-008 (diff reader) can reuse the
 * same threshold — per the WP-007 Blue spec on reuse.
 */
export const MAX_BYTES = 1024 * 1024;

interface ReadFileContentsOptions {
  /** Override the 1 MiB cap (useful for tests + future tuning). */
  maxBytes?: number;
}

/**
 * Read a file inside `worktreeRoot` and shape it into a `FileContents`.
 *
 * Behaviour (per WP-007 Contract):
 *   - `safeJoin` first. Throws `PathOutsideWorktreeError` on escape.
 *   - `fs.stat` to discover size + kind. ENOENT → `NotFoundError`;
 *     directory → `IsADirectoryError`.
 *   - Size > `maxBytes` (default `MAX_BYTES`) → return `{ content:
 *     null, truncated: true, binary: false, sizeBytes, ... }`.
 *   - Else read the whole file. If `detectBinary` returns true →
 *     `{ content: null, binary: true, truncated: false, sizeBytes, ... }`.
 *   - Else decode UTF-8 → `{ content: <string>, binary: false,
 *     truncated: false, sizeBytes, ... }`.
 *
 * `language` is set from `languageHint(relativePath)` — null when the
 * extension isn't in the map, or when the file is binary (a language
 * hint for a binary file is meaningless to the viewer).
 *
 * `absolutePath` is the realpath-resolved path that `safeJoin`
 * returned — suitable for the UI's copy-to-clipboard.
 *
 * `path` is echoed back as the input `relativePath` (unmodified).
 */
export async function readFileContents(
  worktreeRoot: string,
  relativePath: string,
  opts: ReadFileContentsOptions = {},
): Promise<FileContents> {
  const maxBytes = opts.maxBytes ?? MAX_BYTES;

  // 1. Sanitise the path. safeJoin throws PathOutsideWorktreeError on
  //    escape; that propagates to the caller unchanged.
  const absolutePath = await safeJoin(worktreeRoot, relativePath);

  // 2. stat() the resolved path. Map ENOENT → NotFoundError;
  //    everything else (EACCES, EIO, …) propagates as-is to the route
  //    layer's catch-all 500 handler.
  let stats: Awaited<ReturnType<typeof stat>>;
  try {
    stats = await stat(absolutePath);
  } catch (err) {
    if (isErrnoException(err) && err.code === "ENOENT") {
      throw new NotFoundError(`file not found: ${relativePath}`);
    }
    throw err;
  }

  // 3. Reject directories explicitly. The route layer maps to a 400
  //    rather than a 404 because the path does exist.
  if (stats.isDirectory()) {
    throw new IsADirectoryError(
      `path resolves to a directory: ${relativePath}`,
    );
  }

  const sizeBytes = stats.size;
  const language = languageHint(relativePath);

  // 4. Cap check. We use `>`, not `>=`, so a file of EXACTLY
  //    `maxBytes` bytes is still returned in full. The boundary
  //    condition is documented in TDD §5.2 ("capped at 1 MiB").
  if (sizeBytes > maxBytes) {
    return {
      path: relativePath,
      absolutePath,
      content: null,
      binary: false,
      truncated: true,
      sizeBytes,
      language,
    };
  }

  // 5. Read the bytes. We pull the file as a Buffer (not a string)
  //    so the binary-detection pass sees the raw bytes; we only
  //    UTF-8-decode at the end if the file is text.
  const buf = await readFile(absolutePath);

  if (detectBinary(buf)) {
    return {
      path: relativePath,
      absolutePath,
      content: null,
      binary: true,
      truncated: false,
      sizeBytes,
      // A language hint for a binary file is meaningless to the viewer
      // (no syntax highlighting will run). Suppress it.
      language: null,
    };
  }

  return {
    path: relativePath,
    absolutePath,
    content: buf.toString("utf8"),
    binary: false,
    truncated: false,
    sizeBytes,
    language,
  };
}

function isErrnoException(err: unknown): err is NodeJS.ErrnoException {
  return (
    err instanceof Error &&
    typeof (err as NodeJS.ErrnoException).code === "string"
  );
}
