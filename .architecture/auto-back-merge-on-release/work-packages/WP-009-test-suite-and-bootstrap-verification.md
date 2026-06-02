---
id: WP-009
title: Author the full test suite — unit + regression + chaos + bootstrap-from-zero
status: pending
change_id: auto-back-merge-on-release
kind: backend
primitive: create
group: GENERATE
sequence_id: WP-009
dependsOn: [WP-001, WP-003, WP-004, WP-005, WP-006, WP-007, WP-008]
blocks: []
estimated_token_cost:
  input: 4k
  output: 5k
tdd_section: §6 Proof — Verification Protocol (§6.1–§6.7); §9 Verification Plan (§9.1–§9.6)
adrs: [ADR-001, ADR-002, ADR-003, ADR-005, ADR-006]
verification:
  adapter: backend
  artifact: plugins/sulis/scripts/tests/integration/test_clean_release_e2e.sh
---

## Context

Authors the **full test suite** that proves the auto-back-merge
design holds end-to-end. The suite is structured per TDD §6's three
rings:

1. **Unit tests** (TDD §6.1) — eight bash tests against the drift
   helper, the pin format, the workflow YAML statics, and the
   concurrency directive. Sub-second; run on every commit.
2. **Regression tests** (TDD §6.2) — four end-to-end paths against
   scripted local git remotes + stubbed `gh`: clean, raced, branch-
   protection-rejected, atomicity-failure.
3. **Chaos test** (TDD §6.3) — race-window simulation:
   `git ls-remote` returns SHA ≠ pin → assert PR-open path fires
   and no force flag ever gets used.
4. **Bootstrap-from-zero** (TDD §9.3) — end-to-end test that
   exercises a fresh consumer (empty repo → branch protection →
   install shim → drop changeset → release → assert dev == main
   within window).
5. **Verification of the verification** (TDD §6.7) — meta-step
   that, for each unit test, temporarily reverts the relevant
   production change and confirms the test goes red.

Earlier WPs (WP-001, WP-003, WP-006) authored 1–5 individual tests
each as their Red tests. **This WP authors the rest of the suite
(the canonical-string parity test, the chaos test, the bootstrap
test, the n=1 dogfood check, the meta-revert verification harness)
AND wires everything into a single `run.sh` orchestrator.**

The dependency graph for this WP is deliberately deep — it depends
on every WP that landed production code (1, 3, 4, 5, 6, 7, 8). WP-002
is transitively covered via WP-003 (which depends on WP-002). The
test suite cannot meaningfully exist before its production-code
subjects exist.

## Contract

### Files created

```
plugins/sulis/scripts/tests/
├── run.sh                                          (orchestrator — runs unit/integration/chaos)
├── unit/
│   ├── test_drift_check_clean.sh                   (NEW HERE — TDD §6.1 row 1)
│   ├── test_drift_check_drifted_no_pr.sh           (NEW HERE — TDD §6.1 row 2)
│   ├── test_drift_check_drifted_with_pr.sh         (NEW HERE — TDD §6.1 row 3)
│   ├── test_drift_check_under_5_seconds.sh         (NEW HERE — NFR-007)
│   ├── test_canonical_strings_parity.sh            (NEW HERE — TDD §3 P8)
│   ├── test_pin_write_format.sh                    (extended from WP-006)
│   ├── test_pin_read_parity.sh                     (extended from WP-006)
│   ├── test_no_force_push_static.sh                (extended from WP-002)
│   ├── test_concurrency_present.sh                 (extended from WP-002)
│   ├── test_post_condition_step_present.sh         (extended from WP-003)
│   └── ... (other per-WP unit tests authored upstream)
├── integration/
│   ├── test_clean_release_e2e.sh                   (extended from WP-003)
│   ├── test_raced_release_e2e.sh                   (extended from WP-003)
│   ├── test_branch_protection_fallthrough.sh       (extended from WP-003)
│   ├── test_atomicity_failure_exits_nonzero.sh     (extended from WP-003)
│   ├── test_marketplace_shim_calls_reusable.sh     (extended from WP-005)
│   ├── test_change_start_drift_gate_blocks.sh      (extended from WP-007)
│   └── test_release_train_e2e.sh                   (NEW HERE — runs release-train against fixture)
├── chaos/
│   └── test_race_window.sh                         (NEW HERE — TDD §6.3)
├── methodology/
│   ├── test_release_on_merge_yaml_unchanged_behaviour.sh   (from WP-002 characterisation)
│   └── test_verification_revert_harness.sh         (NEW HERE — TDD §6.7 verification of verification)
├── bootstrap_from_zero.sh                          (NEW HERE — TDD §9.3 end-to-end)
├── fixtures/
│   ├── drift_check/
│   │   ├── repo-clean/                             (populated HERE)
│   │   ├── repo-drifted/                           (populated HERE)
│   │   └── gh-stubs/                               (populated HERE)
│   ├── release-on-merge/
│   │   ├── pre-move-snapshot.yml                   (from WP-002)
│   │   └── release-pr-body-with-pin.txt            (populated HERE)
│   └── bootstrap/
│       └── sandbox-template/                       (NEW HERE — fixture repo skeleton)
└── README.md                                        (NEW HERE — how to run the suite)
```

### Critical new test — `test_canonical_strings_parity.sh`

This is the load-bearing P8 enforcement. It reads the four canonical
strings from FOUR sources and asserts byte-for-byte parity:

| Source | What's extracted |
|---|---|
| `plugins/sulis/scripts/drift_check.sh` | `LABEL`, `TITLE_PREFIX`, `BASE_BRANCH`, `HEAD_BRANCH` constants (WP-001) |
| `plugins/sulis/templates/workflows/release-on-merge.yml` | `--label "..."`, `--title "..."`, `--base "..."`, `--head "..."` literals (WP-003) |
| `plugins/sulis/skills/release-train/SKILL.md` | The pin format string in Step 5's snippet (WP-006) |
| `plugins/sulis/references/git-workflow-standard.md` | The four strings as they appear in GIT-12 worked examples (WP-008) |

Test logic: extract each string from each source, assert all four
sources agree. Test fails if a future WP touches one source without
updating the others.

### Critical new test — `test_race_window.sh` (chaos)

Per TDD §6.3, this is the load-bearing chaos test for MUC-001. Setup:

1. A fixture git remote at `fixtures/drift_check/repo-drifted/`
   with `origin/dev` at SHA `def456...` and `origin/main` at SHA
   `abc123...` (dev ahead of main is the post-release-merge state
   in the workflow's runtime).
2. A stub `gh` on `$PATH` configured to return the test fixture's
   pin and PR list responses.
3. The reusable workflow (WP-003) is executed via `bash` directly
   on the step scripts.

Assertions:
- The pin-read step extracts a SHA different from `def456...`.
- The decide+act step takes the raced path.
- `gh pr create --base dev --head main --label back-integrate` is
  invoked (verified via the stub's recorded call log).
- **`git push origin main:dev` is NEVER invoked** — verified by
  asserting the stub `git push` was either not called or called only
  to other refs.
- **`--force` and `--force-with-lease` flags never appear in any
  recorded call** — even at runtime.

### Critical new test — `bootstrap_from_zero.sh`

Per TDD §9.3, this runs against `sulis-ai/release-flow-sandbox` (a
throwaway repo). The test orchestrates:

1. `gh repo create sulis-ai/release-flow-sandbox-${RUN_ID} --private`
   (a per-run sandbox to avoid state leakage between runs).
2. Configure branch protection on `dev` and `main` per GIT-04.
3. Install Sulis plugin at the shipping version.
4. Copy `plugins/sulis/templates/shims/release-on-merge.yml` (WP-004)
   into `.github/workflows/release-on-merge.yml`. Substitute the
   `<MAJOR>.<MINOR>.<PATCH>` placeholder with the shipping version.
   Commit to dev.
5. Drop a `.changesets/*.yaml`; merge to dev.
6. Invoke `/sulis:release-train` (the prose from WP-006 is executed
   as a shell sequence).
7. Merge the release PR.
8. Poll `git ls-remote origin dev` and `git ls-remote origin main`
   every 30 seconds for up to 5 minutes.
9. Assert: `dev == main` within 5 minutes.
10. Tear down: `gh repo delete sulis-ai/release-flow-sandbox-${RUN_ID}
    --yes`.

Test is invoked from the sandbox CI on every plugin version that
touches the workflow (per TDD §6.4 + §9.2).

### Critical new test — `test_verification_revert_harness.sh`

Per TDD §6.7, this is the meta-test that proves each unit test
actually catches the regression it claims to catch. For each unit
test:

1. Identify the production file it asserts against (from the test's
   header comment — convention: `# verifies: <file>`).
2. Temporarily revert a one-line targeted change in that file (e.g.
   delete the `concurrency:` block, or replace `--label back-integrate`
   with `--label backintegrate`).
3. Re-run the unit test. Assert it now exits non-zero (i.e. it
   detects the regression).
4. Restore the file. Assert the test now passes again.

The harness runs as a single bash script that loops over the unit
tests directory. It produces a one-line report per test: "test_X:
detects regression as expected" or "test_X: does NOT detect
regression — TEST IS WORTHLESS".

### The `run.sh` orchestrator

```bash
#!/usr/bin/env bash
# plugins/sulis/scripts/tests/run.sh — run the auto-back-merge test suite

set -u
set -o pipefail

PASS=0
FAIL=0
FAILED_TESTS=()

run_directory() {
  local dir=$1
  for t in "$dir"/test_*.sh; do
    [[ -f "$t" ]] || continue
    if bash "$t" >/dev/null 2>&1; then
      PASS=$((PASS+1))
    else
      FAIL=$((FAIL+1))
      FAILED_TESTS+=("$t")
    fi
  done
}

echo "=== unit ==="
run_directory "$(dirname "$0")/unit"
echo "=== integration ==="
run_directory "$(dirname "$0")/integration"
echo "=== chaos ==="
run_directory "$(dirname "$0")/chaos"
echo "=== methodology ==="
run_directory "$(dirname "$0")/methodology"

echo
echo "PASS: $PASS"
echo "FAIL: $FAIL"
if (( FAIL > 0 )); then
  printf '  FAILED: %s\n' "${FAILED_TESTS[@]}"
  exit 1
fi
exit 0
```

### Fixture content authored here

- `fixtures/drift_check/repo-clean/`: scripted local git remote where
  `origin/main` is an ancestor of `origin/dev`.
- `fixtures/drift_check/repo-drifted/`: scripted local git remote
  where `origin/dev` is behind `origin/main` (the post-release
  state).
- `fixtures/drift_check/gh-stubs/`: shell stubs for `gh pr list`
  returning either "1 open back-integrate PR" or "no open PRs" based
  on a `STUB_MODE` env var.
- `fixtures/release-on-merge/release-pr-body-with-pin.txt`: a
  recorded release PR body produced by WP-006's Step 5 snippet,
  used as the input to `test_pin_read_parity.sh`.
- `fixtures/bootstrap/sandbox-template/`: a minimal repo skeleton
  the bootstrap test uses to clone-and-customise per run.

### Canonical-string compliance

The whole suite enforces canonical-string parity. No string is
hand-written into a test; every reference to `back-integrate`, the
title prefix, `dev-sha-at-open`, `dev`, or `main` is sourced from
the canonical declaration (either `drift_check.sh`'s constants or
the YAML literals). Tests fail loudly if any source drifts.

## Definition of Done

### Red — Failing tests written

Because WP-009 IS the test suite, "Red tests" here means the
verification-of-verification harness — proving the suite actually
catches regressions.

- [ ] `plugins/sulis/scripts/tests/methodology/test_verification_revert_harness.sh`
      exists and, when run against the production code, exits 0 with
      every unit test passing the "detects-regression" check.
- [ ] `plugins/sulis/scripts/tests/unit/test_canonical_strings_parity.sh`
      exists and passes when run against the assembled production
      code from WP-001 + WP-003 + WP-006 + WP-008.
- [ ] `plugins/sulis/scripts/tests/chaos/test_race_window.sh` exists
      and passes against the drifted fixture.

### Green — Implementation makes tests pass

- [ ] All NEW unit tests authored at the paths listed in the file
      inventory above; each is bash, sub-second, fixture-backed.
- [ ] All NEW integration tests authored; each runs against a
      scripted local git remote + stub `gh`; each is under 30 seconds.
- [ ] The chaos test authored and passes — the workflow takes the
      raced path; `git push origin main:dev` is never invoked.
- [ ] `bootstrap_from_zero.sh` authored; it runs end-to-end against
      `sulis-ai/release-flow-sandbox-${RUN_ID}` when given valid
      `gh auth` and a real plugin version pin.
- [ ] `run.sh` orchestrator authored and exits 0 against the
      production code.
- [ ] All fixture content populated.
- [ ] Top-level `plugins/sulis/scripts/tests/README.md` documents:
      directory structure, how to run locally, how to add a test,
      the canonical-string-parity discipline.

### Blue — Refactor complete

- [ ] Every test header carries a `# verifies: <file>` comment so
      the verification-revert harness knows which production file
      to revert against.
- [ ] No test inlines a canonical string — every test reads it from
      the helper's constants OR the YAML literal at runtime. Grep
      for `back-integrate` outside of the canonical sources should
      return zero hits.
- [ ] Stub `gh` lives in one place (`fixtures/drift_check/gh-stubs/`)
      and is reused across tests via a `PATH` prefix in each test's
      setup. No copy-paste of stub logic.
- [ ] Fixture local git remotes are reproducible — there's a
      `fixtures/drift_check/setup.sh` that recreates the fixture
      from scratch (so CI can rebuild them deterministically).
- [ ] `run.sh` exits non-zero ONLY when tests fail — exits 0 cleanly
      on success. CI uses the exit code, nothing else.
- [ ] No `set -e` in tests (explicit exit-code handling, since
      tests are checking exit codes themselves).

## Sequence

- **dependsOn:**
  - WP-001 (drift_check.sh + its constants — load-bearing for the
    parity test and the drift unit tests)
  - WP-003 (reusable workflow with back-merge steps — load-bearing
    for integration tests, the chaos test, the static workflow
    tests)
  - WP-004 (canonical shim template — bootstrap test installs it)
  - WP-005 (marketplace shim — `test_marketplace_shim_calls_reusable.sh`
    is extended here; the n=1 dogfood check needs the marketplace's
    own shim to be in place)
  - WP-006 (release-train pin write + drift check — pin parity test,
    drift-check call-site test)
  - WP-007 (change start drift check — drift gate integration test
    extended here)
  - WP-008 (GIT-12 — canonical-string parity test reads from GIT-12)
- **blocks:** — (terminal WP)
- **Parallelisable with:** — (depends on every production-code WP)

The seven-dep count exceeds the SHOULD ≤ 5 dependsOn rule. This is
documented in `DECOMPOSE_VALIDATION.md` P4 as a recorded SHOULD
deviation: the test suite is the integration surface; an honest
dependency count would require seven separate "test for WP-N"
fragment-WPs that each only ran when their target was present. That
would produce 7 mini-WPs with significant cross-test infrastructure
duplication (fixtures, stubs, the orchestrator). The single
test-suite WP is the boring choice.

## Estimated Token Cost

- **Input:** ~4k (TDD §6, §9 + every upstream WP's contract + the
  existing test-fixture patterns from `discover-project/` and
  `release-train-as-entities/`)
- **Output:** ~5k (NEW unit tests ≈ 5 × 30 LOC + NEW integration
  test ≈ 60 LOC + chaos test ≈ 80 LOC + bootstrap ≈ 100 LOC + verify-
  the-verifier harness ≈ 60 LOC + run.sh ≈ 30 LOC + README ≈ 80 LOC
  + fixtures ≈ 200 LOC = ~640 LOC across ~20 files)
- **Total:** ~9k

## Notes

- **Why this is one WP, not seven (one per production WP):** the
  cross-test infrastructure (fixtures, stub `gh`, run.sh
  orchestrator) is shared. Splitting would require each per-WP test
  fragment to re-bootstrap the fixtures or to depend on a "test
  infrastructure" WP — at which point we're back to one WP, just
  arrived at slowly. The boring single-WP shape is the right shape.
- **Why the bootstrap test is in the suite, not standalone:** the
  bootstrap is the highest-fidelity verification — fresh consumer,
  real CI, real GitHub. Having it gated by `run.sh` (with a CI-only
  toggle since it costs sandbox repo creation) means it's
  discoverable and runnable by maintainers without learning a
  separate procedure.
- **Why the meta-revert harness is a separate test file:** it's
  expensive (it temporarily reverts production code) and it's
  meta — running it on every commit is overkill. It's gated as a
  weekly CI sweep + a manual invocation, distinct from the per-
  commit unit/integration suite. The harness's existence is the
  TDD §6.7 contract; the gating decision is a CI configuration
  concern.
- **Why "test_canonical_strings_parity.sh" is the most important
  test in the suite:** the design's correctness rests on four
  strings being identical across four files. A subtle typo (e.g.
  `back_integrate` vs `back-integrate`) would break the design
  silently — the drift gate wouldn't find the open PR; the workflow
  wouldn't filter the PR list correctly. The parity test is the
  single artifact that catches the entire class of "one source
  drifted, the rest didn't" bug.
- **Touch surface:** ~20 files (the test suite + fixtures + README).
  Exceeds the SHOULD ≤ 8; documented in DECOMPOSE_VALIDATION.md as
  rationalised — the test suite is one logical unit; splitting it
  produces partial graphs that each can't run independently. Under
  the MUST ≤ 15 if we count grouped fixture directories as 1 each.
- **Sandbox repo creation requirement:** the bootstrap test needs
  `sulis-ai/release-flow-sandbox-${RUN_ID}` creation permissions.
  Documented in TDD §9.6 as a "deferred to follow-on" infra need;
  this WP assumes the permissions are available at execution time.
  If not, `bootstrap_from_zero.sh` is gated behind a `BOOTSTRAP_ENABLED=1`
  env var and skipped without failing the suite.

## Verification Plan

Per TDD §6.7 (verification of the verification) + §9.2 (verification
environments):

- **Adapter:** `backend` (bash test suite that exercises production
  code via fixture remotes + stub `gh`).
- **Concrete artifact:**
  `plugins/sulis/scripts/tests/integration/test_clean_release_e2e.sh`.
  The most distinctive test in this WP is
  `test_canonical_strings_parity.sh` (P8 enforcement across four
  sources) — the parity test is the load-bearing one because it
  catches the entire "source drift" failure class.
- **What this WP's verification proves:** the test suite itself is
  exercised by the meta-revert harness — each unit test catches
  the regression it claims to catch. The end-to-end behaviour
  (release-train → workflow → back-merge → drift gate) is proven
  by the four integration tests + the chaos test + the bootstrap-
  from-zero test. The n=1 dogfood (WP-005) is verified via
  `test_marketplace_shim_calls_reusable.sh` plus an out-of-band
  observation after the next marketplace release.
- **Acceptance criteria:** `run.sh` exits 0 against the production
  code; `test_verification_revert_harness.sh` reports every unit
  test as "detects regression as expected"; `bootstrap_from_zero.sh`
  exits 0 when run against a real sandbox repo (gated by env var).
