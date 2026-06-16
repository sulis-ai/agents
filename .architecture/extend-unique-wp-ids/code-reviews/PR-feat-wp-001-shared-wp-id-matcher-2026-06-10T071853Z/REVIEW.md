# Code Review: feat/wp-001-shared-wp-id-matcher — Widened WP-id matcher defined once, five callers rewired

> **Timestamp:** see folder name (ISO 8601 UTC)
> **Author:** autonomous executor (WP-001, CH-5DMB1N)
> **Branch:** feat/wp-001-shared-wp-id-matcher → change/extend-unique-wp-ids
> **Files changed:** 8 (2 source, 6 unit-test)
>
> **Outcome:** Ready to merge

---

## At a glance

This change does exactly what it set out to do, and it does it the safe way. It defines the rule for "is this string a Work Package id?" in one place, and points all five spots that used to ask that question their own way at the single shared rule. There are no build errors, the change is tightly scoped to the matcher plus its five users, and every new behaviour has a test — including the load-bearing one that proves both the new id style and the old style survive together. Nothing needs fixing before merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** Small and focused: about 90 lines of new logic (one shared recogniser plus three tiny helpers) and five one-line edits where the old hand-rolled checks lived. The rest is test additions.

**Scope — clean.** Single concern: the shared id recogniser and its five users. No unrelated changes rode along.

**Safety — clean.** No database changes, no schema or infrastructure files, no secrets. Pure text-matching logic.

**Completeness — clean.** Tests were added to six existing test files, including a parametrised guard that proves a parse keeps both the new prefixed id (`CH-5DMB1N-WP-001`) and a legacy plain id (`WP-002`) in the same pass — the exact failure this change exists to prevent.

## Things to take away

Nothing to add — the change followed the test-first discipline and reused the codebase's own single-source-of-truth pattern (the existing WP-table-header rule) rather than inventing a new shape. That is the right instinct.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs) for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; both source files read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01). `compileall` clean on HEAD; CI lint gate is `py_compile` + manifest JSON + routing-coverage (no tsc/eslint/mypy/ruff configured — "stdlib-only tooling per plugin contract").
- **PR Hygiene:** 0 findings. Scope low, Size low (366/-9, 8 files), Safety low (0 migrations/schemas/secrets/infra), Completeness low (tests added alongside source).
- **In the changes:** 0 findings.
- **In the neighbours:** 0 findings.
- **Watch List:** 1 (intentional, beneficial behaviour narrowing — see below).
- **Draft fixes:** 0.

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | None — single-source extraction (EP-03), correct dependency direction, no import cycle |
| Security | 0 | 0 | None — anchored, backtracking-free regexes; no secrets/injection/auth surface |
| Quality | 0 | 0 | None — full test coverage; legacy parity verified; no perf anti-patterns |

### Build Verification (CR-01)

No PR-introduced errors. `python3 -m compileall -q plugins/sulis/scripts` clean on HEAD. The repo's configured checks (CI `branch-ci.yml`): manifest JSON validity, `compileall`, routing-coverage gate, `pytest tests/unit/`. All pass. Full unit suite: 2541 passed / 10 skipped / 0 failed; integration suite: 281 passed / 1 skipped / 0 failed.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):        commit_type_spread: n/a (uncommitted at review); module_fan_out: 1 (plugins/sulis/scripts); severity: low
Size (PH-02):         lines_added: 366, lines_removed: 9, files_changed: 8; generated_ratio: 0; severity: low
Safety (PH-03):       migration_count: 0; schema_idl_count: 0; infra_files: 0; secret_pattern_hits: 0; severity: low
Completeness (PH-04): new_source_without_test: 0; api_change_without_schema: false; severity: low
                      (no new source FILES; behaviour added to existing _wpxlib.py/_p_ver_rubric.py; tests added to 6 existing unit files)
```

### Findings in the Changes

None.

### Findings in the Neighbours

None. Neighbour ring: the five rewired call sites (`parse_index_md`, `_normalise_wp_reference`, `_branch_name`, `resolve_wp_branch`, `_p_ver_rubric.run_p_ver`) plus `_wpxlib` importers. All covered by the existing + new unit/integration suites, which stay green.

### Watch List

- **`is_wp_id("WP-")` returns `False` where the old `startswith("WP-")` returned `True`.** This is an intentional, beneficial narrowing: a row/id of exactly `"WP-"` (prefix, no NNN) is malformed and was never a valid WP id. The old filter would have wrongly KEPT such a row and failed downstream on the missing number; the new matcher rejects it cleanly. No real INDEX contains a bare `"WP-"` row. Covered by `test_is_wp_id_rejects_non_wp_strings[WP]`. No fix needed; recorded for awareness.

### Cross-Reference

- No prior `.security/` report for this project.
- No existing hardening-deltas covered.
- No neighbour pattern suggesting a broader audit.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Command: `python3 -m compileall -q plugins/sulis/scripts` (the repo's configured Python check; no tsc/eslint/mypy/ruff in CI per plugin contract). Base + Head: 0 errors. Coverage gap: ruff is not a CI gate and has no repo config — 4 pre-existing ruff findings noted but out-of-scope (recorded in tool-outputs/lint-note.txt).
- [✓] **CR-02 Dispatch shape.** Single-reader pass. Diff: 366/-9 across 8 files; the *source* surface is ~90 new lines + 5 one-line seams in 2 files, the remaining 6 files are additive test fixtures. Both source files read end-to-end; full diligence applied despite the >5-file count, justified by the trivial-per-file test additions.
- [✓] **CR-03 Full-file reads.** Both source files' diffs read end-to-end; the new matcher block and all 5 seams inspected in context. Unread files: none material (test files are additive fixtures, reviewed).
- [✓] **CR-04 Evidence discipline.** Findings (the single Watch List item) cite behaviour + the covering test by name; edge-case probes run live (regression parity, dangerous-widening rejection, ReDoS shape).
- [✓] **CR-05 Severity rubric.** Applied. 0 critical / 0 high / 0 medium / 0 low. 1 Watch List note.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. No auto-downgrade triggers fired (Build Verification empty; all files read; all lenses produced output; no PH-03 high).
- [✓] **CR-07 Lens completion.** Architecture: 0 findings — single-source extraction (EP-03), dependency `_p_ver_rubric → _wpxlib` correct, no cycle confirmed by grep. Security: nothing surfaced — regexes anchored + backtracking-free (no ReDoS), no secrets/injection/auth/external-call surface, inputs are trusted WP ids from committed INDEX files. Quality: 0 findings — every new function + 5 seams covered by tests, `wp_nnn_suffix` parity vs legacy `removeprefix("wp-")` verified for all non-prefixed shapes, no CR-10 perf anti-patterns (O(1) regex, no new loops; rewired sites replaced an O(1) check inside an existing loop with an equivalent O(1) call).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: low (single module). PH-02 Size: low (366/-9, 8 files). PH-03 Safety: low (0 migrations/schemas/secrets/infra). PH-04 Completeness: low (tests added alongside). PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** local working tree vs `change/extend-unique-wp-ids` (branch uncommitted at review time, per Step 6.5 before Step 7 commit).
- **Neighbour expansion:** `git grep` for `startswith("WP-")` / `removeprefix("wp-")` + import-cycle check.
- **Neighbour cap:** not reached (5 call sites + importers).
- **Scanners run:** compileall (py_compile); live Python edge-case probes.
- **Scanners unavailable:** Gitleaks/Semgrep/Trivy not installed in this environment — security lens performed by manual ReDoS + input-trust analysis; diff contains no dependency, network, secret, or auth surface, so scanner coverage gap is low-risk.
- **Lenses dispatched in parallel:** no — single-reader pass per CR-02 (small source surface).
