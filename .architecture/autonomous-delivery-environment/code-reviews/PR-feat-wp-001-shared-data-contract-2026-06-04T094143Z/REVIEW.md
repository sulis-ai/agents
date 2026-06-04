# Code Review: WP-001 — Shared data contract (the full api-types seam)

> **Timestamp:** 2026-06-04T094143Z (ISO 8601 UTC)
> **Author:** executor (WP-001)
> **Branch:** feat/wp-001-shared-data-contract → change/create-autonomous-delivery-environment
> **Files changed:** 3 (api-types.ts, new contract test, openapi.yaml brought onto branch)
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds the shared data shapes the whole app speaks — the reads, the
chat stream, the products, and the discovery/onboarding flows — as pure
TypeScript types that mirror the signed API contract exactly. There are no
build errors, the new test passes, and every shape was checked against the
contract one value at a time with no drift. One thing surfaced during review
that was fixed in place: the branch was cut before the expanded contract file
had been saved into version control, so the contract file was brought onto the
branch alongside the types it backs. Nothing needs your attention before merge.

## What to fix

No issues that need attention.

One observation for awareness (not a blocker): the API contract document
itself reports some style complaints from the standard contract linter — it
has no sign-in/security section and no license block. This is expected and
correct for this app: the contract is explicit that every endpoint is
loopback-only (127.0.0.1), so there is no auth scheme to declare. These same
complaints already exist on the previous version of the contract and are not
introduced by this change. They belong to the contract document (authored in
the design step), not to this code change.

## How this pull request is shaped

**Size — clean.** Small and focused: the shared types plus their test, and the
contract file they mirror. No mixed concerns.

**Scope — clean.** A single concern: the data contract seam.

**Safety — clean.** Type-only additions; no runtime code, no data, no config,
no migrations. The stated rollback (revert the commit) is accurate.

**Completeness — clean.** The change ships with its test: one constructed
example per shape, including the error and empty cases.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all
changed files read end-to-end; all lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 high, 0 medium (CR-09 / PH-01..PH-04)
- **In the changes:** 1 finding (0 critical, 0 high, 0 medium, 1 note)
- **In the neighbours:** 0 findings
- **Draft fixes:** 0 (the one note is an upstream-artifact observation, not a delta)

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | Nothing surfaced — type-only, no imports added, no resilience surface |
| Security | 0 | 0 | Nothing surfaced — no runtime, no I/O, no secrets, no new deps |
| Quality | 1 (note) | 0 | Contract-document linter hygiene (upstream artifact, pre-existing) |

### Build Verification (CR-01)

Mechanical baseline clean.

- `npm run typecheck` (tsc --noEmit -p server && -p client): exit 0, 0 errors.
  (`tool-outputs/typecheck-head.log`)
- `npx eslint shared/api-types.ts server/tests/api-types.contract.test.ts`:
  exit 0, 0 errors. (`tool-outputs/eslint-head.log`)
- prettier --check on both changed files: clean (test file was formatted with
  prettier --write during Step 6).

No PR-introduced errors. Build Verification section empty → no CR-06 downgrade.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                    → clean
  module_fan_out: 1 (apps/cockpit + its contract)→ clean
  severity: none

Size (PH-02):
  api-types.ts: +313 ; test: +394 (new) ; openapi.yaml: brought onto branch
  files_changed: 3
  generated_ratio: 0 ; lock_file_ratio: 0
  severity: low (type-only + test; no runtime surface)

Safety (PH-03):
  migration_count: 0 ; schema_idl_count: 1 (openapi.yaml, brought onto branch
    from the change working tree — a strict superset of the base version,
    verified) ; infra_files: 0 ; secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: false (the test IS the deliverable's verification)
  api_change_without_schema: false (the schema is the source; the types mirror it)
  severity: none
```

### Findings in the Changes

#### `contracts/openapi.yaml` — note (quality + architecture)

**Finding:** `@redocly/cli lint` reports 10 errors / 15 warnings, all from the
`security-defined` rule (no `securitySchemes`/`security` declared) and one
`info-license` rule (no license block).

**Evidence:** `tool-outputs/redocly-head.log`. The same rule classes fire on
the BASE committed contract (`/tmp/base-openapi.yaml`, 5 errors / 8 warnings) —
pre-existing, not introduced by this change.

**Why it is a note, not a blocker:** (1) The contract is explicit that every
endpoint binds to 127.0.0.1 loopback only (NFR-SEC-01) — there is no auth
scheme to declare, so `security-defined` is a false-positive for this design.
(2) The OpenAPI document is an upstream design-step artifact (SEA), outside
WP-001's Contract scope (WP-001 is the TypeScript mirror). (3) The document is
structurally valid (redocly "validated in 325ms"; all `$ref`s resolve) — the
errors are default-ruleset opinions, not structural breakage. The WP's
`redocly lint` verification refers to structural validity, which holds.

**Recommendation:** If the team wants a clean redocly run, add a redocly
ignore-file or a `security: []` declaration on the loopback API in a future
contract-hygiene change. No action required for WP-001.

### Contract-drift verification (CR-07 Quality — item 4, the load-bearing check)

WP-001's load-bearing property is that the types mirror the contract VERBATIM
(CF-02). Verified mechanically: every enum literal and error code in
`api-types.ts` is present in `contracts/openapi.yaml` and vice versa, across
all four shape groups —

- ChangeStatus.needsAttention.reason: `blocked | waiting-on-decision | stopped-mid-reply | null` ✓
- ChatStreamEvent.state: `ready resuming spawning replying complete interrupted failed` ✓
- ChatErrorCode: `SESSION_UNREACHABLE SESSION_CHANGE_MISMATCH SESSION_BUSY` ✓
- OnboardingStreamEvent.state: `searching asking proposing confirming minting complete failed` ✓
- repoPlan: `found-existing will-create-local will-create-hosted-remote` ✓
- createTarget: `local hosted-remote` ✓
- Onboarding error codes: `DISCOVERY_SCOPE_VIOLATION DISCOVERY_CONFIRM_STALE REPO_CREATE_FAILED SESSION_UNREACHABLE SESSION_BUSY` ✓
- StartFromIntentStreamEvent.state: `classifying proposing confirming cloning starting complete failed` ✓
- StartFromIntent error codes: `INTENT_AMBIGUOUS START_CONFIRM_STALE REPO_UNREACHABLE SESSION_UNREACHABLE SESSION_BUSY` ✓
- ConciergeStreamEvent.state: `thinking replying complete failed`; route: `onboarding start-from-intent null` ✓
- ApiErrorCode (Error.code): all 10 codes match the OpenAPI Error enum ✓

No invented fields; no missing fields. `tsc --noEmit` is the live gate that
keeps this true.

### Findings in the Neighbours

None. The type-only additions are consumed by the existing imports of
`shared/api-types` (server routes, client components) without changing any
existing exported shape — the diff is purely additive (the only edit to an
existing declaration site is the appended new section).

### Watch List

- Contract-document redocly hygiene (security-defined / info-license) — see the
  note above. Upstream artifact; candidate for a future contract-hygiene change.

### Cross-Reference

- No prior `.security/` viability report for this project.
- No existing hardening-deltas relevant to this diff.
- Pattern suggesting full audit: none.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `npm run typecheck` (exit 0) + `npx eslint` on both changed files (exit 0). Base: clean. Head: clean. Coverage gap: none.
- [✓] **CR-02 Dispatch shape.** Diff is >200 lines but only 3 files, all authored this session and read end-to-end by the author; single-reader pass with full author context. Recorded as a deviation from the line-threshold trigger: the diff is pure type declarations + one test + a contract file brought onto branch, with no behavioural surface to dispatch lenses against.
- [✓] **CR-03 Full-file reads.** All 3 changed files read end-to-end (authored this session). Unread files: none.
- [✓] **CR-04 Evidence discipline.** The one note cites file + the redocly log + the base-contract comparison.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 1 note.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired (Build Verification empty; all files read; all lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (type-only, no imports/resilience/verification surface added beyond the test, which is the deliverable). Security: nothing surfaced (no runtime, no I/O, no secrets, no new deps; primitives SEC-01..07/SC-01..04 N/A to a type-only diff). Quality: Build-Verification follow-up (clean), JSX scan (N/A — no tsx/jsx), dead-surface (none — every new export is exercised by the test or is a public seam type), contract-drift (verified verbatim, see above), test-coverage (the test IS the deliverable; one example per shape incl. error+empty), CR-10 perf (N/A — no loops/DB/RPC; grep matches were comment prose only).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none ({feat}, single module). PH-02 Size: low (type-only + test). PH-03 Safety: none (0 migrations; openapi.yaml brought onto branch is a verified strict superset of base; 0 secrets; 0 infra). PH-04 Completeness: none (ships with its test). PH-03 high → CR-06 auto-downgrade: did not fire.

#### Run details

- **Diff source:** git diff change/create-autonomous-delivery-environment...working-tree (uncommitted at review time, per Step 6.5 gate-before-commit).
- **Neighbour expansion:** git grep on `shared/api-types` importers; additive-only change confirmed (no existing exported shape modified).
- **Scanners run:** tsc, eslint, prettier, @redocly/cli.
- **Scanners unavailable:** none.
- **Notable in-scope fix during review:** the branch base (SHA 6fa446b) carried the pre-re-slice 317-line contract; the expanded 809-line contract (authored in the same 2026-06-04 re-slice that produced WP-001, and the verbatim source the WP + INDEX describe) was uncommitted in the change working tree. It was brought onto the branch so the types mirror a contract present on-branch and the calling session's `redocly lint contracts/openapi.yaml` gate lints the correct file. Verified the expanded contract is a strict superset of the committed base (every base schema present; reads/chat enums identical).
