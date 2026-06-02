---
founder_facing: false
---
# Spec — Fix the discover-project verify gate that rolls back every mint in consumer repos

**Change:** CH-01KT48 · fix

## Intent

`/sulis:discover-project` mints a Project entity for a repo, then runs a
post-mint drift check that rolls the mint back if it fails. In any repo
other than the Sulis marketplace repo itself, that check fails 100% of the
time, so the mint is *always* rolled back and adopting Sulis in a new repo
is impossible. Confirmed in the wild against `Capsule-Insurance/platform`.

Three independent bugs combine to cause this:

1. **The verifier calls a `--scope` mode the drift checker doesn't have.**
   `_discovery/verifier.py` invokes
   `check-canonical-drift.py --scope <entity> --cross-tenant-refs-allowed-for ...`,
   but `check-canonical-drift.py`'s argparse only accepts `--instance-dir`
   (required), `--yaml-path` (required), `--marketplace-json`,
   `--validate-schemas`, and `--cross-tenant-refs-allowed-for`. There is no
   `--scope` flag. Every invocation exits 2 (`the following arguments are
   required: --instance-dir, --yaml-path`), the verifier reads non-zero as
   drift, and rolls the mint back.

2. **The default detector path is cwd-relative.** `verifier.py` sets
   `_DEFAULT_DRIFT_DETECTOR = Path("plugins/sulis/scripts/check-canonical-drift.py")`
   — relative to the current working directory. That path only resolves
   when run from inside the marketplace repo. In a consumer repo it doesn't
   exist, so `python3` exits 2 before the checker even runs.

3. **`primary_branch` records the checked-out branch, not the repo
   default.** `_discovery/inspector.py` uses `git branch --show-current`,
   so a mint run from a feature branch records e.g.
   `feat/azure-terraform-foundation` as the project's primary branch
   instead of the repo default (`main`).

## Scope

- Add a `--scope <entity-file>` mode to `check-canonical-drift.py` that
  schema-validates one entity file and applies the cross-tenant-ref
  allowlist, **without** requiring `--instance-dir` or `--yaml-path`.
  This is the mode `verifier.py` already expects.
- In `verifier.py`, resolve `_DEFAULT_DRIFT_DETECTOR` relative to
  `__file__` (the installed plugin location) so it works in any repo.
- In `inspector.py`, record `primary_branch` as the repo's default branch
  (resolve from `origin/HEAD`), falling back to `main` when the default
  can't be determined.
- Add a **consumer-repo regression test**: run discover from a repo that is
  not the marketplace repo and assert the mint persists (does not roll
  back).
- Add a **real-subprocess `--scope` test**: actually invoke
  `check-canonical-drift.py --scope <entity>` as a subprocess and assert it
  exits 0 on a valid entity and surfaces drift on an invalid one. This is
  the test whose absence let the broken `--scope` call ship.

## Non-goals

- Do **not** re-architect the verifier, the drift detector, or the
  discover-project flow. These are three surgical fixes.
- The "preview that left a file on disk" seen in the reproduction was a
  hand-rolled debugging step in that session, not a product fault — the
  real verify gate rolls back correctly. Out of scope.
- No change to the cross-tenant-ref allowlist semantics or the MUC-005
  rollback-and-surface contract — only make the gate actually runnable.
- No new entity fields or schema changes.

## Acceptance

- `check-canonical-drift.py --scope <valid-entity>` exits 0 without
  `--instance-dir` / `--yaml-path`; `--scope <drifted-entity>` exits
  non-zero with the structured failure message.
- Running `/sulis:discover-project` (or `run_discovery_headless`) from a
  consumer repo on a feature branch persists the minted entity — no
  rollback — and records `primary_branch: main` (the repo default), not
  the checked-out branch.
- A consumer-repo regression test and a real-subprocess `--scope` test both
  exist and pass. Each was written to fail against the current (broken)
  code first, then pass after the fix (TDD).
- The existing release-train CI invocation of `check-canonical-drift.py`
  (the `--instance-dir`/`--yaml-path` path) still works unchanged.

## Constraints

- TDD-first: write each test, see it fail against current code, then fix.
- Default to the established convention (CP): resolve the repo default
  branch via `git symbolic-ref refs/remotes/origin/HEAD` (the standard
  way), not a bespoke heuristic.
- `--scope` mode and the existing `--yaml-path` mode must coexist;
  `--yaml-path` stays backward-compatible for release-train CI.
- Keep the verifier's typed-error behaviour (`DriftDetectorExtensionMissingError`
  for an unrecognised flag) intact — it's defence-in-depth, not a bug.
