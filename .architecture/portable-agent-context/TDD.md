# Technical Design — Portable agent context (CH-GJ9KQR)

> **Status:** designed · **Tier:** M (see `SIZING.md`) · **Mode:** brownfield
> (extends the cockpit session-manager; no SRD — grounded on
> `.changes/create-portable-agent-context.SPEC.md`, the recon, the Working Set,
> and the platform thread-sdk model).
>
> **Reads first:** ADR-001..005 in `adrs/`. They carry the load-bearing
> rulings; this TDD references rather than restates them.

## 1. Conclusion (lead with the answer)

Give every spawned agent a **rich, vendor-neutral context payload by default**,
backed by a **Sulis-owned, durable, append-only message log** the cockpit owns
— so a thread can be resumed, or restarted on any provider, from **our**
context, never the provider's transcript files. The raw full record is reached
**on demand** through a denyable MCP tool. The store, payload, and discovery
operations conform to the **platform thread-sdk contract** (ADR-001) but run
**local-first** today (ADR-002 hybrid), composing with the hosted platform
later behind the same contract.

The change is **three new pieces over existing seams** — it does not
re-architect the session manager:

1. a **durable thread/message/memory store** (new persistence surface);
2. a **context-payload assembler** (a generated view, not stored);
3. a **discovery seam** (the rich pointer + a read-only MCP tool).

All three are fed by, and reuse, the existing provider-neutral `events.Event`
vocabulary, the `ProviderAdapter` brief-injection seam, the Working Set, and
the brain.

## 2. Scope boundary (what this does NOT touch)

- **Not** the second provider / failover policy — this is the enabler only
  (spec non-goal).
- **Not** ripping out Claude's transcript for the Claude path — we **add** our
  authoritative log; Claude resume still works.
- **Not** the remote/cloud cockpit deployment (parked).
- **Not** a new founder-facing raw-log UI — raw is for the *agent's* discovery.
- **Not** semantic retrieval over the log — relevance starts simple (bound
  change's entities + recency).

---

## 3. Form — Structural Integrity

### 3.1 Reused seams (Respect-Don't-Restate)

| Seam | Location | Role in this change |
|---|---|---|
| `events.Event` + three error categories | `_session_manager/events.py` | The provider-neutral record vocabulary fed into the durable log. **Reused verbatim** — no second decode path. |
| `ProviderAdapter` Protocol + `SessionSpec` | `_session_manager/adapter.py` | The injection seam. The payload reaches a (re)spawned agent through the brief argv (`SessionSpec.brief_change_id`), exactly as the brief does today. |
| In-memory `EventLog` | `_session_manager/event_log.py` | Stays as the **live-tail / viewer** log (its current job). The durable store is a **second sink**, not a replacement (ADR-004). |
| Brief / `pre_prompt.txt` | `~/.sulis/changes/{id}/` | The delivery vehicle for the assembled payload (ADR-004/005). |
| Working Set | `sulis:working-set` / `.changes/*.WORKING-SET.md` | An input to the assembler — the why / decisions / rejected-with-rationale → ThreadMemory.exploration_journal. |
| Brain | `.brain/` | An input — the bound change's Opportunity/Requirement/Decision/Design/Scenario entities, selected by relevance. |
| safe-tools MCP pattern | `_safe_tools_mcp.py` | The shape the discovery tool follows (one parameterised, denyable, change-scoped tool over a wrapped library). |

### 3.2 New components (hexagonal — ports the cockpit domain owns)

```
            ┌──────────────────────────────────────────────────┐
            │  Session pump (existing)  ── decode → Event ──┐    │
            └───────────────────────────────────────────────┼────┘
                                                             │ (append, ADR-004)
                              ┌──────────────────────────────▼─────────────────┐
   brief argv (ADR-004/005)  │   ThreadStore  (PORT: ThreadStore)               │
   ◀── assembled payload ────│   - append_message(thread_id, ThreadMessage)     │
                             │   - get_thread / get_memory / get_messages       │
                             │   - put_memory(thread_id, ThreadMemory)          │
                             │   append-only messages + versioned memory        │
                             └───────────────▲──────────────────┬──────────────┘
                                             │                  │
        ContextPayloadAssembler  ────────────┘                  │ (read-only)
        (GENERATED ARTIFACT, ADR-003):                          │
          assemble(thread_id, tier) → ContextPayload   ◀────────┘
            from: brief + Working Set + brain entities
                  + structured summary (from the log)

        ⚠ The `◀── assembled payload ──` brief-injection arrow above is the
        LIVE WIRING delivered by WP-009 (the manager's composition root
        constructs the assembler with REAL Working Set + brain readers and
        composes the rendered payload into the change's pre_prompt.txt sidecar at
        the spawn/resume seam). WP-003/004/007 built + component-tested the
        assembler; WP-009 connects it to the live `SessionManager` spawn/resume
        path. Until WP-009 ships, the assembler is reachable only from tests.

        Discovery seam (ADR-005):
          - payload pointer (inline, rich-by-default)
          - thread_context MCP tool (read-only, raw-on-demand)
```

**Ports the domain owns** (these are **EXPAND-Create**, not wraps — the public
face is the interface *we* define; see `change-primitives.md` Ports-vs-Wrappers):

- **`ThreadStore`** — the persistence port. One **local adapter** today (the
  durable file/sqlite store under `~/.sulis/changes/{change_id}/threads/` —
  exact backing chosen in the contract WP); the **hosted communication-service
  REST adapter** is the future second adapter behind the same port (ADR-002).
- **`ContextPayloadAssembler`** — a pure query/render component (no persistence
  of its own). Depends inward only on the `ThreadStore` read ops + the Working
  Set reader + the brain reader. Returns a `ContextPayload` value.
- **`thread_context` MCP tool** — the read-only adapter that exposes the store's
  read ops to the agent (ADR-005).

**Dependency direction (MEA-01 / WPB-01):** the assembler and the store types
depend only on the provider-neutral `events`/thread types — never on a
provider, a subprocess, or the cockpit web layer. The local store adapter is
the only place that touches the filesystem/db.

### 3.3 The contract (ADR-001 shape; CONTRACT_FIRST lightweight tier)

Transport-agnostic schema layer (CF-02), conforming to the platform thread-sdk
`ONTOLOGY.jsonld`. Types (field-for-field with the platform):

- `Thread{ id, platform_id, topic?, activity_summary?, created_at, updated_at,
  participant_count, resumed_from? }` — `resumed_from` is our additive resume
  chain (ADR-003); `platform_id="local"` today (ADR-002).
- `ThreadParticipant{ id, thread_id, participant_id, participant_type:
  user|studio_agent, joined_at, role? }`.
- `ThreadMemory{ thread_id, version, content: ThreadMemoryContent, created_at,
  updated_at }` — versioned, incremented on each checkpoint regeneration.
- `ThreadMemoryContent{ messages[], exploration_journal[], participant_context }`.
- `ThreadMessage{ id, participant_id, participant_type, content,
  role: question|answer|observation|decision|null, created_at, order }` —
  `order` is our additive stable-ordering field (the log is offset-ordered).
- `ExplorationJournalEntry{ type: question|answer|pattern_detected|
  decision_captured, content, created_at, participant_id?, metadata? }`.

Operations (the read surface = the discovery seam; the write surface = the
session pump's sink):
- write: `append_message`, `put_memory` (producer-side, session pump).
- read: `get_thread`, `get_memory`, `get_messages(since?, limit?)` — the
  platform's `getThread` / `getThreadMemory` + a message-slice read for the
  discovery seam.

Errors: the three universal categories (CF-03), already modelled in
`events.py` (`ProtocolError` / `ExpectedError` / `InternalError`) — **reused**.
`PermissionError` (NFR-SEC05) is carried for the future hosted binding; not
enforced on the loopback path (ADR-002).

---

## 4. Armor — Operational Hardening

| Concern | Decision | Source |
|---|---|---|
| **Append-only + ordered integrity** | The message log is write-once-append; never rewritten. Ordering is the existing offset convention (monotonic, stable). The store rejects out-of-order or mutating writes (ExpectedError). | spec Constraint; reuses `event_log` offset semantics |
| **No secret leakage on a new persistence surface** | Redaction runs **on write** to the durable store, reusing the existing `_secret_patterns` scrub the outbound path already uses. The durable log is a new content-persistence surface → the same anonymiser/redaction posture applies before bytes land. | spec Constraint; reuses `_secret_patterns` |
| **Credential exclusion** | Unchanged — `spawn_env.child_spawn_env` already keeps credentials out of the agent's env; the assembled payload is built from already-redacted sources. | reuses `spawn_env.py` |
| **At-rest scope** | The store lives under `~/.sulis/changes/{change_id}/threads/` (loopback, single-founder, OS file perms) — the same trust boundary as the brief and Working Set today. No new network surface (ADR-002 local binding). | ADR-002 |
| **Discovery tool is denyable + scoped** | `thread_context` is a denyable MCP identity, read-only, change-scoped server-side (the founder can withhold it; it cannot read another change's thread). | ADR-005; reuses safe-tools scoping |
| **Token-budget enforcement** | The assembler enforces the tier budget (lean/standard/full) as a **hard constraint** — standard tier ships the structured summary, never the raw dump; an over-budget assembly degrades to a tighter tier rather than overflowing. | spec Acceptance |
| **Observability** | Append + assemble + each `thread_context` op emit a structured log line carrying `change_id` / `thread_id` / op / outcome (mirrors the platform's NFR-A04 audit fields), consistent with the session-manager's existing event logging. | reuses session-manager logging |

This change adds **no outbound network call**, so circuit-breaker / retry /
timeout primitives are **N/A in scope** (the deferred hosted-service adapter
will own those — flagged for that future WP, not this change).

---

## 5. Proof — Verification Protocol

| Subject | Test | Level |
|---|---|---|
| `ThreadStore` port | Contract test run against the **in-memory adapter AND the local file/db adapter** (shared contract test — MEA-09: no mocks at integration). | contract + integration |
| Append-only invariant | A characterisation/integration test asserting a rewrite/out-of-order write is rejected. | integration |
| Redaction-on-write | A test feeding a token-shaped secret through `append_message` and asserting the stored bytes are scrubbed. | integration |
| `ContextPayloadAssembler` | Tests asserting each tier stays within budget; standard tier carries the summary not the raw dump; payload is vendor-neutral (no Claude-JSONL structure). | unit |
| **Provider-independent resume — component level** | Integration test: run a thread, capture decisions, end it, **make the provider transcript unavailable**, assemble the payload → assert the rich payload and the raw log are intact from **our** store. Drives the assembler directly (WP-007 `test_provider_independent_resume.py`). | integration / drive |
| **Provider-independent resume — LIVE path** (the load-bearing acceptance) | Integration test driving the real `SessionManager` spawn/resume path with `spec.brief_change_id` set, the durable store factory pointed at a tmp store, a real `.changes/*.WORKING-SET.md` + a real brain entity present, and the provider transcript unavailable → **observe the rich payload reaching the brief** (the `pre_prompt.txt` / argv element the adapter resolves), carrying REAL Working Set + brain content (not empty-lambda output), within the standard-tier budget, vendor-neutral. (WP-009 `test_live_resume_injection.py`.) **This is the live-path acceptance — a live-path observation, not a component call.** | integration / drive |
| `thread_context` MCP tool | Conformance test (mirrors `test_safe_tools_mcp_contract.py`): read-only, change-scoped, three-category errors, ops match the contract read surface. | contract |
| OpenAI-key redaction-on-write | A test feeding a realistic `sk-proj-…` / legacy `sk-…` OpenAI key through `append_message` and asserting the stored bytes are scrubbed (the verified `_secret_patterns` blind spot). (WP-010.) | unit + integration |
| Seam-close (CF-12) | The contract WP + producer + consumer reaching done triggers the real-data drive over the covering Scenarios. **The headline provider-independent-resume Scenario is closed at the LIVE level by WP-009**, not the component-level WP-007 drive (which a `/sulis:prove` reality check found exercised the assembler directly, not the live system). | seam-close |

---

## 6. Component → Work Package map

| Component | Primitive | WP kind |
|---|---|---|
| Thread/Message/Memory contract (schema + errors + stubs + payload schema) | EXPAND-Create | `contract` (FIRST) |
| `ThreadStore` local adapter + append-only + redaction-on-write | EXPAND-Create | `backend` |
| `ContextPayloadAssembler` (tiered, vendor-neutral) | EXPAND-Create | `backend` |
| Session-pump durable-append sink + resume payload-seed | REINFORCE-Instrument over existing pump | `backend` |
| `thread_context` MCP discovery tool (read-only) | EXPAND-Create | `backend` |
| Cockpit raw-view re-point (optional, behind the same read ops) | SUBSTITUTE-Strangle (transcript read → store read) | `frontend` |
| Integration: mock→real + conformance + resume drive (component level) | — | `composite` |
| Thread mint-candidate record (no mint) | — | `docs` |
| **Live assemble→inject resume wiring** (manager spawn/resume seam + real Working Set + brain readers) | REINFORCE-Instrument over the existing spawn/pump path | `backend` (WP-009) |
| **OpenAI-key scrub on write** (widen the shared secret catalogue) | REINFORCE-Harden | `backend` (WP-010) |

See `work-packages/INDEX.md` for the sequenced graph.

> **Remediation note (2026-06-24).** A `/sulis:prove` consumer-level reality
> check found the headline capability ("resume recovers rich context from OUR
> store") was built as components but NOT connected into the live system — the
> §3.2 brief-injection arrow was designed but never wired into
> `SessionManager`. WP-009 (live wiring) + WP-010 (OpenAI-key scrub) close the
> gaps; the live-path acceptance for the headline moves from WP-007 (component
> drive) to WP-009 (live `SessionManager` drive).

---

## 7. Verification Plan

<!-- VERIFICATION_QUESTIONS source: plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md v1.0.0 -->

> No SRD `## Verification Plan` exists (no `.specifications/` SRD for this
> change); this section is authored from the spec's Verification Plan journeys
> and concretised to TDD-level artifacts. `kind` for the change is mixed
> (backend + frontend + contract); per-WP adapters apply per kind.

### 7.1 User-observable behaviour being verified
Provider-independent resume + every-message tracking + raw-on-demand + budget +
vendor-neutral shape (the five spec journeys). The load-bearing one:
**resume recovers from our store with the provider transcript unavailable.**

### 7.2 Verification environment(s)
Local (the cockpit runs on `127.0.0.1`); CI for the unit/contract tests. No
hosted/staging environment in scope (ADR-002 local binding).

### 7.3 Bootstrap-from-zero
A fresh clone at the merge SHA can: instantiate the `ThreadStore` local
adapter, append messages, assemble a payload, and run the `thread_context` tool
conformance test — with no external service. Bootstrap test: the contract WP's
in-memory-adapter contract test (`tests/.../test_thread_store_contract.py`).

### 7.4 Per-integration verification strategy
| Seam | Strategy | Classification | Concretion |
|---|---|---|---|
| `ThreadStore` port ↔ local adapter | shared contract test (in-memory + real adapter), no mocks | existing-in-this-change | `tests/unit/test_thread_store_contract.py` (concrete) |
| Session pump → durable sink | integration over the real pump + real store | existing-in-this-change | `tests/integration/test_durable_append_sink.py` (concrete) |
| Assembler → payload | unit, budget + vendor-neutral assertions | existing-in-this-change | `tests/unit/test_context_payload_assembler.py` (concrete) |
| `thread_context` MCP tool | MCP contract test, mirrors safe-tools | existing-in-this-change | `tests/unit/test_thread_context_mcp_contract.py` (concrete) |
| Hosted communication-service REST adapter | **deferred** — out of scope (ADR-002; remote parked) | deferred | `thread-store-rest-platform` (canonical need id) |

### 7.5 Per-kind verification adapter
- `backend` → pytest nodeids (paths above).
- `frontend` (optional re-point WP) → Vitest spec
  `apps/cockpit/client/src/api/useTranscript.test.ts` driving the store-backed
  read path.
- `contract` → the conformance + stub tests.

### 7.6 Infrastructure needs surfaced (deferred)
- `thread-store-rest-platform` — the hosted communication-service REST binding
  + test JWT/`platform_id` mapping. Deferred (ADR-002); not shippable in this
  change. Canonical need id follows `{noun}-{noun}-{vendor-or-scope}`.

---

## 8. Sizing Report

- **Tier:** M (computed sFPC ≈ 10–11, ASR = 7); confirmed. See `SIZING.md`.
- **TDD length:** within tier-M target (≈ 250–500 lines), achieved by
  referencing existing seams rather than re-deriving them (§3.1).
- **ADRs produced:** 5 (the brief mandated ≥ 4) — within the tier-M maximum;
  no circuit breaker triggered.
- **Authoritative sources referenced (not restated):** the platform
  `thread-sdk` ONTOLOGY + backend DESIGN; `events.py`, `event_log.py`,
  `adapter.py`, `spawn_env.py`, `_safe_tools_mcp.py`; CONTRACT_FIRST /
  WORK_PACKAGE standards.
- **Circuit breakers:** none triggered.
