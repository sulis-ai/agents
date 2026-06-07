---
id: WP-022
title: "POST /api/onboarding/session — orchestrate discovery skills + spine emitters (act, confirm-gated)"
kind: backend
source: feature
change_id: 01KT500K2JTE2EGW6TPPQ4D4VN
parent_phase: chat
parent_group: discovery

atomic_branch: yes
estimate: 8h
blast_radius: high         # the cold-start act path: search → mint the graph
primitive: EXPAND-Create
group: expand
acceptance_criteria:
  - "POST /api/onboarding/session orchestrates the flow over the SAME bridge as the chat (FR-27): SEARCH the chosen area only → ASK → PROPOSE → on CONFIRM find-or-create repo (WP-021) + MINT via the spine emitters; streams OnboardingStreamEvent SSE (state/chunk/proposal/minted/error)"
  - "Search is BOUNDED to the founder's chosen area (FR-N7/NFR-DISC-01): a chosenArea outside the permitted root ⇒ 422 DISCOVERY_SCOPE_VIOLATION; it reuses the existing discover-project/-context/codebase-mapping skills + their skip-list — it reimplements no fs-walk (ADR-007)"
  - "Every entity is minted through the VALIDATED spine emitters (sulis-emit-tenant/-product/-project) — NO onboarding path writes an entity file directly (FR-32/NFR-DISC-03); minted entities are schema-valid"
  - "IDEMPOTENT (FR-31/NFR-DISC-02): an already-minted Tenant/Product/Project is surfaced (proposal.alreadyMinted=true), not duplicated; re-running does not grow the entity count"
  - "CONFIRM-GATED (FR-N6/NFR-DISC-04 via WP-020): mint + repo-create happen ONLY on a confirm turn; ALL-OR-NOTHING (FR-N10/N11): a declined/abandoned flow or a failed repo-create leaves the graph UNCHANGED with NO dangling Product/Project config"
  - "Persists a durable Product/Project config incl. Project.source={repo,path,primary_branch} into the EXISTING graph via the emitters — NO new config store (FR-36/NFR-DISC-06/NFR-DATA-01); ONE Product per onboarding conversation (founder-locked; multi-product deferred)"
  - "One-in-flight: a second discovery session ⇒ 409 SESSION_BUSY; one structured act-log line {act:mint, entity, outcome, code?} per consequential act — never directory contents / prompt / reply (NFR-SEC-03 posture)"
test_plan:
  unit:
    - "apps/cockpit/server/tests/discovery.orchestrator.test.ts (NEW) — sequences search→ask→propose→confirm→mint; asserts it CALLS the existing skills (orchestration, not reimplementation, ADR-007); bounded to fixture-project-directory"
    - "apps/cockpit/server/tests/discovery.emitter-only.test.ts (NEW) — every mint goes through the spine emitters; no direct entity-file write (FR-32)"
  integration:
    - "apps/cockpit/server/tests/routes.onboarding.test.ts (NEW) — supertest with recording-bridge-discovery-session + fixture-project-directory: SSE search→propose→minted; 422 scope-violation; 422 stale confirm; 409 busy; idempotent re-run (no count growth); declined/failed-create leaves graph unchanged (all-or-nothing); ONE Product per conversation"
  verification:
    - "bash apps/cockpit/scripts/check-read-only.sh exits 0 (consequence reached only via the sanctioned emitter path — no new gate write-exception, ADR-006)"
    - "branch-ci green"
verification_gates: [unit, integration, smoke]
verification:
  adapter: backend
  artifact: "apps/cockpit/server/tests/routes.onboarding.test.ts"
  deferred-to-follow-on: recording-bridge-discovery-session
  # search/propose/mint/idempotency/all-or-nothing concrete against fixtures;
  # the LIVE onboarding (real agent, real mint, real git) is deferred + manual.

derived_from:
  - finding: "ADR-007 onboarding orchestrates skills + emitters; ADR-008 repo find-or-create; TDD §3.6 (idempotent mint, all-or-nothing, validated emitter) + §2.4 onboardingOrchestrator row + §5.1 onboarding row; FR-27,28,31,32,35,36, FR-N6,N7,N10,N11, NFR-DISC-01..04,06; openapi /api/onboarding/session"
    found_in: .architecture/autonomous-delivery-environment/adrs/ADR-007-discovery-orchestrates-skills-and-spine-emitters.md
    severity_at_discovery: n/a
generated_by:
  activity: plan-work-run/2026-06-04T09:20:00Z
  agent: sulis:engineering-architect
addresses_findings: []
invalidated_by: { activity: null, result: null }

status: pending
depends_on: [WP-001, WP-006, WP-007, WP-017, WP-020, WP-021]
# bridge port + recorded fixture + onboarding stream types + confirm gate + repo find-or-create

child_wps: []
kinds: null

# LOCKED founder decisions baked in:
locked_decisions:
  - "ONE Product per onboarding conversation (multi-product discovery deferred) — founder-locked"
  - "repo create default LOCAL-ONLY, confirm-gated, no dangling config (inherited from WP-021) — founder-locked"

# safety posture on the cold-start act path:
security_constraints:
  - "Search bounded to the chosen area; no whole-disk / home / parent / sibling roaming (FR-N7, NFR-DISC-01)"
  - "Entity writes ONLY through the validated spine emitters; no freehand entity-file write (FR-32, NFR-DISC-03)"
  - "Confirm-gated + all-or-nothing: no mint/repo-create without confirm; failure leaves the graph unchanged (FR-N6/N10/N11)"
  - "No directory contents / prompt / reply in logs (NFR-SEC-03)"

verifies_scenario: "PENDING-MINT:G"   # Set-up-by-talking (cold-start onboarding, UC-07)

rollback: |
  New onboarding orchestrator + route + tests. Remove the mount + files; revert
  the commit. Mints go through the emitters and only after confirm, so an
  in-flight removal cannot leave a half-written graph (all-or-nothing). No read
  surface affected; the gate is unchanged (consequence via the sanctioned
  emitter path, ADR-006).
---

# POST /api/onboarding/session — orchestrate discovery skills + spine emitters (act, confirm-gated)

## Why

The conversational front door for an **empty** graph (UC-07, FR-27). A form is
useless against nothing to pick — so onboarding is a *conversation that creates
the graph*. Per ADR-007 it is an **orchestration layer** over capabilities that
already exist: the `discover-project`/`-context`/`codebase-mapping` skills
(search), the **validated spine emitters** (mint), and `repoFindOrCreate`
(WP-021). It reimplements nothing — no new fs-walk, no freehand entity write
(the two failure modes ADR-007 rejects). It is confirm-gated (WP-020) and
all-or-nothing (FR-N10/N11), and bakes the two **founder-locked** decisions:
**one Product per conversation**, **local-only repo create**.

## What changes

- `apps/cockpit/server/lib/discovery/onboardingOrchestrator.ts` (NEW, EXPAND-Create) — sequences search → ask → propose → (confirm) → repo find-or-create → mint; probes for an existing entity before minting (idempotency); persists `Project.source` via the emitters as the last step.
- `apps/cockpit/server/routes/onboarding.ts` (NEW, EXPAND-Create) — `POST /session`; drives the bridge; maps to `OnboardingStreamEvent` SSE; 422 scope/stale, 409 busy, 502 unreachable. Mounted at `/api/onboarding`.

The orchestrator composes WP-020 (confirm gate), WP-021 (repo find-or-create),
the existing skills, and the existing emitters — all injected.

## How

Search is bounded to `chosenArea` and delegated to the existing skills (their
skip-list, no roaming). The mint goes **only** through the spine emitters
(Form-pillar guarantee). Before minting, the orchestrator probes the graph and
surfaces an existing entity rather than duplicating (idempotency). Mint +
repo-create wait on the confirm gate; persistence is the last step, conditional
on reachable+confirmed (all-or-nothing). One Product per conversation;
multi-product discovery is deferred (founder-locked). No new config store —
the graph is the durable home (NFR-DATA-01).

## Tests

- `discovery.orchestrator.test.ts` — the sequence; asserts it **calls** the existing skills (orchestration, ADR-007); bounded to `fixture-project-directory`.
- `discovery.emitter-only.test.ts` — every mint via the emitters; no direct file write.
- `routes.onboarding.test.ts` — SSE happy path; 422 scope/stale; 409 busy; idempotent re-run; declined/failed-create leaves graph unchanged; one Product per conversation.

`verification:` — search/propose/mint/idempotency/all-or-nothing are
**concrete** against fixtures; the **live** onboarding (real agent, mint, git)
is **deferred** + manual (`recording-bridge-discovery-session`,
`fixture-project-directory`).

## Scenario linkage

Verifies scenario **G — "Set up by talking (cold-start onboarding)"** (UC-07).
Author scenario G and backfill its `dna:scenario:<ULID>` (aggregated in
WP-027).

## Rollback

Remove the orchestrator + route + tests; revert. All-or-nothing + emitter-only
means no half-written graph survives removal.
