---
id: WP-025
title: "Concierge front door: read-only ask UI reusing the chat composer + SSE client"
kind: frontend
source: feature
change_id: 01KT500K2JTE2EGW6TPPQ4D4VN
parent_phase: surfaces
parent_group: concierge

atomic_branch: yes
estimate: 6h
blast_radius: medium       # the front door; reuses the chat composer but must stay read-only here
primitive: EXPAND-Create
group: expand
visual_contract: WP-002
acceptance_criteria:
  - "The concierge front door lets the founder ask a plain-English question; it POSTs to /api/concierge/query and renders the streamed answer live (ConciergeStreamEvent), REUSING the chat composer + SSE client (Composer/useChatStream from WP-015) — not a parallel UI (EP-03)"
  - "The answer is READ-ONLY navigation / status / Q&A; the front door performs no write / mint / session-start itself (FR-33, FR-N8) — it is the client form of the concierge's coordinate-only rule"
  - "When complete carries a `route` hint (onboarding | start-from-intent), the UI OFFERS the confirm-gated next step (open onboarding / start-from-intent) — it does NOT perform the act inline (FR-34, FR-N9); the founder chooses"
  - "A bridge-unreachable answer shows a clear plain-English failure (SESSION_UNREACHABLE); an empty world (nothing minted yet) prompts onboarding (UC-09 → UC-07)"
  - "Consumes tokens.css only; matches the SIGNED visual contract (WP-002 — now covers the concierge surface)"
test_plan:
  unit: []
  integration:
    - "apps/cockpit/client/src/tests/ConciergeChat.test.tsx (NEW) — ask → streamed answer (reuses useChatStream); route-hint OFFERS onboarding/start, does NOT act inline (FR-N9); unreachable failure; empty-world prompts onboarding; no write/mint/start from this surface (read-only funnel)"
  verification:
    - "axe-core a11y on the concierge front door green"
    - "branch-ci green"
verification_gates: [unit, component, visual_diff, a11y, perf_budget]
verification:
  adapter: frontend
  artifact: "apps/cockpit/client/src/tests/ConciergeChat.test.tsx"

derived_from:
  - finding: "ADR-006 concierge rides the bridge, coordinates only, reuses the chat path; TDD §2.4 ConciergeChat row + §5.1 concierge row; FR-33, FR-34, FR-N8, FR-N9; visual contract covers the concierge surface"
    found_in: .architecture/autonomous-delivery-environment/adrs/ADR-006-concierge-rides-bridge-coordinates-only.md
    severity_at_discovery: n/a
generated_by:
  activity: plan-work-run/2026-06-04T09:20:00Z
  agent: sulis:engineering-architect
addresses_findings: []
invalidated_by: { activity: null, result: null }

status: pending
depends_on: [WP-002, WP-015, WP-017, WP-019]
# SIGNED visual contract (#45) + the chat composer/SSE client it reuses + concierge stream types + the concierge route

child_wps: []
kinds: null

# read-only posture (client side, the front door):
security_constraints:
  - "The concierge front door is read-only: it performs no write / mint / session-start; consequential intent is OFFERED (routed), never performed inline (FR-N8, FR-N9)"
  - "Reuses the chat composer + SSE client (EP-03) — one composer, not a parallel one"

verifies_scenario: "PENDING-MINT:I"   # Concierge ask (UC-09)

rollback: |
  New ConciergeChat surface reusing Composer + useChatStream. Remove the
  surface; the chat composer is unaffected (still used in the thread). Revert
  the commit. No read surface affected.
---

# Concierge front door: read-only ask UI reusing the chat composer + SSE client

## Why

The concierge front door (UC-09, FR-33) — the founder asks plain-English
questions about their world and gets a streamed answer. Per ADR-006/EP-03 it
**reuses** the chat composer + SSE client (WP-015), not a parallel UI. Its
client-side discipline mirrors the server's (WP-019): it is **read-only** and
*coordinates only* — when intent is consequential it **offers** the
confirm-gated next step (onboarding / start-from-intent) rather than doing the
work inline (FR-N8/N9).

## What changes

- `apps/cockpit/client/src/components/ConciergeChat.tsx` (NEW, EXPAND-Create) — the front-door ask surface; reuses `Composer` + `useChatStream` (WP-015) pointed at `POST /api/concierge/query`; renders the streamed answer; on a `route` hint, offers (does not perform) the onboarding / start-from-intent step.
- `apps/cockpit/client/src/api/useConciergeStream.ts` (NEW, thin) — or reuse `useChatStream` with the concierge endpoint + `ConciergeStreamEvent` mapping.

## How

Consume WP-019's read-only relay. Reuse the chat composer + SSE client (one
composer, EP-03). The `route` hint renders an explicit "start this as a piece
of work?" affordance that opens the confirm-gated endpoint — the founder
chooses; nothing happens inline (FR-N9). Empty world (nothing minted) prompts
onboarding (UC-09 → UC-07). Consume `tokens.css` only; match the signed visual
contract (WP-002), which now covers the concierge surface.

## Tests

`ConciergeChat.test.tsx` — ask → streamed answer (reuses useChatStream);
route-hint offers (not acts); unreachable failure; empty-world prompts
onboarding; no write/mint/start from this surface. axe-core.

## Scenario linkage

Verifies scenario **I — "Concierge: find a change / get its status / ask about
your world"** (UC-09). Author scenario I and backfill its `dna:scenario:<ULID>`
(aggregated in WP-027).

## Rollback

Remove the surface; the chat composer is unaffected (still used in the thread).
Revert the commit.
