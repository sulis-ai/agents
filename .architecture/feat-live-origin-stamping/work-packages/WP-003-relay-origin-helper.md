---
wp: WP-003
change_id: 01KTHP2NYQ1A3WHPJD75VP31NT
title: Conversation-identity port + local adapter, and the relay-origin helper (Thread id + Message ordinal)
kind: backend
primitive: expand-create
group: expand
status: pending
dependsOn: [WP-001]
estimated_token_cost: { input: ~18k, output: ~7k }
verification:
  adapter: backend
  artifact: apps/cockpit/server/tests/relayOrigin.test.ts
---

# WP-003 — Conversation-identity seam + relay-origin helper (Thread id + Message ordinal)

## Context

TDD §2/§4/§5 (components 4 + 4a), ADR-016 (conversation = Thread id, turn =
Message ordinal), ADR-018 (the `ConversationIdentity` seam; model-only now). The
relay must turn a resolved session into the assisted `originEnv`
`SULIS_ORIGIN="assisted; conversation=<threadId>; turn=<n>"`, where the values are
modelled on the communication service's Thread/Message shapes — **but derived
locally** (no cross-service call this change; ADR-018 D1).

Isolated as two small units so the identity rule and the env formatting are
testable without an HTTP server or a child process. The grammar is #216's,
unchanged — only the computed values change.

## Contract

### 1. The domain-owned port (the seam)

`apps/cockpit/server/ports/ConversationIdentity.ts` (NEW):

```ts
export interface ThreadIdentity {
  /** A communication-service Thread id ("thread_<…>" shape). */
  threadId: string;
  /** 1-based Message ordinal for the in-flight turn (existing count + 1). */
  turn: number;
}

export interface ConversationIdentity {
  /** Thread identity for a resolved session, or null when none can be derived
   *  (fresh session / no transcript) — caller spawns unstamped. */
  forResolvedSession(
    resolution: SessionResolution,
    transcript: TranscriptMessage[],
  ): ThreadIdentity | null;
}
```

### 2. The local adapter (the only implementation in this change)

`apps/cockpit/server/adapters/LocalTranscriptConversationIdentity.ts` (NEW),
read-only, no network (ADR-003 / ADR-018 D1):

- **threadId** = a deterministic `thread_`-shaped id over the resolved session's
  stable session identity (the stem of `resolution.session.lastSessionRef`).
  Absent `lastSessionRef` (fresh) → `forResolvedSession` returns `null`.
  - It carries the `thread_` prefix so the recorded value already looks like a
    communication-service Thread id (integration-ready; ADR-016).
  - It is constant across a thread's turns (same stem → same id) and distinct
    per thread (distinct stem → distinct id).
  - The session→thread derivation MUST be the **single shared helper** that the
    inferred path also uses in WP-004 (EP-03 — one rule, two readers; recorded
    and inferred render the SAME id for the same file). Put the rule in one
    place (e.g. `lib/threadIdentity.ts`) and call it from both.
- **turn** = `groupTurns(transcript).filter(isTurn).length + 1` — the local
  stand-in for `Thread.message_count + 1` (ADR-016), reusing the shared
  `apps/cockpit/shared/groupTurns.ts`.
- Best-effort: any failure (parse error, missing fields) → `null` (degrade to
  inferred). Never throws.

### 3. The relay helper (formats the env)

`apps/cockpit/server/lib/relayOrigin.ts` (NEW):

```ts
/** Derive the assisted origin env for a resolved session, or null when it
 *  cannot be derived — caller spawns unstamped. Uses ConversationIdentity. */
export function assistedOriginEnv(
  identity: ConversationIdentity,
  resolution: SessionResolution,
  transcript: TranscriptMessage[],
): Record<string, string> | null;
```

- Calls `identity.forResolvedSession(...)`; on `null` → return `null`.
- **value** = the exact `SULIS_ORIGIN` body grammar #216's `parse_origin_env`
  accepts, with the new computed values:
  `assisted; conversation=<threadId>; turn=<n>` under key `SULIS_ORIGIN`.
- Does NOT re-implement #216's formatting beyond emitting the accepted string
  shape; grammar conformance is locked by WP-006's round-trip test.

**Whose interface is the public face?** The cockpit's own `ConversationIdentity`
port — this is EXPAND-Create (a domain-owned port + a local adapter), not a
SUBSTITUTE-Wrap of the communication service (ADR-018 D1; mirrors `SessionBridge`
per ADR-002). The future live adapter is a separate WP.

## Definition of Done

### Red
- [ ] `relayOrigin.test.ts` (helper + local adapter):
      - resolvable transcript `…/<sessionid>.jsonl` → `threadId` has the
        `thread_` shape AND is a pure function of `<sessionid>` (same stem →
        same id; asserted via the shared `threadIdentity` helper).
      - N existing turns in the fixture → `turn === N+1` (Message ordinal).
      - two distinct transcripts → two distinct `threadId`s (multi-session gap).
      - fresh resolution (no `lastSessionRef`) → `null` (unstamped → inferred).
      - emitted value parses to `{kind:'assisted', conversation:<threadId>,
        turn:<n>}` shape and `turn` round-trips as an integer (grammar fit).
      Fails (port/adapter/helper absent).

### Green
- [ ] Add `ConversationIdentity` port + `ThreadIdentity` type.
- [ ] Implement `LocalTranscriptConversationIdentity` per the contract, reusing
      `groupTurns` and the shared `threadIdentity` derivation helper.
- [ ] Implement `assistedOriginEnv` per the contract. Boring, explicit, no `any`.

### Blue
- [ ] No control-char path: `threadId` is derived from a session id, but assert
      the helper does not strip/transform the env value — it passes it as-is for
      #216's parser to guard (no second sanitiser).
- [ ] The session→thread derivation lives in ONE shared helper (EP-03); WP-004's
      inferred path imports the same helper. Assert no duplicated rule.
- [ ] `vitest run relayOrigin` green; typecheck green; `check-read-only.sh`
      passes (new port + adapter are pure reads under allow-listed paths).
