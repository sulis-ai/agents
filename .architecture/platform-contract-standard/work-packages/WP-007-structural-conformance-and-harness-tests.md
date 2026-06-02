---
id: WP-007
title: Author structural / conformance tests + the harness-refusal behavioural test
status: pending
change_id: "01KT3X2M0JHFN583DKKV77W83C"
kind: backend
primitive: create
group: EXPAND
sequence_id: WP-007
dependsOn: [WP-001, WP-002, WP-004, WP-006]
blocks: [WP-008]
estimated_token_cost:
  input: 4k
  output: 7k
tdd_section: "Proof §1 structural/conformance tests (lines 160-168); Proof §2 harness behavioural test (lines 170-175); Verification Plan §per-integration (lines 254-258); FR-006, FR-015; NFR-003, NFR-005"
adrs: [ADR-004, ADR-006]
verification:
  adapter: methodology
  artifact: tests/methodology/test_pplat_rubric.py::test_pplat_fails_no_contract
---

## Context

Authors the structural / conformance test suite (CI) and the harness-refusal
behavioural test (local) that assert the methodology pieces authored in
WP-001..006 actually hold. These are the tests that earlier WPs' Red phases
write stubs for; this WP is their primary-purpose home.

**TDD reference:** Proof leg 1 (lines 160-168) names the five structural /
conformance tests; Proof leg 2 (lines 170-175) names the harness-refusal test.
The Verification Plan per-integration table (lines 254-258) fixes the seams:
the `execute-workflow` engine boundary for the harness (no internal mocking),
the WP-set scan for the rubric.

**Why this depends on WP-001, 002, 004, 006.** The conformance tests read the
standard (WP-001 schema), the storage dir (WP-002), the rubric phase (WP-004),
and the github-actions contract (WP-006). The harness-refusal test asserts the
behaviour the WP-003 glue dispatches — but it runs against a *fixture* manifest
(not the github-actions one), so its hard dependency is the schema + harness
existence, satisfied transitively.

**Why this is separate from WP-008.** WP-007 holds the **structural +
behavioural** tests (the file exists, the schema conforms, the rubric fails on
a synthetic no-contract WP set, the harness refuses an ungrounded claim).
WP-008 holds the **n=1 dogfood acceptance** (the three github-actions rules
become real assertions cited to live URLs). Disjoint test files; WP-008 builds
on WP-007's harness.

**Pre-Work Prior-Art Check:** the verification-by-design change established
`tests/methodology/` + the fixture-directory convention (WP-007 of that change
— P-VER fixtures + tests). This WP **extends** that test tree with platform-
contract fixtures; it mirrors the established fixture-as-WP-set pattern.

## Contract

### Files created

Under `tests/methodology/`:

- `test_platform_contract_standard.py` — structural assertions:
  - `test_standard_exists` (the WP-001 Red assertion; the standard exists,
    declares severity, cites three siblings, contains the schema + `PC-01..08`).
  - `test_storage_and_index_present` (the WP-002 Red assertion).
- `test_github_actions_contract.py`:
  - `test_contract_conformance` (the WP-006 Red assertion; every claim-entry
    invariant A-1/A-4/A-6/A-8 holds).
  - `test_source_urls_resolve` (NFR-003; every `source` URL in
    `github-actions.md` resolves — authoring-time hard, CI soft per OAQ-2).
- `test_pplat_rubric.py`:
  - `test_phase_pplat_present_and_complete` (the WP-004 Red assertion).
  - `test_pplat_fails_no_contract` (FR-015; a synthetic integration WP set
    naming a gated platform with no contract reference triggers
    P-PLAT FAIL → GAPS_FOUND).
  - `test_pplat_grandfathers` (NFR-005; a change with `started_at` before the
    merge constant passes P-PLAT without a contract).
- `test_gate_wiring.py`:
  - `test_skills_reference_platform_contract` (the WP-003 Red assertion).
- `test_plan_work_platform_field.py`:
  - `test_plan_work_emits_platform_field` (the WP-005 Red assertion).
- `test_harness_refusal.py`:
  - `test_harness_refuses_ungrounded_load_bearing` (FR-006 / A-2; a harness
    dispatch against a fixture manifest with one ungrounded load-bearing claim
    produces a refusal `terminal-manifest-insufficient` + a flagged-assumption
    entry, **not** a fabricated citation).

### Fixtures created

- `tests/methodology/fixtures/wp-set-no-contract/` — a synthetic WP set naming
  a gated `platform:` + `touch-class:write` with no contract reference.
- `tests/methodology/fixtures/wp-set-grandfathered/` — a change record with
  `started_at` before the merge constant.
- `tests/methodology/fixtures/ungrounded-manifest.jsonld` — a small closed
  manifest with one ungrounded load-bearing claim (for the harness-refusal
  test).

### Seams (Verification Plan lines 256-258)

- **Harness:** the `/sulis-brain:execute-workflow` engine boundary — **no
  internal mocking** (MEA-09). The refusal test dispatches the real harness
  against the fixture manifest.
- **Rubric:** the WP-set scan — the P-PLAT test runs the rubric phase against
  the fixture WP sets.

## Definition of Done

### Red — Failing tests written first

- [ ] All test functions above exist and **fail** initially where their
  subject is not yet implemented (run against the WP-001..006 outputs as they
  land; the keystone is `test_pplat_fails_no_contract`).
- [ ] `test_harness_refuses_ungrounded_load_bearing` fails (or errors) before
  the fixture manifest + harness dispatch are wired.

### Green — Implementation makes the tests pass

- [ ] Author every test function + every fixture per the Contract.
- [ ] `test_pplat_fails_no_contract`: P-PLAT returns GAPS_FOUND on the
  no-contract fixture WP set.
- [ ] `test_pplat_grandfathers`: P-PLAT returns `PASS — grandfathered` on the
  grandfathered fixture.
- [ ] `test_harness_refuses_ungrounded_load_bearing`: real harness dispatch
  produces `terminal-manifest-insufficient` + a flagged-assumption entry, no
  fabricated citation.
- [ ] `test_contract_conformance` + `test_source_urls_resolve` pass against
  the WP-006 contract.
- [ ] All structural tests pass against WP-001..005 outputs.

### Blue — Refactor + polish

- [ ] Fixtures are minimal (one ungrounded claim; one gated WP) — no
  incidental complexity.
- [ ] The harness-refusal test uses the real `execute-workflow` boundary —
  **no mocks** (MEA-09).
- [ ] Shared assertion helpers (schema-invariant checks) extracted once and
  reused across `test_github_actions_contract` + `test_pplat_rubric` (EP-02
  REFACTOR — extract the shared claim-entry validator).

## Sequence

- **Sequence ID:** WP-007
- **dependsOn:** WP-001 (schema), WP-002 (storage), WP-004 (P-PLAT phase),
  WP-006 (the contract under test). Transitively covers WP-003 + WP-005 (their
  Red-stub assertions live here).
- **blocks:** WP-008 (the dogfood acceptance imports this WP's harness-refusal
  fixtures + the shared claim-entry validator).
- **Parallelisable with:** — (it is the penultimate sink; most things precede it).

## Estimated Token Cost

- **Input:** ~4k (all six methodology outputs + the verification-by-design
  fixture convention + ADR-004/006).
- **Output:** ~7k (eight+ test functions + three fixtures + shared validator).
- **Total:** ~11k.

## Notes

- **Tests of prose, plus one behavioural test.** Most assertions are
  structural (regex / schema scans against methodology prose). The one
  genuinely behavioural test is the harness-refusal test — it dispatches the
  real harness (no mock) and asserts the refusal path (FR-006 / A-2), the
  control that catches the reusable-workflow class.
- **File-count note:** this WP creates several test files + three fixtures.
  Per the verification-by-design WP-007 anchor case, fixture data counts toward
  touch surface but the unit of work is "one test suite + its fixtures" —
  splitting would fragment the suite from its fixtures. Logged for P2.
- The CI link-resolution check (`test_source_urls_resolve`) is **SHOULD-advisory
  in CI, hard at authoring time** per OAQ-2 — CI network checks are flaky.

## Verification Plan (per-WP)

- **Adapter:** `methodology` — **Shape 1 (concrete).**
- **Artifact:** the full suite; keystone
  `tests/methodology/test_pplat_rubric.py::test_pplat_fails_no_contract`.
- **Observable:** running the suite proves the standard, storage, gate, rubric,
  field, and contract all hold their contracts; the harness refuses an
  ungrounded load-bearing claim.
- **Seam:** `execute-workflow` engine boundary for the harness — no internal
  mocking (MEA-09).
