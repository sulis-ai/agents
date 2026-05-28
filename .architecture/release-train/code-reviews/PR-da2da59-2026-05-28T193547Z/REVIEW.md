# Code Review (batch gate): WP-009 — batch-defect remediation

> **Target:** train-2026-05-28T193502Z (batch_size=1, WP-009); merge `da2da59` on `change/create-release-train`
> **Outcome:** Ready to merge (PASS)

## At a glance
WP-009 closes the two findings from the prior batch gate (PR-e858389): the critical str→Path producer crash and the high GHA loop-guard quoting. Per-WP review returned PASS / 0 findings; this batch gate (solo WP) confirms both fixes on the merged tip.

## Verdict
`PASS` per CR-06. No critical/high; Build Verification empty.

## Findings closure (vs PR-e858389)
| Prior finding | Severity | Status |
|---|---|---|
| CR-BATCH-01 — producer passes str to write_changeset → AttributeError | critical | **CLOSED** — keystone coerces str|Path at entry of write_changeset + read_changesets; `test_write_read_changeset_round_trip_accepts_str_dir` fails-then-passes; corrected producer snippet writes a changeset cleanly; 50→51 tests. |
| CR-BATCH-02 — GHA loop-guard double-quoted literal fails expression eval | high | **CLOSED** — line 40 now single-quoted `'${{ !startsWith(..., ''release: sulis'') }}'`; YAML parses; `release: sulis` stays an exact prefix of the step-9 commit message. |

## Build Verification (CR-01)
- pytest tests/unit/test_changeset.py → 51 passed.
- str-dir round-trip: write + read via a plain str dir works (coercion).
- release-on-merge.yml → yaml.safe_load OK; loop-guard expression single-quoted (grep line 40).

## Methodology — CR-08
- [✓] CR-01 baseline on merged tip da2da59 (51 passed; YAML valid).
- [✓] CR-02 full three-lens satisfied by the per-WP pass on identical code (PR-feat-wp-009-…193207Z, PASS, 0 findings); batch_size=1 → no cross-WP surface.
- [✓] CR-06 verdict PASS; both prior findings verified closed.

## Cross-reference
- Closes findings from: .architecture/release-train/code-reviews/PR-e858389-2026-05-28T191515Z/
- Per-WP review: .architecture/release-train/code-reviews/PR-feat-wp-009-batch-defect-remediation-2026-05-28T193207Z/
