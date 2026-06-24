# Mint CANDIDATE — `Thread` (the durable conversation record, an Activity-class entity)

> **Status:** CANDIDATE — captured now, **NOT minted now.** Governed-minted
> LATER, after the two preconditions below hold. This file is a candidate
> descriptor only; it introduces **no** brain entity type and **no** schema
> change.
> **Change:** CH-GJ9KQR (portable-agent-context) · **Recorded:** 2026-06-24
> **Governing decision:** ADR-003 (brain Thread aligns; minted later)
> **Aligned to:** ADR-001 (platform Thread model) · ADR-004 (thread vs cockpit session)
> **Contract it references:** WP-001 (Thread/Message/Memory + payload contract)

---

## Why this is a CANDIDATE and not a mint (the load-bearing part)

Per ADR-003 and the sulis-brain agent's verdict (Working Set
2026-06-24T15:13:02Z), the `Thread` entity is **captured as a mint candidate
now** and **governed-minted later** — deliberately **not** minted by this
change. Minting waits on **two preconditions**:

1. **The log schema settles.** This change is the one *settling* the durable
   message-log shape (the runtime store, ADR-002, and the WP-001 contract).
   Minting a brain entity whose `message_log_ref` semantics the implementation
   is still proving would risk a node the implementation then contradicts.

2. **The failover consumer is real.** The provider-failover consumer that would
   *read* portable context (the load-bearing journey that justifies a durable,
   provider-independent Thread node in the graph) is **out of scope for this
   change**. Minting an entity before a consumer reads it produces a **dead
   node** — the mint-ahead-of-use anti-pattern the Working-Set sequencing
   lesson warns against.

When both hold, the governed mint runs as a **separate, later step** against a
log schema this change has already proven, and the entity arrives with a real
reader. This file is the durable record of *what* to mint *then*.

---

## What `Thread` is (one paragraph)

A **Thread** is the **durable conversation record** for a bound change: the
append-only message log plus the versioned context payload (ThreadMemory) that
survive process death, restart, crash-resume, and — later — a provider switch.
It is the authoritative persisted record that the cockpit's live, in-memory
session `EventLog` mirrors into (ADR-004). It is **not** the cockpit "session"
(the per-change PTY *process* that writes into it). One canonical term —
**"thread"**, never "session" — for the durable record.

## Classification

- **Layer / kind:** a new brain **ENTITY**, a **sparse Activity-class node**
  (`prov:Activity`), a **peer of `lifecyclerun` / `testrun`**. It records THAT
  a conversation happened and ties it to its change, provider, decisions, and
  message log — it does **not** hold the high-volume message bodies (those are
  a referenced runtime store, see below).
- **What it is NOT a mint of:** the **raw message log** is a RUNTIME-FACT store
  the graph *references* — **never one brain node per message** (ADR-003). The
  **context payload** is a GENERATED ARTIFACT (a render/query step), not a
  stored entity. Neither is minted; only the sparse Thread node is the
  candidate here.

## Canonical-term decision

**"thread"**, not "session." The founder's call and the platform's term
(ADR-001). The cockpit's existing per-change PTY process keeps the internal
name "session" (the live *writer*); the durable *record* is the "thread"
(ADR-004). Founder-facing language and the new brain entity say **thread**.

## Alignment discipline (cannot diverge)

The Thread entity's fields **mirror / reference the platform Thread**
(ADR-001 — `~/dev/repos/platform/features/thread-sdk/ONTOLOGY.jsonld`) so the
brain entity and the platform entity cannot drift. Sulis-specific context
(bound `change_id`, provider identity) is carried via reference edges, not by
renaming a platform field. Field detail is in the companion
**`thread-FIELD-SPEC.md`**.

## Relationships (the edges this candidate will introduce when minted)

| Edge | Target | Meaning |
|---|---|---|
| `for_change` | `Change` | the bound change this thread's conversation belongs to (today one thread per change — the same key the session-manager uses). |
| `on_provider` | **`Tool`** (existing entity — **reused, NOT a new provider type**) | the provider the conversation ran on. A provider is a Tool (an external capability the system invokes); EP-03 reuse-over-rebuild, per ADR-003. |
| `message_log_ref` | runtime-store reference (key/path, **not** a graph node) | pointer to the durable append-only message log in the runtime store (ADR-002). The messages live in the store, never as graph nodes. |
| `in_run` | `lifecyclerun` | the lifecycle run(s) the conversation occurred within (Activity-nesting, `prov:wasInformedBy`). |
| `produced` (decisions) | `Decision` | the durable decisions the conversation produced (the brain's existing Decision entity). |
| `resumed_from` | `Thread` (**SELF-REF**) | the predecessor thread a resumed conversation continues from (ADR-003/ADR-004 — restart/resume reuses/chains the Thread). Null for a root thread. |

## Deliberately referenced, NOT minted

- **Message bodies** → runtime store via `message_log_ref` (high-volume runtime
  data; ADR-003 store-the-graph-references pattern).
- **Context payload** → a `render-context-payload` GENERATED ARTIFACT (ADR-003);
  no persisted entity.
- **Provider** → the existing `Tool` entity (no new "provider" entity type).

## Cross-links

- **ADR-003** — `.architecture/portable-agent-context/adrs/ADR-003-brain-thread-entity-aligns-mint-later.md`
  (the mint-candidate-now / mint-later ruling this file records).
- **ADR-001** — `.architecture/portable-agent-context/adrs/ADR-001-adopt-platform-thread-model.md`
  (the platform Thread shape these fields mirror).
- **ADR-004** — `.architecture/portable-agent-context/adrs/ADR-004-thread-vs-cockpit-session-relationship.md`
  (thread = durable record; session = live PTY writer; the term decision).
- **WP-001 contract** — `.architecture/portable-agent-context/work-packages/WP-001-thread-context-contract.md`
  (the Thread/Message/Memory + payload contract these fields conform to).
- **Companion field-spec** — `thread-FIELD-SPEC.md` (this directory).
