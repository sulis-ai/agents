// WP-003 — the relay-origin helper (ADR-016, ADR-018, TDD §2/§4 component 4).
//
// Turns a resolved session into the assisted `SULIS_ORIGIN` env the relay hands
// to the one sanctioned spawn, or `null` when the identity can't be derived
// (caller spawns UNSTAMPED → commit degrades to inferred, ADR-013).
//
// ── How the relay consumes this (the interface pinned for WP-002) ───────────
// WP-001 widened `spawnBridge` with an optional 3rd argument `originEnv:
// Record<string, string>` (ADR-017). The relay (chat.ts, wired in WP-004)
// computes `assistedOriginEnv(identity, resolution, transcript)` and passes the
// RESULT straight through as that 3rd argument:
//
//     const originEnv = assistedOriginEnv(identity, resolution, transcript);
//     // ... then, inside the bridge's relay (WP-002 wiring):
//     spawnBridge(argv, resolution.session.cwd, originEnv ?? undefined);
//
// `null` ⇒ omit the env entirely (spawn byte-identical to today). This is the
// contract WP-002 forwards through the bridge to the spawn and WP-004 calls from
// the relay route. The helper itself starts NO process and writes NOTHING — it
// only computes a value (ADR-003 read-only preserved).
//
// ── Grammar (consume #216 unchanged) ───────────────────────────────────────
// The value is the exact bare trailer BODY that #216's `parse_origin_env`
// accepts (and the cockpit's own `originFromTrailerValue` mirrors):
//
//     assisted; conversation=<threadId>; turn=<n>
//
// `conversation` is a `thread_`-shaped Thread id; `turn` is the integer Message
// ordinal (ADR-016). This helper does NOT re-implement #216's formatting beyond
// emitting the accepted string shape, and it does NOT sanitise the value — the
// id is a session-derived token (no control chars) and #216's parser is the one
// boundary guard (no second sanitiser; ADR-013/§3 hardening). WP-006 locks the
// cross-language round-trip through the Python parser.

import type { ConversationIdentity } from "../ports/ConversationIdentity";
import type { SessionResolution } from "../ports/SessionBridge";
// eslint-disable-next-line no-restricted-imports -- intra-package import to apps/cockpit/shared/ (TDD §9 permits; the rule's `../../*` pattern blocks escapes out of apps/cockpit/, which import/no-restricted-paths already enforces)
import type { TranscriptMessage } from "../../shared/api-types";

/** The env-var key #216's hook reads to decide whether to stamp the commit. */
const ORIGIN_ENV_KEY = "SULIS_ORIGIN";

/**
 * Derive the assisted origin env for a resolved session, or `null` when it
 * cannot be derived (the caller then spawns unstamped). Uses the injected
 * `ConversationIdentity` port — the local adapter in this change, a live
 * service adapter later, with no change here (ADR-018).
 */
export function assistedOriginEnv(
  identity: ConversationIdentity,
  resolution: SessionResolution,
  transcript: TranscriptMessage[],
): Record<string, string> | null {
  const thread = identity.forResolvedSession(resolution, transcript);
  if (thread === null) return null;

  // Emit the exact bare-body grammar #216 accepts. The value is passed AS-IS to
  // the spawn env; #216's parser performs the control-char / shape guard.
  const body = `assisted; conversation=${thread.threadId}; turn=${thread.turn}`;
  return { [ORIGIN_ENV_KEY]: body };
}
