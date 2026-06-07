// WP-007 (Blue refactor) — gatherChangeStatus: a change's read-time
// status context, gathered once.
//
// Both the status route (WP-004) and the search route (WP-007) need the
// same read-time context for a change: its liveness, its parsed
// transcript, its open-BLOCKER signal, and the computed ChangeStatus
// (which derives the FR-12 attention verdict via `needsAttention`). The
// status route returns `status`; the search route additionally reads
// `liveness` (for the wire row) and `transcript` (for the content scan).
//
// 2-consumer threshold reached → extracted (EP-03). Composes the existing
// reads — no new port; no I/O beyond the reads it delegates to.

import type { ChangeStoreRecord } from "../ports/ChangeStoreReader";
// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits; the rule's `../../*` pattern is intended to block escapes out of apps/cockpit/, which `import/no-restricted-paths` already enforces correctly)
import type {
  ChangeStatus,
  Liveness,
  TranscriptMessage,
} from "../../shared/api-types";
import { probeLiveness } from "./probeLiveness";
import { locateTranscripts } from "./locateTranscripts";
import { parseTranscripts } from "./parseTranscripts";
import { detectOpenBlocker } from "./detectOpenBlocker";
import { computeStatus } from "./computeStatus";

export interface GatherChangeStatusDeps {
  sulisStateDir: string;
  claudeProjectsDir: string;
}

/** The gathered read-time context for one change. */
export interface ChangeStatusContext {
  liveness: Liveness;
  transcript: TranscriptMessage[];
  hasOpenBlocker: boolean;
  /** The computed ChangeStatus (headline + FR-12 attention verdict). */
  status: ChangeStatus;
}

/**
 * Gather a change's read-time status context: liveness + transcript +
 * open-BLOCKER signal, then the computed ChangeStatus. Best-effort — the
 * underlying reads each fail-soft (absent worktree/transcripts/blocker →
 * benign defaults), so a change with a gone worktree still yields a valid
 * (idle, unflagged) context rather than throwing.
 */
export async function gatherChangeStatus(
  deps: GatherChangeStatusDeps,
  record: ChangeStoreRecord,
): Promise<ChangeStatusContext> {
  const [liveness, transcriptPaths, hasOpenBlocker] = await Promise.all([
    probeLiveness(deps.sulisStateDir, record.changeId),
    locateTranscripts(record.worktreePath, deps.claudeProjectsDir),
    detectOpenBlocker(record.worktreePath),
  ]);
  const transcript = await parseTranscripts(transcriptPaths);
  const status = computeStatus({ record, transcript, liveness, hasOpenBlocker });
  return { liveness, transcript, hasOpenBlocker, status };
}
