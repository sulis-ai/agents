---
id: WP-008
title: Wire drift detector into branch-ci.yml as a PR-blocking step
status: pending
kind: infra
primitive: extend
group: EXPAND
sequence_id: WP-008
dependsOn: [WP-007]
blocks: []
estimated_token_cost:
  input: 2k
  output: 1k
tdd_section: FR-015; CI wiring
adrs: [ADR-001]
---

## Context

Adds a CI step to `.github/workflows/branch-ci.yml` that invokes
`check-canonical-drift.py` against the canonical instance dir + the
`release-on-merge.yml` workflow file. A drift-detector failure fails
the PR build; the canonical-vs-imperative conformance bridge is now
enforced.

Depends on WP-007 (the script must exist + be tested).

## Contract

### branch-ci.yml addition

A new job (or step within an existing job) at the end of branch-ci's
test phase:

```yaml
  canonical-drift-check:
    name: Canonical-vs-implementation drift
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install deps
        run: |
          curl -LsSf https://astral.sh/uv/install.sh | sh
          source $HOME/.local/bin/env
          uv sync --frozen --directory plugins/sulis/scripts
      - name: Run drift detector
        run: |
          uv run --directory plugins/sulis/scripts python check-canonical-drift.py \
            --instance-dir plugins/sulis/instances/release-train \
            --yaml-path .github/workflows/release-on-merge.yml
```

### Annotation

This step block carries `# canonical:meta:drift-detector` to mark it
as the drift-detector wiring step itself (not a canonical Workflow
Step; the meta-prefix distinguishes).

## Definition of Done

### Red — Failing tests written
- [ ] `tests/test_branch_ci_includes_drift_detector.py` — reads `.github/workflows/branch-ci.yml` + asserts the new job/step is present with the correct invocation
- [ ] Manual: in a sandbox PR, deliberately divert a canonical Step name from the YAML annotation; the drift detector run fails the build

### Green — Implementation makes tests pass
- [ ] `.github/workflows/branch-ci.yml` modified per Contract
- [ ] YAML parses (existing `test_github_workflows_parse.py` regression covers this)
- [ ] The job runs in ≤ 60s (drift detector is pure-local; should be fast)
- [ ] On clean repo: step exits 0, build green
- [ ] On deliberate drift (fixture PR): step exits 1, build fails with named gap in logs

### Blue — Refactor complete
- [ ] Job name + step names readable in GitHub UI
- [ ] No leaked secrets (this step needs none)
- [ ] uv setup is shared with other Python steps if possible (caching opportunity)

## Sequence

- **dependsOn:** WP-007 (drift detector script must exist + be tested)
- **blocks:** —
- **Parallelisable with:** WP-009, WP-010, WP-011 (after WP-007 unblocks)

## Estimated Token Cost

- **Input:** ~2k (branch-ci.yml + drift detector CLI spec)
- **Output:** ~1k (YAML addition + test assertion)
- **Total:** ~3k

## Notes

- The drift-detector step runs ON EVERY PR to dev (per branch-ci's
  trigger). Cost is one ~5s job per PR — acceptable.
- The step does NOT need to run in `release-on-merge.yml` itself —
  it runs at PR time, before the merge. By the time
  release-on-merge.yml fires (on push to main), drift has already
  been caught.
- If the step exits 2 (invocation error), CI also fails — that's
  correct; a misconfigured invocation deserves visibility.
