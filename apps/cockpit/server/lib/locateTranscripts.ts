// WP-009 — locate Claude Code session transcripts for a worktree.
//
// Per WP-009 Contract "Locator" section + TDD §4 (the load-bearing
// heuristic, restated below) + TDD §14.2 + ADR-004:
//
//   1. Compute the expected mangled directory: `mangleCwd(worktreePath)`.
//   2. The expected project directory is `projectsDir/<mangled-cwd>/`.
//   3. List every `*.jsonl` in that directory.
//   4. For each candidate, read until the first content-bearing
//      record (`type` ∈ {user, assistant, system, attachment}) and
//      check `record.cwd === worktreePath`. Accept iff it matches.
//   5. If the directory doesn't exist, return [].
//
// The cwd-field verification is the failsafe — see ADR-004 §Rationale.
// If Claude Code ever changes its mangling, the symptom is "no
// transcripts found" rather than "the wrong thread's chat rendered".
//
// Streaming discipline (TDD §13.6): we never slurp. The first
// content-bearing record can sit at line 200+ in a multi-MB
// transcript; we read line-by-line and stop as soon as we find it.

import { createReadStream } from "node:fs";
import { readdir } from "node:fs/promises";
import { join } from "node:path";
import { createInterface } from "node:readline";

import { mangleCwd } from "./mangleCwd";

/** Content-bearing record types per ADR-004 §Consequences. */
const CONTENT_TYPES = new Set([
  "user",
  "assistant",
  "system",
  "attachment",
]);

/**
 * Return absolute paths of every `*.jsonl` in
 * `projectsDir/mangleCwd(worktreePath)/` whose first content-bearing
 * record has `cwd === worktreePath`.
 *
 * Returns `[]` if `projectsDir` or the mangled subdirectory doesn't
 * exist. Files without any content-bearing record (empty files,
 * meta-only files) are skipped. Malformed lines are skipped while
 * scanning for the first content-bearing record (the next parseable
 * line decides).
 *
 * The result is in `readdir` order (no sort applied here — callers
 * that need timestamp order go through `parseTranscripts` which
 * merges chronologically).
 */
export async function locateTranscripts(
  worktreePath: string,
  projectsDir: string,
): Promise<string[]> {
  const mangled = mangleCwd(worktreePath);
  const projectDir = join(projectsDir, mangled);

  let entries: string[];
  try {
    entries = await readdir(projectDir);
  } catch (err) {
    if (isErrnoException(err) && err.code === "ENOENT") {
      // Mangled dir (or its parent projectsDir) doesn't exist — no
      // transcripts. Per the WP-009 Contract this is a normal "no
      // sessions yet" state, not an error.
      return [];
    }
    throw err;
  }

  const candidates = entries
    .filter((name) => name.endsWith(".jsonl"))
    .map((name) => join(projectDir, name));

  const accepted: string[] = [];
  for (const path of candidates) {
    if (await fileCwdMatches(path, worktreePath)) {
      accepted.push(path);
    }
  }
  return accepted;
}

/**
 * Stream `path` line-by-line, parsing each as JSON, until we find
 * the first record whose `type` is content-bearing. Return `true`
 * iff that record's `cwd` field equals `worktreePath`.
 *
 * If no content-bearing record exists (empty file, meta-only file),
 * return `false` — the file is skipped.
 *
 * Streams via `readline` over a `createReadStream` so a multi-MB
 * transcript with the first content record at line 200 doesn't
 * pull the whole file into memory.
 */
async function fileCwdMatches(
  path: string,
  worktreePath: string,
): Promise<boolean> {
  const stream = createReadStream(path, { encoding: "utf8" });
  const lines = createInterface({ input: stream, crlfDelay: Infinity });

  try {
    for await (const line of lines) {
      if (line.trim() === "") continue;

      let record: unknown;
      try {
        record = JSON.parse(line);
      } catch {
        // Malformed line — skip and keep scanning. The next parseable
        // content-bearing record decides.
        continue;
      }

      if (!isContentBearing(record)) continue;

      const cwd = (record as { cwd?: unknown }).cwd;
      return typeof cwd === "string" && cwd === worktreePath;
    }
    return false;
  } finally {
    // Make sure the underlying stream is closed even if we returned
    // early (we always read to the first content record; the rest of
    // the file is left unread).
    stream.destroy();
  }
}

function isContentBearing(record: unknown): boolean {
  if (typeof record !== "object" || record === null) return false;
  const t = (record as { type?: unknown }).type;
  return typeof t === "string" && CONTENT_TYPES.has(t);
}

function isErrnoException(err: unknown): err is NodeJS.ErrnoException {
  return (
    err instanceof Error &&
    typeof (err as NodeJS.ErrnoException).code === "string"
  );
}
