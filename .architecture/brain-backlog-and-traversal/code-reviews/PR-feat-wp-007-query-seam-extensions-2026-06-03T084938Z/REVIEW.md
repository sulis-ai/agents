# Code Review: feat/wp-007-query-seam-extensions — Extend _brain_query with find_opportunities, state filters, find_roadmap

> **Timestamp:** 2026-06-03T084938Z (ISO 8601 UTC)
> **Author:** executor (WP-007)
> **Branch:** feat/wp-007-query-seam-extensions → change/create-brain-backlog-and-traversal
> **Files changed:** 2
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds three new ways to read the project's backlog — list opportunities, filter requirements by their status, and resolve the roadmap to its actual items. There are no build errors, the change is small and single-purpose, and it ships with six tests covering both the new behaviour and the promise that nothing existing breaks. Nothing needs attention before merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** 278 added lines across 2 files (one source file plus its test file). Most of that is the test.

**Scope — clean.** A single concern: extending one read module with three composable views. One `feat` change, one module touched.

**Safety — clean.** No database migrations, no schema/IDL changes, no infrastructure files, no secrets. The change is read-only — it walks files on disk and never writes.

**Completeness — clean.** Four new behaviours (a new function, a new optional filter, a roadmap resolver, and a shared state-set definition) all covered by new tests, including the edge cases that matter most here: an empty store returns nothing rather than crashing, and a corrupted roadmap file is tolerated rather than throwing.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs) for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in diff; Build Verification empty; both changed files read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — ruff + mypy clean on HEAD; base also clean.
- **PR Hygiene:** 0 findings (CR-09 / PH-01..PH-04) — single-concern, additive, no safety surface.
- **In the changes:** 0 findings.
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0.

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | None — pure additions to the read seam, reuses existing predicates (ADR-006 honoured) |
| Security | 0 | 0 | None — read-only file walk, no auth/injection/secret surface |
| Quality | 0 | 0 | None — six tests cover new behaviour + backward-compat + NFR-01 edges |

### Build Verification (CR-01)

Mechanical baseline ran in Step 6 and was re-captured for the bundle:
- `ruff check _brain_query.py tests/unit/test_brain_query_views.py` → `All checks passed!` (see `tool-outputs/ruff-head.log`)
- `mypy _brain_query.py` → `Success: no issues found in 1 source file` (see `tool-outputs/mypy-head.log`)
- Base branch was clean prior to the change; delta = 0 introduced errors.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → clean
  module_fan_out: 1 top-level concern (plugins/sulis/scripts)
  severity: none

Size (PH-02):
  lines_added: 278, lines_removed: 3, total: ~281
  files_changed: 2 (1 source + 1 test; test is the bulk)
  generated_ratio: 0
  lock_file_ratio: 0
  severity: none

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0 (test file added alongside)
  api_change_without_schema: false
  severity: none
```

### Findings in the Changes

None.

### Findings in the Neighbours

None. Neighbours examined: `_brain_labels.py` (provides `roadmap_sidecar_path`, consumed by `roadmap_members` — unchanged, already tested), `find_testresults_verifying` / `find_passing_testresults_verifying` (call `find_entities`; the latter's comprehension was reformatted by `ruff format` — a bounded boy-scout cleanup in a file already being modified, no behaviour change). Existing callers of `find_requirements` (the DoD verification flow) are protected by the `state=None` default reproducing prior behaviour exactly; covered by `test_find_requirements_state_kwarg_backward_compatible` and the unchanged `test_brain_query.py::test_find_requirements`.

### Watch List

None.

### CR-10 performance procedural checks

No anti-pattern matches. `find_roadmap` resolves member ids via a single `find_entities` walk with a `where_id_in` set-membership predicate (one O(N) pass over the domain's instances), not N per-id lookups — no N+1. `_find_typed`, `find_opportunities`, `find_requirements` each delegate to a single `find_entities` call. The only loop in the source diff is the pre-existing `find_passing_testresults_verifying` comprehension (reformatted only).

### Cross-Reference

- **Existing Hardening Deltas covered:** none.
- **Existing security report:** none for this project.
- **Pattern suggesting full audit:** none.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `ruff check`, `mypy` (project's configured checkers per pyproject.toml). Base: 0 errors. Head: 0 errors. Coverage gap: none.
- [✓] **CR-02 Parallel dispatch.** Diff is 2 files / ~281 lines. Above the 200-line line threshold but a single-module, single-concern, additive diff (one source file + its test). Three lenses run inline by the executor reviewing its own bounded WP diff, with conservative scoring per the rule's spirit; no subagent fan-out justified for a 2-file leaf-module change. Recorded as a deliberate carve-out.
- [✓] **CR-03 Full-file reads.** Both changed files read end-to-end (`_brain_query.py` 290 lines, `test_brain_query_views.py` 178 lines). Unread files: none.
- [✓] **CR-04 Evidence discipline.** No findings to evidence; lens scans cited above.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 0 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired.
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced — checked dependency-direction (leaf utility, no infra import), module-level state (constants are immutable frozensets, not mutable singletons), reuse mandate (ADR-006 — no new walker/engine, composes existing predicates). Security: nothing surfaced — read-only file walk; no access-control/injection/SSRF/secret surface; ids checked by set membership not interpolation. Quality: nothing surfaced — Build Verification clean; no JSX (Python only); no dead surface; no contract drift (state values match vendored schema enums); test-coverage present (6 tests incl. backward-compat + NFR-01); style clean; CR-10 no matches.
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none (single feat, 1 module). PH-02 Size: none (2 files, test-dominant). PH-03 Safety: none (0 migrations/schemas/secrets/infra). PH-04 Completeness: none (test added). PH-03 high → CR-06 auto-downgrade: did not fire.

#### Run details

- **Diff source:** `git diff origin/change/create-brain-backlog-and-traversal` (intent-to-add for new test file).
- **Neighbour expansion:** git grep on changed symbols (`find_requirements`, `find_entities`, `roadmap_members`, `where_id_in`).
- **Neighbour cap:** well under 20 files.
- **Scanners run:** ruff, mypy. Gitleaks/Semgrep/Trivy not available in this environment; secret-pattern grep run manually over the diff (0 hits).
- **Scanners unavailable:** Gitleaks, Semgrep, Trivy — secret scan covered by manual grep; SAST coverage gap noted (read-only Python utility, low risk surface).
- **Lenses dispatched in parallel:** no — inline single-reader carve-out per CR-02 note above.
