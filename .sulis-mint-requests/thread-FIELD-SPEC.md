# Field-spec — `Thread` (mint CANDIDATE, sparse Activity-class entity)

> **Status:** CANDIDATE descriptor — for the LATER governed mint, **not minted
> now** (see `mint-candidate-thread.md` and ADR-003 for the mint-later
> discipline and its two preconditions).
> **Change:** CH-GJ9KQR · **Recorded:** 2026-06-24
> **Shape alignment:** platform thread-sdk ONTOLOGY (ADR-001) +
> the WP-001 vendor-neutral contract types. Activity base-field shape mirrors
> `lifecyclerun` (its sibling Activity).

---

## 0. Shape summary

`Thread` is a **sparse** node: it carries the Activity envelope, a small set of
identity/state fields that **mirror the platform Thread** (ADR-001), and a set
of **reference edges** to the change, the provider (Tool), the runtime message
log, the lifecycle run(s), the decisions it produced, and its predecessor
thread. It deliberately does **not** carry message bodies or the assembled
payload — those are a referenced runtime store and a generated artifact
respectively (ADR-003).

## 1. Fields

`Thread` carries the **foundation bitemporal envelope** (identical to every
entity, identical to `lifecyclerun`): `id`, `sys_status`, `valid_from`,
`valid_to`, `confidence`.

| Field | Type | Required | Notes / grounding |
|---|---|---|---|
| `id` | `string` pattern `^dna:thread:[0-9A-HJKMNP-TV-Z]{26}$` | ✅ | ULID, Crockford base32 — mirrors the `lifecyclerun` id pattern. |
| `sys_status` | enum `active\|archived\|deleted\|purged` | ✅ | foundation envelope (record lifecycle — is this ROW live). |
| `valid_from` | date-time, nullable | — | bitemporal business-truth window start. |
| `valid_to` | date-time, nullable | — | bitemporal business-truth window end. |
| `confidence` | number 0..1 | — | instance reliability. |
| `platform_id` | string, nullable | — | the platform Thread id this mirrors (ADR-001 `Thread.platform_id`). Null for a local-only thread; set when bound to a platform thread. |
| `topic` | string, nullable | — | mirrors platform `Thread.topic` — the conversation subject. |
| `activity_summary` | string, nullable | — | mirrors platform `Thread.activity_summary` — the rolled-up state. |
| `participant_count` | integer, nullable | — | mirrors platform `Thread.participant_count`. (ThreadParticipant detail lives in the runtime ThreadMemory, ADR-001 — not as graph nodes.) |
| `started_at` | date-time | ✅ | lifecycle timestamp — when the thread opened (mirrors platform `created_at`; aligns with `lifecyclerun` Activity start). |
| `updated_at` | date-time, nullable | — | mirrors platform `Thread.updated_at` — last append/checkpoint. |

### Required set (Thread)
`id`, `sys_status`, `started_at`.
(Identity/state fields mirror the platform Thread and are nullable where the
platform allows a thread to exist before they resolve.)

### prov_constraints
```
{ "is_a": "prov:Activity",
  "wasInformedBy": "the lifecyclerun(s) the conversation occurred within (in_run)",
  "wasAttributedTo": "(later) the actor/participants — carried via ThreadMemory participant_context, not minted as nodes" }
```

### what_its_not (the antithesis — scope-anchored)
> NOT the cockpit **session** — that is the per-change live PTY *process* that
> *writes into* the thread (in-memory `EventLog`, process-bound lifetime;
> ADR-004). A Thread is the **durable record** that survives process death.
> NOT a `lifecyclerun` — that is a fine-grained step-run Activity; a Thread is
> the durable conversation record that lifecycle runs occur within. NOT the
> **message log** — the high-volume message bodies live in the runtime store,
> referenced by `message_log_ref`, never as graph nodes. NOT the **context
> payload** — that is a generated artifact (render/query), not a Thread field.
> NOT a new **provider** entity — the provider is the existing `Tool` entity.

`x-schema-org-extends`: **`schema:Conversation`** (the durable conversation
record), with the Activity envelope mirroring `lifecyclerun`.

## 2. Relationship edges

| Edge | Type / target | Required | Meaning |
|---|---|---|---|
| `for_change` | `^dna:change:[0-9A-HJKMNP-TV-Z]{26}$` → `Change` | ✅ | the bound change. One thread per change today (same key the session-manager uses, ADR-004); the schema permits more later. |
| `on_provider` | `^dna:tool:[0-9A-HJKMNP-TV-Z]{26}$` → **`Tool`** (existing) | — | the provider the conversation ran on, modelled by **reusing the `Tool` entity** — **no new "provider" entity type** (EP-03; ADR-003). Nullable until the provider resolves. |
| `message_log_ref` | string (runtime-store key/path) | — | reference to the durable append-only message log in the runtime store (ADR-002 / WP-001 pinned root `~/.sulis/changes/{change_id}/threads/`). **A store reference, NOT a graph node per message** (ADR-003). |
| `in_run` | array of `^dna:lifecyclerun:[0-9A-HJKMNP-TV-Z]{26}$` → `lifecyclerun` | — | the lifecycle run(s) the conversation occurred within (`prov:wasInformedBy`; Activity-nesting). |
| `produced` | array of `^dna:decision:[0-9A-HJKMNP-TV-Z]{26}$` → `Decision` | — | the durable decisions the conversation produced (the brain's existing `Decision` entity). |
| `resumed_from` | `^dna:thread:[0-9A-HJKMNP-TV-Z]{26}$` → `Thread` (**SELF-EDGE**) | — | the predecessor thread a resumed conversation continues from (ADR-003/ADR-004). Null for a root thread. ABox invariant: the resume chain must be acyclic (a DAG) — not schema-enforceable, a ref-integrity concern. |

## 3. Deliberately EXCLUDED (referenced, not minted)

| Excluded | Why | Where it lives instead |
|---|---|---|
| message bodies / `messages[]` | high-volume runtime data — one node per message would bloat the graph (ADR-003) | the runtime store, via `message_log_ref` |
| the assembled context payload | a GENERATED ARTIFACT (`render-context-payload` query), not stored structure (ADR-003) | produced on demand from ThreadMemory + brain entities |
| `ThreadParticipant` rows | per-conversation runtime detail, not durable graph truth | platform / runtime ThreadMemory `participant_context` (ADR-001) |
| a new `provider` entity | a provider is a `Tool` — reuse over rebuild (EP-03) | the existing `Tool` entity, via `on_provider` |

## 4. Mint discipline (when, not now)

The governed mint runs **later**, as a separate step, **only after**:

1. the durable log schema this change is settling has landed (the runtime store
   + the WP-001 contract are proven), and
2. the failover **consumer** that reads portable context is real (out of scope
   for this change).

Until both hold, this descriptor is the durable record of *what* to mint. See
ADR-003 and `mint-candidate-thread.md` for the full rationale (the
mint-ahead-of-use / dead-node anti-pattern this defers around).

## 5. Schema work for the LATER mint (cross-repo, recorded — not done now)

- **NEW (later):** add `Thread` to the source entities ontology → compile
  `thread.schema.json`, grounded against the platform thread-sdk ONTOLOGY
  (ADR-001) so the brain entity and platform entity cannot diverge.
- **REUSE (no new type):** `on_provider` targets the existing `Tool` entity.
- **REFERENCE (no per-message nodes):** `message_log_ref` is a runtime-store
  reference; the message log is not minted.
- **GLOSSARY (later):** Thread / session / lifecyclerun with "NOT the same as"
  cross-links (the term decision in ADR-001 / ADR-004).
