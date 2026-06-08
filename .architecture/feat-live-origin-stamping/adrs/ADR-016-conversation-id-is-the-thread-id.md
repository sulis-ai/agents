# ADR-016 — The assisted conversation id is a communication-service Thread id; turn is the Message ordinal

- **Status:** accepted (rewritten 2026-06-07 — supersedes the prior
  "conversation-id is the transcript stem" decision; same ADR number)
- **Date:** 2026-06-07
- **Change:** CH-01KTHP · feat: live-origin-stamping
- **Deciders:** SEA
- **Extends:** ADR-012 (origin attribution is a domain-owned port), ADR-013
  (origin is stamped in the write paths)
- **Aligns to:** the platform communication service Thread/Message domain
  (`apps/api/sulis/services/communication/domain/models/{thread,message}.py`)
- **Paired with:** ADR-018 (the conversation-identity seam + likely→exact
  reconciliation)

> **Supersession note.** The first cut of this ADR made the assisted
> conversation id the *transcript stem* (the Claude Code session id), on the
> stated premise that recorded and inferred origin had to share an id scheme to
> reconcile. The founder has since steered the identity to be modelled on the
> platform's existing communication service so this change is integration-ready.
> Reading the actual cockpit code (`lib/originAttribution/correlate.ts`,
> `adapters/InferredOriginAttribution.ts`) also showed the reconciliation premise
> was wrong on mechanism (see ADR-018). Both facts retire the prior decision.

## Context

To stamp an **assisted** commit, the chat relay must supply a conversation id
and a turn index. The constraints (spec §Constraints) are unchanged: the id must
be stable across the turns of one chat thread, distinct per thread, and
collision-resistant. The trailer grammar owned by #216 is also unchanged:

```
Sulis-Origin: assisted; conversation=<id>; turn=<n>
```

`<n>` is parsed as an **integer** on both sides — Python
`_origin_stamp` / `format_trailer`, and the TS reader
`originFromTrailerValue` (`Number.parseInt(turn)`). This change touches **only
the computed values**, never the grammar.

The new requirement from the founder: model the assisted identity on the
platform communication service's canonical domain shapes, so the live identity
this change records is the same identity a future integration into that service
would use.

The communication service's shapes:

- `Thread(id="thread_<shortuuid>", owner_id, owner_type[user|agent],
  thread_type[direct|group|agent], status, message_count, platform_id,
  external_id, created_at, …)`
- `Message(id="msg_<shortuuid>", thread_id, author_id, role[user|assistant|
  system], content, created_at, …)`

## Decision

**The assisted `conversation` value is a communication-service Thread id
(`thread_<…>` shape); the `turn` value is the 1-based Message ordinal within
that thread.**

- **conversation = Thread id.** A chat thread maps to a `Thread`. The id carries
  the `thread_<shortuuid>` shape so it is the same identifier the communication
  service would assign. How the relay obtains the Thread id is the
  conversation-identity seam in ADR-018 (model-only now: derived
  deterministically from the resolved session; live later: read/created via the
  Thread repository port).
- **turn = Message ordinal (1-based) within the thread.** A chat turn maps to a
  `Message`. The ordinal is the message's position in the thread —
  equivalently `Thread.message_count` after the in-flight message, i.e.
  `existing_message_count + 1`.

### Why the ordinal, not the `msg_` id

The `turn=<n>` slot is integer-typed by the existing grammar on both language
sides. Three reasons make the **1-based ordinal** the boring, correct choice and
the `msg_<shortuuid>` id the wrong one for this slot:

1. **Grammar fit (decisive).** `originFromTrailerValue` does
   `Number.parseInt(fields.get("turn"))` and `_origin_stamp` treats turn as an
   int. A `msg_` id would not parse as `<n>` — using it would force a grammar
   change, which the steer explicitly forbids ("the trailer grammar accepts
   these values UNCHANGED").
2. **Stability / monotonicity.** The ordinal is monotonic and reproducible from
   the thread's message history; it is exactly `Thread.message_count`’s
   semantics. The `msg_` id is a random shortuuid — globally unique but not
   ordered, not derivable from position, and meaningless as a "turn number".
3. **Read-path parity.** The inferred read path already produces a 1-based
   ordinal (`InferredOriginAttribution.turnsFromMessages` → `idx + 1`). Keeping
   recorded and inferred on the same ordinal scheme means a file's displayed
   turn number does not jump when it flips likely→exact.

The `msg_` id is recorded *implicitly* — it is the message whose ordinal is
`<n>` within `thread=<id>`. If a future need arises to carry the opaque message
id as well, it is an additive trailer field, not a change to `turn=<n>`. Out of
scope here.

## Why this satisfies the constraints

- **Stable across one thread's turns** — all turns of a thread share one Thread
  id (the seam returns the same id for the same resolved session; ADR-018).
- **Distinct per thread** — distinct threads carry distinct `thread_` ids.
- **Collision-resistant** — inherited from the `shortuuid` Thread id namespace
  (the communication service's own guarantee), not invented here.
- **Integration-ready** — the recorded identity is byte-for-byte the shape the
  communication service uses, so wiring the live service later changes only
  *where the Thread id comes from* (the adapter behind the ADR-018 port), not
  the trailer, the stamper, the hook, or the read path.

## Alternatives considered

- **Keep the transcript stem (Claude session id) as the conversation id —
  rejected (superseded).** Not aligned to the communication service, so not
  integration-ready; the founder's steer requires the Thread shape. (The prior
  reconciliation argument for the stem is also moot — see ADR-018: inferred
  correlation is by timestamp window, not by id.)
- **conversation = Thread id, turn = `msg_<shortuuid>` id — rejected.** Breaks
  the integer `turn=<n>` grammar; non-monotonic; diverges from the inferred
  read path's ordinal. See "Why the ordinal" above.
- **Mint a fresh bespoke cockpit id — rejected.** Bespoke when an established
  platform convention (the Thread id) exists; CP-01 prefers the convention.

## Consequences

- **A fresh resolution** (no resumable session / no thread yet) has no Thread id
  to derive. The relay omits the assisted origin and the commit degrades
  gracefully to inferred (ADR-013 invariant); once the thread is resolvable,
  stamping begins from turn 1. Unchanged from the prior decision.
- **The turn ordinal is computed from the resolved transcript** via the shared
  `groupTurns` (`existing turns + 1`), which is the local stand-in for
  `Thread.message_count`. When the live service is wired (ADR-018), the ordinal
  comes from the Message repository's count for the thread instead — same value,
  authoritative source.
- **The displayed conversation id changes shape** (stem → `thread_`). For
  likely→exact to read consistently, the inferred path must render the same
  `thread_` id for the same file. That is ADR-018's reconciliation decision; it
  also closes the multi-session attribution TODO (#23) in
  `InferredOriginAttribution.loadTurns`.
- **No grammar / stamper / hook / read-path change.** Only the computed
  `conversation` and `turn` values change. #216 is consumed unchanged.
