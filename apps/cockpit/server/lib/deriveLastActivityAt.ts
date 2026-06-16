// WP-002 — deriveLastActivityAt: the feed's last-activity recency (FR-40/42).
//
// PURE: no I/O. The route already parses the change's transcript (for the
// FR-12 attention verdict via gatherChangeStatus), so the last-activity
// timestamp is derived from that already-gathered context rather than a new
// read — keeping the per-record fan-out bounded (MUC-2 / A-3).
//
//   - the timestamp of the most-recent transcript message, when present
//     (the transcript is the change's real activity truth),
//   - else the record's own `updatedAt` (the last stage transition),
//   - else null (FR-42 — a never-active change shows "—", not a bogus age).

// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits; the rule's `../../*` pattern is intended to block escapes out of apps/cockpit/, which `import/no-restricted-paths` already enforces correctly)
import type { TranscriptMessage } from "../../shared/api-types";

/**
 * Derive `lastActivityAt`: the last transcript message's timestamp, else the
 * record's `updatedAt`, else null. `updatedAt` is passed (not read) so this
 * stays pure. An empty-string `updatedAt` is treated as absent.
 */
export function deriveLastActivityAt(
  transcript: readonly TranscriptMessage[],
  updatedAt: string | null,
): string | null {
  if (transcript.length > 0) {
    const last = transcript[transcript.length - 1];
    if (last && last.timestamp) {
      return last.timestamp;
    }
  }
  if (updatedAt) {
    return updatedAt;
  }
  return null;
}
