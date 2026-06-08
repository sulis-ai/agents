// WP-003 — LocalTranscriptConversationIdentity (ADR-018 D1, ADR-003, ADR-013).
//
// The ONLY ConversationIdentity adapter this change ships. It derives the
// assisted Thread identity LOCALLY and read-only from the already-resolved
// session — no cross-service call, no network, no file write (ADR-003
// preserved; the live Thread/Message repository adapter is a later WP behind the
// same port — ADR-018):
//
//   - threadId = `deriveThreadId(<session stem of lastSessionRef>)` — the SINGLE
//     shared rule (lib/threadIdentity), so the relay (here) and the inferred
//     read path (WP-004) render the SAME `thread_` id for the same session
//     (EP-03, ADR-018 D2). A fresh resolution (no `lastSessionRef`) → null.
//   - turn = `groupTurns(transcript).filter(isTurn).length + 1` — the 1-based
//     Message ordinal, reusing the shared `groupTurns` (apps/cockpit/shared) as
//     the local stand-in for `Thread.message_count + 1` (ADR-016).
//
// Best-effort throughout (ADR-013 non-fatal): ANY failure — a missing
// `lastSessionRef`, an empty stem, a malformed transcript — resolves to `null`
// (degrade to inferred). It NEVER throws.

import type {
  ConversationIdentity,
  ThreadIdentity,
} from "../ports/ConversationIdentity";
import type { SessionResolution } from "../ports/SessionBridge";
import { deriveThreadId, sessionStemFromRef } from "../lib/threadIdentity";
// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits; the rule's `../../*` pattern blocks escapes out of apps/cockpit/, which import/no-restricted-paths already enforces)
import type { TranscriptMessage } from "../../shared/api-types";
// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits; the rule's `../../*` pattern blocks escapes out of apps/cockpit/, which import/no-restricted-paths already enforces)
import { groupTurns, type TurnItem } from "../../shared/groupTurns";

/** The grouped-turn type-guard — the same `isTurn` filter the inferred path uses. */
function isTurn(item: { type: string }): item is TurnItem {
  return item.type === "turn";
}

/**
 * Count the existing turns in a transcript (the grouped agent turns). The
 * in-flight turn is `count + 1` — the 1-based Message ordinal (ADR-016).
 */
function existingTurnCount(transcript: TranscriptMessage[]): number {
  return groupTurns(transcript).filter(isTurn).length;
}

export class LocalTranscriptConversationIdentity implements ConversationIdentity {
  forResolvedSession(
    resolution: SessionResolution,
    transcript: TranscriptMessage[],
  ): ThreadIdentity | null {
    try {
      const stem = sessionStemFromRef(resolution.session.lastSessionRef);
      if (stem === null) return null;

      const threadId = deriveThreadId(stem);
      if (threadId === null) return null;

      const turn = existingTurnCount(transcript) + 1;
      return { threadId, turn };
    } catch {
      // Best-effort (ADR-013): any derivation failure → unstamped → inferred.
      return null;
    }
  }
}
