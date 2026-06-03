# Code Review: feat/wp-010-backlog-skill — Create /sulis:backlog skill (traverse off the brain graph)

> **Timestamp:** 2026-06-03T093751Z (ISO 8601 UTC)
> **Author:** WP-010 executor
> **Branch:** feat/wp-010-backlog-skill → change/create-brain-backlog-and-traversal
> **Files changed:** 2 (1 new skill body, 1 new shape test)
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds the founder-facing `/sulis:backlog` command — one new skill
body plus its shape test. It is well-scoped (a single concern), it includes
tests, and the mechanical checks (lint, compile) are clean. There's nothing
that needs attention before merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Scope — clean.** One concern: the new backlog command and its test. No
mixing of unrelated changes.

**Size — clean.** Two files, ~457 lines, both new.

**Safety — clean.** No database migrations, no schema files, no secrets, no
infrastructure changes.

**Completeness — clean.** The new skill body ships with a 3-case shape test
covering the brain-vs-change-store distinction, the no-jargon frontmatter
rule, and the open/roadmap/done coverage.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs)
> for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty;
both files read end-to-end; all three lenses produced output. No
auto-downgrade trigger fired.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (CR-09 / PH-01..PH-04 all clean)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | nothing surfaced |
| Security | 0 | 0 | nothing surfaced |
| Quality | 0 | 0 | nothing surfaced |

### Build Verification (CR-01)

Mechanical baseline ran on the one Python file in the diff
(`tests/methodology/test_backlog_skill_shape.py`):

- `ruff check` → All checks passed
- `ruff format --check` → already formatted
- `python3 -m py_compile` → OK
- `python3 -m compileall plugins/sulis/scripts` → OK

No type-checker is configured for this repo (per `branch-ci.yml`:
*"no type-checker configured for this repo"*). The SKILL.md is markdown — no
mechanical typecheck applies; its contract is verified by the shape test.

Build Verification section empty → PASS not blocked.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → clean (single type)
  module_fan_out: 1 logical concern (backlog skill + its test)
  severity: none

Size (PH-02):
  lines_added: ~457, lines_removed: 0, total: ~457
  files_changed: 2
  generated_ratio: 0
  lock_file_ratio: 0
  severity: none (both files new; small)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0 (SKILL.md covered by test_backlog_skill_shape.py)
  api_change_without_schema: false
  severity: none
```

### Findings in the Changes

None.

### Findings in the Neighbours

None. The skill invokes the existing `sulis-brain-query` seam (WP-008) by
name; it does not modify it. The shape test mirrors the established
`test_opportunity_analyst_agent_shape.py` structure (path resolution via
`Path(__file__).parents[5]`, frontmatter regex, body-after-frontmatter
extraction).

### Watch List

None.

### Cross-Reference

- **Existing Hardening Deltas covered:** none
- **Existing security report:** none for this project
- **Pattern suggesting full audit:** none

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `ruff check`,
  `ruff format --check`, `py_compile`, `compileall plugins/sulis/scripts`.
  Base vs head: the diff is two NEW files; head adds 0 lint/compile errors.
  Coverage gap: no type-checker configured for the repo (documented in
  branch-ci.yml) — recorded, not skipped silently.
- [✓] **CR-02 Dispatch shape.** Diff is 2 files / ~457 lines. >200 lines, so
  not the formal single-reader carve-out; reviewed thoroughly as a
  single reader with extra conservatism — justified because the content is
  one markdown skill body + one stdlib-only shape test with no executable
  runtime logic and no concurrency to fan out across.
- [✓] **CR-03 Full-file reads.** Both files read end-to-end
  (SKILL.md 250 lines; test 207 lines). Unread files: none.
- [✓] **CR-04 Evidence discipline.** No findings to evidence.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 0 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers:
  none fired (Build Verification empty; all files read end-to-end; all
  lenses produced output; no PH-03 high).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced — checked
  for infra imports, singletons, layout reach-through, external calls
  (none present). Security: nothing surfaced — checked for secrets, auth
  surface, injection, external calls (none present); resolver mirrors the
  established dashboard skill pattern. Quality: 0 findings — build follow-up
  (none), JSX scan (N/A, no JSX), dead-surface (ruff F401/F841 clean),
  contract-drift (seam modes asserted match the real WP-008 argparse modes),
  test-coverage (deliverable fully covered by 3 shape tests), style (0
  TODO/FIXME, mirrors sibling conventions), CR-10 performance (only small
  fixed-iteration assertion loops over 3-element tuples — no anti-pattern).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none (single feat concern).
  PH-02 Size: none (~457 lines / 2 files). PH-03 Safety: none (0 migrations,
  0 schemas, 0 secrets, 0 infra). PH-04 Completeness: none (test ships with
  source). PH-03 high → CR-06 auto-downgrade fired: no.

#### Run details

- **Diff source:** `git diff origin/change/create-brain-backlog-and-traversal...HEAD` plus untracked working-tree files (Step 6.5 runs pre-commit)
- **Neighbour expansion:** git grep — the seam (`sulis-brain-query`) and the sibling shape test; not modified by this diff
- **Neighbour cap:** not reached (well under 20 files)
- **Scanners run:** ruff (lint + format); compileall
- **Scanners unavailable:** Gitleaks/Semgrep/Trivy not installed in this worktree — diff has no secrets/dependencies/Docker surface, so coverage impact is nil
- **Lenses dispatched in parallel:** no — single-reader pass on a 2-file documentation+test diff with no runtime logic
