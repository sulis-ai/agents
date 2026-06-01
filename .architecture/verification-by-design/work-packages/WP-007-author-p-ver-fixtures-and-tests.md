---
id: WP-007
title: Author P-VER structural-assertion fixtures + tests (8 failure-mode fixtures + 4 PASS fixtures + idempotency test)
status: pending
change_id: 01KT2BPBFESCCDY8F7Y5M8RN4R
kind: backend
primitive: create
group: GENERATE
sequence_id: WP-007
dependsOn: [WP-002]
blocks: [WP-008]
estimated_token_cost:
  input: 4k
  output: 8k
tdd_section: Proof pillar test classes 1-2 + 4 (lines 240-291)
adrs: [ADR-002, ADR-007]
verification:
  adapter: methodology
  artifact: tests/methodology/p_ver/test_p_ver_fixtures.py::test_all_failure_modes_and_passes
---

## Context

Authors the structural-assertion fixtures that prove P-VER works:
eight synthetic SRD/TDD/WP fixtures triggering exactly one P-VER failure
mode each, plus four PASS fixtures, plus an idempotency test for the
slice-end auto-draft scan (per Proof pillar test class 4).

**TDD reference:** Proof pillar lines 240-291. Eight failure modes
(FR-009), four PASS shapes (P-A, P-B, P-C, P-D), plus the idempotency
test.

**Why kind: backend** (not docs): the fixtures are real markdown files,
but the test code (pytest harness invoking P-VER + asserting verdicts)
is Python. The WP delivers executable tests, hence `backend` per WP_BACKEND_STANDARD's
verification-gate row.

**Why this depends on WP-002.** The fixtures are tested against P-VER's
spec — which is the prose contract added by WP-002 to the rubric file.
Without the spec, there's nothing to assert against. (The Python
implementation of P-VER lives in the existing rubric harness; this WP
authors fixtures + tests that exercise the spec as-implemented.)

**Pre-Work Prior-Art Check:** `tests/methodology/` may not yet exist as
a top-level test directory. Check via `find tests -type d -name
methodology`. If missing, this WP creates it (with `__init__.py` + a
`README.md` describing the directory's purpose). If present, this WP
adds the `p_ver/` subdirectory.

## Contract

### Files created (new)

Directory layout:

```
tests/methodology/
├── __init__.py
├── README.md                                           # purpose of the directory
└── p_ver/
    ├── __init__.py
    ├── fixtures/
    │   ├── fail_01_section_missing/
    │   │   └── SRD.md                                   # synthetic SRD; no Verification Plan section
    │   ├── fail_02_placeholder_content/
    │   │   └── SRD.md                                   # subsection contains TBD
    │   ├── fail_03_na_without_justification/
    │   │   └── SRD.md                                   # bare `n/a` without justification
    │   ├── fail_04_hallucinated_infrastructure/
    │   │   └── TDD.md                                   # cites existing path that doesn't resolve
    │   ├── fail_05_unmapped_kind/
    │   │   ├── SRD.md
    │   │   └── .changes/fake-change.yaml                # kind: data-migration (not in canonical table)
    │   ├── fail_06_no_canonical_citation/
    │   │   └── SRD.md                                   # section present, no citation
    │   ├── fail_07_wp_missing_verification_field/
    │   │   └── WP-001-example.md                        # WP frontmatter missing verification:
    │   ├── fail_08_adapter_mismatch/
    │   │   └── WP-001-example.md                        # WP verification.adapter doesn't match change kind
    │   ├── pass_a_complete_srd/
    │   │   └── SRD.md                                   # all six subsections populated; citation present
    │   ├── pass_b_complete_tdd_with_deferred/
    │   │   └── TDD.md                                   # subsections + deferred entries with canonical IDs
    │   ├── pass_c_wp_set_three_shapes/
    │   │   ├── WP-A.md                                  # Shape 1 (concrete)
    │   │   ├── WP-B.md                                  # Shape 2 (deferred)
    │   │   └── WP-C.md                                  # Shape 3 (trivial carveout)
    │   ├── pass_d_grandfathered_change/
    │   │   ├── SRD.md                                   # no Verification Plan section
    │   │   └── .changes/grandfathered.yaml              # started_at preceding merge date
    │   └── slice_two_changes_same_need/
    │       ├── change-a/SRD.md                          # flags recording-mock-sendgrid
    │       └── change-b/SRD.md                          # flags recording-mock-sendgrid
    ├── test_p_ver_fixtures.py                           # main test file
    ├── test_p_ver_phase.py                              # asserts rubric file contains P-VER phase
    ├── test_canonical_verification_questions_structural.py    # WP-001's Red
    ├── test_agent_prompts_cite_canonical.py             # WP-003's + WP-004's Red
    ├── test_plan_work_skill_enforces_verification_field.py  # WP-005's Red
    ├── test_slice_end_scans_deferred_needs.py           # WP-005's Red
    ├── test_orchestrator_skills_invoke_pver.py          # WP-006's Red
    ├── test_template_block_in_requirements_templates.py # WP-006's Red
    └── test_idempotency_slice_end_scan.py               # idempotency test class 4
```

### Test bodies (overview)

**`test_p_ver_fixtures.py::test_all_failure_modes_and_passes`** — the
main parametrised test. Per fixture, invoke the rubric harness against
the fixture's artifacts, assert the verdict matches the fixture's
expected outcome (FAIL with specific failure-mode message, or PASS, or
`PASS — grandfathered`).

**`test_idempotency_slice_end_scan.py::test_idempotent`** — invokes the
slice-end deferred-needs scan twice over the
`slice_two_changes_same_need/` fixture; asserts exactly one follow-on
auto-draft is produced (the second run is a no-op).

**Other test files** are the Red-phase tests cited by WP-001, WP-002,
WP-003, WP-004, WP-005, WP-006 — each WP's Definition of Done points
at one of these. They live here (not scattered) because they share the
test harness + fixtures.

### Test harness

- The harness invokes the existing rubric runner (whichever script
  drives `decompose-validation-rubric.md` checks today; check existing
  patterns under `plugins/sulis/scripts/` during execution).
- If no harness exists yet, the WP implements a minimal one that reads
  the rubric prose's check IDs + applies them mechanically. Defer-call
  out: the harness is a small, well-scoped deliverable; if it grows
  beyond ~100 LOC, split into a follow-on WP.

## Definition of Done

### Red — Failing tests written first

- [ ] `tests/methodology/p_ver/test_p_ver_fixtures.py::test_all_failure_modes_and_passes` exists; asserts each of the 12 fixtures (8 fail + 4 pass) produces the expected verdict.
- [ ] Initial run FAILS because (a) fixtures don't exist yet and (b) P-VER may not be enforced by a runner yet.

### Green — Implementation makes tests pass

- [ ] Create `tests/methodology/__init__.py` + `README.md`.
- [ ] Create `tests/methodology/p_ver/` + 12 fixture directories + their synthetic SRD/TDD/WP files.
- [ ] Each fixture is the smallest synthetic file that triggers exactly one failure mode (or none, for pass fixtures) — keeps the fixtures readable.
- [ ] Implement (or wire into) the rubric harness so `test_p_ver_fixtures.py` runs end-to-end.
- [ ] Author the per-WP Red-phase tests cited by WP-001..WP-006.
- [ ] Author the idempotency test for the slice-end scan.
- [ ] All tests pass against the live (WP-002-extended) rubric.

### Blue — Refactor + polish

- [ ] Extract shared fixture-building helpers into a `fixture_helpers.py` module (e.g., `build_minimal_srd_skeleton()`) — RGB Blue extracts the shared primitives.
- [ ] Fixture filenames are descriptive (`fail_NN_<mode>/`) — discoverable by `ls`.
- [ ] Each fixture has a one-line comment at the top of its SRD/TDD describing what failure mode it triggers.
- [ ] Test output (when a fixture fails the assertion) is debuggable — surface the rubric's actual verdict + expected verdict + which check fired.
- [ ] No mocks in the harness — runs against real rubric prose + real (synthetic but well-formed) artifacts.

## Sequence

- **Sequence ID:** WP-007
- **dependsOn:** WP-002 (P-VER spec exists; fixtures assert against it)
- **blocks:** WP-008 (E2E test imports the harness + fixtures from this WP)
- **Parallelisable with:** WP-003, WP-004, WP-005, WP-006 (different files; tests are independent of skill prose changes)

## Estimated Token Cost

- **Input:** ~4k (TDD Proof pillar + ADR-002 + ADR-007 + existing rubric harness patterns)
- **Output:** ~8k (12 fixture artifacts + 9 test files + harness shim ≈ ~400 LOC across all files)
- **Total:** ~12k

## Notes

- **Why this WP is `kind: backend`** (despite producing markdown
  fixtures): the deliverable's centre of gravity is the executable test
  suite (Python under `tests/`). The markdown fixtures are *data* the
  tests consume. Per WP_BACKEND_STANDARD's verification-gate row: unit
  tests + integration tests at the rubric-runner boundary.
- **P2 atomicity rationale:** this WP creates many files (12 fixture
  dirs + 9 test files ≈ 30+ files), exceeding the MUST ≤ 15 ceiling for
  touch surface. **Justification:** the fixture files are test data, not
  production code (the existing rubric on release-train accepted the
  same pattern in WP-007's drift detector). The unit of work is "one
  test harness + one fixture set proving the rubric works"; splitting
  would fragment the harness from its fixtures. **Recorded as
  PASS-WITH-RATIONALE in DECOMPOSE_VALIDATION.md**.
- **Where the rubric harness lives** — Prior-Art Check at execution
  time. If `plugins/sulis/scripts/sulis-validate-decompose` exists, this
  WP plugs into it. If not, this WP creates a minimal harness scoped
  to P-VER checks only (other phases handled by their existing runners).
- **No mocks.** Real fixtures, real rubric file, real harness — the
  failure modes are real (placeholder strings, missing sections,
  unmapped kinds) and the assertions are real.
