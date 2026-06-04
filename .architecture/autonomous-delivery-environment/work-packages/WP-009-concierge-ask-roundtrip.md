---
# Identity (WP-01)
id: WP-009
title: "Journey I round-trip: ask the concierge a plain-English question → get a read-only answer about your world"
kind: full-round-trip
source: feature
change_id: 01KT500K2JTE2EGW6TPPQ4D4VN
parent_phase: vertical-slice
slice_kind: round-trip
journey: "I — Concierge: find a change / get its status / ask about your world"

atomic_branch: yes
estimate: 12h
blast_radius: medium     # rides the bridge; must stay provably read-only
primitive: EXPAND-Create
group: expand
visual_contract: WP-002

observed_acceptance:
  scenario: "PENDING-MINT:I"   # author scenario I then backfill dna:scenario:<ULID>
  observable_result: "The founder opens the concierge front door, asks a plain-English question ('which change was I doing the login fix in?', 'what needs my attention?'), and a read-only answer streams back — navigation / status / Q&A over their changes + brain. When intent is consequential (start work / investigate), the concierge OFFERS the next step (open onboarding / start-from-intent) rather than doing it inline."
  how_observed: "TWO-PART. (1) CI/local with the RecordedSessionBridge: ask a question through the front door, OBSERVE the streamed read-only answer; ask to 'start a change', OBSERVE a route-hint offer (not an inline act); confirm the path performed zero writes/mints/starts/signals. (2) BLOCK-and-hand-to-founder: on the founder machine with a real claude, ask a real question and OBSERVE the live streamed answer over the real world."
  not_sufficient: "Green CI / from-graph run / the recorded observation alone are NOT the full DoD. The slice is DONE only after the founder asks a real question through the running app and OBSERVES a live read-only answer (the BLOCK-and-hand-to-founder step)."
  human_hops: "BLOCK-and-hand-to-founder: the live concierge answer (real claude -p) cannot bootstrap in CI; the founder observes it on their machine. Read-only containment, route-hinting, and the failure path are observable in CI against the recorded fixture."

acceptance_criteria:
  - "ROUTE: POST /api/concierge/query {question, product?} answers navigation/status/Q&A over the change store + brain, READ-ONLY, streaming ConciergeStreamEvent SSE (state→chunk*→complete) (FR-33); rides the SAME SessionBridge as the chat (no second bridge, no parallel relay; ADR-006, FR-27); EXPAND-Reuse transport"
  - "CONTAINMENT: the query path performs ZERO writes/mints/session-starts/signals — coordinates only (FR-N8, NFR-DISC-05), asserted by a read-only test mirroring the board's; when intent is to START WORK or INVESTIGATE, complete carries a `route` hint (onboarding|start-from-intent) and the concierge does NOT act inline (FR-34, FR-N9)"
  - "FAILURE/LOG: bridge unreachable ⇒ 502 SESSION_UNREACHABLE; one structured log line per query, never the question or reply text (NFR-SEC-03); read-only gate gains NO new file-level write exception for the concierge (ADR-006)"
  - "UI: the concierge front door lets the founder ask a question and renders the streamed answer live, REUSING the chat composer + SSE client (Composer/useChatStream from WP-005) — not a parallel UI (EP-03); the answer is read-only nav/status/Q&A and the front door performs no write/mint/start itself (FR-33, FR-N8); on a `route` hint it OFFERS the confirm-gated next step (does not act inline, FR-N9); a bridge-unreachable answer shows a clear failure; an empty world (nothing minted) prompts onboarding (UC-09→UC-07); consumes tokens.css only; matches the SIGNED visual contract (WP-002)"
  - "OBSERVED ROUND-TRIP (the gate): (a) ask via the front door against the RecordedSessionBridge and OBSERVE the read-only answer + the route-hint offer; (b) BLOCK-and-hand-to-founder: ask a real question through the running app on the founder machine and OBSERVE a live read-only answer. DONE only after (b)."
test_plan:
  unit:
    - "apps/cockpit/server/tests/conciergeRead.test.ts (NEW) — read path composes ChangeStoreReader + brain read into nav/status/Q&A; route-hint detection (start/investigate → route, not act)"
  integration:
    - "apps/cockpit/server/tests/routes.concierge.test.ts (NEW) — supertest with RecordedSessionBridge + FakeChangeStoreReader + brain fixtures: SSE state→chunk→complete; complete.route hint; 502 unreachable; ZERO writes/mints/starts/signals"
    - "apps/cockpit/server/tests/read-only-inventory.test.ts (EXTEND) — the concierge route starts no process beyond the read-only bridge read; mutates nothing"
    - "apps/cockpit/client/src/tests/ConciergeChat.test.tsx (NEW) — ask → streamed answer (reuses useChatStream); route-hint OFFERS onboarding/start, does NOT act inline; unreachable failure; empty-world prompts onboarding; no write/mint/start from this surface"
  observed:
    - "DRIVEN (recorded): ask via the front door against RecordedSessionBridge, OBSERVE the read-only answer + route-hint offer + zero-consequence containment"
    - "BLOCK-AND-HAND-TO-FOUNDER (the live gate): founder asks a real question through the running app, OBSERVES a live read-only answer over the real world"
  verification:
    - "bash apps/cockpit/scripts/check-read-only.sh exits 0"
    - "axe-core a11y on the concierge front door green"
    - "branch-ci green"
    - "OBSERVED live round-trip on the founder machine recorded"
verification_gates: [unit, integration, component, visual_diff, a11y, observed_roundtrip, live_founder_machine]
verification:
  adapter: backend
  artifact: "apps/cockpit/server/tests/routes.concierge.test.ts"
  deferred-to-follow-on: recording-bridge-discovery-session
  # read-only containment / route-hinting / failure concrete against the recorded fixture now;
  # the LIVE concierge answer is the BLOCK-and-hand-to-founder observation.

infrastructure_needs:
  - id: recording-bridge-discovery-session
    why: "recorded/replayable discovery-session stream-json fixture so the concierge read-only round-trip is CI-testable and recorded-observable without a live agent; the live answer is the founder-machine observation"

derived_from:
  - finding: "Re-slice vertical: Journey I (concierge ask). Folds prior horizontal WP-019 (concierge route + conciergeRead) + WP-025 (ConciergeChat UI) into ONE observable round-trip. ADR-006 concierge rides the bridge, coordinates only, reuses the chat path; FR-33, FR-34, FR-N8, FR-N9, NFR-DISC-05."
    found_in: .architecture/autonomous-delivery-environment/adrs/ADR-006-concierge-rides-bridge-coordinates-only.md
    severity_at_discovery: n/a
generated_by:
  activity: re-slice-vertical/2026-06-04
  agent: sulis:engineering-architect
addresses_findings: []
invalidated_by: { activity: null, result: null }

status: pending
depends_on: [WP-001, WP-002, WP-005]
# data contract + visual contract + the chat composer/SSE client + SessionBridge it reuses (WP-005)

child_wps: []
kinds: null

security_constraints:
  - "Concierge query is read-only: zero writes/mints/session-starts/signals (FR-N8, NFR-DISC-05) — the read-only discipline extended to the front door"
  - "Consequential intent is ROUTED to a confirm-gated act endpoint, never performed inline (FR-34, FR-N9, ADR-006)"
  - "No new gate write-exception for the concierge; no question/reply text in logs (NFR-SEC-03)"

verifies_scenario: "PENDING-MINT:I"   # Concierge ask (UC-09)

rollback: |
  New conciergeRead lib + concierge route + ConciergeChat surface (reusing
  Composer + useChatStream). Remove the mount + files + surface; revert the
  commit. No gate write-exception was added (read-only); the chat composer is
  unaffected (still used in the thread). No read surface affected.
---

# Journey I round-trip: ask the concierge → a read-only answer about your world

## The round-trip this slice delivers

**Ask a plain-English question at the front door → (action: ask) → OBSERVE: a
read-only streamed answer about your changes + brain; consequential intent is
OFFERED, never done inline.** The concierge route and the front-door UI that
drives it ship together. The front door **reuses** the chat composer + SSE client
from WP-005 (EP-03) — which is why this slice depends on the chat slice rather
than re-building a composer.

## What changes (the whole round-trip, one branch)

- **Route + lib (server):** `lib/concierge/conciergeRead.ts` (composes the
  existing `ChangeStoreReader` + brain read into nav/status/Q&A; detects
  consequential intent and emits a `route` hint instead of acting);
  `routes/concierge.ts` (`POST /query`, drives the **read-only** bridge read,
  maps to `ConciergeStreamEvent` SSE, 502 on unreachable). Reuses `SessionBridge`
  (ADR-002) — no new port, no second bridge (ADR-006).
- **UI (client):** `components/ConciergeChat.tsx` (the front-door ask surface;
  reuses `Composer` + `useChatStream` pointed at `/api/concierge/query`; on a
  `route` hint, offers — does not perform — the onboarding / start-from-intent
  step); `api/useConciergeStream.ts` (thin, or reuse `useChatStream`).

## The observed-acceptance gate (MUST) — TWO parts

- **(a) Recorded round-trip (CI / local):** ask through the front door against the
  `RecordedSessionBridge` and **see** the streamed read-only answer; ask to "start
  a change" and **see** a route-hint offer (not an inline act); confirm zero
  writes/mints/starts/signals.
- **(b) BLOCK-and-hand-to-founder — the live answer:** on the founder machine with
  a real `claude`, ask a real question and **observe** the live read-only answer
  over the real world. **The slice is not "done" until this is observed.**

Author scenario I and run it from-graph on top of the live observation.

## Rollback

Remove the lib + route + surface; revert. No gate exception added (read-only);
the chat composer is unaffected.
