---
id: WP-010
title: Build 4 fixture consumer repos + integration test + dogfood marketplace verification
status: pending
kind: backend
primitive: create
group: GENERATE
change_id: CH-01KT1W
sequence_id: WP-010
dependsOn: [WP-008]
blocks: []
estimated_token_cost:
  input: 5k
  output: 6k
tdd_section: Proof §Integration tests; FR-008 dogfood acceptance
adrs: []
---

## Context

Builds the **E2E proof surface** for the entire change. Four fixture
consumer repos exercise the six UCs end-to-end; one explicit dogfood
run on the marketplace's own repo provides the first observed
`tokens_consumed` data point for ADR-006's v1.1 calibration.

This is the load-bearing acceptance test of Path A n=2 (ADR-001):
when the marketplace's own repo runs discovery through the assembled
skill against the canonical, and the result passes drift verify, the
n=2 dogfood is proven.

The four fixtures per TDD §Proof §Integration tests:

| Fixture | Shape | UC exercised |
|---|---|---|
| `empty/` | `.git/` + remote, no manifests, no CI | UC-001 happy path with all-human-ask fallback (NFR-006 path) |
| `populated/` | `.git/` + remote + `package.json` + `.github/workflows/release.yml` | UC-001 with full Infer phase; UC-006 override flow |
| `monorepo/` | `.git/` + remote + `apps/backend/package.json` + `apps/cli/package.json` | UC-003 with `--path apps/cli` then `--path apps/backend` |
| `pre-existing/` | `.git/` + remote + `.sulis/projects/foo.jsonld` already present | UC-002 (`--update`) + MUC-003 (refuse without `--update`) |

Plus four explicit-error fixtures created on-the-fly per the TDD:
`non-git/`, `no-remote/`, `token-budget/`, `bad-workflow-ref/`.

Plus the idempotent-cancellation test (UC-005 / MUC-002) and the
dogfood run.

## Contract

### Files created

```
tests/fixtures/discover-project/
├── empty/.git/                     (minimal git fixture)
├── empty/.git/HEAD
├── empty/.git/config               (with [remote "origin"])
├── populated/.git/                 (same minimal git fixture)
├── populated/.git/HEAD
├── populated/.git/config
├── populated/package.json
├── populated/.github/workflows/release.yml
├── monorepo/.git/...
├── monorepo/apps/backend/package.json
├── monorepo/apps/cli/package.json
├── monorepo/.github/workflows/ci.yml
├── pre-existing/.git/...
├── pre-existing/.sulis/projects/foo.jsonld
└── (4 explicit-error fixtures are created in test setup, not pre-committed)

plugins/sulis/scripts/tests/integration/
├── test_discover_e2e.py            # the load-bearing E2E test
└── test_discover_cancellation_idempotent.py
```

The `tests/fixtures/discover-project/` tree is a few dozen tiny files
(each fixture has 5-10 files of synthetic repo content). The 4 explicit-
error fixtures are constructed in `setup`/`teardown` rather than
committed.

### E2E test shape (one test per UC)

```python
# plugins/sulis/scripts/tests/integration/test_discover_e2e.py
from pathlib import Path
import pytest
import subprocess


FIXTURES = Path("tests/fixtures/discover-project")


def run_discover(fixture: Path, *args: str, mock_llm=None) -> dict:
    """Run /sulis:discover-project against a fixture. Returns the JSON envelope."""


def test_uc_001_empty_repo_all_human_ask(monkeypatch):
    """UC-001 with all-human-ask fallback (NFR-006 — Null inferrer)."""
    # arrange: mock LLM as unreachable
    # act: run discover against fixtures/empty/
    # assert:
    #   - exit 0
    #   - .sulis/projects/<expected-slug>.jsonld exists
    #   - drift verify passes
    #   - source.repo matches the fixture's git remote
    #   - belongs_to_tenant matches Sha256CrockfordTenantDeriver output


def test_uc_001_populated_repo_full_infer(monkeypatch):
    """UC-001 with full Infer phase happy path."""


def test_uc_006_override_inferred_value(monkeypatch):
    """UC-006 — consumer overrides deploy_target from github-release to npm-publish."""
    # arrange: mock LLM returns deploy_target=github-release
    # act: in the Ask phase, override with npm-publish
    # assert: minted entity has deploy_target=npm-publish (the override, not the inference)


def test_uc_002_re_discovery_per_field_diff(monkeypatch):
    """UC-002 — --update on pre-existing entity; per-field diff (ADR-005)."""
    # arrange: pre-existing entity with deploy_target=npm-publish
    # arrange: mock LLM returns deploy_target=github-release (proposed change)
    # act: run with --update; in Ask, choose 'k' (keep existing)
    # assert: post-mint entity still has deploy_target=npm-publish


def test_uc_003_monorepo_path_scoped():
    """UC-003 — --path apps/cli then --path apps/backend."""
    # act 1: --path apps/cli
    # assert: .sulis/projects/cli.jsonld exists; backend.jsonld absent
    # act 2: --path apps/backend
    # assert: both cli.jsonld and backend.jsonld exist; cli.jsonld untouched (mtime preserved)


def test_uc_004_non_git_directory():
    """UC-004 / MUC-001."""
    # act: run against a non-git tmpdir
    # assert: exit non-zero; stderr matches MUC-001 system response verbatim;
    #         .sulis/projects/ does not exist OR is empty


def test_muc_006_no_remote_with_override():
    """MUC-006 — no remote but --source-repo provided."""


def test_muc_003_refuse_overwrite():
    """MUC-003 — run without --update on pre-existing repo."""
    # assert: exit non-zero; stderr matches MUC-003 system response; existing entity untouched


def test_muc_005_bad_workflow_ref_rolls_back():
    """MUC-005 — bad release_workflow_ref triggers Verify failure + roll-back."""
    # arrange: mock the composition root to write a deliberately-bad release_workflow_ref
    # act: run discover
    # assert: exit non-zero; the entity file is absent (rolled back); stderr names the bad ULID


def test_muc_008_token_budget_falls_back_to_all_human_ask(monkeypatch):
    """MUC-008 / NFR-006 — LLM returns usage > 10,000; Null inferrer takes over; entity still mints."""


def test_dogfood_marketplace_repo_acceptance():
    """The n=2 acceptance: run discovery against the marketplace's own repo.

    Records observed `tokens_consumed` for ADR-006 v1.1 calibration.

    Tolerated to skip in offline environments via SULIS_OFFLINE=1; CI runs
    it for-real with a known-good LLM.
    """
```

### Cancellation idempotency

```python
# test_discover_cancellation_idempotent.py
import os
import signal


def test_sigint_during_ask_phase_leaves_no_partial_state():
    """UC-005 / MUC-002."""
    # arrange: fork-and-run discovery against fixtures/populated/
    # act: when child reaches the Ask phase, send SIGINT
    # assert:
    #   - child exits non-zero with KeyboardInterrupt
    #   - .sulis/projects/ contains zero .jsonld files
    #   - .sulis/projects/ contains zero .tmp files (sweep ran)


def test_re_run_after_cancellation_is_first_time_outcome():
    """UC-005 — re-run after cancel produces a fresh-run experience (NFR-003)."""
```

## Definition of Done

### Red — Failing tests written

- [ ] `test_discover_e2e.py::test_uc_001_empty_repo_all_human_ask`
- [ ] `test_discover_e2e.py::test_uc_001_populated_repo_full_infer`
- [ ] `test_discover_e2e.py::test_uc_006_override_inferred_value`
- [ ] `test_discover_e2e.py::test_uc_002_re_discovery_per_field_diff`
- [ ] `test_discover_e2e.py::test_uc_003_monorepo_path_scoped`
- [ ] `test_discover_e2e.py::test_uc_004_non_git_directory`
- [ ] `test_discover_e2e.py::test_muc_006_no_remote_with_override`
- [ ] `test_discover_e2e.py::test_muc_003_refuse_overwrite`
- [ ] `test_discover_e2e.py::test_muc_005_bad_workflow_ref_rolls_back`
- [ ] `test_discover_e2e.py::test_muc_008_token_budget_falls_back_to_all_human_ask`
- [ ] `test_discover_e2e.py::test_dogfood_marketplace_repo_acceptance`
- [ ] `test_discover_cancellation_idempotent.py::test_sigint_during_ask_phase_leaves_no_partial_state`
- [ ] `test_discover_cancellation_idempotent.py::test_re_run_after_cancellation_is_first_time_outcome`

### Green — Implementation makes tests pass

- [ ] 4 fixture consumer repos at `tests/fixtures/discover-project/{empty,populated,monorepo,pre-existing}/` populated
- [ ] Integration test file `tests/integration/test_discover_e2e.py` authored — covers all 6 UCs + the 4 explicit-error fixtures (created on-the-fly per test)
- [ ] `test_discover_cancellation_idempotent.py` authored
- [ ] All 13 Red tests pass against the assembled skill from WP-008
- [ ] Dogfood test records observed `tokens_consumed` to `.architecture/discover-project/dogfood-tokens.txt` for v1.1 calibration (ADR-006)
- [ ] The dogfood run produces a valid `.sulis/projects/<marketplace-slug>.jsonld` in a tmp copy of the marketplace repo (NOT in the real marketplace — the test uses a copy to avoid polluting the real `.sulis/projects/`)

### Blue — Refactor complete

- [ ] Shared fixture-creation helpers extracted (e.g., `make_minimal_git_repo(path, remote_url, primary_branch)`) — no per-test duplication of `.git/` content
- [ ] LLM mock helper (`mock_llm_returns(...)`) is one fixture used across UC-001/002/006/MUC-008 tests
- [ ] Dogfood test is decorated `@pytest.mark.dogfood` so CI can run it conditionally (the explicit-error fixtures' tests are unconditional)
- [ ] Fixture data is the minimum sufficient — no large `package.json` files; no real LLM keys committed; no `.git/` objects packed (we use `.git/config` + `.git/HEAD` only; `git rev-parse --show-toplevel` resolves without requiring a full object database)

## Sequence

- **dependsOn:** WP-008 (the assembled skill is the system under test)
- **blocks:** — (this is the tail of the dependency graph)
- **Parallelisable with:** — (sole occupant of the final wave)

## Estimated Token Cost

- **Input:** ~5k (TDD §Proof §Integration tests + all 8 MUCs + 6 UCs + ADR-005/006 + dogfood acceptance criteria from SRD §Acceptance)
- **Output:** ~6k (`test_discover_e2e.py` ≈ 400 LOC + cancellation test ≈ 80 LOC + 4 fixture dirs ≈ 20 files of minimal content + helper module ≈ 100 LOC)
- **Total:** ~11k

## Performance

- Each E2E test should complete in <30 seconds (NFR-001 wall-time budget on a typical repo, with mocked LLM bringing the Infer phase to <1s).
- The dogfood test against the real marketplace repo is allotted up to 5 minutes (real LLM call inside the actual NFR-001 envelope).
- Cancellation test uses `os.fork` + `signal.SIGINT` — completes in <2 seconds.

## Notes

- Fixtures intentionally use the minimum `.git/` structure that `git rev-parse --show-toplevel` and `git remote get-url origin` need (a `.git/HEAD` pointing at refs/heads/main + a `.git/config` with a `[remote "origin"]` block). No git objects, no refs database — keeps fixture size small and fast.
- The dogfood test is decorated `@pytest.mark.dogfood` so a CI environment without an LLM key can skip it; locally and on the main CI it runs for real. Observed `tokens_consumed` is the first calibration data point for ADR-006's v1.1 revisit.
- The dogfood test does NOT pollute the real marketplace's `.sulis/projects/` — it copies the marketplace repo to a `tempfile.mkdtemp()` and runs discovery against the copy. Path safety (WP-006) is also exercised here: even if a bug tried to write outside the tmp dir, the path-safety check would block it.
- This WP closes the n=2 acceptance loop per SRD §Acceptance: "Demonstrate a working first-time setup (UC-001) on at least one non-marketplace consumer repo (dogfood)" — the dogfood is the marketplace itself, treated as a consumer for the purposes of this test. A real third-party consumer adoption follows post-merge as a separate validation.
