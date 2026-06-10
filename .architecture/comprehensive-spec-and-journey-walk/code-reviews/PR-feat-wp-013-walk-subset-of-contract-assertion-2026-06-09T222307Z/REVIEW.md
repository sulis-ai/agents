# Code Review: PR-feat-wp-013 — Build the walk-operations-subset-of-contract assertion

> **Timestamp:** 2026-06-09T222307Z (ISO 8601 UTC)
> **Author:** autonomous executor (WP-013)
> **Branch:** feat/wp-013-walk-subset-of-contract-assertion → change/harden-comprehensive-spec-and-journey-walk
> **Files changed:** 4 (1 new script, 1 new test, 1 modified script, 1 modified skill doc) + 1 bookkeeping journal (excluded from review)
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds a small, self-contained check that ties two earlier pieces of the design pipeline together: the list of tool operations the design "walk" found, and the list of operations the interface contract actually declares. The check fails the build if the walk ever references an operation the contract never declared — which is exactly the rule the design called for. There are no build errors, the change is well-scoped (one new check plus its tests), the tests drive the real upstream pieces end-to-end (not mocks), and a small duplicate-parsing concern was already resolved by moving the shared table-reading logic to its rightful owner. No issues need attention.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** Small and focused: one new check (~160 lines), its tests (~300 lines), a six-line tidy-up of a sibling file, and one documentation line. Easy to review thoroughly.

**Scope — clean.** Single concern: the walk-subset-of-contract check. The only file touched outside the new script is a sibling parser, and that edit exists solely to share parsing logic this change needs (no duplicated table-reading).

**Safety — clean.** No database migrations, no schema/IDL files, no infrastructure or CI changes, no secrets. The new code only reads a document and reports — it writes nothing.

**Completeness — clean.** New behaviour ships with tests: two that drive the real upstream walk + a real contract section through to the new check, plus targeted tests for each branch of the logic.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs) for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; every file >50 lines read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01 — ruff check clean, py_compile clean on all touched files).
- **PR Hygiene:** 0 findings (PH-01..04 all clean / low).
- **In the changes:** 0 findings.
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0.

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none — clean one-direction reuse of sibling parsers |
| Security | 0 | 0 | none — pure read-only inspector, no secret/auth/injection surface |
| Quality | 0 | 0 | none — tests present, no dead surface / contract drift / CR-10 match |

### Build Verification (CR-01)

`uv run ruff check` on `_assert_walk_subset_of_contract.py`, `_assert_walk_table.py`, and the test file — "All checks passed!". `python3 -m py_compile` on all three — OK. Marketplace branch-ci lint profile is manifest-JSON validity + py_compile; no manifest touched. Base vs head: no new errors. Coverage gap: none.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → clean (single concern)
  module_fan_out: 1 top-level dir (plugins/sulis) → clean
  severity: low

Size (PH-02):
  lines_added: ~480, lines_removed: ~6 (new script 159 + test 297 + sibling edit 23/-6 + 1 doc line)
  files_changed: 4 reviewable (+1 bookkeeping journal excluded)
  generated_ratio: 0
  lock_file_ratio: 0
  severity: low (well within single-reader carve-out: <200 reviewable-logic lines per file, <5 files)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: low

Completeness (PH-04):
  new_source_without_test: 0 (new script ships with a dedicated test file)
  api_change_without_schema: false
  severity: low
```

No PH-03 high → no CR-06 auto-downgrade fired.

### Findings in the Changes

None.

### Findings in the Neighbours

None. The only neighbour touched (`_assert_walk_table.py`) was modified by this PR itself — the `hop_rows()` extraction — and is reviewed as part of the changes, not the neighbour ring.

### Watch List

None.

### Cross-Reference

- No prior `.security/comprehensive-spec-and-journey-walk/viability-report-*.md` to cite.
- No existing hardening-deltas to dedupe against.
- No neighbour pattern suggests a broader audit.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `uv run ruff check` + `python3 -m py_compile` on all 3 touched Python files. Base: clean. Head: clean (0 new errors). Coverage gap: none.
- [✓] **CR-02 Single-reader pass justified by diff size.** 4 reviewable files, largest logic file 159 lines (test 297, all read end-to-end) — within the ≤200-line/≤5-file carve-out. No parallel dispatch required.
- [✓] **CR-03 Full-file reads.** `_assert_walk_subset_of_contract.py` (159), `tests/unit/test_assert_walk_subset_of_contract.py` (297), and the `_assert_walk_table.py` edit region all read end-to-end. Unread files: none.
- [✓] **CR-04 Evidence discipline.** No findings to evidence; scans cited inline (secret grep, CR-10 loop grep, I/O grep).
- [✓] **CR-05 Severity rubric.** Applied — 0 findings at any severity.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. No auto-downgrade triggers fired (Build Verification empty; all files read end-to-end; all lenses produced output; no PH-03 high).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced — checks run: dependency direction (one-way reuse of `_assert_interface_contract` + `_assert_walk_table`), no singletons, no circular imports, no resilience surface (pure in-process inspector). Security: nothing surfaced — primitives checked SEC-01..07 (no auth/injection/validation/secrets surface; only `Path.read_text` with OSError→exit 2), no secret-pattern hits. Quality: 0 findings — JSX scan n/a (no TSX/JSX), dead-surface none, contract-drift none, test-coverage present (11 tests incl. 2 real end-to-end seam ties), CR-10 no anti-pattern match (the single loop iterates in-memory parsed sections, no I/O in body).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: low (single feat concern). PH-02 Size: low (small, single-reader). PH-03 Safety: low (no migrations/schema/infra/secrets). PH-04 Completeness: low (new behaviour has tests). PH-03 high → CR-06 auto-downgrade: did not fire.

#### Run details

- **Diff source:** local git, working tree vs `change/harden-comprehensive-spec-and-journey-walk`.
- **Neighbour expansion:** git grep over importers; `_assert_walk_table.py` is the only coupled file and is part of the diff.
- **Neighbour cap:** not reached (0 external neighbours reviewed).
- **Scanners run:** ruff, py_compile, grep-based secret/CR-10/I-O scans.
- **Scanners unavailable:** Gitleaks / Semgrep / Trivy not invoked (no signals in a pure-stdlib read-only inspector; grep secret-scan substituted and clean).
- **Lenses dispatched in parallel:** no — single-reader pass per CR-02 carve-out.
