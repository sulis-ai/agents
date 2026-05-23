---
id: HD-002
title: TrainTestbed integration fixture (`cmd_run` end-to-end failure-path coverage)
status: implemented
severity: HIGH
pillar: proof
sources:
  - SEA audit report 2026-05-23 (Pattern A — cmd_run's failure paths covered only by per-helper monkeypatches; no end-to-end harness; HD-001 cannot safely refactor cmd_run without one)
  - HD-005 (the GHClient protocol — this delta consumes that seam)
created: 2026-05-23
implemented: 2026-05-23
depends_on:
  - HD-005
---

## Context

`wpx-train`'s `cmd_run` orchestrates the integration pipeline: rebase chain,
bundled-tip CI poll, sequential squash-merge, deploy poll, health check,
smoke test, plus the ADR-212 revert path on post-merge failure and the
HD-003 partial-merge recovery path on mid-batch merge failure. Six failure
modes exist:

| # | Failure | Recovery |
|---|---|---|
| 1 | Rebase conflict on WP-N (mid-batch) | Flip WP-N to step-7-blocked; write per-WP BLOCKER; continue with remaining WPs |
| 2 | Bundled-tip CI red/timeout | Pause train; founder inspect/resume/abort (no merges have happened) |
| 3 | Mid-batch merge failure | HD-003 — revert successful merges, restore branches, train BLOCKER |
| 4 | Deploy timeout | Pause train; founder check deploy URL, resume/abort |
| 5 | Deploy explicit failure | ADR-212 revert path |
| 6 | Health unhealthy / smoke FAIL | ADR-212 revert path |

Today, each of these paths is tested in isolation via per-helper
monkeypatches (`test_wpx_train_partial_merge_failure.py` patches eleven
collaborators; `test_wpx_train_paused_state.py`, `test_wpx_train_drift_detection.py`,
etc. each set up similar scaffolding). Test setup is the bulk of each test
file; the assertion-to-setup ratio is low; and the assertions rarely cross
helper boundaries.

The architectural consequence:

- **HD-001 (cmd_run plan/commit/verify split) cannot ship safely.** The
  split refactors the orchestration into three callable phases. Each
  failure mode crosses phase boundaries. Without an end-to-end harness
  that drives all six failure paths against the *real* orchestrator, the
  refactor either skips coverage of cross-phase invariants (the rebase
  conflict's effect on subsequent merges, the deploy failure's effect on
  the restore loop) or attempts to verify them through ad-hoc test
  reshuffling. The former leaks regressions; the latter has historically
  produced the 2026-05-23 partial-merge crash that HD-003 just fixed.
- **The HD-005 GHClient seam is the missing ingredient.** With a real
  local git repo as the "remote" and a `FakeGHClient` injected via
  `_default_gh_client`, the testbed can drive `cmd_run` against
  deterministic data while controlling exactly which GitHub-API call
  fails when. Plus the rebase phase still uses real `git rebase`
  against real commits — so the test exercises the same code path
  production hits.

## Decision

Build **`scripts/tests/integration/testbed.py`** containing a `TrainTestbed`
pytest fixture that:

1. **Provisions a real local bare git repo** as `origin` plus a working
   "founder workspace" clone where the train operates. The repo seeds
   `dev` with a baseline commit and provides helpers to create feature
   branches with N distinct commits.
2. **Injects a `FakeGHClient`** that swaps the module-level
   `_default_gh_client` from HD-005. The fake's read methods (`branch_sha`,
   `ref_sha`, `compare`, `branch_exists`) query the local bare repo
   directly via `git` plumbing — so production-shaped data flows through
   them. The fake's `merge` simulates a squash-merge by fast-forwarding
   `dev` on the bare repo to the head of the merged branch (the historical
   `gh api -X POST /merges` endpoint's effect). The fake's `clone` runs
   `git clone` from the bare repo. The fake's `check_runs` / `deploy_runs`
   are pure stubs the test configures.
3. **Provides named failure injection.** A small set of fluent methods on
   the fixture configures the FakeGHClient + the testbed-owned simulation
   state to inject specific failures: `fail_rebase(wp)`, `fail_ci()`,
   `timeout_ci()`, `fail_merge(wp)`, `fail_deploy()`, `timeout_deploy()`,
   `fail_health()`, `fail_smoke()`. Each is deterministic and idempotent.
4. **Exposes assertion helpers** for dev state, INDEX state, BLOCKER
   presence, and train-state YAML contents.

Then write **`scripts/tests/integration/test_train_failure_paths.py`**
with 7 tests covering the happy path plus the six failure modes above.

This is **EXPAND-Create** in REINFORCE-Test mode: net-new test
infrastructure on top of HD-005's adapter port. No subject to wrap.
Characterisation tests are not required (this delta IS the
characterisation test for HD-001's forthcoming refactor).

## Verification

### Characterisation test

This delta IS the characterisation suite for HD-001. The failing-test
contract here is: **without the testbed, cmd_run's six failure paths
cannot be driven end-to-end through a single orchestrator entry point.**
The proof is the test count delta: today there are zero tests under
`scripts/tests/integration/test_train_*`; after this delta there are
seven, each calling `cmd_run` directly and asserting on real INDEX +
git state.

### Acceptance criteria

1. `scripts/tests/integration/testbed.py` exists and exports
   `TrainTestbed` plus a `train_testbed` pytest fixture.
2. The fixture provisions a real local bare repo + clone, with helpers
   to seed feature branches, seed INDEX, and inject failures.
3. `FakeGHClient` implements every GHClient Protocol method (HD-005),
   verified by `isinstance(fake, GHClient)` (the Protocol is
   `@runtime_checkable`).
4. `scripts/tests/integration/test_train_failure_paths.py` contains
   at minimum seven tests:
   - happy path (3-WP bundle, all green, all merge, deploy green,
     health healthy, smoke PASS)
   - rebase conflict on the second of three WPs
   - bundled-tip CI red
   - bundled-tip CI timeout
   - mid-batch merge failure (HD-003 path)
   - deploy timeout (paused state)
   - deploy explicit failure (ADR-212 revert)
   - health unhealthy (ADR-212 revert)
   - smoke FAIL (ADR-212 revert)
5. All seven (or more) new tests pass. All 268 existing tests continue
   to pass. Teardown is clean — no leftover tmp dirs or branches in the
   developer's `~` between tests (verified by pytest's `tmp_path`
   isolation).
6. No real network calls. No real `gh` binary needed. No real GitHub.

## ADDED

- **`scripts/tests/integration/testbed.py`** (~300 LOC):
  - `FakeGHClient` class implementing the HD-005 Protocol against a local
    bare git repo + a configurable simulation state.
  - `TrainTestbed` dataclass with seed helpers (`seed_wp_branch`,
    `seed_index_with_wps`) and failure-injection methods (`fail_rebase`,
    `fail_ci`, `timeout_ci`, `fail_merge`, `fail_deploy`, `timeout_deploy`,
    `fail_health`, `fail_smoke`).
  - Assertion helpers (`assert_merged_on_dev`, `assert_wp_status`,
    `assert_blocker_exists`, `read_train_record`).
  - `train_testbed` pytest fixture that constructs the testbed,
    monkeypatches `_wpxlib._default_gh_client`, and tears down all
    state on exit.
- **`scripts/tests/integration/test_train_failure_paths.py`** (~300 LOC):
  - Eight tests covering the happy path + the seven failure modes above.

## MODIFIED

- Nothing in production code. The testbed consumes HD-005's existing
  injection seam; no further changes to `_wpxlib.py` or `wpx-train` are
  required for this delta.

## REMOVED

- Nothing.

## Trade-offs

- **+** End-to-end coverage of all six failure paths through a single
  orchestrator entry point — HD-001's refactor can now be verified
  against behaviour-preservation rather than against ad-hoc helper-level
  mocks.
- **+** Real git rebase against real commits exercises the same code
  paths production runs (only the GitHub-API surface is faked). Future
  rebase bugs surface here rather than in production.
- **+** The named failure-injection API documents the failure
  vocabulary the train tolerates. Adding a new failure mode (e.g.
  HD-001's MQ-ejection) is one new method, not a fresh per-test
  monkeypatch dance.
- **−** ~300 LOC of test infrastructure to maintain. Mitigated by:
  the testbed lives in `tests/integration/` and is opt-in (tests
  that don't need it use the existing fixtures); the public API is
  small (eight failure methods + four assertion helpers + two seed
  helpers).
- **−** The FakeGHClient's `merge()` simulation is a model of the real
  `/merges` endpoint, not the endpoint itself. If GitHub's behaviour
  diverges (new conflict semantics, etc.), the fake must follow. We
  accept the model-drift risk because the alternative — exercising
  every test against real GitHub — is not deterministic and not free.
- **−** The fake's `deploy_runs` and `check_runs` are pure stubs. We
  do not simulate CI workflow timing realistically. Tests configure
  the desired verdict directly. This is the standard test trade-off
  (control vs realism); the tests that need realistic CI timing live
  outside this suite.

## Rationale (boring-code check)

`FakeGHClient` is a plain class implementing the Protocol via duck
typing; no Protocol metaclass tricks. `TrainTestbed` is a dataclass
with explicit fields. Failure injection is a dict on the testbed —
no decorators, no metaprogramming. Teardown is via pytest's standard
`tmp_path` + `monkeypatch` auto-restore. Side-effect helpers
(`flip_index_status_via_cli`, `write_train_blocker`,
`revert_train_on_dev`, `restore_branch_with_guard`) are monkeypatched
to record-and-no-op so tests stay fast; assertion helpers read the
recorded calls.
