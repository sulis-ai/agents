---
# Identity (WP-01)
id: WP-001
title: "Shared data contract: the full api-types seam (reads + chat + products + discovery)"
kind: contract
contract_type: data
source: feature
change_id: 01KT500K2JTE2EGW6TPPQ4D4VN
parent_phase: foundation
slice_kind: foundation        # not a journey round-trip; the seam every slice builds on

# Scope (WP-02..04)
atomic_branch: yes
estimate: 5h
blast_radius: medium          # every slice imports these wire shapes
primitive: EXPAND-Extend
group: expand
acceptance_criteria:
  - "shared/api-types.ts adds the READ shapes (ChangeStatus, BrainEntity/BrainGroup/BrainView), the CHAT shapes (ChatStreamEvent discriminated union + chat error codes SESSION_BUSY/SESSION_CHANGE_MISMATCH/SESSION_UNREACHABLE), the PRODUCT shapes (Product, ProductList, ProjectSource), and the DISCOVERY shapes (OnboardingRequest/StreamEvent, StartFromIntentRequest/StreamEvent, ConciergeStreamEvent + discovery/start error codes) — all matching contracts/openapi.yaml verbatim (CF-02 single source of truth)"
  - "All stream-event types are discriminated unions on a literal `type` field (state|chunk|proposal|minted|started|complete|error), mirroring ChatStreamEvent's shape (CF-09; ADR-001)"
  - "The Error.code union carries all three categories: chat codes, discovery codes (DISCOVERY_SCOPE_VIOLATION, DISCOVERY_CONFIRM_STALE, REPO_CREATE_FAILED), start codes (INTENT_AMBIGUOUS, START_CONFIRM_STALE, REPO_UNREACHABLE) (CF-03)"
  - "Example fixtures cover happy/error/empty per shape (CF-03/04): an empty BrainView (groups:[]), each ChatStreamEvent variant + an error event per chat code, a proposal+minted onboarding pair, a started start-from-intent, a concierge complete-with-route, one error per new code"
  - "tsc --noEmit clean across server + client + shared; no snake_case leakage on the wire; type-only (no runtime export)"
test_plan:
  unit:
    - "apps/cockpit/server/tests/api-types.contract.test.ts (NEW) — constructs one example per new shape from the OpenAPI examples incl. error + empty; asserts the unions narrow on `type`; the error union accepts every code; the existing anti-hardwiring assertion (no snake_case) still holds"
  integration: []
  verification:
    - "npx tsc --noEmit (workspace)"
    - "npx @redocly/cli lint contracts/openapi.yaml (or equivalent) passes"
    - "branch-ci green"
verification_gates: [contract]
verification:
  adapter: backend
  artifact: "apps/cockpit/server/tests/api-types.contract.test.ts"

# Lineage (WP-06)
derived_from:
  - finding: "TDD §2.2 + §2.4 component inventories (shared/api-types.ts EXPAND-Extend); contracts/openapi.yaml (10 paths); CF-02/03/04/09. Merges the prior horizontal WP-001 (reads+chat types) and WP-017 (product+discovery types) into one foundation contract so each vertical slice has the full seam available."
    found_in: .architecture/autonomous-delivery-environment/TDD.md
    severity_at_discovery: n/a
generated_by:
  activity: re-slice-vertical/2026-06-04
  agent: sulis:engineering-architect
addresses_findings: []
invalidated_by:
  activity: null
  result: null

# Lifecycle (WP-07)
status: pending
depends_on: []

child_wps: []
kinds: null

rollback: |
  Pure type additions to shared/api-types.ts + one new test file. Revert the
  commit; no runtime behaviour, no data, no config touched.
---

# Shared data contract: the full api-types seam

## Why this is a foundation, not a journey slice

Re-sliced plan: every WP after this one is a **complete observable round-trip**
for one journey (data + route + bridge + UI together). For those slices to build
their data + route + UI in one branch, the wire contract they all import must
already exist. This WP is that seam — the runtime TypeScript mirror of the signed
`contracts/openapi.yaml`. It is the only non-round-trip WP besides the signed
visual contract (WP-002).

It **merges** the two prior horizontal contract WPs (the reads+chat types and the
product+discovery types) into one foundation: there is no longer a separate
"expanded contract" WP, because the slices that consume product/discovery types
ship as their own vertical round-trips and need the types present from the start.

## What changes

`apps/cockpit/shared/api-types.ts` (EXPAND-Extend) gains, copied **verbatim from
`contracts/openapi.yaml`**:

- **Reads:** `ChangeStatus` (`{ changeId, stage, headline, needsAttention: { flagged, reason } }`, reason ∈ blocked | waiting-on-decision | stopped-mid-reply | null); `BrainEntity` / `BrainGroup` / `BrainView`.
- **Chat:** `ChatStreamEvent` SSE union (`state`: ready|resuming|spawning|replying|complete|interrupted|failed; `chunk`: text; `complete`: resumed:boolean; `error`: code,message); chat error codes.
- **Products:** `Product`, `ProductList`, `ProjectSource` (`{ repo, path, primary_branch }`).
- **Discovery:** `OnboardingRequest` / `OnboardingStreamEvent`; `StartFromIntentRequest` / `StartFromIntentStreamEvent`; `ConciergeStreamEvent` (chat shapes + a `route` hint); the six discovery+start error codes added to the `Error.code` union.

## How

Pure `export interface` / `export type` additions; the file is type-only today and
stays type-only. Discriminated unions on the literal `type` field, exactly as the
existing event types are. No invented fields — the OpenAPI seam is the source.

## Tests

`api-types.contract.test.ts` constructs an example per shape from the OpenAPI
`description`/`enum`/example values, including the empty BrainView, each chat
event variant + an error per code, the onboarding proposal+minted pair, the
start-from-intent started event, the concierge complete-with-route, and one error
per new code. Reuse the existing anti-hardwiring assertion (no snake_case). `tsc
--noEmit` is the real gate.

## Rollback

Revert the commit. Type-only; nothing downstream has shipped against it.
