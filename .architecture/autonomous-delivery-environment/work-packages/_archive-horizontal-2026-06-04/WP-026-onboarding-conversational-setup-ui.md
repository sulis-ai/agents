---
id: WP-026
title: "Conversational setup UI: onboarding chat with the find-vs-create-repo + confirm branch"
kind: frontend
source: feature
change_id: 01KT500K2JTE2EGW6TPPQ4D4VN
parent_phase: surfaces
parent_group: discovery

atomic_branch: yes
estimate: 7h
blast_radius: medium       # the cold-start front door; drives the act path
primitive: EXPAND-Create
group: expand
visual_contract: WP-002
acceptance_criteria:
  - "The onboarding conversation drives POST /api/onboarding/session over SSE (OnboardingStreamEvent), REUSING the chat composer + SSE client (EP-03): the founder chooses an area, answers questions, sees the PROPOSAL, and CONFIRMS — the mint happens only on confirm (FR-27, FR-N6)"
  - "The proposal is shown in plain English (the Tenant/Product/Project + the repo plan) BEFORE any mint; a declined/abandoned flow creates nothing (FR-N6, FR-N11 surfaced client-side)"
  - "The do-you-have-a-repo branch is explicit: FIND (point at an existing repo) vs CREATE (default a plain repo on your machine — local-only; GitHub is a separate, clearly-labelled opt-in) — the LOCKED local-only default is the pre-selected choice (FR-35, ADR-008)"
  - "Product icon is a NEUTRAL TWO-LETTER TILE (no logo upload in this slice — founder-locked); ONE Product per conversation (founder-locked); an already-set-up entity is surfaced, not re-created (FR-31)"
  - "A failed repo-create shows a clear plain-English failure and leaves the setup as it was (FR-N10/N11); a scope-violation (area outside the permitted root) is surfaced plainly (FR-N7)"
  - "Consumes tokens.css only; matches the SIGNED visual contract (WP-002 — now covers the conversational-setup surface)"
test_plan:
  unit: []
  integration:
    - "apps/cockpit/client/src/tests/OnboardingChat.test.tsx (NEW) — search→ask→proposal→confirm→minted (reuses useChatStream); find-vs-create branch with local-only PRE-SELECTED; neutral two-letter tile (no upload control); declined flow creates nothing; failed-create leaves setup unchanged; scope-violation surfaced; one Product per conversation"
  verification:
    - "axe-core a11y on the onboarding conversation green"
    - "branch-ci green"
verification_gates: [unit, component, visual_diff, a11y, perf_budget]
verification:
  adapter: frontend
  artifact: "apps/cockpit/client/src/tests/OnboardingChat.test.tsx"

derived_from:
  - finding: "ADR-007 onboarding conversation; ADR-008 find-vs-create local-first default; TDD §2.4 OnboardingChat row + §5.1 onboarding row; FR-27,31,35, FR-N6,N7,N10,N11; visual contract covers the conversational-setup surface; founder-locked: local-only repo, one Product, neutral two-letter tile"
    found_in: .architecture/autonomous-delivery-environment/adrs/ADR-007-discovery-orchestrates-skills-and-spine-emitters.md
    severity_at_discovery: n/a
generated_by:
  activity: plan-work-run/2026-06-04T09:20:00Z
  agent: sulis:engineering-architect
addresses_findings: []
invalidated_by: { activity: null, result: null }

status: pending
depends_on: [WP-002, WP-015, WP-017, WP-022]
# SIGNED visual contract (#45) + the chat composer/SSE client it reuses + onboarding stream types + the onboarding route

child_wps: []
kinds: null

# LOCKED founder decisions baked into the UI:
locked_decisions:
  - "repo create default LOCAL-ONLY — pre-selected; GitHub is a clearly-labelled separate opt-in, never the default (ADR-008)"
  - "ONE Product per onboarding conversation (multi-product deferred)"
  - "Product icon = NEUTRAL TWO-LETTER TILE — no logo upload control in this slice"

# safety posture (client side, the cold-start front door):
security_constraints:
  - "The proposal is shown and confirmed BEFORE any mint; a declined flow creates nothing (FR-N6, FR-N11 surfaced client-side)"
  - "Failed repo-create leaves the setup unchanged (FR-N10/N11); scope-violation surfaced plainly (FR-N7)"

verifies_scenario: "PENDING-MINT:G"   # Set-up-by-talking (cold-start onboarding, UC-07)

rollback: |
  New OnboardingChat surface reusing Composer + useChatStream. Remove the
  surface; the chat composer is unaffected. Revert the commit. No read surface
  affected.
---

# Conversational setup UI: onboarding chat with the find-vs-create-repo + confirm branch

## Why

The first time the founder opens the app there's nothing there — so a
**conversation**, not a form, does the setup (UC-07, FR-27). This is the client
half of WP-022: the founder picks an area, answers questions, sees a
plain-English **proposal**, and **confirms** before anything is created
(FR-N6). It reuses the chat composer + SSE client (EP-03). It bakes the three
**founder-locked** decisions for this slice: **local-only repo create** as the
pre-selected default (GitHub a labelled opt-in), **one Product per
conversation**, and a **neutral two-letter tile** for the Product icon (no logo
upload).

## What changes

- `apps/cockpit/client/src/components/OnboardingChat.tsx` (NEW, EXPAND-Create) — the conversational-setup surface; reuses `Composer` + `useChatStream` pointed at `POST /api/onboarding/session`; renders state/chunk/proposal/minted; the find-vs-create-repo branch (local-only pre-selected); the neutral two-letter Product tile; the confirm affordance.
- `apps/cockpit/client/src/api/useOnboardingStream.ts` (NEW, thin) — or reuse `useChatStream` with the onboarding endpoint + `OnboardingStreamEvent` mapping + the `phase`/`confirmToken` turn shape.

## How

Consume WP-022's onboarding route. Reuse the chat composer + SSE client. The
proposal turn renders the Tenant/Product/Project + repo plan in plain English;
the confirm turn triggers the mint (server-side, FR-N6). The repo branch shows
**find** vs **create**, with **local-only pre-selected** and GitHub a clearly
labelled separate opt-in (ADR-008, founder-locked). The Product icon is a
neutral two-letter tile — no upload control. One Product per conversation.
A failed create / scope-violation is surfaced plainly. Consume `tokens.css`
only; match the signed visual contract (WP-002), which now covers the
conversational-setup surface.

## Tests

`OnboardingChat.test.tsx` — search→ask→proposal→confirm→minted; find-vs-create
with local-only pre-selected; neutral two-letter tile (no upload control);
declined flow creates nothing; failed-create leaves setup unchanged;
scope-violation surfaced; one Product per conversation. axe-core.

## Scenario linkage

Verifies scenario **G — "Set up by talking (cold-start onboarding)"** (UC-07).
Author scenario G and backfill its `dna:scenario:<ULID>` (aggregated in
WP-027).

## Rollback

Remove the surface; the chat composer is unaffected. Revert the commit.
