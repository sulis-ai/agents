# TDD — Record change-origin exactly at commit time (live-stamping)

> **Change:** CH-01KTHP · feat: live-origin-stamping
> **Status:** designed
> **Sourced from:** `.changes/feat-live-origin-stamping.SPEC.md`
> **Tier:** S (see Sizing Report) · **Doctrine:** `WP_BACKEND_STANDARD`
> **Builds on (consume unchanged):** ADE epic #216 — `_origin_stamp.py`,
> `hooks/prepare-commit-msg`, `RecordedOriginAttribution`, `InferredOriginAttribution`,
> `spawnClaudeBridge`'s `originEnv` param.
> **New ADRs:** ADR-016 (conversation = communication-service Thread id, turn =
> Message ordinal), ADR-017 (port widening), ADR-018 (conversation-identity seam:
> model-only now / live later, + how likely→exact reconciles).
> **Aligns to:** the platform communication service Thread/Message domain
> (`apps/api/sulis/services/communication/domain/models/{thread,message}.py`) —
> the recorded identity is modelled on those shapes so this change is
> integration-ready (ADR-016/018).
> **Honoured (not re-decided):** ADR-003 (cockpit read-only), ADR-012 (origin is a
> domain-owned port), ADR-013 (stamping in the write paths, append-only, non-fatal).

## 1. Scope in one paragraph

#216 built the **receiving** end of change-origin (the hook that appends a
`Sulis-Origin:` trailer when `SULIS_ORIGIN` is set, the stamper/constructors, the
recorded>inferred read path). This change wires the **sending** end so the trailer
actually gets set, in both write paths: the cockpit **chat relay** (assisted) and
the **executor** (autonomous). The observable payoff is that the cockpit's origin
view flips a file/commit from **likely (inferred) → exact (recorded)**, and commits
from different chat conversations are attributed to their own conversation.

Nothing in #216 is re-implemented. The trailer format, the boundary guards
(`_has_control_char`, `parse_origin_env`), the hook, and the read adapters are
consumed as-is.

## 2. Form — Structural Integrity

The hexagonal shape already exists and is honoured:

- **The seam** is the existing `SessionBridge` port and its `spawnBridge` injection
  point (`apps/cockpit/server/ports/SessionBridge.ts`,
  `apps/cockpit/server/adapters/StreamJsonSessionBridge.ts`). This change **widens
  one port signature** (ADR-017) — it adds no new port, no new adapter, no new
  process-start site (ADR-003 preserved).
- **The relay** (`apps/cockpit/server/routes/chat.ts`) is the producer of the
  assisted `originEnv`; the bridge adapter is the consumer that hands it to the
  one sanctioned spawn. Producer/consumer contract pinned per CONTRACT_FIRST
  (§4, ADR-017).
- **Conversation identity is modelled on the communication service** (ADR-016):
  the assisted `conversation` value is a **Thread id** (`thread_<…>` shape) and
  the `turn` value is the **1-based Message ordinal** within that thread
  (`existing message count + 1`, i.e. `Thread.message_count + 1`). A new
  domain-owned `ConversationIdentity` port is the seam (ADR-018); in this change
  its only adapter, `LocalTranscriptConversationIdentity`, derives the identity
  **locally and read-only** from the resolved session (the stable session
  identity → a deterministic `thread_`-shaped id), with the turn count from the
  shared `groupTurns` (`apps/cockpit/shared/groupTurns.ts`). **No cross-service
  call this change** (ADR-018 D1 — model-only / integration-ready; the live
  Thread/Message repository adapter is a clean later WP). The session→thread
  derivation is a single shared helper (EP-03) so the inferred read path renders
  the SAME `thread_` id (ADR-018 D2).
- **The executor** stamps via the existing `prepare-commit-msg` hook the launcher
  already wires (`_terminal_launcher.py` `enable_origin_hook`). This change feeds
  the hook by exporting `SULIS_ORIGIN` at the executor's commit step. No new Python
  module; the executor agent/seam sets one env var consumed by an existing hook.

**Cross-language seam (TS ↔ Python).** The contract that bridges the two languages
is the **`SULIS_ORIGIN` env-var grammar** owned by #216:

```
SULIS_ORIGIN="assisted; conversation=<thread_id>; turn=<ordinal>"  # relay (TS) → hook (PY)
SULIS_ORIGIN="autonomous; run=<ulid>; confidence=<0..1>"          # executor → hook (PY)
```

The **grammar is #216's, unchanged** (the steer's hard constraint): `conversation`
is still a free string field and `turn` is still an integer (`Number.parseInt` on
the read side). Only the **computed values** change — `conversation` now carries a
`thread_`-shaped Thread id and `turn` carries the 1-based Message ordinal
(ADR-016). No stamper, hook, or parser change.

The TS side (relay) builds the **assisted** string; the Python side (`format_trailer`
via the hook's `parse_origin_env`) parses it. To avoid a second formatter drifting
from #216's grammar, the TS relay emits the exact string shape `parse_origin_env`
accepts, and the contract test (§4) asserts the emitted string round-trips through
the Python parser's accepted grammar (the bare body form). The executor (Python)
side reuses `_origin_stamp.autonomous_origin` + `format_trailer` directly — no new
formatter at all.

## 3. Armor — Operational Hardening

All Armor properties are **inherited from #216 and must be preserved end-to-end** —
this change adds no new external call, no network, no new secret.

- **Non-fatal stamping (ADR-013, MUST).** A stamp failure never blocks or loses a
  commit. The hook already exits 0 on any error; the relay's origin computation must
  also be best-effort — if conv-id/turn can't be derived, omit `originEnv` and
  spawn exactly as today (degrade to inferred). The executor's export must not abort
  the commit if the run-ulid is unavailable.
- **Read-only cockpit (ADR-003, MUST).** The relay only *computes* an id+turn (pure
  reads of the already-resolved transcript) and passes an env to the
  already-sanctioned spawn. No file write, no git mutation, no new spawn site.
  `check-read-only.sh` already allow-lists `chat.ts` and the bridge by path → **no
  gate change**. A WP DoD asserts the gate still passes.
- **No trailer injection (MUST).** Reuse #216's `_has_control_char` / the env
  parser's control-char rejection. The relay must not bypass them; the conv-id is a
  Claude session id (no control chars) but the TS side still passes the env value
  through the hook's parser unchanged (no second sanitiser).
- **Logging discipline (NFR-SEC-03 / TDD §3.4, MUST).** One structured line per
  stamp — ulid / id / confidence / outcome only; **never** commit-message text,
  prompt text, or reply text. #216's `_log` already obeys this; the relay's existing
  one-line-per-send log (`ChatLogLine`) must not start carrying the conversation id
  body or any prompt text. The relay MAY add `originStamped: boolean` to its log
  line (no id, no text) so the live round-trip is observable.

## 4. Proof — Verification Protocol

See `## Verification Plan` below for the per-integration concretions. Summary:

- **The widened port is a contract** (ADR-017). The `session-bridge.contract.test.ts`
  suite gains an assertion that an `originEnv` passed to `relay` reaches the injected
  `spawnBridge` as its third argument; absent origin → third argument undefined
  (byte-identical to today).
- **The relay's assisted-origin computation** is unit-tested against the
  resolved-transcript fixture (via the `ConversationIdentity` port): conversation
  = a `thread_`-shaped Thread id derived from the session; turn = existing
  messages + 1 (the Message ordinal); two distinct transcripts → two distinct
  Thread ids; fresh resolution → no origin.
- **Reconciliation (likely→exact) is verified at the read path** (ADR-018 D2):
  the inferred path renders the SAME `thread_` id for a file as the relay records
  (shared-helper parity), and a multi-session change yields per-transcript Thread
  ids with per-transcript 1-based turns — closing the #23 multi-session TODO. A
  **characterisation test pins current inferred output first** (REORGANISE
  discipline) before the per-transcript refactor. Note the flip itself does not
  depend on ids matching: a recorded trailer short-circuits correlation, and
  inferred correlation matches by timestamp window, not by id.
- **Cross-language grammar conformance:** the TS-emitted assisted string is asserted
  to be accepted by #216's `parse_origin_env` accepted grammar (round-trip test) so
  the TS formatter cannot drift from the Python parser.
- **The executor's autonomous export** is tested: the commit step's env carries a
  well-formed `SULIS_ORIGIN="autonomous; run=…"`; missing run-ulid → no export, no
  abort.
- **Degradation** (MUST): force a stamp failure and assert the commit still lands and
  origin falls back to inferred (reuse #216's non-fatal test pattern at the new call
  sites).
- **Live round-trip** (MUST, founder machine, out of CI): one real cockpit-chat
  commit and one real executor commit; assert the trailer is present
  (`git log --format='%(trailers)'`) and the cockpit origin view reads **exact**.
  CI uses a stubbed child, so this is the green-but-broken guard and is its own WP.

Integration tests use real adapters / recorded real streams (MEA-09) — no mocks for
the bridge. The contract suite's stubbed child is a test double of the *process*, not
a mock of the port (the established pattern in this codebase).

## 5. Components touched (inventory)

| # | Component | Language | Change primitive | Notes |
|---|---|---|---|---|
| 1 | `ports/SessionBridge.ts` (`spawnBridge` type + `relay` carry) | TS | REINFORCE/contract widen | ADR-017; optional 3rd arg |
| 2 | `adapters/StreamJsonSessionBridge.ts` (`spawnBridge` call, remove TODO) | TS | EXPAND-Create wiring | pass `originEnv` through to spawn |
| 3 | `routes/chat.ts` (relay computes assisted origin, injects identity port) | TS | EXPAND-Create | Thread id + Message ordinal → assisted env |
| 4 | relay helper `lib/relayOrigin.ts` (format assisted env) | TS | EXPAND-Create | emits #216 grammar with Thread/Message values |
| 4a | `ports/ConversationIdentity.ts` + `adapters/LocalTranscriptConversationIdentity.ts` (the seam; ADR-018) | TS | EXPAND-Create | domain-owned port + local read-only adapter; `thread_` id + ordinal; **no cross-service call** |
| 4b | `adapters/InferredOriginAttribution.ts` (reconcile onto shared Thread id; per-transcript indexing — closes #23) | TS | REORGANISE-Refactor | characterisation test first; shared `threadIdentity` helper (EP-03) |
| 5 | executor commit step exports autonomous `SULIS_ORIGIN` | PY/agent | EXPAND-Create | reuses `autonomous_origin`+`format_trailer` (unaffected by remodel) |
| 6 | live round-trip verification | — | REINFORCE/Proof | founder machine |

`spawnClaudeBridge` itself is **not** modified (it already accepts `originEnv`).

## 6. Sequencing

Contract first (WP-001), then the two language tracks can proceed in parallel
(TS: WP-002→003→004; PY: WP-005), then the live round-trip (WP-006) last. Full
graph in `work-packages/INDEX.md`.

## 7. Open architecture questions

**One genuine scope call (founder).** *Integrate live now, or model-only now?*
The founder's steer was "model as though we're going to integrate" —
integration-**ready**, not necessarily live-wired. This TDD takes the lighter,
integration-ready interpretation (ADR-018 D1): adopt the communication service's
Thread/Message **shapes** plus a domain-owned `ConversationIdentity` **seam** now,
and **defer the live cross-service call**. Rationale: the cockpit has zero reach
into the communication service today (no client, no `platform_id`); a live call
would add an outbound integration with a full Armor surface (timeout, retry,
circuit breaker, auth) that the steer told us to avoid unless trivial — and it is
not trivial. The seam makes the live wiring a single additive WP later (a
`CommunicationServiceConversationIdentity` adapter behind the same port) with no
change to the relay, grammar, stamper, hook, or read path. **If the founder wants
the live call in this change instead, that adapter + its Armor become an
additional WP and ADR-018 D1 flips.** Defaulting to model-only.

**Resolved by design (no founder call):** the autonomous `confidence` value
source — `confidence` is optional in `_origin_stamp.autonomous_origin` and the
trailer format; omit it when no per-run confidence scalar exists. Flagged for
WP-005, not a blocker. (Unaffected by the Thread/Message remodel — WP-005 is the
autonomous path, no threads/messages.)

---

## Verification Plan

<!-- VERIFICATION_QUESTIONS source: plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md v1.0.0 -->

**1. User-observable behaviour under test.** A commit made by a real cockpit-chat
session and a real executor run carries a `Sulis-Origin:` trailer, and the cockpit
origin view reports that commit's origin as **exact (recorded)** rather than **likely
(inferred)**. Two different chat conversations produce two different conversation
ids; turn index increments within a conversation. A stamp failure still lands the
commit (origin degrades to inferred).

**2. Verification environment(s).**
- **CI** — Vitest (TS) for the bridge contract + relay-origin unit/contract tests
  with a **stubbed child**; pytest (Python) for the executor-export + cross-language
  grammar conformance test. Real `claude` never runs in CI.
- **Founder machine (out of CI)** — the live round-trip (WP-006).

**3. Bootstrap-from-zero.** A fresh clone at the merge SHA can run the TS contract +
relay tests (`vitest`) and the Python tests (`pytest plugins/sulis/scripts/tests`)
with no external service — the bridge child is stubbed and `_origin_stamp` is local.

**4. Per-integration verification strategy.**

| Integration | Strategy | Classification | Concretion (shape) |
|---|---|---|---|
| Relay → widened `spawnBridge` port → session env | contract test, stubbed child | existing (`session-bridge.contract.test.ts`) | **concrete** — `apps/cockpit/server/tests/session-bridge.contract.test.ts` asserts `originEnv` reaches `spawnBridge` arg 3 |
| Relay computes Thread id + Message ordinal (via `ConversationIdentity` port) | in-memory unit test over a transcript fixture | existing fixtures | **concrete** — new `apps/cockpit/server/tests/relayOrigin.test.ts` |
| Inferred path reconciles on the same Thread id + per-transcript indexing (#23) | characterisation test first, then refactor | existing adapter | **concrete** — `apps/cockpit/server/tests/InferredOriginAttribution.test.ts` |
| TS assisted string ↔ Python `parse_origin_env` grammar | round-trip conformance test | existing parser | **concrete** — `plugins/sulis/scripts/tests/unit/test_assisted_grammar_conformance.py` |
| Executor → hook (autonomous export) | unit test on the commit-step env builder | existing hook | **concrete** — `plugins/sulis/scripts/tests/unit/test_executor_autonomous_origin.py` |
| Degradation (stamp failure non-fatal) | force-failure test at the new call sites | existing #216 pattern | **concrete** — assertions in the relay + executor tests above |
| Real `claude` round-trip (likely→exact) | live observation, founder machine | deferred-to-live | **deferred** — `live-round-trip-origin-cockpit` (WP-006) |

**5. Per-kind verification adapter.** `kind: backend` → pytest nodeids (Python WPs)
and Vitest spec paths (TS WPs), per the canonical kind→adapter table. The live
round-trip WP is `kind: integration` and ships an observed-evidence artifact, not a
CI test.

**6. Infrastructure needs surfaced (deferred).**
- `live-round-trip-origin-cockpit` — a real `claude` child + a running cockpit on the
  founder's machine; not available in CI. Carried by WP-006 as the green-but-broken
  guard.

### Contradictions with the SPEC

None on verification. **Design-intent update (not a contradiction):** the SPEC's
design locked conversation-id = transcript stem (the Claude session id); the
founder has since steered the identity onto the communication service's
Thread/Message model (integration-ready). ADR-016 is rewritten and ADR-018 added
to record the new decision and the (corrected) reconciliation analysis; the SPEC's
acceptance (likely→exact on a real round-trip; non-fatal degradation) is
unchanged and still honoured. The trailer grammar is unchanged per the steer.

---

## Sizing Report

- **Tier:** S (computed), confirmed by design scope. Still tier S after the
  remodel — the remodel adds one domain-owned port + one local adapter and a
  read-path refactor, all within the existing hexagonal seam; no new persistent
  entity, no new external client (the live service client is explicitly deferred).
- **sFPC:** ~6 — 0 new persistent entities (ILF); 0 new external clients (EIF —
  the live communication-service call is **deferred** behind the
  `ConversationIdentity` port, so it is not an EIF this change); ~5 operations
  (relay origin computation, identity-port derivation, port pass-through, inferred
  per-transcript reconcile, executor export), 1 derived read (Message ordinal /
  turn count).
- **ASR count:** ~5 — read-only invariant (ADR-003), non-fatal degradation
  (ADR-013), Thread-id stability/collision-resistance (ADR-016), read/recorded
  identity reconciliation incl. #23 multi-session fix (ADR-018), logging
  discipline (NFR-SEC-03).
- **Per-pillar coverage (from foundation):** Form — mostly covered (hexagonal seam
  exists; this widens one port and adds one domain-owned port + local adapter in
  the same shape, ADR-002). Armor — fully covered by #216 invariants; this change
  preserves them and adds **no** new external call (live call deferred). Proof —
  contract suite + read-path tests exist; this adds the sending-side tests, the
  identity-port tests, a characterisation test for the inferred refactor, and the
  live round-trip.
- **TDD length vs target:** within tier-S target; references #216, the
  communication service models, and the ADRs rather than restating them
  (Respect-Don't-Restate).
- **ADRs:** 3 (ADR-016 rewritten — supersedes its own prior cut; ADR-017 unchanged;
  ADR-018 new). Each locks a decision with rejected alternatives affecting more
  than one component. ADR-018 is the highest local number; no collision with the
  External ADR Registry (highest existing provenance ADR = 015). ADR count = 3 is
  within the tier-S maximum.
- **Circuit breakers:** none triggered. (The live cross-service call — which would
  need a circuit breaker — is deferred behind the port; flagged in §7 as the one
  founder scope call.)
