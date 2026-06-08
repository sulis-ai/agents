---
# Identity (WP-01)
id: WP-011
title: "Journey H+J round-trip: say what you want → a change starts at Recon (incl. investigation→change)"
kind: full-round-trip
source: feature
change_id: 01KT500K2JTE2EGW6TPPQ4D4VN
parent_phase: vertical-slice
slice_kind: round-trip
journey: "H — Start from intent; J — An investigation becomes a change"

atomic_branch: yes
estimate: 13h
blast_radius: high     # starts a real change; clones repos
primitive: EXPAND-Create
group: expand
visual_contract: WP-002

observed_acceptance:
  scenario: "PENDING-MINT:H"   # author scenario H then backfill dna:scenario:<ULID>
  also_exercises: "PENDING-MINT:J"   # J — investigation becomes a change (UC-10)
  observable_result: "The founder says in plain English what they want ('fix the login bug', 'look into why checkout is slow'); the app classifies it into a change primitive + slug, shows the proposal, and on CONFIRM a change starts and appears on the board at Recon. An investigation does NOT run inline — it is CONTAINED in a real change that lands at Recon exactly like a build change. If the Project's repo is absent it is cloned first; a clone failure starts NO change."
  how_observed: "TWO-PART. (1) CI/local with the RecordedSessionBridge + fixtures: drive the intent flow, OBSERVE classify→proposal→confirm→started and the new change appearing at Recon; OBSERVE an ambiguous intent asks one clarifying question (no guess); OBSERVE an investigation request creates a contained change, not inline work; OBSERVE an absent repo is cloned first and a broken clone starts no change. (2) BLOCK-and-hand-to-founder: on the founder machine with a real claude + real git + real sulis-change start, say a real intent and OBSERVE a real change start at Recon on the board."
  not_sufficient: "Green CI / from-graph run / the recorded observation alone are NOT the full DoD. The slice is DONE only after the founder says a REAL intent through the running app and OBSERVES a real change start on the board (the BLOCK-and-hand-to-founder step)."
  human_hops: "BLOCK-and-hand-to-founder: the live start (real classifier, real `git clone`, real `sulis-change start`) cannot bootstrap in CI; the founder observes the change appearing on the board on their machine. Classification, ambiguity handling, investigation containment, clone-then-start, and confirm-gating are observable in CI against the recorded fixtures."

acceptance_criteria:
  - "ROUTE (propose): POST /api/changes/start-from-intent {phase:propose} resolves intent → change PRIMITIVE + SLUG via the EXISTING _specify_classifier + change-primitives vocabulary (FR-29); ambiguous intent ⇒ 422 INTENT_AMBIGUOUS (asks one clarifying question, never guesses)"
  - "ROUTE (confirm): {phase:confirm} maps the chosen Project's source={repo,path,primary_branch} to --repo-root and runs `sulis-change start` so the change appears on the board at RECON; streams StartFromIntentStreamEvent SSE; confirm-gated via the WP-010 confirmGate (FR-N6); stale confirm ⇒ 422 START_CONFIRM_STALE"
  - "LOCAL-FIRST (FR-30): if the Project's repo is not present, it is CLONED from Project.source.repo first (bounded by the 5s-class subprocess timeout); a clone failure ⇒ 502 REPO_UNREACHABLE, visible failure, NO change started"
  - "INVESTIGATION CONTAINMENT (FR-34/FR-N9): kind:investigation creates a real investigation change (after confirm) to CONTAIN the work — it does NOT run exploration inline; the change lands at Recon exactly like a build change"
  - "ONE-IN-FLIGHT/LOG/GATE: a second start ⇒ 409 SESSION_BUSY; one structured act-log line {act:start, outcome, code?} per act, never the intent text (NFR-SEC-03); reaches consequence only through the sanctioned `sulis-change start` path — no new gate write-exception (ADR-006)"
  - "UI: the founder triggers start-from-intent from the concierge front door's route-offer (WP-009) OR a direct intent box; the proposal (primitive + slug + repo plan) is shown before confirm; on confirm the change starts and the board (WP-003) shows it at Recon; an investigation offer is clearly framed as 'I'll create a change to look into this' (not inline); consumes tokens.css only; matches the SIGNED visual contract (WP-002)"
  - "OBSERVED ROUND-TRIP (the gate): (a) drive the intent flow against the recorded fixtures and OBSERVE classify→proposal→confirm→started at Recon, ambiguity handling, investigation containment, clone-then-start; (b) BLOCK-and-hand-to-founder: say a REAL intent on the founder machine and OBSERVE a real change start at Recon on the board. DONE only after (b)."
test_plan:
  unit:
    - "apps/cockpit/server/tests/startFromIntent.classify.test.ts (NEW) — intent → primitive+slug via the existing classifier (FR-29); ambiguous ⇒ INTENT_AMBIGUOUS; investigation kind resolves to a change, not inline work (FR-34/N9)"
  integration:
    - "apps/cockpit/server/tests/startFromIntent.clone.test.ts (NEW) — absent repo ⇒ clone from fixture-local-repo-for-clone then start at Recon (FR-30); broken variant ⇒ REPO_UNREACHABLE + no change started"
    - "apps/cockpit/server/tests/routes.startChange.test.ts (NEW) — supertest with recording-bridge-discovery-session: propose→started SSE; confirm-gated; 422 ambiguous/stale; 409 busy; investigation containment (change created, no inline exploration)"
    - "apps/cockpit/client/src/tests/StartFromIntent.test.tsx (NEW) — intent box / concierge route-offer → proposal → confirm → change-appears; investigation framed as a contained change; ambiguity surfaced"
  observed:
    - "DRIVEN (recorded): drive the intent flow against the fixtures, OBSERVE classify→proposal→confirm→started + ambiguity + investigation containment + clone-then-start"
    - "BLOCK-AND-HAND-TO-FOUNDER (the live gate): founder says a real intent, OBSERVES a real change start at Recon on the board"
  verification:
    - "bash apps/cockpit/scripts/check-read-only.sh exits 0"
    - "axe-core a11y on the start-from-intent surface green"
    - "branch-ci green"
    - "OBSERVED live round-trip on the founder machine recorded"
verification_gates: [unit, integration, component, visual_diff, a11y, observed_roundtrip, live_founder_machine]
verification:
  adapter: backend
  artifact: "apps/cockpit/server/tests/routes.startChange.test.ts"
  deferred-to-follow-on: fixture-local-repo-for-clone
  # classify/clone/start/containment concrete against fixtures now;
  # the LIVE start (real classifier, real clone, real sulis-change start) is the BLOCK-and-hand-to-founder observation.

infrastructure_needs:
  - id: recording-bridge-discovery-session
    why: "recorded discovery-session stream-json fixture for the classify→clone→start orchestration, CI-testable without a live agent"
  - id: fixture-local-repo-for-clone
    why: "a local git repo usable as a Project.source.repo clone target (plus a deliberately-broken variant) so local-first clone-then-start and clone-failure (FR-30) verify without network"

derived_from:
  - finding: "Re-slice vertical: Journeys H + J. Folds prior horizontal WP-023 (start-from-intent route incl. investigation containment) + the start/investigate route-offer half of WP-025 into ONE observable round-trip. H (start) and J (investigation) ship together because J IS the start-from-intent endpoint with kind:investigation. Reuses the confirmGate from WP-010. ADR-006/007; FR-29, FR-30, FR-34, FR-N6, FR-N9."
    found_in: .architecture/autonomous-delivery-environment/adrs/ADR-007-discovery-orchestrates-skills-and-spine-emitters.md
    severity_at_discovery: n/a
generated_by:
  activity: re-slice-vertical/2026-06-04
  agent: sulis:engineering-architect
addresses_findings: []
invalidated_by: { activity: null, result: null }

status: pending
depends_on: [WP-001, WP-002, WP-003, WP-005, WP-009, WP-010]
# data contract + visual contract + the board the change appears on (WP-003) + the chat composer/SSE + bridge (WP-005)
# + the concierge route-offer that triggers it (WP-009) + the confirmGate (WP-010)
# NOTE: presumes a Product/Project already exists (UC-08 precondition) — onboarding (WP-010) mints them in a separate flow,
#       but this slice reuses WP-010's confirmGate, hence the dep.

child_wps: []
kinds: null

security_constraints:
  - "Confirm-gated (WP-010's confirmGate); no change started without confirm (FR-N6)"
  - "Local-first clone bounded; clone failure ⇒ visible failure + NO change started (FR-30)"
  - "Investigation is contained in a change — never inline exploration (FR-34, FR-N9)"
  - "Consequence only via sanctioned sulis-change start; no new gate write-exception (ADR-006); no intent text in logs (NFR-SEC-03)"

verifies_scenario:
  - "PENDING-MINT:H"   # Start-from-intent (UC-08)
  - "PENDING-MINT:J"   # Investigation becomes a change (UC-10)

rollback: |
  New startFromIntent lib + startChange route + the intent/route-offer UI. Remove
  the mount + files + UI; revert the commit. A change starts only after a
  confirmed, reachable repo, so removal cannot leave an orphaned half-started
  change. The confirmGate (WP-010), the concierge (WP-009), and read surfaces are
  unaffected; the gate is unchanged.
---

# Journey H+J round-trip: say what you want → a change starts (incl. investigation→change)

## The round-trip this slice delivers

**Say what you want in plain English → (action: confirm the proposal) → OBSERVE:
a change starts and appears on the board at Recon.** The classify→clone→start
route and the UI that triggers it (the concierge's route-offer from WP-009, plus
a direct intent box) ship together. H (start-from-intent) and J
(investigation→change) are **one slice** because J *is* the same endpoint with
`kind:investigation` — the load-bearing rule (FR-N9) is that investigation, like
all real work, is contained in a change, never run inline.

It reuses the `confirmGate` from WP-010 (the cold-start slice) and the chat
bridge/composer from WP-005, and presumes a Product/Project already exists
(UC-08 precondition — onboarding mints them).

## What changes (the whole round-trip, one branch)

- **Route + lib (server):** `lib/discovery/startFromIntent.ts`
  (`classify(intent)→{primitive,slug}` via the existing `_specify_classifier`;
  `start({productId,primitive,slug,kind}, confirm)→Change`; maps `Project.source`
  → `--repo-root`; clones from `source.repo` first if absent (local-first);
  investigation → a contained change); `routes/startChange.ts`
  (`POST /start-from-intent`, drives the bridge, maps to
  `StartFromIntentStreamEvent` SSE, 422 ambiguous/stale, 409 busy, 502
  repo/bridge-unreachable). Reaches consequence only through `sulis-change start`
  (no new gate exception, ADR-006).
- **UI (client):** the start-from-intent surface — triggered from the concierge
  front door's route-offer (WP-009) and/or a direct intent box; renders the
  proposal (primitive + slug + repo plan) before confirm; on confirm shows the new
  change at Recon on the board (WP-003); frames an investigation as "I'll create a
  change to look into this".

## The observed-acceptance gate (MUST) — TWO parts

- **(a) Recorded round-trip (CI / local):** drive the intent flow against the
  recorded fixtures and **see** classify→proposal→confirm→started at Recon;
  **see** an ambiguous intent ask one clarifying question; **see** an investigation
  create a contained change (not inline work); **see** an absent repo cloned first
  and a broken clone start no change.
- **(b) BLOCK-and-hand-to-founder — the live start:** on the founder machine with a
  real `claude` + real `git` + real `sulis-change start`, say a real intent and
  **observe** a real change start at Recon on the board. **The slice is not "done"
  until this is observed.**

Author scenarios H and J and run them from-graph on top of the live observation.

## Rollback

A change starts only after a confirmed, reachable repo, so removal leaves no
orphaned half-started change. The confirmGate, concierge, and read surfaces are
unaffected. Revert the commit.
