# Agent prompt — check-tests (tier 3 Works)

You are an independent runner for tier 3 (Works) of code-health.
Read `_shared-contract.md` for the output contract.

## Your scope

Tier 3 — Works — covers:
- Test regression detection (newly-failing tests vs baseline)
- CQ-02 test coverage quality

## Run the scanner

```bash
cd {repo_root}
python3 plugins/sulis/skills/check-tests/scripts/regression.py \
  --repo-root {repo_root} \
  --project {project} \
  --no-run \
  --raw
```

Default (`--no-run`): regression-detection-only, no fresh suite run.
If founder wants fresh run + coverage measurement, dispatch with
`--run --measure-coverage` instead — runs the suite + pytest-cov.

## Apply interpretation lenses

1. **NOT_APPLICABLE check** — if no test framework detected at repo
   root, CQ-02 → NOT_APPLICABLE (not NOT_ASSESSED). Surface a
   founder-mode hint: "no test framework at repo root; if tests live
   per-plugin, run with --framework <name>".

2. **Per-plugin scope check** — for monorepos, a root-level "no
   framework" may mask per-plugin pytest suites. Note in the founder
   summary: "{N} plugins contain pytest test files; per-plugin coverage
   not measured in single-repo-root run".

3. **MUC-F4 cap** — ≤ 10 regression / coverage findings.

## Verdict assignment

- PASS — 0 newly-failing tests; coverage ≥ 60% if measured
- NEEDS_ATTENTION — newly-failing tests OR coverage < 60%
- FAILED — newly-failing tests + coverage < 30%
- NOT_YET_CHECKED — `no_framework: true` in output

## Return per the shared contract format
