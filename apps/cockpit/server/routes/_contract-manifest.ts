// WP-003 — consumer-side reader for the shared contract manifest
// (TDD §2.3 "the data seam"; ADR-001 read-only cockpit; CF-05/06).
//
// The renderers (WP-001 `wpx-render-contract`, WP-002 `wpx-render-ui`) BOTH
// read-modify-write one file per change: `<worktree>/CONTRACT.manifest.json`.
// It carries two halves:
//
//   {
//     "data_contract": { "format": "...", "name": "...", "contracts": [...] },
//     "contract_html": "<abs path to CONTRACT.html>",
//     "ui_contract": "present" | "none",
//     "path": "<abs path to UI.html>",     // when ui_contract == "present"
//     "note": "no UI contract for this change …"  // when ui_contract == "none"
//   }
//
// This module is the cockpit's ONLY reader of that file. The cockpit
// CONSUMES the manifest + serves the named files; it never parses the
// contracts themselves (that is the renderers' job — keeping the cockpit
// read-only, ADR-001). Every accessor is defensive: an absent or corrupt
// manifest, or either half missing (the renderers run independently and
// either may land first), degrades to a safe shape rather than throwing
// into the serving path.

import { readFile } from "node:fs/promises";
import { join } from "node:path";

/** The conventional manifest filename (matches both renderers' MANIFEST_NAME). */
export const MANIFEST_NAME = "CONTRACT.manifest.json";

/** The UI half as the consumer projects it (carries the path for serving). */
export type UiContractState =
  | { status: "present"; path: string | null }
  | { status: "none"; note: string };

/** The data half as the consumer projects it. */
export interface DataContractState {
  format: string;
  name: string | null;
}

/**
 * The consumer-side projection of one change's CONTRACT.manifest.json.
 *
 *   - `present`      → a manifest file was found AND parsed. False means no
 *                      render has happened yet (or the file was corrupt);
 *                      callers show a "not rendered yet" affordance, not an
 *                      error.
 *   - `dataContract` → the data half (format + name), or null if absent.
 *   - `contractHtml` → absolute path to CONTRACT.html, or null if absent.
 *   - `uiContract`   → the UI half. Defaults to a "none" note when the UI
 *                      half is absent (the data renderer ran but the UI one
 *                      hasn't), so the cockpit shows a note, never a broken
 *                      link.
 */
export interface ContractManifest {
  present: boolean;
  dataContract: DataContractState | null;
  contractHtml: string | null;
  uiContract: UiContractState;
}

const DEFAULT_NO_UI_NOTE =
  "No UI contract for this change — it carries no visual contract / design tokens.";

function absent(): ContractManifest {
  return {
    present: false,
    dataContract: null,
    contractHtml: null,
    uiContract: { status: "none", note: DEFAULT_NO_UI_NOTE },
  };
}

function asString(v: unknown): string | null {
  return typeof v === "string" && v.length > 0 ? v : null;
}

function projectDataContract(raw: unknown): DataContractState | null {
  if (typeof raw !== "object" || raw === null) {
    return null;
  }
  const obj = raw as Record<string, unknown>;
  const format = asString(obj.format) ?? "none";
  return { format, name: asString(obj.name) };
}

function projectUiContract(manifest: Record<string, unknown>): UiContractState {
  // The data renderer may have landed before the UI renderer — treat an
  // absent ui_contract key as a "none" note, not a crash.
  if (manifest.ui_contract === "present") {
    return { status: "present", path: asString(manifest.path) };
  }
  const note = asString(manifest.note) ?? DEFAULT_NO_UI_NOTE;
  return { status: "none", note };
}

/**
 * Read + project the shared contract manifest for a resolved worktree root.
 * Never throws for the "no manifest" / "corrupt manifest" / "partial
 * manifest" cases — those all degrade to a safe shape. (A genuine I/O fault
 * other than ENOENT propagates, as elsewhere in the cockpit.)
 */
export async function readContractManifest(
  worktreeRoot: string,
): Promise<ContractManifest> {
  const manifestPath = join(worktreeRoot, MANIFEST_NAME);

  let text: string;
  try {
    text = await readFile(manifestPath, "utf8");
  } catch (err) {
    if (isErrnoException(err) && err.code === "ENOENT") {
      return absent(); // no render yet
    }
    throw err; // real I/O fault — surface it
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(text);
  } catch {
    return absent(); // corrupt — degrade, don't 500
  }
  if (typeof parsed !== "object" || parsed === null) {
    return absent();
  }

  const manifest = parsed as Record<string, unknown>;
  return {
    present: true,
    dataContract: projectDataContract(manifest.data_contract),
    contractHtml: asString(manifest.contract_html),
    uiContract: projectUiContract(manifest),
  };
}

function isErrnoException(err: unknown): err is NodeJS.ErrnoException {
  return (
    err instanceof Error &&
    typeof (err as NodeJS.ErrnoException).code === "string"
  );
}
