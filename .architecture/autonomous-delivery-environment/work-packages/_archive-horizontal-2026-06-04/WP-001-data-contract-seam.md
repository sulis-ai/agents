---
# Identity (WP-01)
id: WP-001
title: "Data contract: extend shared/api-types.ts + lock the OpenAPI seam"
kind: contract
contract_type: data
source: feature
change_id: 01KT500K2JTE2EGW6TPPQ4D4VN
parent_phase: contract

# Scope (WP-02..04)
atomic_branch: yes
estimate: 3h
blast_radius: medium            # every backend + frontend WP imports these types
primitive: EXPAND-Extend
group: expand
acceptance_criteria:
  - "shared/api-types.ts adds: ChangeStatus, BrainEntity, BrainGroup, BrainView, ChatStreamEvent, and the chat error codes (SESSION_BUSY, SESSION_CHANGE_MISMATCH, SESSION_UNREACHABLE) — shapes match contracts/openapi.yaml exactly"
  - "server/tests/contract.anti-hardwiring.test.ts (existing pattern) extended: the new wire shapes round-trip and carry no snake_case leakage"
  - "An example fixture covers the three SSE event kinds (state, chunk, complete) AND the error case AND the empty case (empty BrainView.groups) — CF-03/CF-04"
  - "tsc --noEmit clean across server + client + shared"
test_plan:
  unit:
    - "apps/cockpit/server/tests/api-types.contract.test.ts (NEW) — asserts the new shapes parse the openapi examples incl. error + empty"
  integration: []
  verification:
    - "npx tsc --noEmit (workspace)"
    - "branch-ci green"
verification_gates: [contract]
verification:
  adapter: backend
  artifact: "apps/cockpit/server/tests/api-types.contract.test.ts"

# Lineage (WP-06)
derived_from:
  - finding: "TDD §2.2 component inventory — shared/api-types.ts EXPAND-Extend; contracts/openapi.yaml"
    found_in: .architecture/autonomous-delivery-environment/TDD.md
    severity_at_discovery: n/a
generated_by:
  activity: plan-work-run/2026-06-03T08:34:19Z
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

# Data contract: extend shared/api-types.ts + lock the OpenAPI seam

## Why

This is the cross-kind seam (CF-01). Every backend route WP and every frontend
WP that follows imports its wire shapes from `apps/cockpit/shared/api-types.ts`,
which is the runtime mirror of `contracts/openapi.yaml`. Decomposing
contract-first (WP-08.5) means this lands **first** so backend and frontend WPs
can build in parallel against a fixed contract (CF-05), the frontend against the
contract examples until the real routes exist.

## What changes

`apps/cockpit/shared/api-types.ts` (EXPAND-Extend — TDD §2.2) gains:

- `ChangeStatus` — `{ changeId, stage, headline, needsAttention: { flagged, reason } }`, where `reason ∈ blocked | waiting-on-decision | stopped-mid-reply | null` (FR-05, FR-12).
- `BrainEntity` / `BrainGroup` / `BrainView` — grouped-by-kind entities (FR-06, FR-07).
- `ChatStreamEvent` — the SSE discriminated union: `state` (ready | resuming | spawning | replying | complete | interrupted | failed), `chunk` (`text`), `complete` (`resumed: boolean`), `error` (`code`, `message`) — ADR-001, FR-17/23/26.
- Chat error codes added to the existing `{ error, code }` envelope union: `SESSION_BUSY`, `SESSION_CHANGE_MISMATCH`, `SESSION_UNREACHABLE`.

The shapes are copied **verbatim from `contracts/openapi.yaml`** — that file is the
signed data contract; this WP makes it executable TypeScript. No invented fields.

## How

Pure `export interface` / `export type` additions. No runtime code (the file is
type-only today and stays type-only). Follow the existing comment-block style.

## Tests

`apps/cockpit/server/tests/api-types.contract.test.ts` (NEW): construct one
example per new shape from the OpenAPI `description`/`enum` values, including:
- a `BrainView` with two groups AND an empty `BrainView` (`groups: []`) — CF-04 empty case;
- each `ChatStreamEvent` variant AND an `error` event with each of the three codes — CF-03/CF-04 error case;
- assert no snake_case keys leak (reuse the existing anti-hardwiring assertion).

## Rollback

Revert the commit. Type-only; nothing downstream has shipped against it yet.
