---
id: WP-001
title: Fix the discover-project verify gate that rolls back every mint in consumer repos
status: pending
kind: backend
primitive: fix
group: REORGANISE
composite_of: [REORGANISE, REINFORCE]
change_id: CH-01KT48
sequence_id: WP-001
dependsOn: []
blocks: []
estimated_token_cost:
  input: 8k
  output: 6k
spec_section: SPEC.md §Scope (3 surgical fixes); §Acceptance; §Constraints
characterisation_test: tests/integration/test_discover_consumer_repo_regression.py::test_consumer_repo_mint_persists_and_records_default_branch
verification:
  adapter: backend
  artifact: tests/unit/test_check_canonical_drift_scope.py::test_scope_valid_entity_exits_zero
adrs: []
---

## Context

Source of record: `.changes/fix-discover-verify-scope.SPEC.md` (this change
skipped a full blueprint by design — it is three surgical bug fixes in
existing code, fully specified). No new entity fields, no schema changes,
no re-architecture.

`/sulis:discover-project` mints a Project entity for a repo, then runs a
post-mint drift check (`_discovery.verifier.verify_and_roll_back_on_failure`)
that rolls the mint back if the check fails. In any repo other than the
Sulis marketplace repo itself, that check fails 100% of the time, so the
mint is *always* rolled back — adopting Sulis in a new repo is impossible.
Confirmed in the wild against `Capsule-Insurance/platform`.

Three independent bugs combine on the **same verify path**:

1. **The verifier calls a `--scope` mode the drift checker doesn't have.**
   `_discovery/verifier.py` already builds the argv
   `check-canonical-drift.py --scope <entity> --cross-tenant-refs-allowed-for ...`
   (lines 134-141), but `check-canonical-drift.py`'s argparse only accepts
   `--instance-dir` (required), `--yaml-path` (required), `--marketplace-json`,
   `--validate-schemas`, and `--cross-tenant-refs-allowed-for`. There is no
   `--scope` flag. Every invocation exits 2 (`the following arguments are
   required: --instance-dir, --yaml-path`); the verifier reads non-zero as
   drift and rolls the mint back.

2. **The default detector path is cwd-relative.** `verifier.py:58` sets
   `_DEFAULT_DRIFT_DETECTOR = Path("plugins/sulis/scripts/check-canonical-drift.py")`
   — relative to the current working directory. That path only resolves
   from inside the marketplace repo. In a consumer repo it doesn't exist,
   so `python3` exits before the checker runs.

3. **`primary_branch` records the checked-out branch, not the repo default.**
   `_discovery/inspector.py:181` uses `git branch --show-current`, so a mint
   run from a feature branch records e.g. `feat/azure-terraform-foundation`
   as the project's primary branch instead of the repo default (`main`).

These three are one Work Package, not three. The consumer-repo regression
test (the load-bearing acceptance evidence) only goes green when **all
three** are fixed: the mint must persist (fixes 1 + 2 make the real
detector runnable and findable) AND `primary_branch` must read `main`
(fix 3). They share the same code path and the same failing test. Splitting
them would create artificial parallelism for sequential, same-capability
work and leave the headline regression test red after any single fix.

## Why this primitive

- **REORGANISE (Refactor)** for fixes 2 and 3: behaviour-preserving internal
  corrections to existing functions (`_DEFAULT_DRIFT_DETECTOR` resolution;
  `primary_branch` derivation). Per the Characterisation-Tests-Before-Refactor
  MUST, both are pinned by the consumer-repo regression test before the change.
- **EXPAND-Extend** for fix 1: `check-canonical-drift.py` gains a new `--scope`
  mode alongside the existing `--instance-dir`/`--yaml-path` mode. The existing
  release-train CI path stays backward-compatible (regression guard below).
- **REINFORCE (Test)** runs orthogonally: two new tests close the gap that let
  the broken `--scope` call ship — a real-subprocess `--scope` test and the
  consumer-repo regression test.

No Wrap. Fix 1 extends an internal script the change owns (Extend, not Wrap).
Fixes 2 and 3 are in-place corrections (Refactor, not Wrap). No new wrapper
layer over internal code.

## Contract

### Files modified

```
plugins/sulis/scripts/check-canonical-drift.py        # add --scope <entity-file> mode
plugins/sulis/scripts/_discovery/verifier.py          # resolve _DEFAULT_DRIFT_DETECTOR via __file__
plugins/sulis/scripts/_discovery/inspector.py         # record repo-default branch, not checked-out
```

### Files created

```
plugins/sulis/scripts/tests/unit/test_check_canonical_drift_scope.py     # real-subprocess --scope test
plugins/sulis/scripts/tests/integration/test_discover_consumer_repo_regression.py  # consumer-repo regression
```

### Fix 1 — `--scope <entity-file>` mode in `check-canonical-drift.py`

A new argparse mode that schema-validates **one** entity file and applies
the cross-tenant-ref allowlist, **without** requiring `--instance-dir` or
`--yaml-path`. This is the mode `verifier.py` already invokes.

Contract:

- `--scope <path>` and the existing `--instance-dir`/`--yaml-path` pair are
  mutually exclusive entry points. When `--scope` is present, `--instance-dir`
  and `--yaml-path` MUST NOT be required (today argparse marks them
  `required=True`; the requiredness moves to a post-parse check so the two
  modes coexist).
- `--scope` reads the named entity file (a Project bag of shape
  `{"@context": ..., "projects": [ {Project}, ... ]}` per the discover-project
  mint output — see `instances/release-train/projects.jsonld`), schema-validates
  each contained Project against the vendored
  `plugins/sulis/brain/compiled/foundation/project.schema.json`, and applies
  the cross-tenant-ref allowlist from `--cross-tenant-refs-allowed-for` (a
  `release_workflow_ref` pointing at the marketplace tenant's Workflow is NOT
  drift when allowlisted; `cross_tenant_ref_is_allowed` is the single source
  of truth already present in `_canonical_drift.matcher`).
- Exit codes preserve the existing contract: `0` clean, `1` drift (the JSON
  envelope's `data.drift` names the gap), `2` invocation error (missing arg;
  file not found; malformed entity). The envelope shape (`{"ok": bool, ...}`)
  is unchanged.
- A valid entity → exit 0. A drifted entity (e.g. missing a `project.schema.json`
  `required` field, or a non-allowlisted cross-tenant ref) → exit non-zero
  with the structured failure message.

The flag-name `--yaml-path` stays (historic; the dispatcher already routes by
file extension). No change to cross-tenant-ref allowlist semantics or the
MUC-005 rollback-and-surface contract — only make the gate runnable in
single-entity scope.

### Fix 2 — resolve `_DEFAULT_DRIFT_DETECTOR` via `__file__`

```python
# plugins/sulis/scripts/_discovery/verifier.py
# verifier.py lives at plugins/sulis/scripts/_discovery/verifier.py;
# the detector is its sibling-one-up at plugins/sulis/scripts/check-canonical-drift.py
_DEFAULT_DRIFT_DETECTOR = (
    Path(__file__).resolve().parent.parent / "check-canonical-drift.py"
)
```

Resolves to the installed plugin location regardless of cwd. The
`drift_detector_path` kwarg override (used by test harnesses) is unchanged.

### Fix 3 — record the repo default branch in `inspector.py`

Per the SPEC's CP constraint, resolve the repo default via the **established**
mechanism, not a bespoke heuristic:

```python
# plugins/sulis/scripts/_discovery/inspector.py, in read_root()
# Repo DEFAULT branch (not the checked-out branch). Standard resolution:
#   git symbolic-ref refs/remotes/origin/HEAD  -> "refs/remotes/origin/main"
# Strip the refs/remotes/origin/ prefix. Fall back to "main" when origin/HEAD
# is unset (e.g. remote never fetched, or set-head never run).
```

- Use `git symbolic-ref refs/remotes/origin/HEAD` (best-effort; `on_failure=None`
  so a missing symbolic-ref is non-fatal).
- Strip the `refs/remotes/origin/` prefix to get the bare branch name.
- Fall back to `"main"` when the default can't be determined.
- `RepoRoot.primary_branch` now carries the repo default, not the checked-out
  branch. The dataclass shape is unchanged.

## Definition of Done

### Red — failing tests written first, seen to fail against current code

- [ ] `tests/unit/test_check_canonical_drift_scope.py::test_scope_valid_entity_exits_zero`
      — **real subprocess** (`subprocess.run([sys.executable, str(_CLI), "--scope", <valid-entity>, "--cross-tenant-refs-allowed-for", "release_workflow_ref"])`),
      asserts `returncode == 0` and the JSON envelope `ok is True`. The valid
      entity is a fixture Project bag whose `release_workflow_ref` points at
      the marketplace Workflow ULID (allowlisted). Fails today: argparse rejects
      `--scope` → exit 2.
- [ ] `tests/unit/test_check_canonical_drift_scope.py::test_scope_drifted_entity_exits_nonzero`
      — real subprocess against a drifted fixture (a Project missing a
      `project.schema.json` `required` field, OR a non-allowlisted cross-tenant
      ref). Asserts `returncode != 0` and the envelope surfaces the structured
      failure. Fails today: exit 2 for the wrong reason (unrecognised `--scope`),
      not the structured drift reason.
- [ ] `tests/unit/test_check_canonical_drift_scope.py::test_scope_does_not_require_instance_dir_or_yaml_path`
      — real subprocess: `--scope <valid>` with NO `--instance-dir`/`--yaml-path`
      exits 0 (not 2). Pins the "modes coexist" contract. Fails today.
- [ ] `tests/integration/test_discover_consumer_repo_regression.py::test_consumer_repo_mint_persists_and_records_default_branch`
      — the **characterisation / regression** test. Build a tmp git repo that
      is NOT the marketplace repo, with `origin/HEAD -> main`, check out a
      feature branch (e.g. `feat/x`), then run discovery against it through the
      **real** verifier (`verifier_fn=verify_and_roll_back_on_failure`, NOT the
      `_fake_verify_pass` stand-in the other e2e tests use), with cwd set
      *outside* the marketplace repo root. Assert: (a) the minted entity file
      persists on disk — no rollback; (b) the recorded `primary_branch == "main"`
      (the repo default), NOT `feat/x` (the checked-out branch). Fails today on
      all three bug surfaces.
- [ ] `tests/integration/test_discover_consumer_repo_regression.py::test_consumer_repo_default_branch_falls_back_to_main`
      — a consumer repo with no `origin/HEAD` set records `primary_branch == "main"`
      via the fallback. Fails today (records the checked-out branch).

### Green — implementation makes the tests pass

- [ ] Fix 1: `--scope` mode added to `check-canonical-drift.py`; `--instance-dir`/`--yaml-path`
      requiredness moved to a post-parse check so the modes coexist; single-entity
      schema-validation + allowlist applied; exit-code + envelope contract preserved.
- [ ] Fix 2: `_DEFAULT_DRIFT_DETECTOR` resolves via `__file__`; the verifier finds
      the detector from any cwd.
- [ ] Fix 3: `inspector.read_root` records the repo default branch via
      `git symbolic-ref refs/remotes/origin/HEAD`, stripping the prefix, falling
      back to `"main"`.
- [ ] All 5 Red tests pass.

### Blue — refactor + regression guard

- [ ] The existing release-train CI invocation (`--instance-dir`/`--yaml-path`)
      still works unchanged — assert by re-running the existing
      `test_check_canonical_drift_discover.py::test_release_train_still_passes`
      and `test_default_cross_tenant_flag_empty_list_no_behaviour_change` green
      (no edits to those tests).
- [ ] `DriftDetectorExtensionMissingError` behaviour intact — the verifier still
      raises the typed error when the detector exits 2 with an "unrecognized
      arguments: --cross-tenant-refs-allowed-for" stderr
      (`test_discovery_verifier.py::test_detector_missing_raises_clear_error`
      stays green). This is defence-in-depth, not a bug.
- [ ] `--scope` and `--yaml-path` mode-selection logic is a single readable
      branch in `main()`; no duplicated read/validate code — the entity read +
      schema-validate path reuses the existing `JsonLdFileReader._validate_each`
      machinery where practical, or a small named helper.
- [ ] No silent failure paths: a malformed entity, missing file, or unrecognised
      mode each maps to exit 2 with a structured envelope `error` string.
- [ ] `inspector.py` branch-resolution is one named local with a comment citing
      the `git symbolic-ref` convention (CP) and the `main` fallback rationale.
- [ ] Whole `plugins/sulis/scripts` test suite green; no type or lint errors.

## Regression guard (explicit)

The release-train CI calls
`check-canonical-drift.py --instance-dir <dir> --yaml-path <file> [...]`.
That path MUST remain byte-for-byte behaviourally identical. The two existing
characterisation tests in `test_check_canonical_drift_discover.py`
(`test_release_train_still_passes`, `test_default_cross_tenant_flag_empty_list_no_behaviour_change`)
are the guard — they must stay green untouched.

## Sequence

- **dependsOn:** none — single contained fix, no upstream WP.
- **blocks:** none.
- This is the only WP in the set; there is no parallelism to express.

## Estimated Token Cost

- **Input:** ~8k (three source files + verifier/inspector tests + the
  `_canonical_drift` package + project schema + a sample Project bag).
- **Output:** ~6k (three surgical source edits ≈ 120 LOC total + two new test
  files ≈ 200 LOC).
- **Total:** ~14k.

## Notes

- The verifier already builds the `--scope` argv and already references
  "WP-009" extending the detector — the verifier side was written expecting a
  `--scope` mode that never landed. This WP closes that gap.
- The existing e2e suite (`test_discover_e2e.py`) deliberately injects
  `_fake_verify_pass` and documents (lines 238-248) that "the detector script
  doesn't know [`--scope`] yet ... entity-scoped invocation is a small follow-on
  extension." This WP IS that follow-on. The new consumer-repo regression test
  is the first test to drive the **real** verifier end-to-end against the
  **real** detector from outside the marketplace repo — which is exactly the
  condition that was failing in the wild.
- Out of scope per SPEC §Non-goals: no re-architecture of the verifier/detector/
  flow; the "preview left a file on disk" repro artefact was a debugging step,
  not a product fault; no allowlist-semantics or MUC-005 contract change; no new
  entity fields or schema changes.

## Acceptance Evidence

- Branch: feat/wp-001-fix-discover-verify-scope (deleted post-merge)
- Squash-merge SHA on dev: `f51a70fc37d4692fa1b8bc13408593967ddc33ae`
- Health status: `skipped (no --staging-url)`
- Smoke-test verdict: PASS
- Completed: `2026-06-02T14:01:44Z` (Step 12 by calling session)
