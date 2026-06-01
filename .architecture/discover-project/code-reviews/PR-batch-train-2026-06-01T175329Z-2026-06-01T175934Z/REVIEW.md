# Code Review: train-2026-06-01T175329Z — wave 2 (3 of 5 shipped; 2 rebase-blocked)

> **Train ID:** train-2026-06-01T175329Z
> **Diff range:** dbaa5da..6e55fa2
> **WPs shipped:** WP-002 (tenant derivation), WP-007 (Verify phase), WP-009 (drift-detector extensions)
> **WPs step-7-blocked (rebase conflict):** WP-003 (Detect phase), WP-004 (Infer phase)
> **Outcome:** PASS for the 3 shipped; WP-003 + WP-004 need conflict resolution then re-train

## At a glance

Wave 2 dispatched 5 WPs eligible. The train hit **rebase conflicts on `plugins/sulis/scripts/_discovery/__init__.py`** for WP-003 and WP-004 — each WP independently created the package marker, so when WP-002 landed first, the remaining branches' "add new file" rebases against a base that already has the file conflicted. Train correctly skipped both and proceeded with the 3 that did rebase cleanly. WP-002 + WP-007 + WP-009 squash-merged successfully; mechanical baseline 31/31 tests pass.

**Decompose lesson worth capturing**: when N WPs share the same package-marker file (or any shared upstream boilerplate), the decompose should hoist it into an upstream WP, OR have N-1 WPs declare it as `dependsOn` the first WP. The discover-project decompose missed this — `__init__.py` belongs in an upstream WP that all 3 backend WPs (WP-002, WP-003, WP-004) depend on.

## What to fix

**Nothing in the 3 shipped.** The 2 blocked WPs need a manual rebase + conflict resolution + re-push, then another train batch.

## Things to take away

1. **Decompose validation should catch shared-file collisions before dispatch.** The rubric's P6 (Peer-collision risk) checks that no two WPs `Create` the same file — but the architect's decompose listed each backend WP touching `_discovery/<adapter>.py` separately and missed that all three would independently emit `_discovery/__init__.py`. A small refinement: P6 should also flag shared-package-marker files (anything created by multiple WPs in the same package), not just core source files.

---

## Technical detail

### Verdict

`PASS` for the 3 shipped (WP-002, WP-007, WP-009). The 2 blocked (WP-003, WP-004) are tracked for manual remediation in the same change.

### Summary

- **CR-01 mechanical baseline:** 31/31 release-train-discovery tests pass on the change branch.
- **CR-09 PR Hygiene:** clean for the 3 shipped.
- **In the changes (3 WPs):** 0 lens findings.
- **Step 11:** not dispatched as subagent (canonical-data + tooling extension — narrow security surface; per-WP Step 6.5 bundles all PASS).
- **Step 7-blocked WPs:** WP-003 + WP-004 are tracked separately (rebase conflict, not a finding).

### Run details

- Train rebase phase hit conflicts on `_discovery/__init__.py` for WP-003 and WP-004 because both branches created the file in the same path. WP-002 won the rebase race (lowest-sequence_id), landed first; subsequent rebases conflicted.
- Train correctly emitted `step-7-blocked` for the 2 conflicted WPs and proceeded with the 3 clean ones.
- Bundled-tip CI passed on the 3 clean branches' rebased tips; sequential squash-merge succeeded.

### Watch List

- **Decompose Validation Rubric P6 refinement.** Add explicit shared-package-marker file detection (anything where N WPs all create the same `__init__.py` / equivalent). Recommend a small follow-on change to the rubric.
- **Conflict-resolution workflow for the blocked 2 WPs.** Manual rebase + conflict resolution + re-push for WP-003 and WP-004. The conflict is mechanical (both add a near-identical `__init__.py`) — pick the version on the base, drop the duplicate add.

### Methodology

- [✓] CR-01: 31/31 tests on the 3 shipped.
- [—] CR-02: reduced inline; per-WP Step 6.5 bundles already PASS.
- [✓] CR-03: inline read of the 3 shipped diffs.
- [✓] CR-05: 0 findings.
- [✓] CR-06: PASS verdict for the 3 shipped.
- [—] CR-07: per-WP bundles substituted; Step 11 not dispatched.
- [✓] CR-09: PR Hygiene clean for the 3 shipped.
