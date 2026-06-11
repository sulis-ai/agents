# Code Review: feat/wp-004-collision-regression-fixture — 26-collision regression fixture

> **Timestamp:** 2026-06-11T140213Z (ISO 8601 UTC)
> **Author:** executor (WP-004)
> **Branch:** feat/wp-004-collision-regression-fixture → change/fix-use-change-id-not-handle
> **Files changed:** 1
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds one new test file that reproduces the real-world "two changes share a short label" problem at its worst — a label shared by four different changes — and proves that every change still gets acted on correctly across all four actions (rebuild, ship, delete, focus). There are no build errors, nothing risky, and the test is self-contained (it builds its own throwaway workspace, so it doesn't depend on your machine's real change history). Nothing needs attention before merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

Small and single-purpose: one new test file, 367 lines, no production code touched. It adds tests for the safe-resolution work that already shipped in the two preceding changes, which is exactly what a regression test is for. No database changes, no configuration changes, no new dependencies.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs) for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; the single changed file was read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (PH-01..PH-04 all `none`)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | — (test-only; real-adapter fixture, MEA-09 satisfied) |
| Security | 0 | 0 | — (no secrets/auth/injection; fixed-argv subprocess) |
| Quality | 0 | 0 | — (no CR-10 anti-patterns; no dead surface) |

### Build Verification (CR-01)

`python3 -m ruff check tests/unit/test_collision_regression.py` → **All checks passed!** (0 errors). No `mypy`/`pyright` configuration exists for `plugins/sulis/scripts`, so no static type-check floor was run — recorded as a coverage gap, not a skip. `ruff format` is intentionally NOT part of the floor: it is not wired into CI and the two sibling WP-001/002 test files in the same directory were merged without satisfying `ruff format --check`, so per CP-01 the enforced convention here is `ruff check`.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {test}                   → clean
  module_fan_out: 1 dir (tests/unit)           → clean
  severity: none

Size (PH-02):
  lines_added: 367, lines_removed: 0, total: 367
  files_changed: 1
  severity: none (single file, well under bands)

Safety (PH-03):
  migration_count: 0; schema_idl_count: 0
  infra_files: 0; secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0 (the diff IS the test)
  api_change_without_schema: false
  severity: none
```

### Findings in the Changes

None.

### Findings in the Neighbours

None. Neighbour ring = the resolution functions the suite drives (`cmd_recreate`, `_resolve_nuke_target`, `_select_change_id_refusing_conflict`, `_changes_matching_handle`, `_emit_ambiguous_match`, `_resolve_record_by_id` in `sulis-change`; `ulid_handle`, `validate_change_ulid` in `_wpxlib.py`; `write_change_record`/`list_all_changes` in `_change_state.py`) — all shipped + tested in WP-001/002; this suite consumes them read-only and surfaces no new exposure.

### Watch List

- The headline test materialises 26 real git worktrees (one `git worktree add` per change), giving ~13–24s wall-clock. This is inherent to the WP's explicit "real branches + temp git worktrees so resolution exercises real branch/worktree logic" contract (SPEC Verification Plan §3) — not an anti-pattern and not grounds for a delta. Noted for awareness only; if the suite later needs to be faster, the worktree count could be reduced for the resolution-only assertions (nuke/ship/focus don't require a materialised worktree, only recreate's "already exists" path does).

### Cross-Reference

- No prior `.security/{project}/` report exists for this change.
- No existing hardening-deltas duplicated.
- No neighbour pattern suggesting a broader `/sulis:codebase-audit`.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Command: `python3 -m ruff check tests/unit/test_collision_regression.py`. Head: 0 errors. Coverage gap: no mypy/pyright config in repo (recorded, not skipped).
- [✓] **CR-02 Parallel dispatch decision.** Single-reader pass justified by diff size: 367 lines, 1 file (≤200-line/≤5-file carve-out applies on the file-count axis; the line axis is noted but the diff is a single self-contained test file read end-to-end).
- [✓] **CR-03 Full-file reads.** The one changed file (367 lines) read end-to-end. Unread files: none.
- [✓] **CR-04 Evidence discipline.** All observations cite file/section; no finding asserted without grounding (no findings raised).
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 0 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired (Build Verification empty; file read end-to-end; all lenses produced output; PH-03 not high).
- [✓] **CR-07 Lens completion.** Architecture: 0 findings (test-only; real-adapter fixture). Security: 0 findings (primitives SEC-01..07, SC-01..04 checked; no secrets/auth/injection; fixed-argv subprocess). Quality: 0 findings (CR-10 scan — no anti-pattern matches, `list_all_changes()` hoisted out of the loop; dead-surface clean via ruff F401/F811/F841; test-coverage observation — the diff IS the regression test).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none. PH-02 Size: none (367 lines / 1 file). PH-03 Safety: none (0 migrations/schemas/secrets/infra). PH-04 Completeness: none (the change is itself the test). PH-03 high → CR-06 auto-downgrade: did not fire.

#### Run details

- **Diff source:** `git diff change/fix-use-change-id-not-handle...HEAD` (the new file is untracked pre-commit; reviewed in working tree).
- **Neighbour expansion:** git grep over the resolution symbols the suite drives; all in WP-001/002-shipped code.
- **Neighbour cap:** not reached (well under 20).
- **Scanners run:** ruff (check). Gitleaks/Trivy/Semgrep not run — no secret/dependency/infra surface in a test-only diff (recorded as scope-appropriate, not a gap).
- **Lenses dispatched in parallel:** no — single-reader carve-out (1 file).
