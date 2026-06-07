---
id: WP-020
title: "Confirm gate (pure lib): ask-before-consequential for mint + start"
kind: backend
source: feature
change_id: 01KT500K2JTE2EGW6TPPQ4D4VN
parent_phase: chat
parent_group: discovery

atomic_branch: yes
estimate: 4h
blast_radius: low          # pure lib, no I/O
primitive: EXPAND-Create
group: expand
acceptance_criteria:
  - "lib/discovery/confirmGate.ts is a pure module: a read-and-propose turn needs NO confirmation; the ACT (mint or change-start) requires an explicit confirm referencing the pending proposal (FR-N6, NFR-DISC-04)"
  - "A confirm carrying a token that does NOT match the live proposal is refused as STALE (DISCOVERY_CONFIRM_STALE / START_CONFIRM_STALE) — a stale proposal cannot be mis-confirmed (TDD §3.6; openapi confirmToken)"
  - "A declined or absent confirm leaves the gate closed — the caller (mint / start) MUST NOT proceed; the gate is the precondition both acts wait on (ADR-007, ADR-008)"
  - "Pure & deterministic: no fs, no git, no process, no bridge — exactly like lib/sessionBinding.ts + lib/inFlightLock.ts (the WP-008 sibling pattern)"
  - "Reuses the chat relay's ask-before-consequential discipline — it is NOT a new approval mechanism (ADR-006/007)"
test_plan:
  unit:
    - "apps/cockpit/server/tests/confirmGate.test.ts (NEW) — propose-without-confirm → gate closed; matching confirm → gate open once; stale/mismatched token → refused; declined → closed; deterministic (no I/O)"
  integration: []
  verification:
    - "branch-ci green"
verification_gates: [unit, smoke]
verification:
  adapter: backend
  artifact: "apps/cockpit/server/tests/confirmGate.test.ts"

derived_from:
  - finding: "TDD §3.6 confirm-before-consequential + §2.4 confirmGate row; ADR-007 confirm gate; ADR-008 repo create confirm-gated; FR-N6, NFR-DISC-04"
    found_in: .architecture/autonomous-delivery-environment/TDD.md
    severity_at_discovery: n/a
generated_by:
  activity: plan-work-run/2026-06-04T09:20:00Z
  agent: sulis:engineering-architect
addresses_findings: []
invalidated_by: { activity: null, result: null }

status: pending
depends_on: [WP-017]      # uses the confirmToken shapes from the OnboardingRequest / StartFromIntentRequest types

child_wps: []
kinds: null

# safety posture — the gate is the precondition for both consequential acts:
security_constraints:
  - "No consequential act (mint, change-start) proceeds without an explicit, token-matched confirm (FR-N6, NFR-DISC-04)"
  - "Stale-proposal confirms are refused — the founder cannot accidentally confirm a changed plan"

rollback: |
  New pure lib + its unit test. Remove the file + test; revert the commit. No
  caller depends on it until WP-021/022/023 land, so removal is isolated.
---

# Confirm gate (pure lib): ask-before-consequential for mint + start

## Why

Both consequential discovery acts — minting an entity (FR-28) and starting a
change (FR-29/FR-34) — must be **confirmed first** (FR-N6, NFR-DISC-04). A
read-and-propose turn needs no confirmation; the act does. Per ADR-007 this is
the **same** "ask before consequential" discipline the chat relay already
uses, factored into one pure module so the onboarding orchestrator (WP-022)
and start-from-intent (WP-023) share exactly one gate — not two re-implemented
ones. Pure-lib, deterministic, no I/O: the WP-008 sibling pattern
(`sessionBinding.ts` / `inFlightLock.ts`).

## What changes

- `apps/cockpit/server/lib/discovery/confirmGate.ts` (NEW, EXPAND-Create) — `propose(proposal) → {confirmToken}`; `confirm(token) → open | stale | closed`. Holds the pending proposal; opens exactly once on a matching confirm; refuses a stale/mismatched token. No fs / git / process / bridge.

## How

Model on `lib/inFlightLock.ts` (in-memory, deterministic). The `confirmToken`
shapes come from the contract types (WP-017). The gate exposes a boolean
precondition the mint and start callers check before any consequential act —
they never bypass it.

## Tests

`confirmGate.test.ts` — propose-without-confirm → closed; matching confirm →
open once; stale/mismatched token → refused; declined → closed; deterministic.

## Rollback

Remove the file + test; revert. Isolated until its callers land.
