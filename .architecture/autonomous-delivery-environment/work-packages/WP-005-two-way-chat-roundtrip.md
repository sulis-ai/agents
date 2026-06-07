---
# Identity (WP-01)
id: WP-005
title: "Journey C round-trip: type a message to a change → the agent resumes/spawns and replies live"
kind: full-round-trip
source: feature
change_id: 01KT500K2JTE2EGW6TPPQ4D4VN
parent_phase: vertical-slice
slice_kind: round-trip
journey: "C — Talk to the agent about a change (the app's first write/act path)"

atomic_branch: yes
estimate: 24h           # the largest slice: bridge port + contract + fixture + binding/lock + relay + prod adapter + gate + composer/SSE UI
blast_radius: high      # the app's first write path AND the highest-risk consumption half — sequenced EARLY for that reason
primitive: EXPAND-Create
group: expand
visual_contract: WP-002
# SUBSTITUTE/wrap discipline: SessionBridge is EXPAND-Create (an adapter for a port WE own),
# NOT a wrap of the claude CLI. The CLI is *called by* the adapter (ADR-002).
subject_ownership: domain-owned-port   # the public face is the cockpit's SessionBridge port

observed_acceptance:
  scenario: "dna:scenario:YY4RJ7JS8KT55BS61BD0ER3ZNF"   # C — Talk to the agent about a change
  observable_result: "The founder opens a change, types a message in the docked composer, and the agent's reply streams back live and joins the conversation — the founder never had to choose 'resume' vs 'spawn'; it just works. A message to the wrong change is impossible; a second send mid-reply is refused; an unreachable session shows a clear failure and is NOT shown as delivered; on resume an HONEST 'resumed' indication is shown and an incomplete step is re-run, never reported done."
  how_observed: "TWO-PART. (1) CI/local with the RecordedSessionBridge fixture: drive the composer, OBSERVE the recorded reply stream live; OBSERVE SESSION_BUSY on a second send, SESSION_CHANGE_MISMATCH (zero bytes) on a mis-bound request, the honest 'resumed' note on the mid-step fixture. (2) BLOCK-and-hand-to-founder: on the founder machine with a REAL claude, type a real message to a real change and OBSERVE the live reply stream (real resume + real spawn + mid-step re-run). This live hop is the one irreducibly-human/third-party step in the whole plan."
  not_sufficient: "Green CI, green deploy, a green from-graph scenario run, and even the recorded-fixture observation are NOT the full DoD on their own. The slice is DONE only when the founder has driven a REAL claude session through the running app and OBSERVED a live reply (the BLOCK-and-hand-to-founder step below)."
  human_hops: "BLOCK-and-hand-to-founder: driving a real `claude` session for the live two-way chat (real resume / real spawn / mid-step re-run) cannot bootstrap in CI — it requires a live agent on the founder machine. The slice is not 'done' until this is observed. Everything else (binding, lock, failure codes, SSE plumbing, composer states) is observable in CI against the recorded fixture."

acceptance_criteria:
  - "PORT + CONTRACT: ports/SessionBridge.ts defines resolveSession(changeId)→SessionResolution ({live|resumable|fresh}) and relay(changeId, prompt, sink)→RelayOutcome (ADR-002); session-bridge.contract.test.ts is the import-and-run runContract suite every adapter satisfies (resolve returns the right kind; relay emits state→chunk*→complete; resolveSession is side-effect-free, FR-N4). EXPAND-Create (adapter for OUR port), not a wrap of the CLI"
  - "RECORDED FIXTURE: adapters/RecordedSessionBridge.ts replays a recorded real stream-json session (MEA-09: recorded, NOT a mock) and satisfies the contract suite; the recording-bridge-claude-session fixture covers ALL FOUR cases — live, resume-from-transcript, spawn-grounded, mid-step; the mid-step case surfaces complete.resumed=true with the incomplete step re-run (FR-N5)"
  - "SAFETY LIBS: lib/sessionBinding.ts is pure, proves change_id-equality AND cwd/worktreePath-equality fail-closed before any delivery (ADR-004, FR-21, NFR-SEC-02) — same verdict for live/resumed/spawned; lib/inFlightLock.ts is a per-change in-memory lock (acquire/held/release; double-acquire ⇒ SESSION_BUSY, FR-20/NFR-REL-03)"
  - "RELAY ROUTE: POST /api/changes/:id/chat runs the load-bearing order acquire lock → resolveSession → bind → act → stream SSE → release (TDD §3.1); 409 SESSION_BUSY, 422 SESSION_CHANGE_MISMATCH (zero bytes, no process touched), 502 SESSION_UNREACHABLE (not marked delivered); SSE text/event-stream/no-cache/keep-alive/unbuffered, state→chunk*→complete (ADR-001); mid-stream drop ⇒ partial preserved + interrupted (FR-22); one structured log line per send {changeId, resolution, outcome, code?}, never body/reply (NFR-SEC-03); bridge startup timeout + idle watchdog so the lock can't leak"
  - "READ-ONLY GATE EXTENSION: check-read-only.sh + read-only-inventory.test.ts extended so the relay route file is the only app.post exception and the bridge adapter file is the only process-start exception, plus a NEW rule flagging process-start anywhere else; loading any read surface starts no process (ADR-003, FR-N1, NFR-SEC-05, NFR-ARCH-02)"
  - "PROD ADAPTER: adapters/StreamJsonSessionBridge.ts drives `claude -p --output-format stream-json --include-partial-messages` (resume via --resume/--continue or Agent SDK; NO interactive-TUI/pty path); satisfies the contract suite (parity with the recorded fixture); resume restarts from the persisted transcript, spawn seeds with saved context; never synthesises completion (FR-24/25/26/N5); process-start confined to this one file"
  - "UI: the docked composer sends to the open change via POST /api/changes/:id/chat and renders the streamed reply live (FR-16/17), joining the conversation on complete (FR-18); reflects lifecycle states in plain English (ready / agent-replying / waking-the-change-up / couldn't-start, FR-23); send disabled while THIS change streams (FR-20); mid-stream break shows 'reply was interrupted' + preserves the partial (FR-22); unreachable shows a clear failure and does NOT show delivered (FR-19/N3); on resume an HONEST 'resumed' indication (NOT 'silently continued'), incomplete step shown re-run (FR-26/N5); acts ONLY on the open change; consumes tokens.css only; matches the SIGNED visual contract (WP-002)"
  - "OBSERVED ROUND-TRIP (the gate): (a) drive the composer against the RecordedSessionBridge and OBSERVE the live stream + the three failure behaviours + the honest resumed note; (b) BLOCK-and-hand-to-founder: drive a REAL claude session on the founder machine and OBSERVE a live reply (real resume + real spawn + mid-step). The slice is DONE only after (b)."
test_plan:
  unit:
    - "apps/cockpit/server/tests/sessionBinding.test.ts (NEW) — A-request→B-session ⇒ mismatch (zero bytes); A→A ⇒ bound; resumed + spawned records both checked; cwd-mismatch ⇒ mismatch"
    - "apps/cockpit/server/tests/inFlightLock.test.ts (NEW) — acquire/held/release; double-acquire ⇒ busy; release after complete frees"
  integration:
    - "apps/cockpit/server/tests/session-bridge.contract.test.ts (NEW) — the reusable runContract suite"
    - "apps/cockpit/server/tests/session-bridge.recorded.test.ts (NEW) — runContract vs RecordedSessionBridge over all four fixture cases + the FR-N5 mid-step assertion"
    - "apps/cockpit/server/tests/session-bridge.streamjson.test.ts (NEW) — runContract vs StreamJsonSessionBridge with a stubbed stream-json child (CI); real claude path is the founder-machine observation"
    - "apps/cockpit/server/tests/routes.chat.test.ts (NEW) — supertest with RecordedSessionBridge: SESSION_BUSY, SESSION_CHANGE_MISMATCH (zero bytes), SESSION_UNREACHABLE (not delivered), state→chunk→complete, mid-stream drop→interrupted+partial"
    - "apps/cockpit/server/tests/read-only-inventory.test.ts + check-read-only-script.test.ts (EXTEND) — exactly one process-start; reads start none; the allow-listed relay + bridge"
    - "apps/cockpit/client/src/tests/Composer.test.tsx (NEW) — FR-23 states; FR-20 disable; FR-22 partial+interrupted; FR-19 not-delivered; FR-26 honest resumed note"
    - "apps/cockpit/client/src/tests/useChatStream.test.tsx (NEW) — SSE state→chunk*→complete; error events map to the right plain-English state"
  observed:
    - "DRIVEN (recorded): drive the composer against RecordedSessionBridge, OBSERVE live stream + the three failures + the honest resumed note"
    - "BLOCK-AND-HAND-TO-FOUNDER (the live gate): founder drives a REAL claude session through the running app, OBSERVES a live reply (real resume + real spawn + mid-step). The slice is not done until this is observed."
  verification:
    - "bash apps/cockpit/scripts/check-read-only.sh exits 0 WITH the chat path present"
    - "axe-core a11y on the chat dock green"
    - "branch-ci green"
    - "OBSERVED live round-trip on the founder machine recorded — the from-graph scenario-C run sits on top of it, not instead of it"
verification_gates: [unit, integration, component, visual_diff, a11y, observed_roundtrip, live_founder_machine]
verification:
  adapter: backend
  artifact: "apps/cockpit/server/tests/routes.chat.test.ts"
  deferred-to-follow-on: recording-bridge-claude-session
  # binding/lock/failure/SSE/composer logic is CONCRETE against the recorded fixture now;
  # the LIVE resume/spawn round-trip is the BLOCK-and-hand-to-founder observation on the founder machine.

infrastructure_needs:
  - id: recording-bridge-claude-session
    why: "recorded/replayable stream-json session covering live + resume-from-transcript + spawn-grounded + mid-step, so binding/lock/relay/composer are CI-testable AND the recorded round-trip is observable without a live agent; the live round-trip is the founder-machine observation"

derived_from:
  - finding: "Re-slice vertical: Journey C (two-way chat) — the highest-risk consumption half, sequenced EARLY. Folds prior horizontal WP-006 (port+contract), WP-007 (recorded fixture), WP-008 (binding+lock), WP-009 (relay route + gate), WP-010 (prod adapter), WP-015 (composer/SSE UI) into ONE observable round-trip with a live BLOCK-and-hand-to-founder step. ADR-001/002/003/004; FR-16..26, FR-N1..N5; NFR-SEC/REL."
    found_in: .architecture/autonomous-delivery-environment/adrs/ADR-002-session-bridge-port-resume-spawn.md
    severity_at_discovery: n/a
generated_by:
  activity: re-slice-vertical/2026-06-04
  agent: sulis:engineering-architect
addresses_findings: []
invalidated_by: { activity: null, result: null }

status: pending
depends_on: [WP-001, WP-002, WP-004]
# data contract + signed visual contract + the thread shell (WP-004) the composer docks into

child_wps: []
kinds: null
# This slice is LARGE because the chat round-trip is irreducible: a composer with no relay,
# or a relay with no composer, is exactly the half-built failure the re-slice exists to prevent.
# Its internal Red-Green-Blue order is: port+contract → recorded fixture → binding/lock libs →
# relay route + gate → prod adapter → composer/SSE UI → observe. Build it as one branch; do not
# split the consumption half (composer) from the production half (relay).

# NFR-SEC constraints carried on the sensitive write/act path:
security_constraints:
  - "Act only on the targeted change's session; binding (sessionBinding) runs before any process start (NFR-SEC-06)"
  - "Every other surface stays provably read-only; the gate fails on any new mutation elsewhere (FR-N1)"
  - "No message body / reply text in logs (NFR-SEC-03)"
  - "Resume/spawn surfaced honestly to the founder; never a fabricated completion (FR-26/FR-N5)"

verifies_scenario: "dna:scenario:YY4RJ7JS8KT55BS61BD0ER3ZNF"   # C

rollback: |
  New port + contract + recorded fixture + two pure safety libs + relay route +
  gate-rule additions + prod adapter + composer/SSE UI. Remove the relay mount +
  the POST funnel exception; revert the gate-script + inventory-test edits (the
  gate returns to forbidding ALL mutations — safe by construction); revert the
  index.ts adapter selection (chat degrades to unavailable; read surfaces
  unaffected); the thread reverts to the read-only transcript Chat. Revert the
  commit.
---

# Journey C round-trip: talk to the agent — it resumes/spawns and replies live

## The round-trip this slice delivers

**Type a message to a change → (action: send) → OBSERVE: the agent's reply
streams back live and joins the conversation — and it "just works" (resume or
spawn, the founder never chose).** This is the app's first write/act path and the
**highest-risk consumption half** in the whole plan, which is why it is sequenced
**early** — right after the thread shell (WP-004) it docks into, before the
lower-risk read slices (brain, search).

The re-slice rule is most important here: the old horizontal plan split the
composer (consumption) from the relay (production) across separate WPs and left
integration to the very end. This slice ships the **whole** round-trip in one
branch — port, contract, recorded fixture, binding + lock, relay route, gate
extension, prod adapter, AND the composer/SSE client — so the consumption half
cannot go missing and "done" cannot be declared on a relay with no composer.

## Why it is large, and why it must not be split

A composer with no relay, or a relay with no composer, is exactly the half-built
failure this re-slice exists to prevent. The chat round-trip is irreducible. Its
internal order (Red→Green→Blue across the branch) is:

1. **Port + contract suite** (`SessionBridge.ts`, `session-bridge.contract.test.ts`) — EXPAND-Create, an adapter for OUR port; the CLI is *called by* the adapter, never wrapped (ADR-002).
2. **Recorded fixture** (`RecordedSessionBridge.ts` + `recording-bridge-claude-session`) — a recorded REAL stream-json session (MEA-09, not a mock) covering live / resume / spawn / mid-step.
3. **Safety libs** (`sessionBinding.ts`, `inFlightLock.ts`) — pure, fail-closed binding + per-change lock, in the load-bearing order.
4. **Relay route + gate** (`routes/chat.ts`, `check-read-only.sh` extension) — lock→resolve→bind→act→stream→release; the one sanctioned write path.
5. **Prod adapter** (`StreamJsonSessionBridge.ts`) — drives headless `claude -p` stream-json; the one process-start site.
6. **Composer + SSE client** (`Composer.tsx`, `useChatStream.ts`) — the docked write surface; honest lifecycle states.
7. **Observe** — recorded round-trip in CI, then the live founder-machine round-trip.

## The observed-acceptance gate (MUST) — TWO parts, the second is human

DoD has two observed parts, and the second is the one irreducibly-human hop in
the plan:

- **(a) Recorded round-trip (CI / local):** drive the composer against the
  `RecordedSessionBridge` and **see** the recorded reply stream live; **see**
  SESSION_BUSY on a second send, SESSION_CHANGE_MISMATCH with zero bytes on a
  mis-bound request, and the honest "resumed" note on the mid-step fixture.
- **(b) BLOCK-and-hand-to-founder — the live round-trip:** on the founder machine
  with a **real `claude`**, type a real message to a real change and **observe a
  live reply** (real resume + real spawn + mid-step re-run). This cannot bootstrap
  in CI; it requires a live agent. **The slice is not "done" until this is
  observed.**

Green CI, green deploy, a green from-graph scenario-C run, and even part (a) are
**not** the full DoD. Only after part (b) — the founder driving a real session
through the running app and seeing a live reply — is journey C done. The
`sulis-verify-acceptance --scenario dna:scenario:YY4RJ7JS8KT55BS61BD0ER3ZNF` run
records the acceptance on top of the live observation.

## Rollback

Remove the relay mount + POST funnel exception; revert the gate-script + inventory
edits (gate reverts to forbidding all mutations — safe); revert the index.ts
adapter selection (chat degrades to unavailable; reads unaffected); the thread
reverts to the read-only transcript Chat. Revert the commit.
