# Code Review: feat/wp-009-capture-skill — Create /sulis:capture skill (founder-English capture front door)

> **Timestamp:** 2026-06-03T093703Z (ISO 8601 UTC)
> **Author:** executor (WP-009)
> **Branch:** feat/wp-009-capture-skill → change/create-brain-backlog-and-traversal
> **Files changed:** 2
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds the friendly front door for jotting down an idea — a new `/sulis:capture` skill — plus a small test that checks the skill is shaped the way it should be (plain English, no codes, points at the right tool). There are no build errors, the change is well-scoped (one feature, two files), and it ships with its own test. Nothing needs attention before merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** 413 lines across 2 files (one new skill, one new test). Easy to review thoroughly.

**Scope — clean.** Single concern: the capture skill and its shape test. No mixed refactor, no migrations, no infrastructure changes.

**Safety — clean.** No database migrations, no schema changes, no infrastructure files, no secrets.

**Completeness — clean.** The new skill ships with a test that checks its shape (plain English, drives the right tool, recommends the specialist for the deeper path).

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs) for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in diff; Build Verification empty; both changed files read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01). `ruff check` clean, `ruff format --check` clean, 3/3 shape tests pass.
- **PR Hygiene:** 0 findings (PH-01..PH-04 all clean).
- **In the changes:** 0 findings.
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0.

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | None — new skill body + stdlib regex test; no new domain imports, no runtime call surface |
| Security | 0 | 0 | None — no secrets, no auth/injection surface; prose + regex shape test only |
| Quality | 0 | 0 | None — test ships with the artifact; ruff + format clean; no dead surface / contract drift |

### Build Verification (CR-01)

No PR-introduced errors. The change is one SKILL.md (markdown prose; no executable runtime surface) and one Python shape test (stdlib `re` + `pathlib` + pytest). `ruff check` and `ruff format --check` clean on the test file; the markdown carries no typecheck/lint surface. Full backend suite green (1969 passed, 9 pre-existing skips).

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → clean
  module_fan_out: 2 (skills/, scripts/tests/)  → clean
  severity: none

Size (PH-02):
  lines_added: 413, lines_removed: 0, total: 413
  files_changed: 2
  severity: none (within carve-out: a methodology test + a skill body)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0 (SKILL.md ships with test_capture_skill_shape.py)
  api_change_without_schema: false
  severity: none
```

### Findings in the Changes

None.

### Findings in the Neighbours

None. The skill forward-references `../backlog/SKILL.md` (WP-010, same parallel batch) and `../../agents/opportunity-analyst.md` (WP-011, already merged) — both are intentional cross-references within the change, not gaps this PR introduces.

### Watch List

None.

### Cross-Reference

- **Existing Hardening Deltas covered:** none.
- **Existing security report:** none for this diff scope.
- **Pattern suggesting full audit:** none.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `ruff check`, `ruff format --check`, `pytest` on changed files. Head: 0 errors. Coverage gap: none (markdown SKILL.md has no typecheck surface; its shape is verified by the shipped pytest shape test).
- [✓] **CR-02 Single-reader pass.** Diff is 413 lines / 2 files. Above the 200-line line-count threshold but the surface is one markdown skill body + one stdlib regex shape test — no runtime/executable surface warranting parallel lens sub-agents. Both files read end-to-end by the author; the three lenses applied inline. Recorded as a conscious carve-out given the non-executable nature of the diff.
- [✓] **CR-03 Full-file reads.** Both changed files read end-to-end. Unread files: none.
- [✓] **CR-04 Evidence discipline.** No findings to evidence; lens "nothing surfaced" entries recorded with checks-run notes.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 0 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired.
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (no new domain imports, no singletons, no new external calls — the skill drives the existing `sulis-capture` CLI, does not add a call surface). Security: nothing surfaced (no secrets, no auth, no injection/SSRF; the shape test is read-only regex). Quality: test ships with the artifact; no dead surface; no contract drift; CR-10 performance scan — no anti-pattern matches (no loops with I/O; the test does single file reads).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none. PH-02 Size: none. PH-03 Safety: none. PH-04 Completeness: none. PH-03 high → CR-06 auto-downgrade: did not fire.

#### Run details

- **Diff source:** `git diff --cached origin/change/create-brain-backlog-and-traversal`
- **Neighbour expansion:** string scan; no callers/callees of new symbols (the skill is markdown; the test only imports stdlib).
- **Neighbour cap:** not reached.
- **Scanners run:** ruff (lint + format), pytest. Gitleaks/Semgrep/Trivy not applicable to a prose + stdlib-regex diff with no secrets/dependency surface.
- **Scanners unavailable:** none material to this diff.
- **Lenses dispatched in parallel:** no — single-reader carve-out for a non-executable 2-file diff (recorded above).
