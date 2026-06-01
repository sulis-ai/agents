# Code Review: WP-003 — Extend requirements-analyst agent prompt

> **Timestamp:** 2026-06-01T20:45:32Z (ISO 8601 UTC)
> **Author:** iain (executor — WP-003)
> **Branch:** feat/wp-003-extend-requirements-analyst → change/extend-verification-by-design
> **Files changed:** 2 (1 modified, 1 new)
>
> **Outcome:** Ready to merge

---

## At a glance

Your change extends the requirements-analyst agent so it asks the new
verification questions during Phase 3 and produces the new
`## Verification Plan` section in every SRD. The change cites the
canonical question file by path (it doesn't copy the questions inline,
which would drift over time). The test file you wrote first locks in
five structural properties of the extension so any future edit that
breaks them fails loudly.

No issues that need attention. The build is clean, the test suite is
green, and the change stays inside the work package's scope.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — well-scoped.** 124 lines across 2 files: one prose extension
to the existing agent prompt, one new structural test file. Single
concern, single Conventional Commit type, no migrations or schema
changes.

**Completeness — good.** Test file written first (failing for the
right reason), then the agent prompt extension was made, then tests
re-ran green. Red → Green discipline visible in the journal.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN)
> for engineers and downstream agents. The author tier above contains
> everything the PR author needs to act.

### Verdict

`PASS` per CR-06.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings — all four primitives clean (CR-09 /
  PH-01..PH-04)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings (no neighbour expansion required —
  the agent prompt is consumed by `sulis:specify`, which is owned by
  WP-006; the test file imports only stdlib + pytest)
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | — |
| Security | 0 | 0 | — |
| Quality | 0 | 0 | — |

### Build Verification (CR-01)

`ruff check` clean. `ruff format --check` clean. `pytest
plugins/sulis/scripts/tests/unit/` → 1453 passed, 0 failed. New
test file's 7 assertions all green against the extended agent prompt.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → clean
  module_fan_out: 1 (plugins/sulis/...)        → clean
  severity: none

Size (PH-02):
  lines_added: 102, lines_removed: 2, total: 104
  files_changed: 2
  generated_ratio: 0.0
  lock_file_ratio: 0.0
  severity: none

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0
  api_change_without_schema: false
  severity: none
```

### Findings in the Changes

None.

### Findings in the Neighbours

None. Neighbour ring not expanded — the agent prompt is prose-only
configuration consumed by `sulis:specify` (downstream WP-006);
the test file imports only stdlib + pytest with no project-internal
imports.

### Watch List

None.

### Cross-Reference

- No existing Hardening Deltas covered or duplicated.
- No existing security report referenced (none exists for this
  change yet).
- No neighbour pattern suggests a broader gap.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `ruff check
  <test-file>`; `ruff format --check <test-file>`; `pytest
  plugins/sulis/scripts/tests/unit/`. Base: clean (no project changes
  on base). Head: clean. New tests: 7 passed. Full suite: 1453 passed.
- [✓] **CR-02 Single-reader pass justified.** Diff size 124 lines,
  2 files (well below the 200-line / 5-file carve-out threshold).
- [✓] **CR-03 Full-file reads.** Both in-scope files read end-to-end.
  Markdown extension is 100 new LOC. Test file is 210 LOC.
- [✓] **CR-04 Evidence discipline.** No findings produced — vacuous.
- [✓] **CR-05 Severity rubric.** Applied against the empty finding set.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. No auto-downgrade
  trigger fired.
- [✓] **CR-07 Lens completion.** Architecture: explicit
  *"nothing surfaced"* + checks-run list. Security: explicit
  *"nothing surfaced"* + primitives-checked list. Quality: all seven
  outputs produced (jsx-ident-scan recorded as N/A; CR-10 performance
  scan recorded as no-match for all 10 patterns).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none (1 commit
  type, 1 top-level module). PH-02 Size: none (104 net lines / 2
  files). PH-03 Safety: none (0 migrations / 0 schemas / 0 secrets / 0
  infra). PH-04 Completeness: none (test file precedes implementation
  per RGB). PH-03 high → CR-06 auto-downgrade: not fired.

#### Run details

- **Diff source:** `git diff origin/change/extend-verification-by-design`
  + untracked test file in scope.
- **Neighbour expansion:** Not run — no signal warrants it (prose-only
  configuration + stdlib-only test).
- **Neighbour cap:** N/A.
- **Scanners run:** None (no signal — no secrets pattern, no
  dependency changes, no IaC, no Dockerfiles).
- **Scanners unavailable:** N/A (none applicable to this diff shape).
- **Lenses dispatched in parallel:** No — single-reader pass per CR-02
  carve-out.
