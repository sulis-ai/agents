// WP-003 — ConversationIdentity port (ADR-016, ADR-018 D1).
//
// The domain-owned seam between a resolved cockpit session and the
// communication-service identity its assisted commits are stamped with: a
// Thread id (`thread_<…>` shape) as the `conversation`, and the 1-based Message
// ordinal as the `turn` (ADR-016).
//
// This is EXPAND-Create (a port the cockpit domain owns + one local adapter),
// NOT a SUBSTITUTE-Wrap of the communication service: the public face is THIS
// interface; a future `CommunicationServiceConversationIdentity` adapter will be
// *called by* the seam, the same hexagonal shape as `SessionBridge` (ADR-002).
//
// In THIS change the only implementation is `LocalTranscriptConversationIdentity`
// (adapters/), which derives the identity LOCALLY and read-only from the resolved
// session — no cross-service call, no network (ADR-018 D1, ADR-003 preserved).
// The live Thread/Message repository adapter is a clean later WP behind this same
// port (ADR-018: swapping it changes nothing else — relay, grammar, stamper,
// hook, and read path are all untouched).

import type { SessionResolution } from "./SessionBridge";
// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits; the rule's `../../*` pattern blocks escapes out of apps/cockpit/, which import/no-restricted-paths already enforces)
import type { TranscriptMessage } from "../../shared/api-types";

/**
 * The communication-service identity of one chat turn, modelled on the
 * `Thread`/`Message` domain (ADR-016).
 */
export interface ThreadIdentity {
  /**
   * A communication-service Thread id (`thread_<…>` shape). Constant across a
   * thread's turns and distinct per thread; carries the `thread_` prefix so the
   * recorded value already looks like a service-assigned Thread id
   * (integration-ready).
   */
  threadId: string;
  /**
   * The 1-based Message ordinal for the in-flight turn — the local stand-in for
   * `Thread.message_count + 1` (existing turn count + 1).
   */
  turn: number;
}

/**
 * Maps a resolved session to its Thread identity. The relay calls this to build
 * the assisted origin; the inferred read path (WP-004) renders the SAME
 * `thread_` id via the same shared derivation (`lib/threadIdentity`, EP-03).
 */
export interface ConversationIdentity {
  /**
   * The Thread identity for a resolved session, or `null` when none can be
   * derived (a fresh session / no transcript) — in which case the caller spawns
   * UNSTAMPED and the commit degrades to inferred origin (ADR-013). Best-effort:
   * never throws.
   */
  forResolvedSession(
    resolution: SessionResolution,
    transcript: TranscriptMessage[],
  ): ThreadIdentity | null;
}
