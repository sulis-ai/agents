---
id: WP-008
title: End-to-end methodology test — dispatch updated agents against fixture spec + dogfood assertion on this change's own artifacts
status: pending
change_id: 01KT2BPBFESCCDY8F7Y5M8RN4R
kind: backend
primitive: create
group: GENERATE
sequence_id: WP-008
dependsOn: [WP-003, WP-004, WP-005, WP-006, WP-007]
blocks: []
estimated_token_cost:
  input: 5k
  output: 6k
tdd_section: Proof pillar test class 3 + 5 (lines 277-291); NFR-005 dogfood gate
adrs: [ADR-002]
verification:
  adapter: methodology
  artifact: tests/methodology/test_verification_by_design_e2e.py::test_dispatch_produces_populated_verification_plan
---

## Context

The end-to-end methodology test that closes the loop. Two assertions:

1. **Fresh dispatch produces output with the new shape** (Proof pillar
   test class 3) — dispatch the updated requirements-analyst (WP-003)
   against a scripted founder persona answering Q1-Q4; assert the
   produced SRD has the `## Verification Plan` section, all six
   subsections populated, no placeholders.

2. **Dogfood assertion** (Proof pillar test class 5; NFR-005) — P-VER
   runs against this very change's own SRD + TDD + WP set; returns
   PASS for each. This is the ship gate per ADR-002: the change cannot
   merge to `dev` until its own rubric passes against its own artifacts.

**TDD reference:** Proof pillar lines 277-291. NFR-005 is the dogfood
gate. ADR-002 fixes the merge-as-cutover behaviour.

**Why this depends on WP-003..WP-006.** The E2E test dispatches the
real updated agents (WP-003 requirements-analyst, WP-004 engineering-
architect) through the real updated skills (WP-005 plan-work, WP-006
specify / draft-architecture / requirements-validation). Until all the
prose extensions land, the agents don't read the canonical, the skills
don't invoke P-VER, and the test asserts nothing meaningful.

**Why this depends on WP-007.** The harness + fixtures + scripted
persona files live under `tests/methodology/`; this WP reuses WP-007's
harness shim.

**Pre-Work Prior-Art Check:** scripted founder personae for E2E agent
dispatch may exist under `tests/fixtures/personae/` from prior changes
— check before authoring. If a similar persona pattern exists, this
WP follows it; if not, this WP introduces a minimal persona schema
(YAML question→answer mapping) scoped to this test.

## Contract

### Files created (new)

```
tests/methodology/
├── test_verification_by_design_e2e.py                     # the E2E test
└── fixtures/
    ├── personae/
    │   └── foundational-questions-answered.yaml           # scripted persona
    ├── changes/
    │   └── e2e-fixture-change/
    │       ├── .change.yaml                               # synthetic change record
    │       └── (no SRD yet — produced by the test)
    └── dogfood-paths.yaml                                 # paths to this change's own SRD/TDD/WP set
```

### Test bodies

**`test_verification_by_design_e2e.py::test_dispatch_produces_populated_verification_plan`**

1. Set up a fixture change record at
   `tests/methodology/fixtures/changes/e2e-fixture-change/` (a fresh
   synthetic change with `kind: documentation` and a single touched
   integration to keep it minimal).
2. Load the scripted persona at
   `tests/methodology/fixtures/personae/foundational-questions-answered.yaml`.
   The persona is a YAML map from question (Q1..Q20) to the
   founder-English answer the persona will give.
3. Dispatch `/sulis:specify` (or the requirements-analyst agent
   directly via the test harness) against the fixture change with the
   persona as the input source.
4. Assert: a file at
   `tests/methodology/fixtures/changes/e2e-fixture-change/SRD.md`
   exists.
5. Assert: the SRD contains a `## Verification Plan` section.
6. Assert: all six required subsections are present.
7. Assert: each subsection has ≥ 30 substantive characters of content
   (not `TBD`, not blank, not bare `n/a`).
8. Assert: the section contains the HTML-comment annotation citing
   `VERIFICATION_QUESTIONS.md`.
9. Assert: P-VER against the produced SRD returns PASS.

**`test_verification_by_design_e2e.py::test_dogfood_pver_passes_on_own_artifacts`**

1. Load `tests/methodology/fixtures/dogfood-paths.yaml` (or compute
   from this change's slug — `.specifications/verification-by-design/`,
   `.architecture/verification-by-design/`).
2. Run P-VER against:
   - `.specifications/verification-by-design/SRD.md`
   - `.architecture/verification-by-design/TDD.md`
   - Every `WP-NNN-*.md` under `.architecture/verification-by-design/work-packages/`
3. Assert: each returns PASS.
4. If any returns FAIL, the test surfaces the rubric's exact failure
   message (the assertion error contains the rubric's verdict + message
   for debuggability).

**`test_verification_by_design_e2e.py::test_grandfather_check_against_pre_merge_change`**

1. Construct a synthetic change record with `started_at` preceding the
   current date by one day (simulating a grandfathered change).
2. Construct a synthetic SRD without a `## Verification Plan` section.
3. Run P-VER.
4. Assert: returns `PASS — grandfathered`, no per-subsection check
   fires.

## Definition of Done

### Red — Failing tests written first

- [ ] All three test functions exist as failing assertions.
- [ ] Initial run FAILS because the agents haven't been updated yet (WP-003..006 not landed) AND the harness isn't wired (WP-007 not landed). Both upstream dependencies prove their value here.

### Green — Implementation makes tests pass

- [ ] Author the scripted persona YAML.
- [ ] Author the fixture change record + dogfood-paths.yaml.
- [ ] Author the three E2E test functions.
- [ ] Wire the test functions through WP-007's harness (re-use, not duplicate).
- [ ] Confirm all three tests pass against the updated agents + skills + rubric.

### Blue — Refactor + polish

- [ ] Persona YAML is founder-readable (FE-04 — no internal IDs in the answers).
- [ ] Test output (on assertion failure) names the exact subsection / file / rubric verdict so debugging is obvious.
- [ ] Test fixture cleanup: produced SRD is git-ignored or written to a tmpdir; doesn't pollute the test directory between runs.
- [ ] CI wiring: the dogfood test runs as part of the merge gate for this change (per ADR-002).
- [ ] No mocks — real agents, real skills, real rubric, real artifacts (this change's own + the synthetic fixture).

## Sequence

- **Sequence ID:** WP-008 (terminal — runs last)
- **dependsOn:** WP-003 (requirements-analyst), WP-004 (engineering-architect), WP-005 (plan-work), WP-006 (orchestrator skills + template), WP-007 (test harness + fixtures)
- **blocks:** none (terminal)
- **Parallelisable with:** none (must run after all dependencies land)

## Estimated Token Cost

- **Input:** ~5k (Proof pillar §test class 3 + 5 + scripted persona pattern + WP-007 harness)
- **Output:** ~6k (≈ 250 LOC across test file + fixtures)
- **Total:** ~11k

## Notes

- **Why this WP is `kind: backend`:** Python test file + YAML fixtures.
  Per WP_BACKEND_STANDARD: unit tests + integration tests + smoke at the
  agent-dispatch boundary.
- **P2 atomicity:** ≤ 8 files touched; one logical unit (E2E + dogfood).
  PASS.
- **The dogfood test is the ship gate.** Per ADR-002, this change cannot
  merge to `dev` until `test_dogfood_pver_passes_on_own_artifacts`
  returns green in CI. The other tests are also blocking, but the
  dogfood test specifically defends NFR-005.
- **Persona schema is intentionally minimal.** A YAML question→answer
  map; the agent's Phase 3 reads the persona as if it were the
  founder's turn-by-turn responses. Future cross-change personae can
  reuse the shape; this WP doesn't try to generalise it.
- **No flakiness budget.** If the agent dispatch is non-deterministic
  (LLM token variance), assert on structural properties (section
  presence, subsection count, ≥ 30 chars per subsection, citation
  presence), never on specific wording. The persona answers are short
  and unambiguous.
- **Total tokens across all 8 WPs:** ~71k input + ~37k output ≈ 108k.
  Well within budget.
