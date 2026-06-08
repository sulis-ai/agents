// WP-007 — gatherChangeContent: fold a change's searchable text (FR-10).
//
// Search hits CONTENT, not just labels (FR-10): the founder can find a
// change by a word that appears only in its conversation or in something
// the agent created for it. This pure helper folds three sources into one
// searchable string the `searchChanges` filter scans:
//
//   1. the record's own labels  — handle, slug, intent, primitive, branch
//      (so a title/handle hit still works);
//   2. the conversation         — every user/assistant/system text block
//      from the parsed transcript;
//   3. the created entities      — each brain entity's title + its detail
//      fields' text (so an entity-only term matches, FR-10).
//
// Pure: no I/O. The route gathers the transcript + brain via the existing
// reads and passes them in. The reply BODY discipline (NFR-SEC-03) keeps
// transcript text off the wire surfaces, but search needs to scan it
// server-side; the scanned text never leaves the server — only the matched
// `Change` rows do.

import type { ChangeStoreRecord } from "../ports/ChangeStoreReader";
// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits; the rule's `../../*` pattern is intended to block escapes out of apps/cockpit/, which `import/no-restricted-paths` already enforces correctly)
import type {
  BrainView,
  TranscriptMessage,
} from "../../shared/api-types";

/**
 * Fold a change's labels + conversation + created-entity text into a
 * single searchable string. Order is label → conversation → entities;
 * the result is whitespace-joined.
 */
export function gatherChangeContent(
  record: ChangeStoreRecord,
  transcript: readonly TranscriptMessage[],
  brain: BrainView,
): string {
  const parts: string[] = [];

  // 1. Labels (so a handle/intent/slug hit still works).
  parts.push(record.handle, record.slug, record.intent, record.primitive, record.branch);

  // 2. Conversation text.
  for (const msg of transcript) {
    parts.push(transcriptText(msg));
  }

  // 3. Created entities — title + detail text.
  for (const group of brain.groups) {
    for (const entity of group.items) {
      parts.push(entity.kind, entity.title);
      if (entity.detail) {
        parts.push(flattenStrings(entity.detail));
      }
    }
  }

  return parts.filter((p) => p && p.length > 0).join(" ");
}

/** Pull the searchable text out of one transcript message. */
function transcriptText(msg: TranscriptMessage): string {
  switch (msg.kind) {
    case "user":
      return msg.text;
    case "system":
      return msg.text;
    case "assistant":
      return msg.blocks
        .map((b) => (b.kind === "text" ? b.text : ""))
        .filter((t) => t.length > 0)
        .join(" ");
  }
}

/**
 * Recursively collect every string value from a JSON-ish object/array
 * into a single space-joined string. Keys are not collected — only values
 * — so an entity's content is searchable without the schema noise. Bounded
 * by the parsed entity size (already capped by readBrain's per-file read).
 */
function flattenStrings(value: unknown): string {
  if (typeof value === "string") return value;
  if (Array.isArray(value)) {
    return value.map(flattenStrings).filter((s) => s.length > 0).join(" ");
  }
  if (value && typeof value === "object") {
    return Object.values(value as Record<string, unknown>)
      .map(flattenStrings)
      .filter((s) => s.length > 0)
      .join(" ");
  }
  return "";
}
