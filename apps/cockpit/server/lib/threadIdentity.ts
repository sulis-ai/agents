// WP-003 — the ONE shared session→Thread-id derivation rule (ADR-016/018, EP-03).
//
// Both readers of conversation identity render the SAME `thread_`-shaped id for
// the same session, so a file's displayed conversation id does not change shape
// when it flips likely→exact (ADR-018 D2):
//
//   - the relay (this WP, via LocalTranscriptConversationIdentity) records it on
//     the assisted commit, and
//   - the inferred read path (WP-004) derives it for display.
//
// Keeping the rule in ONE place is the EP-03 "one rule, two readers" guarantee:
// WP-004 imports `deriveThreadId` from here rather than re-implementing it, so
// the two can never drift. A test asserts the relay's id equals `deriveThreadId`
// of the session stem; WP-004's inferred test will assert the same.
//
// The derivation is PURE and LOCAL (no network, no store — ADR-018 D1): a
// Thread id is the stable session identity (the Claude session id, already a
// collision-resistant token) carried under the communication service's
// `thread_<…>` shape. When the live service is wired later, the id will come
// from the Thread repository instead — same shape, authoritative source — with
// no change to this helper's callers.

/** The `thread_` prefix the communication service stamps on every Thread id. */
const THREAD_ID_PREFIX = "thread_";

/** A transcript filename suffix, stripped to recover the bare session id stem. */
const TRANSCRIPT_SUFFIX = ".jsonl";

/**
 * The Thread id for a resolved session, derived deterministically from its
 * stable session identity (`sessionId`). A pure function of `sessionId`:
 *
 *   - same `sessionId` → same id (stable across a thread's turns),
 *   - distinct `sessionId` → distinct id (distinct per thread),
 *   - collision resistance inherited from the session-id namespace.
 *
 * Returns `null` for an empty / whitespace-only session id (a fresh session
 * with no stable identity yet) — the caller degrades to unstamped/inferred.
 */
export function deriveThreadId(sessionId: string): string | null {
  const stem = sessionId.trim();
  if (stem === "") return null;
  return `${THREAD_ID_PREFIX}${stem}`;
}

/**
 * Recover the bare session-id stem from a `lastSessionRef` (a transcript path
 * `…/<sessionId>.jsonl`) or a raw session id. Returns `null` when no stem can be
 * recovered. This is the SAME stem the inferred read path takes from a transcript
 * filename, so both sides feed `deriveThreadId` the identical value (ADR-018 D2).
 */
export function sessionStemFromRef(ref: string | undefined): string | null {
  if (ref === undefined) return null;
  const base = ref.split("/").pop() ?? ref;
  const stem = base.endsWith(TRANSCRIPT_SUFFIX)
    ? base.slice(0, -TRANSCRIPT_SUFFIX.length)
    : base;
  const trimmed = stem.trim();
  return trimmed === "" ? null : trimmed;
}
