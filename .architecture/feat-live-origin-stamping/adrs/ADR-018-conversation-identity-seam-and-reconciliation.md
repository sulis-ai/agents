# ADR-018 — A conversation-identity seam (model-only now, live later) + how likely→exact reconciles

- **Status:** accepted
- **Date:** 2026-06-07
- **Change:** CH-01KTHP · feat: live-origin-stamping
- **Deciders:** SEA
- **Extends:** ADR-012 (origin attribution is a domain-owned port), ADR-016
  (conversation = Thread id, turn = Message ordinal)
- **Honours:** ADR-003 (cockpit read-only), ADR-013 (non-fatal stamping)

## Context

ADR-016 sets the assisted identity to the communication service's Thread id +
Message ordinal. Two design questions follow, and both are load-bearing enough
to record:

### Q1 — Do we make a LIVE cross-service call into the communication service now?

The founder's steer was *"model as though we're going to integrate"* — i.e.
integration-**ready**, not necessarily live-wired now. The cockpit today has
**zero reach** into the communication service: no client, no Thread/Message
repository binding, no `platform_id` in scope (confirmed by grep — no
`thread_` / `platform_id` / `owner_type` anywhere under
`apps/cockpit/server`). A live call would introduce a new outbound integration
(EIF) and with it a new Armor surface: timeout, retry, circuit breaker, auth to
the service. That is the heavier interpretation the steer told us to avoid
"unless the live call is trivial" — and it is not trivial here.

### Q2 — How does likely→exact actually reconcile? (the crux, re-grounded on code)

The prior ADR-016 premise was: *if recorded carries a different conversation id
from inferred, the two won't line up and likely→exact fails.* **Reading the
code shows that premise is wrong on mechanism:**

- `correlate()` (`lib/originAttribution/correlate.ts`) is the inferred path.
  **Step 1 short-circuits on a recorded trailer** and returns it immediately
  with `attribution: "recorded"`. Correlation is the *fallback only*.
- When it does correlate an assisted commit, it matches the commit to a turn by
  **timestamp window** (`nearestTurn`, default 15 min) — **not by conversation
  id**. The `conversationId` is an *output* attached to the matched turn; it is
  **never used as a correlation key**.

So a recorded `thread_` id does **not** have to "line up" with any inferred turn
for the flip to happen — the presence of the trailer is what flips likely→exact.
The real reconciliation requirement is narrower and is a **display** concern:

> For the same file, the cockpit should show the *same* conversation id before
> the flip (inferred) and after (recorded). Today inferred renders the
> **transcript stem** (Claude session id); recorded will now render a
> **`thread_` id**. Left unaddressed, the id string visibly changes on flip even
> though it is the same conversation.

There is a second, pre-existing defect in the same area: the multi-session TODO
in `InferredOriginAttribution.loadTurns` (lines ~220-226) — only the **first**
transcript's stem is used as the conversation id and turns are indexed across the
**merged** stream, so a change spanning 2+ sessions reports the wrong id/turn.
This TODO is tagged `#23` — this change's own issue.

## Decision

### D1 — Model-only now; a domain-owned `ConversationIdentity` port is the seam

Introduce one domain-owned port, `ConversationIdentity`, that maps a resolved
session to its Thread identity:

```ts
// apps/cockpit/server/ports/ConversationIdentity.ts  (NEW — domain-owned)
export interface ThreadIdentity {
  /** A communication-service Thread id ("thread_<…>" shape). */
  threadId: string;
  /** 1-based Message ordinal for the in-flight turn (existing count + 1). */
  turn: number;
}

export interface ConversationIdentity {
  /** The Thread identity for a resolved session, or null when none can be
   *  derived (fresh session / no transcript) → caller spawns unstamped. */
  forResolvedSession(
    resolution: SessionResolution,
    transcript: TranscriptMessage[],
  ): ThreadIdentity | null;
}
```

- **Now (the default adapter, in this change):**
  `LocalTranscriptConversationIdentity` derives the identity **without any
  cross-service call** — read-only, ADR-003 preserved:
  - `threadId` = a deterministic `thread_`-shaped id derived from the resolved
    transcript's stable session identity (the transcript stem), so it is
    constant across a thread's turns and distinct per thread. It carries the
    `thread_` *shape* (`thread_` prefix over the stable session-derived token),
    so the recorded value already looks like a communication-service Thread id.
  - `turn` = `groupTurns(transcript).filter(isTurn).length + 1` — the local
    stand-in for `Thread.message_count + 1`.
- **Later (a follow-on adapter, NOT this change):**
  `CommunicationServiceConversationIdentity` implements the **same port** by
  reading/creating the real `Thread` via `ThreadRepositoryPort` and counting
  messages via `MessageRepositoryPort.list_by_thread`. Swapping the adapter
  changes nothing else — the relay, the trailer grammar, the stamper, the hook,
  and the read path are all untouched. That swap is where the Armor surface for
  the live call (timeout / retry / circuit breaker / auth / `platform_id`
  threading) gets designed; it is explicitly out of scope here and flagged to
  the founder.

This is EXPAND-Create (a new port the cockpit domain owns + one local adapter),
**not** a SUBSTITUTE-Wrap of the communication service — the public face is the
cockpit's own port; the future service client will be *called by* its adapter
(ADR-002 pattern, mirrors `SessionBridge`).

### D2 — Reconcile by moving the inferred path onto the same Thread identity

Route the inferred path's conversation id through the **same**
`ConversationIdentity` derivation, so inferred and recorded render the **same
`thread_` id** for the same file:

- `InferredOriginAttribution.loadTurns` derives each transcript's Thread id via
  the same local rule the relay uses (transcript stem → `thread_`-shaped id),
  instead of using the raw stem.
- **This also closes the #23 multi-session TODO:** index turns **per transcript**
  with a Thread id **per transcript** (one `Thread` per session), rather than
  "first stem only across the merged stream". Each session's turns then carry
  their own correct `thread_` id and their own 1-based ordinals.

Because correlation matches by timestamp window (not by id), this change is
purely about what id/turn the matched turn *reports* — it does not alter which
commit matches which turn, so it cannot regress correlation. It only makes the
displayed identity consistent with the recorded value and fixes the
multi-session mis-attribution.

## Alternatives considered

- **Make the live cross-service call now — rejected (for this change).** Heavier
  than the steer asked for; introduces an outbound integration + full Armor
  surface with no requirement to do so now. The seam (D1) makes it a clean later
  step. Recorded as the one genuine founder scope call.
- **Carry the thread id through the relay env from a live service lookup —
  rejected now, enabled later.** This is exactly what the
  `CommunicationServiceConversationIdentity` adapter will do; deferring it behind
  the port keeps this change read-only and CI-stub-friendly.
- **Leave the inferred path on the transcript stem and accept the id changing
  shape on flip — rejected.** The whole point of likely→exact is that it is the
  *same* fact getting more precise; a conversation id that visibly mutates on
  flip undermines that. Cheap to fix via the shared derivation (D2).
- **Map session-id → thread-id in a side table — rejected.** A second store to
  keep in sync and to drift; the deterministic derivation needs no store now,
  and the live adapter will use the service's own store later.

## Consequences

- **One new domain-owned port + one local adapter** in this change; no outbound
  call, no network, no new secret, read-only (ADR-003 gate unchanged — the port
  + adapter live under the already-allow-listed cockpit server paths; a WP DoD
  re-asserts the gate).
- **The relay-origin helper (WP-003) is re-spec'd** to call the
  `ConversationIdentity` port and emit `conversation=<threadId>; turn=<n>` — the
  grammar is unchanged, only the source of the two values changes.
- **The inferred path (WP-004 scope) gains the shared derivation + per-transcript
  indexing**, retiring the #23 TODO. A characterisation test pins current
  inferred output first (REORGANISE discipline) before the per-transcript change.
- **Live integration becomes a single additive WP later** (new adapter behind
  the port + its Armor) with no change to anything decided here.
