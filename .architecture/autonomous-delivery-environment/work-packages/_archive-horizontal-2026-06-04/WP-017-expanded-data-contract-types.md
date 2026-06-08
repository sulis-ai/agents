---
id: WP-017
title: "Expanded data contract: Product / ProjectSource / discovery + concierge stream types"
kind: contract
source: feature
change_id: 01KT500K2JTE2EGW6TPPQ4D4VN
parent_phase: contract

atomic_branch: yes
estimate: 3h
blast_radius: low          # type-only seam extension; no runtime behaviour
primitive: EXPAND-Extend
group: expand
acceptance_criteria:
  - "shared/api-types.ts gains Product, ProductList, ProjectSource, OnboardingRequest, OnboardingStreamEvent, StartFromIntentRequest, StartFromIntentStreamEvent, ConciergeStreamEvent — matching contracts/openapi.yaml exactly (CF-02 single source of truth)"
  - "Error.code union is extended with the discovery codes (DISCOVERY_SCOPE_VIOLATION, DISCOVERY_CONFIRM_STALE, REPO_CREATE_FAILED) and the start codes (INTENT_AMBIGUOUS, START_CONFIRM_STALE, REPO_UNREACHABLE) — the existing chat codes are unchanged (CF-03 three-category errors)"
  - "Stream event types are discriminated unions on a literal `type` field (state|chunk|proposal|minted|started|complete|error), mirroring ChatStreamEvent's shape (CF-09 structured streaming contract, ADR-001)"
  - "A consumer (a route, a component) can import the new types and build against them; tsc passes; no runtime export added (types only)"
  - "Example fixtures cover happy / error / empty per stream (CF-03/04): a proposal+minted onboarding pair, a started start-from-intent, a concierge complete-with-route, and one error per new code"
test_plan:
  unit:
    - "apps/cockpit/shared/tests/api-types.contract.test.ts (EXTEND) — the new types compile against the openapi.yaml example payloads; the discriminated unions narrow on `type`; error union includes the six new codes"
  integration: []
  verification:
    - "tsc --noEmit (shared) passes"
    - "npx @redocly/cli lint contracts/openapi.yaml (or equivalent) passes"
    - "branch-ci green"
verification_gates: [unit, smoke]
verification:
  adapter: backend
  artifact: "apps/cockpit/shared/tests/api-types.contract.test.ts"

derived_from:
  - finding: "TDD §2.4 (expanded inventory) + §5.1 (expanded surfaces→endpoints); ADR-006/007/008/009; openapi.yaml schemas Product/ProductList/ProjectSource/Onboarding*/StartFromIntent*/Concierge*; FR-27..38, FR-N6..N11"
    found_in: .architecture/autonomous-delivery-environment/contracts/openapi.yaml
    severity_at_discovery: n/a
generated_by:
  activity: plan-work-run/2026-06-04T09:20:00Z
  agent: sulis:engineering-architect
addresses_findings: []
invalidated_by: { activity: null, result: null }

status: pending
depends_on: [WP-001]      # extends the same shared/api-types.ts WP-001 created; lands after it

child_wps: []
kinds: null

rollback: |
  Type-only additions to shared/api-types.ts + the contract test cases.
  Remove the added type declarations + test cases; revert the commit. No
  runtime behaviour changes, so nothing downstream breaks beyond consumers
  that referenced the new types (none until their own WPs land).
---

# Expanded data contract: Product / ProjectSource / discovery + concierge stream types

## Why

The expanded scope (concierge, onboarding/discovery, start-from-intent,
multi-product) needs its shared types before backend and frontend can build
against the contract in parallel (CONTRACT_FIRST CF-05). The OpenAPI seam
(`contracts/openapi.yaml`) already carries every new schema and the
founder-readable `DATA-CONTRACT-GUIDE.md` is signed; this WP mirrors those
schemas into the TypeScript shared types so producer and consumer share one
source of truth (CF-02). It is the contract sibling of WP-001 for the new
surfaces — type-only, no runtime.

## What changes

- `apps/cockpit/shared/api-types.ts` (EXTEND, EXPAND-Extend) — add:
  - `Product`, `ProductList`, `ProjectSource`;
  - `OnboardingRequest`, `OnboardingStreamEvent` (state/chunk/proposal/minted/error);
  - `StartFromIntentRequest`, `StartFromIntentStreamEvent` (state/chunk/proposal/started/error);
  - `ConciergeStreamEvent` (reuses the chat event shapes + a `route` hint);
  - extend the `Error.code` union with the six new codes.
- `apps/cockpit/shared/tests/api-types.contract.test.ts` (EXTEND) — compile-and-narrow tests + example payloads.

## How

Transcribe the openapi.yaml schemas verbatim into TS discriminated unions on
the literal `type` field, exactly as `ChatStreamEvent` already is (ADR-001).
The `Error.code` union gains the discovery + start codes; the chat codes are
untouched. No new runtime export — these are interfaces/types only.

## Tests

`api-types.contract.test.ts` asserts the openapi example payloads assign to
the new types, the unions narrow on `type`, and the error union accepts each
new code. `tsc --noEmit` is the real gate.

## Rollback

Remove the added types + test cases; revert. Type-only, nothing else breaks.
