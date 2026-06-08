---
# Identity (WP-01)
id: WP-010
title: "Journey G round-trip: set up by talking → search, propose, confirm, and the graph is minted"
kind: full-round-trip
source: feature
change_id: 01KT500K2JTE2EGW6TPPQ4D4VN
parent_phase: vertical-slice
slice_kind: round-trip
journey: "G — Set up by talking (cold-start onboarding)"

atomic_branch: yes
estimate: 18h          # confirm gate + repo find/create + onboarding orchestrator route + OnboardingChat UI
blast_radius: high     # the cold-start act path: search → mint the graph
primitive: EXPAND-Create
group: expand
visual_contract: WP-002

observed_acceptance:
  scenario: "PENDING-MINT:G"   # author scenario G then backfill dna:scenario:<ULID>
  observable_result: "The first time the founder opens the app with an empty graph, a conversation (not a form) sets them up: they choose an area, answer questions, see a plain-English PROPOSAL (the Tenant/Product/Project + the repo plan), and on CONFIRM the graph is minted and a Product/Project (with Project.source) exists. A declined or failed flow leaves the graph exactly as it was."
  how_observed: "TWO-PART. (1) CI/local with the RecordedSessionBridge + fixtures: drive the onboarding conversation, OBSERVE search→ask→proposal→confirm→minted; OBSERVE the find-vs-create-repo branch with local-only PRE-SELECTED and the neutral two-letter tile; OBSERVE a declined flow creates nothing and a failed repo-create leaves no dangling config; OBSERVE re-running does not grow the entity count (idempotent). (2) BLOCK-and-hand-to-founder: on the founder machine with a real claude + real git, run a real cold-start onboarding and OBSERVE a real Product/Project minted with a real local repo."
  not_sufficient: "Green CI / from-graph run / the recorded observation alone are NOT the full DoD. The slice is DONE only after the founder runs a REAL cold-start onboarding through the running app and OBSERVES a real graph minted (the BLOCK-and-hand-to-founder step)."
  human_hops: "BLOCK-and-hand-to-founder: the live onboarding (real claude agent, real spine-emitter mint, real `git init`) cannot bootstrap in CI; the founder observes it on their machine. Search-bounding, emitter-only mint, idempotency, confirm-gating, and all-or-nothing are observable in CI against the recorded fixtures."

acceptance_criteria:
  - "CONFIRM GATE: lib/discovery/confirmGate.ts is a pure module — a read-and-propose turn needs NO confirmation; the ACT (mint or repo-create) requires an explicit token-matched confirm referencing the live proposal (FR-N6, NFR-DISC-04); a stale/mismatched token is refused (DISCOVERY_CONFIRM_STALE); declined/absent ⇒ gate closed, caller MUST NOT proceed; pure & deterministic (no fs/git/process/bridge), the WP-005 sessionBinding/inFlightLock sibling pattern"
  - "REPO FIND-OR-CREATE: lib/discovery/repoFindOrCreate.ts — FIND branch configures an existing repo from the founder's pointer, bounded to the chosen area (FR-N7), sets Project.source={repo,path,primary_branch}, NO creation; CREATE branch on explicit confirm creates a repo — DEFAULT local-only `git init`, no network, nothing published, fully reversible (FOUNDER-LOCKED; ADR-008); hosted-remote is a SEPARATELY-confirmed createTarget, never the default; NO DANGLING CONFIG (FR-N10/N11): Project.source persisted ONLY after the repo is found-or-created AND reachable AND confirmed; a failed create surfaces REPO_CREATE_FAILED and persists NO config; git bounded by the 5s-class timeout"
  - "ORCHESTRATOR ROUTE: POST /api/onboarding/session orchestrates over the SAME bridge as the chat (FR-27): SEARCH the chosen area only → ASK → PROPOSE → on CONFIRM repo find-or-create + MINT via the spine emitters; streams OnboardingStreamEvent SSE; search bounded (chosenArea outside the root ⇒ 422 DISCOVERY_SCOPE_VIOLATION) and delegates to the EXISTING discover-project/-context/codebase-mapping skills (no reimplemented fs-walk, ADR-007); every entity minted ONLY through the validated spine emitters (no direct entity-file write, FR-32/NFR-DISC-03); IDEMPOTENT (already-minted entity surfaced, not duplicated, FR-31); confirm-gated + ALL-OR-NOTHING (FR-N6/N10/N11); persists a durable Product/Project config incl. Project.source into the EXISTING graph (no new config store, FR-36/NFR-DATA-01); ONE Product per conversation (FOUNDER-LOCKED); second session ⇒ 409 SESSION_BUSY; one structured act-log line per consequential act, never directory/prompt/reply"
  - "UI: the onboarding conversation drives the route over SSE, REUSING the chat composer + SSE client (EP-03): choose area → answer → see PROPOSAL → CONFIRM; the proposal (Tenant/Product/Project + repo plan) is shown in plain English BEFORE any mint; the do-you-have-a-repo branch is explicit FIND vs CREATE with local-only PRE-SELECTED (GitHub a clearly-labelled separate opt-in, FOUNDER-LOCKED); Product icon is a NEUTRAL TWO-LETTER TILE (no logo upload this slice, FOUNDER-LOCKED); a declined flow creates nothing; a failed repo-create / scope-violation is surfaced plainly; consumes tokens.css only; matches the SIGNED visual contract (WP-002)"
  - "OBSERVED ROUND-TRIP (the gate): (a) drive the onboarding conversation against the recorded fixtures and OBSERVE search→proposal→confirm→minted + the locked-decision UI + all-or-nothing + idempotency; (b) BLOCK-and-hand-to-founder: run a REAL cold-start onboarding on the founder machine and OBSERVE a real graph minted with a real local repo. DONE only after (b)."
test_plan:
  unit:
    - "apps/cockpit/server/tests/confirmGate.test.ts (NEW) — propose-without-confirm → closed; matching confirm → open once; stale/mismatched → refused; declined → closed; deterministic"
    - "apps/cockpit/server/tests/repoFindOrCreate.test.ts (NEW) — find vs fixture-project-directory (configures, no creation); create git init into fixture-repo-create-target (confirm-gated); simulated create-failure persists NO config (dangling-config assertion, FR-N10/N11); unconfirmed create is a no-op"
    - "apps/cockpit/server/tests/discovery.orchestrator.test.ts (NEW) — sequences search→ask→propose→confirm→mint; asserts it CALLS the existing skills (orchestration, ADR-007); bounded to fixture-project-directory"
    - "apps/cockpit/server/tests/discovery.emitter-only.test.ts (NEW) — every mint via the spine emitters; no direct entity-file write (FR-32)"
  integration:
    - "apps/cockpit/server/tests/routes.onboarding.test.ts (NEW) — supertest with recording-bridge-discovery-session + fixture-project-directory: SSE search→propose→minted; 422 scope-violation; 422 stale confirm; 409 busy; idempotent re-run (no count growth); declined/failed-create leaves graph unchanged (all-or-nothing); ONE Product per conversation"
    - "apps/cockpit/client/src/tests/OnboardingChat.test.tsx (NEW) — search→ask→proposal→confirm→minted (reuses useChatStream); find-vs-create with local-only PRE-SELECTED; neutral two-letter tile (no upload control); declined flow creates nothing; failed-create leaves setup unchanged; scope-violation surfaced; one Product per conversation"
  observed:
    - "DRIVEN (recorded): drive the onboarding conversation against the fixtures, OBSERVE the full search→proposal→confirm→minted flow + locked-decision UI + all-or-nothing + idempotency"
    - "BLOCK-AND-HAND-TO-FOUNDER (the live gate): founder runs a REAL cold-start onboarding, OBSERVES a real Product/Project minted with a real local repo"
  verification:
    - "bash apps/cockpit/scripts/check-read-only.sh exits 0 (consequence reached only via the sanctioned emitter path — no new gate write-exception, ADR-006)"
    - "axe-core a11y on the onboarding conversation green"
    - "branch-ci green"
    - "OBSERVED live round-trip on the founder machine recorded"
verification_gates: [unit, integration, component, visual_diff, a11y, observed_roundtrip, live_founder_machine]
verification:
  adapter: backend
  artifact: "apps/cockpit/server/tests/routes.onboarding.test.ts"
  deferred-to-follow-on: recording-bridge-discovery-session
  # search/propose/mint/idempotency/all-or-nothing concrete against fixtures now;
  # the LIVE onboarding (real agent, real mint, real git) is the BLOCK-and-hand-to-founder observation.

infrastructure_needs:
  - id: recording-bridge-discovery-session
    why: "recorded discovery-session stream-json fixture for the onboarding orchestration (search→ask→confirm→mint), CI-testable + recorded-observable without a live agent"
  - id: fixture-project-directory
    why: "a seeded local folder (plus an already-minted variant) so search-scope (FR-N7), dedupe (FR-31), and the discovery skills' orchestration verify from a fresh clone"
  - id: fixture-repo-create-target
    why: "a writable temp dir as the local repo-creation target (plus a deliberately-failing variant) so the confirm-gated git-init create (FR-35/FR-N10) and no-dangling-config-on-failure (FR-N10/N11) verify in CI"

derived_from:
  - finding: "Re-slice vertical: Journey G (cold-start onboarding). Folds prior horizontal WP-020 (confirm gate) + WP-021 (repo find-or-create) + WP-022 (onboarding orchestrator route) + WP-026 (OnboardingChat UI) into ONE observable round-trip. ADR-007 onboarding orchestrates skills + emitters; ADR-008 repo local-first; FR-27,28,31,32,35,36, FR-N6,N7,N10,N11, NFR-DISC-01..04,06. Carries all three founder-locked decisions."
    found_in: .architecture/autonomous-delivery-environment/adrs/ADR-007-discovery-orchestrates-skills-and-spine-emitters.md
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

locked_decisions:
  - "repo create default LOCAL-ONLY (git init); hosted-remote (GitHub) is a separately-confirmed, clearly-labelled opt-in, never the default (ADR-008, founder-locked); pre-selected in the UI"
  - "ONE Product per onboarding conversation (multi-product setup deferred) — founder-locked"
  - "Product icon = NEUTRAL TWO-LETTER TILE — no logo upload control in this slice — founder-locked"

security_constraints:
  - "Search bounded to the chosen area; no whole-disk / home / parent / sibling roaming (FR-N7, NFR-DISC-01)"
  - "Entity writes ONLY through the validated spine emitters; no freehand entity-file write (FR-32, NFR-DISC-03)"
  - "Confirm-gated + all-or-nothing: no mint/repo-create without confirm; failure leaves the graph unchanged (FR-N6/N10/N11)"
  - "No directory contents / prompt / reply in logs (NFR-SEC-03)"

verifies_scenario: "PENDING-MINT:G"   # Set-up-by-talking (cold-start onboarding, UC-07)

rollback: |
  New confirmGate + repoFindOrCreate + onboardingOrchestrator + onboarding route +
  OnboardingChat surface (reusing Composer + useChatStream). Remove the mount +
  files + surface; revert the commit. Mints go through the emitters and only after
  confirm, with all-or-nothing persistence, so an in-flight removal cannot leave a
  half-written graph or dangling config. The chat composer is unaffected; the gate
  is unchanged (consequence via the sanctioned emitter path, ADR-006).
---

# Journey G round-trip: set up by talking → the graph is minted

## The round-trip this slice delivers

**Open the app on an empty graph → (action: have the setup conversation, confirm
the proposal) → OBSERVE: a real Product/Project minted, with a repo, ready to
work.** A form is useless against nothing to pick, so onboarding is a
*conversation that creates the graph*. The orchestrator route and the
conversational UI that drives it ship together, with the confirm gate and repo
find-or-create that the act depends on — the whole cold-start round-trip in one
branch.

It **reuses** the chat composer + SSE client from WP-005 (EP-03), so it depends on
the chat slice rather than rebuilding a composer. It is an **orchestration layer**
over capabilities that already exist (the discover-project/-context/codebase-mapping
skills, the validated spine emitters) — it reimplements nothing (ADR-007).

## The three founder-locked decisions baked in

1. **Repo create default LOCAL-ONLY** (`git init`, no network, nothing published, reversible) — pre-selected in the UI; GitHub is a clearly-labelled separate opt-in, never the default (ADR-008).
2. **One Product per onboarding conversation** (multi-product setup deferred).
3. **Product icon = neutral two-letter tile** — no logo upload control this slice.

## The observed-acceptance gate (MUST) — TWO parts

- **(a) Recorded round-trip (CI / local):** drive the onboarding conversation
  against the recorded fixtures and **see** search→proposal→confirm→minted, the
  find-vs-create branch with local-only pre-selected, the neutral tile, a declined
  flow creating nothing, a failed create leaving no dangling config, and an
  idempotent re-run not growing the entity count.
- **(b) BLOCK-and-hand-to-founder — the live mint:** on the founder machine with a
  real `claude` + real `git`, run a real cold-start onboarding and **observe** a
  real Product/Project minted with a real local repo. **The slice is not "done"
  until this is observed.**

Author scenario G and run it from-graph on top of the live observation.

## Fix-forward (2026-06-04) — the mint is server-side deterministic

Driving the confirm→mint LIVE against a sandbox brain with a real `claude`
bridge surfaced that the **mint minted nothing**: the request ran 167s, returned
200, and the agent only narrated "let me locate the emitters" — no
Tenant/Product/Project landed. The recorded-bridge test passed because it
*stubbed* the bridge (it proved a prompt was relayed, not that a graph was
minted).

The fix (ADR-007 amended): the bridge AGENT keeps the **conversation** (search /
clarify / propose, read-only); the **mint** + repo `git init` move to a
deterministic SERVER action behind a new `SpineMinter` port. Its adapter
(`SpineEmitterMinter`) invokes the validated spine-emitter CLIs
(`sulis-emit-tenant` / `-product`) + a schema-validated Project emit directly
via `child_process` into the active `SULIS_STATE_DIR` brain — all-or-nothing
(staged, promoted only on full success), idempotent (deterministic ULIDs). It is
the cockpit's second sanctioned process-start / write site (read-only gate
allow-listed by path). A new integration test
(`server/tests/discovery.mint-real.test.ts`) drives a confirm against a temp
state dir and asserts REAL entities land with `Project.source` persisted — the
thing that failed live.

## Rollback

All-or-nothing + emitter-only means no half-written graph or dangling config
survives removal. The chat composer and the gate are unaffected. Revert the commit.
