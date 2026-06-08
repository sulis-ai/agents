# Code Review: feat/wp-008-prov-edge-product-opportunity — re-vendor the wasGeneratedBy prov edge on Product + Opportunity

> **Timestamp:** 2026-06-03T150010Z (ISO 8601 UTC)
> **Author:** executor (WP-008)
> **Branch:** feat/wp-008-prov-edge-product-opportunity → change/feat-product-project-opportunity-evolution
> **Files changed:** 4 (2 schema, 1 test, 1 doc)
>
> **Outcome:** Ready to merge

---

## At a glance

This change brings two data contracts up to date with a decision that was already made and approved upstream: Product and Opportunity can now record which automated run produced them. It is a small, low-risk update — it bumps two schema files to their new versions, adds a test file that proves the new behaviour, and updates the README that tracks which versions are in use. There are no build errors, the tests come first and pass, and the change is tightly scoped. Nothing needs attention before merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** 4 files, 19 lines of net change. Easy to review thoroughly.

**Scope — clean.** A single concern: consume the upstream-minted provenance edge. One change type (`feat`), two directories.

**Safety — clean.** Two compiled schema files are replaced with their new versions, copied exactly from the authoritative source. The version change is additive and optional, so anything created under the old version stays valid — no data migration, no risk to existing records.

**Completeness — clean.** Seven tests were written first, then the schemas were updated to make them pass. The full test suite (1,790 tests) was re-run with no failures.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs) for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; every file >50 lines read end-to-end (the test file, authored this WP); all applicable lenses produced output. No auto-downgrade triggers fired.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (PH-01..04 all `none`)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none — data-contract re-vendor, no code paths |
| Security | 0 | 0 | none — no secret patterns; data-only diff |
| Quality | 0 | 0 | none — test-first, full suite green |

### Build Verification (CR-01)

No PR-introduced errors. Repo is stdlib-only (no ruff/mypy/pyright configured — the documented plugin contract). The CI mechanical floor (`branch-ci.yml`) is JSON-validity of manifests + schemas plus `python -m compileall plugins/sulis/scripts`; both run clean locally:
- `python3 -m py_compile .../test_prov_edge_schemas.py` → clean
- `json.load()` on both re-vendored schemas → valid

Coverage gap: no static type-checker (repo policy, not a skip).

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):       commit_type_spread {feat}; module_fan_out 2 → severity none
Size (PH-02):        +17 / -2; files 4 → severity none
Safety (PH-03):      migrations 0; schema/idl 2 (additive MINOR re-vendor); secrets 0; infra 0 → severity none
Completeness (PH-04): new_source_without_test 0; new_tests 1; api_change_without_schema false → severity none
```

No PH-03 high → no CR-06 auto-downgrade.

### Findings in the Changes

None. The two schema diffs are single-line `$id` bumps byte-faithful to the canonical compiled source (`product 1.0.0→1.1.0`, `opportunity 2.0.0→2.1.0`). The `wasGeneratedBy` edge is a triples-layer (`prov_constraints`) concern, not a JSON-Schema property, and the vendored tree is schema-only by established convention (no entity vendors triples), so the schema body delta is correctly just the version. The README paragraph documents the re-vendor. The test file asserts the seven DoD properties (edge present + optional via canonical triples, no snake_case scalar, 0..1 cardinality, Project unchanged at 1.0.0, version bumps, no wasRevisionOf, byte-faithfulness) with CI-safe skip-when-canonical-absent guards mirroring the WP-002 sibling.

### Findings in the Neighbours

None. The re-vendored schemas are consumed by drift-detector + instance-validity tests; the full unit suite (1790 passed, 9 skipped) re-ran with no regression.

### Watch List

None.

### Cross-Reference

- **Existing Hardening Deltas covered:** none
- **Existing security report:** none for this change
- **Pattern suggesting full audit:** none

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `py_compile` on the new test + `json.load` on both schemas. Base vs head: 0 new errors. Coverage gap: no static type-checker configured (repo policy).
- [✓] **CR-02 Single-reader pass justified by diff size:** 19 net lines, 4 files — within the ≤200-line / ≤5-file carve-out.
- [✓] **CR-03 Full-file reads.** The one file >50 lines (the new test, ~210 lines) was authored + read end-to-end this WP. Schema diffs are 1 line each; README diff is one paragraph.
- [✓] **CR-04 Evidence discipline.** Findings: none. The clean assertions cite the diff + the full-suite re-run.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical / 0 high / 0 medium / 0 low.
- [✓] **CR-06 Verdict computed.** `PASS`. No auto-downgrade trigger fired.
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (data-contract re-vendor, no code paths). Security: nothing surfaced — secret-pattern scan on added lines clean; primitives checked SEC-06. Quality: build-verification clean, no JSX (no frontend files), dead-surface none, contract-drift none, test-coverage present (test-first), CR-10 perf no anti-pattern matches (tests load 1-2 small JSON files, no DB/RPC/FS loop).
- [✓] **CR-09 PR Hygiene applied.** PH-01 none / PH-02 none / PH-03 none / PH-04 none. No high → no auto-downgrade.

#### Run details

- **Diff source:** `git diff origin/change/feat-product-project-opportunity-evolution...HEAD` (local working tree; branch not yet committed at review time)
- **Neighbour expansion:** full unit-suite re-run (1790 passed) in lieu of symbol-graph walk — appropriate for a 2-file data-contract change
- **Neighbour cap:** not reached
- **Scanners run:** stdlib secret-pattern grep on added lines
- **Scanners unavailable:** Gitleaks/Semgrep/Trivy not installed; data-only diff with no secret surface makes this a low-risk gap
- **Lenses dispatched in parallel:** no — single-reader carve-out (CR-02)
