---
id: WP-019
title: "POST /api/concierge/query — read-only nav/status/Q&A over the seam + bridge"
kind: backend
source: feature
change_id: 01KT500K2JTE2EGW6TPPQ4D4VN
parent_phase: chat
parent_group: concierge

atomic_branch: yes
estimate: 6h
blast_radius: medium       # rides the bridge; must stay provably read-only
primitive: EXPAND-Create
group: expand
acceptance_criteria:
  - "POST /api/concierge/query {question, product?} answers navigation / status / Q&A over the change store + brain, READ-ONLY, streaming ConciergeStreamEvent SSE (state→chunk*→complete) (FR-33)"
  - "The concierge rides the SAME SessionBridge as the chat (claude -p over stream-json) — NO second bridge, NO parallel relay (ADR-006, FR-27); transport is EXPAND-Reuse"
  - "The query path performs ZERO writes, ZERO mints, ZERO session-starts, ZERO signals — it COORDINATES ONLY (FR-N8, NFR-DISC-05); asserted by a read-only test mirroring the board's"
  - "When the founder's intent is to START WORK or INVESTIGATE, complete carries a `route` hint (onboarding | start-from-intent) — the concierge does NOT act inline; it routes to the confirm-gated endpoint (FR-34, FR-N9, ADR-006)"
  - "Bridge unreachable ⇒ 502 SESSION_UNREACHABLE (clear failure); one structured log line per query, never the question or reply text (NFR-SEC-03 posture)"
  - "read-only gate gains NO new file-level write exception for the concierge — the only consequence-reaching paths are the FR-28 mint + FR-29 start, in their own WPs (ADR-006)"
test_plan:
  unit:
    - "apps/cockpit/server/tests/conciergeRead.test.ts (NEW) — read path composes ChangeStoreReader + brain read; produces nav/status/Q&A answers; route-hint detection (start/investigate → route, not act)"
  integration:
    - "apps/cockpit/server/tests/routes.concierge.test.ts (NEW) — supertest with RecordedSessionBridge + FakeChangeStoreReader + brain fixtures: SSE state→chunk→complete; complete.route hint; 502 on unreachable; ZERO writes/mints/starts/signals (FR-33/FR-N8/NFR-DISC-05)"
    - "apps/cockpit/server/tests/read-only-inventory.test.ts (EXTEND) — the concierge route starts no process beyond the read-only bridge read; mutates nothing"
  verification:
    - "bash apps/cockpit/scripts/check-read-only.sh exits 0"
    - "branch-ci green"
verification_gates: [unit, integration, smoke]
verification:
  adapter: backend
  artifact: "apps/cockpit/server/tests/routes.concierge.test.ts"
  # concrete against RecordedSessionBridge + fixtures now; the LIVE concierge
  # path (real claude -p) is deferred to WP-027 (recording-bridge-discovery-session).

derived_from:
  - finding: "ADR-006 concierge rides the bridge, coordinates only; TDD §2.4 conciergeRead row + §3.6 concierge containment + §5.1 concierge row; FR-33, FR-34, FR-N8, FR-N9, NFR-DISC-05; openapi.yaml /api/concierge/query"
    found_in: .architecture/autonomous-delivery-environment/adrs/ADR-006-concierge-rides-bridge-coordinates-only.md
    severity_at_discovery: n/a
generated_by:
  activity: plan-work-run/2026-06-04T09:20:00Z
  agent: sulis:engineering-architect
addresses_findings: []
invalidated_by: { activity: null, result: null }

status: pending
depends_on: [WP-001, WP-006, WP-007, WP-017]   # change types + SessionBridge port + recorded fixture + concierge stream types

child_wps: []
kinds: null

# read-only posture carried on the front door:
security_constraints:
  - "Concierge query is read-only: zero writes / mints / session-starts / signals (FR-N8, NFR-DISC-05) — the read-only discipline extended to the front door"
  - "Consequential intent is ROUTED to a confirm-gated act endpoint, never performed inline (FR-34, FR-N9, ADR-006)"
  - "No new gate write-exception for the concierge; no question/reply text in logs (NFR-SEC-03)"

verifies_scenario: "PENDING-MINT:I"   # Concierge ask (UC-09) — author scenario I then backfill the dna:scenario ULID

rollback: |
  New conciergeRead lib + concierge route + tests. Remove the mount + files;
  revert the commit. No gate write-exception was added (read-only), so the gate
  is unchanged. No read surface affected.
---

# POST /api/concierge/query — read-only nav/status/Q&A over the seam + bridge

## Why

The concierge front door (UC-09, FR-33), modelled on `sulis:sulis`. The
founder asks plain-English questions about their world — "which change was I
doing the login fix in?", "what needs my attention?" — and the concierge
answers over the change store + brain, **read-only**. The load-bearing rule
(ADR-006, FR-N8): the concierge *coordinates only*. It rides the **same**
headless bridge as the chat (no second transport, EP-03) and its only
consequential acts (mint, change-start) live in their own confirm-gated WPs —
this query path does none of them. When intent is consequential it **routes**
(a `route` hint) rather than acting (FR-34, FR-N9).

## What changes

- `apps/cockpit/server/lib/concierge/conciergeRead.ts` (NEW, EXPAND-Create) — composes the existing `ChangeStoreReader` + brain read into nav/status/Q&A answers; detects consequential intent (start/investigate) and emits a `route` hint instead of acting.
- `apps/cockpit/server/routes/concierge.ts` (NEW, EXPAND-Create) — `POST /query`; drives the read-only bridge read (ADR-006); maps to `ConciergeStreamEvent` SSE; 502 on unreachable. Mounted at `/api/concierge`.

The route takes the injected `SessionBridge` (recorded fixture in tests, prod
adapter in production) and the read projections the board/thread already use.

## How

Reuse `SessionBridge` (ADR-002) — no new port (ADR-006). The read path uses
the same `FakeChangeStoreReader` + brain fixtures the board/thread read tests
use, so the read-only assertion is identical to the board's. Route detection
maps "start / build / investigate / look into" intent to a `route` hint
(`onboarding` | `start-from-intent`), never to an inline act (FR-N8/N9).
Logging reuses the no-bodies discipline (NFR-SEC-03).

## Tests

- `conciergeRead.test.ts` — read composition + route-hint detection.
- `routes.concierge.test.ts` — SSE happy path; `complete.route` hint; 502 unreachable; **zero** writes/mints/starts/signals.
- `read-only-inventory.test.ts` — the concierge route adds no write/mutation/process-start.

`verification:` — concrete against the recorded fixture now; the **live**
concierge (real `claude -p`) is deferred to WP-027 (manual,
`recording-bridge-discovery-session`).

## Scenario linkage

Verifies scenario **I — "Concierge: find a change / get its status / ask
about your world"** (UC-09). Scenario I is not yet minted; author it and
backfill the `dna:scenario:<ULID>` here (aggregated in WP-027).

## Rollback

Remove the lib + route + tests; revert. No gate exception added (read-only).
