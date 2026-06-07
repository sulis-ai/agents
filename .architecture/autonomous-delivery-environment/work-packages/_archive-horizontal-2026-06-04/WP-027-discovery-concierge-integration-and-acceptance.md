---
id: WP-027
title: "Expanded-scope integration: discovery/concierge bridge end-to-end + a11y/visual sweep + from-graph acceptance (G–K)"
kind: composite
source: feature
change_id: 01KT500K2JTE2EGW6TPPQ4D4VN
parent_phase: integration
parent_group: expanded-scope

atomic_branch: yes
estimate: 7h
blast_radius: high         # ties the expanded scope together; the parent merge gate for the new surfaces
primitive: REINFORCE-Test
group: reinforce
visual_contract: WP-002
acceptance_criteria:
  - "The concierge + onboarding + start-from-intent paths run end-to-end against the recorded fixtures in CI, then are swapped to the LIVE bridge on the founder machine (CF-07 conformance: recorded→real parity, same suite both adapters) — mirrors WP-016's mock→real swap"
  - "a11y (axe-core) + visual sweep across ALL new surfaces (product switcher, concierge front door, onboarding conversation) against the SIGNED visual contract (WP-002 — now covers concierge, conversational setup, product switcher, per-product board)"
  - "from-graph acceptance runs the five NEW scenarios via `sulis-verify-acceptance --scenario`: G set-up-by-talking, H start-from-intent, I concierge-ask, J investigation→change, K product-switch — each linked to its delivering WP(s)"
  - "The whole expanded scope stays provably read-only except the two sanctioned consequence paths (emitter mint, sulis-change start) + the scope-selection verb: the extended read-only gate is green; no surface beyond those reaches consequence (FR-N1, FR-N8, ADR-006/009)"
  - "All-or-nothing + no-dangling-config holds end-to-end: a declined/failed onboarding leaves the graph unchanged (FR-N10/N11); a clone-failure starts no change (FR-30)"
  - "Idempotency holds end-to-end: re-running onboarding against the same area does not grow the entity count (FR-31); durable config round-trips across sessions (FR-36)"
test_plan:
  unit: []
  integration:
    - "apps/cockpit/server/tests/discovery.conformance.test.ts (NEW) — the CF-07 recorded→real conformance: the SessionBridge contract suite passes against RecordedSessionBridge AND (on the founder machine) StreamJsonSessionBridge for the discovery/concierge paths"
    - "apps/cockpit/server/tests/durableConfig.roundtrip.test.ts (NEW) — mint Project.source in one session, read back + start a change in a FRESH session, no re-discovery, no new config store (FR-36, NFR-DISC-06, NFR-DATA-01)"
    - "apps/cockpit/client/src/tests/expanded-a11y.e2e.test.tsx (NEW) — axe-core across product switcher / concierge / onboarding surfaces; visual check vs the signed contract"
  verification:
    - "sulis-verify-acceptance --scenario G,H,I,J,K  (from-graph; all five linked + green)"
    - "bash apps/cockpit/scripts/check-read-only.sh exits 0 (the full extended gate)"
    - "branch-ci green; manual live swap on the founder machine recorded"
verification_gates: [integration, a11y, visual_diff, smoke]
verification:
  adapter: backend
  artifact: "apps/cockpit/server/tests/discovery.conformance.test.ts"
  deferred-to-follow-on: recording-bridge-discovery-session
  # CI runs against recorded fixtures; the LIVE discovery/concierge swap
  # (real claude -p, real mint, real git clone, real sulis-change start, and
  # real hosted-remote create IF the founder opts in) is verified manually.

derived_from:
  - finding: "TDD §4.3 (what's added for the expanded scope) + §9 Verification Plan (discovery/concierge deferred rows, durable-config round-trip, per-Product scope); ADR-006/007/008/009; FR-27..38, FR-N6..N11, NFR-DISC-01..06; scenarios G–K"
    found_in: .architecture/autonomous-delivery-environment/TDD.md
    severity_at_discovery: n/a
generated_by:
  activity: plan-work-run/2026-06-04T09:20:00Z
  agent: sulis:engineering-architect
addresses_findings: []
invalidated_by: { activity: null, result: null }

status: pending
depends_on: [WP-018, WP-019, WP-021, WP-022, WP-023, WP-024, WP-025, WP-026]
# all expanded-scope backend + frontend WPs (the integration is last, CF-05)

child_wps: []
kinds: null
composite_of:
  - "CF-07 recorded→real bridge conformance for the discovery/concierge paths"
  - "a11y + visual sweep across the new surfaces"
  - "from-graph acceptance for scenarios G–K"
  - "end-to-end read-only / all-or-nothing / idempotency / durable-config guarantees"

# safety posture — the expanded-scope parent merge gate:
security_constraints:
  - "Whole expanded scope provably read-only except the two sanctioned consequence paths + the scope-selection verb (FR-N1, FR-N8, ADR-006/009)"
  - "All-or-nothing + no-dangling-config + idempotency + durable-config hold end-to-end (FR-N10/N11, FR-31, FR-36)"

verifies_scenario: "PENDING-MINT:G,H,I,J,K"   # aggregates all five NEW scenarios for from-graph verification

rollback: |
  Test-only WP (REINFORCE-Test) plus the live-swap wiring. Remove the new test
  files + the live-bridge swap config; revert the commit. The expanded-scope
  feature WPs (017–026) are unaffected — this WP only verifies them.
---

# Expanded-scope integration: discovery/concierge bridge end-to-end + a11y/visual sweep + from-graph acceptance (G–K)

## Why

The integration child for the expanded scope — the parent merge gate for the
concierge, onboarding/discovery, start-from-intent, and multi-product surfaces.
It mirrors WP-016 (the chat integration): run the new paths against the recorded
fixtures in CI, then swap to the **live** bridge on the founder machine
(CF-07 conformance — same suite, both adapters). It sweeps a11y + visual across
all the new surfaces against the **signed** visual contract (WP-002, which now
covers concierge, conversational setup, product switcher, per-product board),
and runs the five **new** scenarios from-graph.

## What changes

- `apps/cockpit/server/tests/discovery.conformance.test.ts` (NEW) — the CF-07 recorded→real conformance for the discovery/concierge bridge paths.
- `apps/cockpit/server/tests/durableConfig.roundtrip.test.ts` (NEW) — mint→read-back across two sessions; no new config store (FR-36).
- `apps/cockpit/client/src/tests/expanded-a11y.e2e.test.tsx` (NEW) — axe-core + visual sweep across the new surfaces.
- Live-swap wiring on the founder machine (RecordedSessionBridge → StreamJsonSessionBridge for the discovery/concierge paths), as WP-016 does for the chat.

## How

Reuse the `SessionBridge` contract suite (one suite, both adapters) extended to
the discovery/concierge interactions. The CI guarantees use the recorded
fixtures (`recording-bridge-discovery-session`, `fixture-project-directory`,
`fixture-local-repo-for-clone`, `fixture-repo-create-target`). The live path —
real agent, real mint, real `git clone`, real `sulis-change start`, and real
**hosted-remote** create *if the founder opts in* — is verified manually on the
founder machine (it cannot fully bootstrap in CI). The extended read-only gate
is the end-to-end safety assertion.

## Scenario linkage (from-graph verification)

Aggregates the five **new** scenarios for `sulis-verify-acceptance --scenario`:

| Scenario | Delivering WP(s) |
|---|---|
| **G** — Set up by talking (cold-start onboarding) | WP-022, WP-026 (+ WP-021 repo step) |
| **H** — Start from intent | WP-023, (front-door via WP-025) |
| **I** — Concierge: find / status / ask | WP-019, WP-025 |
| **J** — An investigation becomes a change | WP-023 (`kind:investigation`), WP-025 (route) |
| **K** — Switch the active Product; the board re-scopes | WP-018, WP-024 |

Scenarios G–K are not yet minted. Author them (`sulis-author-scenario` in the
specify step) and backfill each `dna:scenario:<ULID>` into the delivering WPs'
`verifies_scenario` and into this WP's aggregate, so the from-graph run is
linked end-to-end (the six original scenarios A–F are aggregated by WP-016).

## Rollback

Test-only + live-swap wiring. Remove the new test files + the swap config;
revert. The feature WPs (017–026) are unaffected.
