---
wp: WP-004
change_id: 01KTHP2NYQ1A3WHPJD75VP31NT
title: Relay wires assisted Thread/Message origin end-to-end + inferred path reconciles on the same Thread id (closes #23)
kind: backend
primitive: expand-create
group: expand
composite_of: [relay-wiring (expand-create), inferred-path-reconcile (reorganise-refactor)]
characterisation_test: apps/cockpit/server/tests/InferredOriginAttribution.test.ts
status: pending
dependsOn: [WP-002, WP-003]
estimated_token_cost: { input: ~22k, output: ~8k }
verification:
  adapter: backend
  artifact: apps/cockpit/server/tests/routes.chat.test.ts
---

# WP-004 — Relay wires assisted Thread/Message origin end-to-end; inferred path reconciles

## Context

TDD §2/§3/§5 (components 3 + 7), ADR-016 (conversation = Thread id, turn =
Message ordinal), ADR-017 (widened port), ADR-018 (the conversation-identity
seam + how likely→exact reconciles). Two coupled pieces, both needed for the
observable likely→exact flip to render consistently:

1. **Wire the relay (EXPAND-Create).** Join the helper + local identity adapter
   (WP-003) to the widened bridge (WP-002): on each relay, derive the assisted
   env (`assisted; conversation=<threadId>; turn=<n>`) from the resolved session
   and pass it through `relay` → `spawnBridge`. This is THE sanctioned write path
   (ADR-003) — it stays read-only (computes ids, passes env; no fs/git write, no
   cross-service call).
2. **Reconcile the inferred path (REORGANISE-Refactor).** Move
   `InferredOriginAttribution` onto the **same** Thread-identity derivation the
   relay uses, so a file shows the same `thread_` id before the flip (inferred)
   and after (recorded) — ADR-018 D2. Fix the #23 multi-session TODO at the same
   time: index turns **per transcript** with a Thread id **per transcript**
   (one `Thread` per session), retiring "first stem only across the merged
   stream".

> **Reconciliation note (the crux).** Inferred correlation matches commits to
> turns by **timestamp window** (`correlate.nearestTurn`), NOT by conversation
> id, and a recorded trailer **short-circuits** correlation entirely
> (`correlate` step 1). So the flip does not depend on ids "lining up" — piece 2
> is purely about the *displayed* id being consistent and about fixing
> multi-session mis-attribution. It cannot regress which commit matches which
> turn. See ADR-018 for the full grounding.

## Contract

### Piece 1 — relay wiring

In `routes/chat.ts` `handleChat`, after `resolveSession` + bind succeeds and
before `relay`, compute `assistedOriginEnv(conversationIdentity, resolution,
transcript)` (WP-003) and pass it to `sessionBridge.relay(...)` via the param
WP-002 consumes. Inject the `ConversationIdentity` adapter
(`LocalTranscriptConversationIdentity`) at the route's composition root
alongside the existing bridge wiring. The transcript is the one the resolve path
already parsed (no new disk read on the hot path; if not in hand, the parse is
read-only and fail-soft).

Logging (NFR-SEC-03, MUST): the existing `ChatLogLine` MAY gain
`originStamped?: boolean` (and nothing else origin-related) so the live
round-trip is observable. **Never** log the thread id body, prompt, or reply
text.

### Piece 2 — inferred-path reconcile (the shared derivation + per-transcript indexing)

In `adapters/InferredOriginAttribution.ts` `loadTurns`:
- Replace "first transcript stem as conversation id, turns indexed across the
  merged stream" with: for **each** located transcript, derive its Thread id via
  the **shared `threadIdentity` helper** (the same one WP-003's relay adapter
  uses — EP-03) and index that transcript's turns 1-based **within that
  transcript**. Concatenate the per-transcript `TurnFacts`.
- Remove the `TODO(deferred)` #23 block; replace with a one-line ADR-018
  reference.

This is REORGANISE-Refactor of an existing reader, so a **characterisation test**
pins current behaviour first (see Red).

## Definition of Done

### Red
- [ ] **Characterisation test first** (`InferredOriginAttribution.test.ts`):
      pin CURRENT inferred output for (a) a single-transcript change and (b) a
      two-transcript change (capturing today's first-stem-only / merged-index
      behaviour). Confirm it passes against the unchanged adapter BEFORE
      refactoring (Fowler discipline; EP-07).
- [ ] `routes.chat.test.ts`: a relayed send over a resumable resolution causes
      the injected bridge to receive an assisted `originEnv` whose `conversation`
      is the `thread_`-shaped id for the transcript and whose `turn` is
      existing+1. Fails until wired.
- [ ] Degradation case: a fresh resolution (no transcript) relays with NO origin
      env and still completes normally (commit unstamped → inferred). Fails
      until the null-origin path is handled.
- [ ] Log discipline: assert the relay log line carries no prompt / thread-id-body
      text.
- [ ] Reconcile case (`InferredOriginAttribution.test.ts`, NEW assertions): the
      inferred conversation id for a transcript equals the SAME `thread_` id the
      relay would record for that transcript (shared-helper parity); a
      two-transcript change yields TWO distinct `thread_` ids with per-transcript
      1-based turns (the #23 fix). Fails until the refactor lands.

### Green
- [ ] Wire `assistedOriginEnv` + `LocalTranscriptConversationIdentity` into
      `handleChat`; pass through to `relay`; omit on null.
- [ ] Add `originStamped` to the log line only (boolean; no id/text).
- [ ] Refactor `loadTurns` to per-transcript Thread ids + per-transcript turn
      indexing via the shared `threadIdentity` helper; remove the #23 TODO.
- [ ] Re-run the characterisation test: update its expectations to the corrected
      multi-session output (the OLD merged-index expectations are now the bug
      that #23 describes; the change is intentional and the test documents it).

### Blue
- [ ] `vitest run routes.chat` + `session-bridge` + `InferredOriginAttribution`
      green; typecheck green.
- [ ] `check-read-only.sh` passes — relay still does no fs/git write, no new
      spawn, no cross-service call.
- [ ] Confirm concierge/onboarding/start paths (same file) are untouched and
      still relay with no origin.
- [ ] Confirm the session→thread derivation is the ONE shared helper used by both
      the relay adapter (WP-003) and the inferred path (no duplicated rule; EP-03).
