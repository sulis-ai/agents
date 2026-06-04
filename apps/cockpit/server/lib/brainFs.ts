// WP-008 (BLUE) — shared brain-filesystem primitives.
//
// readBrain (WP-006) and readProducts (WP-008) both walk the on-disk brain
// tree (`<root>/.brain/instances/<domain>/<kind>/<ULID>.jsonld`) with the same
// fail-soft directory listing + JSON parsing. Extracted here once (the
// 2-consumer threshold; EP-03 / WPB-12) so the walking discipline lives in
// ONE place: an absent directory yields [], a malformed entity file is
// skipped rather than throwing.
//
// Pure reads — no process start, no write (the read-only gate proves it).

import { readdir, readFile } from "node:fs/promises";

/** Sub-directory names under `dir`; [] if the dir is absent. */
export async function listDirs(dir: string): Promise<string[]> {
  try {
    const entries = await readdir(dir, { withFileTypes: true });
    return entries.filter((e) => e.isDirectory()).map((e) => e.name);
  } catch {
    return [];
  }
}

/** `.jsonld` file names in `dir`; [] if absent. Skips `.journal.md` etc. */
export async function listEntityFiles(dir: string): Promise<string[]> {
  try {
    const entries = await readdir(dir, { withFileTypes: true });
    return entries
      .filter((e) => e.isFile() && e.name.endsWith(".jsonld"))
      .map((e) => e.name);
  } catch {
    return [];
  }
}

/**
 * Parse one `.jsonld` entity file into a plain object. Returns null (skip)
 * when the file is missing or not valid JSON — a malformed file must not sink
 * the whole read.
 */
export async function readJsonldEntity(
  path: string,
): Promise<Record<string, unknown> | null> {
  try {
    const raw = await readFile(path, "utf8");
    const parsed = JSON.parse(raw) as unknown;
    if (parsed === null || typeof parsed !== "object") return null;
    return parsed as Record<string, unknown>;
  } catch {
    return null;
  }
}
