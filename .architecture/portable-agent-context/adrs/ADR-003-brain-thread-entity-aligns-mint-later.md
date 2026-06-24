# ADR-003 — The brain Thread entity aligns with the platform Thread; minted as a candidate now, governed-minted later

> **Status:** accepted · **Date:** 2026-06-24 · **Change:** CH-GJ9KQR
> **Decision-makers:** engineering-architect, grounded on the sulis-brain
> agent's verdict (Working Set 2026-06-24T15:13:02Z)

## Context

The brain (`.brain/` graph) holds durable Opportunity / Requirement / Decision
/ Design / Scenario entities. The portable-context change introduces three
candidate brain concepts:

1. A **Thread** (the durable conversation record) — would be a new entity.
2. The **raw message log** — a high-volume per-message record stream.
3. The **context payload** — the assembled rich view.

The sulis-brain agent ruled on the shape of each. This ADR records and locks
that ruling, and the **sequencing discipline** around minting.

## Decision

- **Thread = a new brain ENTITY** — a sparse **Activity-class node**, a peer of
  `lifecyclerun` / `testrun`. It ties a conversation → its bound change →
  provider → decisions → the message-log reference. Its fields **mirror /
  reference the platform Thread** (ADR-001) so the brain entity and the
  platform entity cannot diverge. Provider is modelled by **reusing the
  existing `Tool` entity** — we do **not** mint a new "provider" entity type.
  We pick **one term: "thread"** (not session + thread). Resume is modelled as
  a `resumed_from` self-reference on Thread.

- **Raw message log = a RUNTIME-FACT store the graph REFERENCES** — **never one
  brain node per message.** The brain Thread node carries a reference
  (a store key / path) to the durable message log; the messages themselves live
  in the runtime store (ADR-002), not as graph nodes. (Per
  `sulis-brain:classify-candidate`: high-volume runtime data is a referenced
  store, not minted nodes.)

- **Context payload = a GENERATED ARTIFACT** — a `render-context-payload`
  assembler/query, **not stored structure.** It is produced on demand from the
  Working Set + brain entities + brief + the structured summary; it is not a
  minted entity and not a persisted record (beyond an optional cache).

- **Minting discipline (the load-bearing part):** the Thread entity is
  **captured as a mint CANDIDATE now** and **governed-minted LATER** — after
  (a) this design settles the log schema and (b) the failover *consumer* of
  portable context is real. **Do not mint ahead of use** (the Working-Set
  sequencing lesson: minting an entity before there is a consumer that reads it
  produces a dead node). This change records the candidate in
  `.sulis-mint-requests/`; the governed mint runs as a separate, later step.

## Rejected alternatives

- **Mint Thread now, eagerly.** Rejected per the mint-ahead-of-use lesson: the
  failover consumer is out of scope, and the log schema is still being settled
  by this very change; minting now risks a node whose shape the
  implementation then contradicts.
- **One brain node per message.** Rejected: the message log is high-volume
  runtime data (potentially thousands of records per thread); modelling each as
  a graph node would bloat the graph and conflate runtime facts with durable
  decisions. The store-the-graph-references pattern is the brain's convention
  for this.
- **Mint a new "provider" entity.** Rejected: the existing `Tool` entity
  already models an external capability the system invokes; a provider is a
  Tool. Reuse over rebuild (EP-03).

## Consequences

- This change ships a **mint-candidate record** for Thread (under
  `.sulis-mint-requests/`), aligned field-for-field to the platform Thread, and
  a **runtime-store reference convention** (how a Thread node will point at its
  message log). It does **not** mint the entity.
- The assembler is built as a query/render step (the GENERATED ARTIFACT), so it
  has no persistence of its own to govern.
- When the failover consumer lands, the governed mint runs against a log schema
  this change has already proven — the entity arrives with a real reader.
