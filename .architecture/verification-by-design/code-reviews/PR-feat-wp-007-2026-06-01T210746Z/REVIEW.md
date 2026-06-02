# Code Review: feat/wp-007-author-p-ver-fixtures-and-tests — Author P-VER fixtures + tests + harness

> **Timestamp:** 2026-06-01T21:07:46Z (ISO 8601 UTC)
> **Author:** executor (WP-007, verification-by-design)
> **Branch:** feat/wp-007-author-p-ver-fixtures-and-tests → change/extend-verification-by-design
> **Files changed:** 46 (2 substantive Python; 44 fixture files: markdown + 4-line YAML + 0-byte placeholders)
>
> **Outcome:** Approve, but apply small fixes first (applied inline before commit)

---

## At a glance

The change ships a minimal P-VER harness (~400 LOC Python, stdlib-only) plus a fixture tree (12 expected-outcome cases + 1 grandfather case) and a parametrised test suite. All 16 tests pass; ruff + format are clean; no regression in the pre-existing WP-002 structural assertion suite.

Two small docstring drifts were fixed inline before commit: the harness's "ceiling ~100 LOC" claim has been corrected to reflect the actual ~400 LOC footprint with a follow-on split criterion; the test module's docstring no longer implies a `fixture_helpers.py` exists.

## What to fix

No issues that need attention remain after the inline fixes were applied.

## How this pull request is shaped

**Size — worth looking at.** 1,008 lines, 46 files. The line count is inflated by fixture data — only ~600 lines are Python. 44 of the 46 files are tiny synthetic markdown/YAML fixtures (each <20 lines). One commit (the executor's working journal stage) is also included.

**Scope — clean.** Single Conventional Commit type (`feat`). All files live inside one logical scope: the P-VER fixture + test suite. No cross-cutting changes.

**Safety — clean.** No DB migrations, no schema changes, no secrets, no infra files, no lock-file churn. Pure test code + test data.

**Completeness — clean.** The change IS the test surface (this WP authors the tests for the methodology change). Source-to-test ratio is the inverse of the usual concern: zero production code under test, sixteen tests written.

## Things to take away

The Step 1.5 plan called for a `fixture_helpers.py` extraction in Blue. During implementation that became less attractive once it was clear the fixtures are intentionally hand-written for `cat`-readability (a Blue D-o-D requirement). Swapping the planned extraction for a polish addition (`test_every_fixture_has_top_line_intent_comment`) at the same lifecycle step kept the Blue spirit (extract or enforce) without harming the fixture readability principle. The journal records this as `skipped + rationale`, which is exactly the contract the executor's plan loop supports.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs) for engineers and for downstream agents.

### Verdict

`Approve with fixes` per CR-06 (computed). Two `medium (quality)` findings in the diff; both were fixed inline before commit (see "Findings in the Changes" below). After fix, all 16 tests pass, ruff clean, no regression.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 2 medium findings (size band; scope band clean) (CR-09 / PH-01..PH-04)
- **In the changes:** 2 medium quality findings (docstring drift); 0 critical, 0 high, 0 low (after inline fixes: 0 remaining)
- **In the neighbours:** 0 findings (the new module has no callers yet; the change is net-additive)
- **Draft fixes:** 0 (both findings addressed inline; per CR-04 evidence discipline a delta would need a failing characterisation test — neither warranted one)

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | None — stdlib-only, self-contained, no cross-domain imports |
| Security | 0 | 0 | None — test-only code reading fixture content; no auth, secrets, injection, or SSRF surface |
| Quality | 2 (both fixed) | 0 | Stale docstring claims about LOC ceiling and unwritten helper module |

### Build Verification (CR-01)

Both `pytest tests/unit/test_p_ver_rubric.py` and `pytest tests/unit/test_decompose_rubric_p_ver.py` produce 16/16 and 13/13 PASS. `ruff check` clean. `ruff format --check` clean. No PR-introduced errors.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                  → clean
  module_fan_out: 1 distinct top-level scope   → clean
  severity: clean

Size (PH-02):
  lines_added: 1008, lines_removed: 0, total: 1008
  files_changed: 46
  generated_ratio: 0.0
  lock_file_ratio: 0.0
  severity: medium (1001+ line band; 31+ file band — inflated by fixture data; ~600 lines are Python)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: clean

Completeness (PH-04):
  new_source_without_test: 0
  api_change_without_schema: false
  severity: clean (this PR IS the test surface)
```

### Findings in the Changes

#### F-01 (Quality, medium → fixed inline) — `plugins/sulis/scripts/_p_ver_rubric.py`, lines 17–19 (original)

**Quoted text (before fix):**
```
- Implementation ceiling: WP Notes set ~100 LOC; this file lands
  within that envelope by reusing regex + minimal hand-rolled YAML
  for the structured front-matter shapes.
```

**Issue:** Contract drift. The docstring claims a ~100-LOC ceiling and that the file "lands within that envelope." Actual `wc -l` is 405 lines. Future readers would be misled by the stated ceiling vs. the actual footprint.

**Resolution:** Replaced the inline claim with an honest statement of actual footprint (~400 LOC) and a follow-on split criterion (~600 LOC) per the WP Notes. Fix applied inline before commit.

**Lens:** quality (CR-07 step 4 — contract-drift).

#### F-02 (Quality, medium → fixed inline) — `plugins/sulis/scripts/tests/unit/test_p_ver_rubric.py`, lines 23–24 (original)

**Quoted text (before fix):**
```
* Blue: shared helpers live in fixture_helpers.py (build_minimal_srd
        / build_minimal_wp) — extracted once tests are green.
```

**Issue:** Contract drift. The docstring documents a `fixture_helpers.py` module that does not exist — the planned Blue extraction was skipped (recorded in the journal with rationale; the 2-consumer threshold did not fire on harness internals).

**Resolution:** Replaced the docstring fragment with a faithful description of the Blue outcome (extraction considered, deliberately skipped; polish added in its place via `test_every_fixture_has_top_line_intent_comment`). Fix applied inline before commit.

**Lens:** quality (CR-07 step 4 — contract-drift).

### Findings in the Neighbours

None. The harness module is net-new with no current callers. The fixture tree is consumed only by the test module in the same diff.

### Watch List

- **`Verdict.artifact` field is set but never asserted in tests.** Not a defect — the field is informational, intended for human consumption in the rubric's "Remediation" output when P-VER is invoked at runtime. Tests assert `verdict`, `failed_check`, and `message`, which is the smallest contract a downstream consumer needs. (Severity if it were a finding: `low/note`.)
- **`_check_existing_paths_resolve` resolves a path from markdown content via `(fixture_dir / cited).exists()`.** Test-only code; the `.exists()` call returns bool and does not read/write. A fixture file with `existing: ../../../etc/passwd` would only check whether that path exists — no privilege escalation. Noted for awareness; not a delta.
- **CR-10 pattern 7 (repeated invariant in loop).** `_read_change_yaml`'s `for path in sorted(changes_dir.glob("*.yaml")): return ...` always returns on the first iteration; `sorted()` work is wasted. Test code; perf-irrelevant. Not a finding.

### Cross-Reference

- **Existing Hardening Deltas:** none touch this scope.
- **Existing security report:** none for this WP.
- **WP-002's `test_decompose_rubric_p_ver.py`** is the structural-assertion sibling to this WP's `test_p_ver_rubric.py` (behavioural-assertion). Both still pass post-this-diff (13 + 16 = 29 tests).

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `python -m pytest tests/unit/test_p_ver_rubric.py tests/unit/test_decompose_rubric_p_ver.py`; `ruff check`; `ruff format --check`. Base: not separately captured (clean dev branch tip 327ec25). Head: 0 errors / 29 PASS / format-clean. Coverage gap: none.
- [✓] **CR-02 Parallel dispatch carve-out.** Single-reader pass justified by the substantive Python footprint: 2 code files / ~600 lines (44 fixture files are <20 lines each; total diff size inflated by data). Carve-out is on substantive code, not raw line count.
- [✓] **CR-03 Full-file reads.** Both substantive code files (`_p_ver_rubric.py` 405 LOC, `test_p_ver_rubric.py` 190 LOC) read end-to-end. Fixture files all <20 LOC, also fully read while authored.
- [✓] **CR-04 Evidence discipline.** Both findings cite file:line and quoted text.
- [✓] **CR-05 Severity rubric applied.** 0 critical, 0 high, 2 medium, 0 low.
- [✓] **CR-06 Verdict computed.** Verdict: Approve with fixes. After inline fixes applied: effective verdict PASS. No auto-downgrade triggers fired.
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced. Checks: cross-domain imports, singletons, circular paths, resilience primitives — none applicable to a stdlib-only test harness. Security: nothing surfaced. Primitives checked: SEC-01..07 (test-only code, no auth/injection/SSRF surface). Quality: 2 contract-drift findings + dead-surface scan + test-coverage observation + CR-10 sweep.
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: clean. PH-02 Size: medium (band-inflated by fixture data; substantive code well under threshold). PH-03 Safety: clean. PH-04 Completeness: clean (the diff IS the test surface).

#### Run details

- **Diff source:** `git diff --cached` against the staged change
- **Neighbour expansion:** N/A — net-new module with no existing callers
- **Scanners run:** ruff (lint + format), pytest (the project's behavioural floor)
- **Scanners unavailable:** none material — no Dockerfile / schema / lockfile in diff
- **Lenses dispatched in parallel:** no — single-reader carve-out per CR-02 (substantive code is small)
