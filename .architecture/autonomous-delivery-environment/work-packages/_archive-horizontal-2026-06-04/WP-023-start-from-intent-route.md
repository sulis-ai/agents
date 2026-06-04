---
id: WP-023
title: "POST /api/changes/start-from-intent — classify → clone-if-absent → sulis-change start (act, confirm-gated)"
kind: backend
source: feature
change_id: 01KT500K2JTE2EGW6TPPQ4D4VN
parent_phase: chat
parent_group: discovery

atomic_branch: yes
estimate: 7h
blast_radius: high         # starts a real change; clones repos
primitive: EXPAND-Create
group: expand
acceptance_criteria:
  - "POST /api/changes/start-from-intent {phase:propose} resolves intent → change PRIMITIVE + SLUG via the EXISTING _specify_classifier + change-primitives vocabulary (FR-29); ambiguous intent ⇒ 422 INTENT_AMBIGUOUS (asks one clarifying question, never guesses)"
  - "{phase:confirm} maps the chosen Project's source={repo,path,primary_branch} to --repo-root and runs `sulis-change start`, so the change appears on the board at RECON; streams StartFromIntentStreamEvent SSE (state/chunk/proposal/started/error); confirm-gated via WP-020 (FR-N6); stale confirm ⇒ 422 START_CONFIRM_STALE"
  - "LOCAL-FIRST (FR-30): if the Project's repo is not present, it is CLONED from Project.source.repo first (bounded by the 5s-class subprocess timeout); a clone failure ⇒ 502 REPO_UNREACHABLE, visible failure, and NO change started"
  - "INVESTIGATION CONTAINMENT (FR-34/FR-N9): kind:investigation creates a real investigation change (after confirm) to CONTAIN the work — it does NOT run exploration inline; the change lands at Recon exactly like a build change"
  - "One-in-flight: a second start ⇒ 409 SESSION_BUSY; one structured act-log line {act:start, outcome, code?} per act — never the intent text (NFR-SEC-03 posture)"
  - "Reaches consequence only through the sanctioned `sulis-change start` path — no new gate write-exception (ADR-006); reads no surface starts a process (NFR-SEC-05)"
test_plan:
  unit:
    - "apps/cockpit/server/tests/startFromIntent.classify.test.ts (NEW) — intent → primitive+slug via the existing classifier (FR-29); ambiguous ⇒ INTENT_AMBIGUOUS; investigation kind resolves to a change, not inline work (FR-34/N9)"
  integration:
    - "apps/cockpit/server/tests/startFromIntent.clone.test.ts (NEW) — absent repo ⇒ clone from fixture-local-repo-for-clone then start at Recon (FR-30); broken variant ⇒ REPO_UNREACHABLE + no change started"
    - "apps/cockpit/server/tests/routes.startChange.test.ts (NEW) — supertest with recording-bridge-discovery-session: propose→started SSE; confirm-gated; 422 ambiguous/stale; 409 busy; investigation containment (change created, no inline exploration)"
  verification:
    - "bash apps/cockpit/scripts/check-read-only.sh exits 0"
    - "branch-ci green"
verification_gates: [unit, integration, smoke]
verification:
  adapter: backend
  artifact: "apps/cockpit/server/tests/routes.startChange.test.ts"
  deferred-to-follow-on: fixture-local-repo-for-clone
  # classify/clone/start/containment concrete against fixtures; the LIVE start
  # (real classifier, real clone, real sulis-change start) is deferred + manual.

derived_from:
  - finding: "ADR-006 concierge routes start to this confirm-gated endpoint (not inline); ADR-007 reuse classifier + sulis-change start; TDD §3.6 local-first clone + concierge containment + §2.4 startFromIntent row + §5.1 start-from-intent row; FR-29, FR-30, FR-34, FR-N6, FR-N9; openapi /api/changes/start-from-intent"
    found_in: .architecture/autonomous-delivery-environment/adrs/ADR-007-discovery-orchestrates-skills-and-spine-emitters.md
    severity_at_discovery: n/a
generated_by:
  activity: plan-work-run/2026-06-04T09:20:00Z
  agent: sulis:engineering-architect
addresses_findings: []
invalidated_by: { activity: null, result: null }

status: pending
depends_on: [WP-001, WP-006, WP-007, WP-017, WP-020]
# bridge port + recorded fixture + start-from-intent stream types + confirm gate
# (NOTE: does NOT depend on WP-022 — start-from-intent presumes a Product/Project
#  already exists, UC-08 precondition; onboarding mints them in a separate flow)

child_wps: []
kinds: null

# safety posture on the change-start act path:
security_constraints:
  - "Confirm-gated (WP-020); no change started without confirm (FR-N6)"
  - "Local-first clone bounded; clone failure ⇒ visible failure + NO change started (FR-30)"
  - "Investigation is contained in a change — never inline exploration (FR-34, FR-N9)"
  - "Consequence only via sanctioned sulis-change start; no new gate write-exception (ADR-006); no intent text in logs (NFR-SEC-03)"

verifies_scenario: "PENDING-MINT:H"   # Start-from-intent (UC-08); the investigation path also exercises scenario J (UC-10)

rollback: |
  New startFromIntent lib + route + tests. Remove the mount + files; revert the
  commit. A change is started only after a confirmed, reachable repo, so an
  in-flight removal cannot leave an orphaned half-started change. No read
  surface affected; the gate is unchanged.
---

# POST /api/changes/start-from-intent — classify → clone-if-absent → sulis-change start (act, confirm-gated)

## Why

Turns plain-English intent into a started change (UC-08), and is **also** the
path an investigation takes (UC-10, FR-34): the load-bearing rule (FR-N9) is
that *all* real activity, including investigation, is contained in a change —
never run inline in the concierge turn. Per ADR-006/007 this endpoint reuses
the existing `_specify_classifier` (intent → primitive + slug) and
`sulis-change start` (the change-creation act); it adds only the orchestration,
the confirm gate (WP-020), and the local-first clone. The concierge (WP-019)
**routes** consequential intent here rather than acting itself.

## What changes

- `apps/cockpit/server/lib/discovery/startFromIntent.ts` (NEW, EXPAND-Create) — `classify(intent) → {primitive, slug}` (existing classifier); `start({productId, primitive, slug, kind}, confirm) → Change`; maps `Project.source` → `--repo-root`; clones from `source.repo` first if the repo is absent (local-first); investigation → a contained change.
- `apps/cockpit/server/routes/startChange.ts` (NEW, EXPAND-Create) — `POST /start-from-intent`; drives the bridge; maps to `StartFromIntentStreamEvent` SSE; 422 ambiguous/stale, 409 busy, 502 repo/bridge-unreachable. Mounted on the changes router.

Composes WP-020 (confirm gate) + the existing classifier + `sulis-change
start`, all injected.

## How

`propose` runs the classifier (ambiguous ⇒ `INTENT_AMBIGUOUS`, one clarifying
question, no guess). `confirm` maps the chosen Project's `source` to
`--repo-root`; if the repo is absent it clones from `source.repo` first (5s-class
timeout); a clone failure ⇒ `REPO_UNREACHABLE` and **no** change started.
`kind:investigation` resolves to a real change to **contain** the work
(FR-34/N9) — never inline exploration. Reaches consequence only through
`sulis-change start` (no new gate exception, ADR-006). Does **not** depend on
onboarding (WP-022) — UC-08 presumes a Product/Project already exists.

## Tests

- `startFromIntent.classify.test.ts` — intent → primitive+slug; ambiguous ⇒ INTENT_AMBIGUOUS; investigation → change-not-inline.
- `startFromIntent.clone.test.ts` — absent repo ⇒ clone from `fixture-local-repo-for-clone` then start; broken variant ⇒ REPO_UNREACHABLE + no change.
- `routes.startChange.test.ts` — propose→started SSE; confirm-gated; 422/409; investigation containment.

`verification:` — classify/clone/start/containment **concrete** against
fixtures; the **live** start is **deferred** + manual
(`fixture-local-repo-for-clone`, `recording-bridge-discovery-session`).

## Scenario linkage

Verifies scenario **H — "Start from intent"** (UC-08); the `kind:investigation`
path also exercises scenario **J — "An investigation becomes a change"**
(UC-10). Author scenarios H + J and backfill their `dna:scenario:<ULID>`s
(aggregated in WP-027).

## Rollback

Remove the lib + route + tests; revert. A change starts only after a confirmed,
reachable repo, so removal leaves no orphaned half-started change.
