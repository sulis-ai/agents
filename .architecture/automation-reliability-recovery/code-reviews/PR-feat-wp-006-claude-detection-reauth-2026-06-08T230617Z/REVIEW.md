# Code Review: PR-feat/wp-006-claude-detection-reauth — Claude provider detection + re-auth

> **Timestamp:** 2026-06-08T230617Z (ISO 8601 UTC)
> **Author:** executor (WP-006)
> **Branch:** feat/wp-006-claude-detection-reauth → change/feat-automation-reliability-recovery
> **Files changed:** 2 (source + test)
>
> **Outcome:** Ready to merge

---

## At a glance

This change teaches the Claude adapter how to read its own failures and decide
what to do next: an expired login pauses and offers a re-login link; a rate
limit or dropped connection retries; a bad request gives up. It is small,
well-tested (every new line is exercised), and keeps Claude's own error codes
walled off in the one place that should know about them. No issues need
attention.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** Two files, ~290 lines, one new test file plus the
implementation it covers. Single, focused concern.

**Scope — clean.** One concern: implement the two adapter methods the seam
declared. No mixed refactor-plus-feature.

**Safety — clean.** No migrations, no schema changes, no infrastructure files,
no secret-shaped strings. The one URL added is a public re-login link, not a
credential.

**Completeness — clean.** The new behaviour ships with its tests in the same
change (7 tests, full line coverage on the changed file).

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high/medium in the diff; Build Verification
empty; both files read end-to-end; all three lenses produced output. No
auto-downgrade triggers fired.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (PH-01..PH-04 all clean)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | — (dependency-inward preserved; HTTP vocab quarantined) |
| Security | 0 | 0 | — (no secrets; re-login link is a public URL) |
| Quality | 0 | 0 | — (100% line coverage on changed file) |

### Build Verification (CR-01)

- **ruff check** (the project's configured linter): clean on both changed files.
- **ruff format --check**: clean (format applied in Step 6).
- **mypy** (available but unconfigured in repo): 0 errors attributed to
  `adapters/claude.py`. The 11 errors mypy reports all live in
  `_session_manager/manager.py`, which is (a) not in this diff and (b) shown to
  pre-exist on the BASE branch (same 11 errors). Not PR-introduced; out of
  this WP's scope.
- **ast.parse + import smoke**: both files parse and import clean.

Build Verification section empty → no `Block` trigger.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → clean
  module_fan_out: 1 top-level dir (_session_manager + its test)
  severity: none (single concern)

Size (PH-02):
  lines_added: 288, lines_removed: 18, total: 306
  files_changed: 2
  generated_ratio: 0
  lock_file_ratio: 0
  severity: none (2-file band; additive)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0 (test file ships with the change)
  api_change_without_schema: false
  severity: none
```

### Findings in the Changes

None.

### Findings in the Neighbours

None. The neighbour ring (`classifier.py`, `recovery.py`, `adapter.py`,
`events.py`) is unchanged and was the WP-004 seam this WP fills; its no-leak
invariant is now positively asserted by the new test rather than merely
documented.

### Watch List

- The `"400"` key in `_RAW_CODE_TO_RECOVERY_CLASS` is redundant with the
  `category == "expected" → DEAD_END` fallthrough below it. This is a
  deliberate clarity choice (it documents the acceptance-criteria status code
  explicitly), annotated in the adjacent comment. Not a defect; no change
  recommended. Recorded here for awareness only.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** ruff check (configured linter):
  clean. ruff format: clean. mypy (unconfigured, scoped to changed file): 0
  errors in `claude.py`; 11 errors confined to pre-existing out-of-diff
  `manager.py` (verified present on BASE). Coverage gap: none.
- [✓] **CR-02 Single-reader pass justified by diff size: 306 lines, 2 files.**
  File count (2) is within the ≤5 carve-out; the change is single-concern and
  purely additive (one new test file + two method bodies), so a single-reader
  pass is justified despite line count nudging just over 200.
- [✓] **CR-03 Full-file reads.** Both changed files read end-to-end
  (`claude.py` 268 lines; the test file in full). No sampling.
- [✓] **CR-04 Evidence discipline.** No findings; nothing to evidence. Watch
  List item cites the specific table key + comment.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 0 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. No auto-downgrade triggers
  fired (Build Verification empty; all files read end-to-end; all lenses
  produced output; PH-03 clean).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced — imports are
  domain/seam only (`adapter`, `classifier`, `events`, `recovery`); no
  infrastructure reach-through; no new IO/singletons/circular imports; HTTP
  vocabulary stays in the adapter (ADR-003). Security: nothing surfaced —
  primitives checked SEC-01..07 (no auth bypass, no injection, no secret), SC
  (no new deps); the only URL is a public re-login link; `reauth()` mints a
  fresh opaque handle per call. Quality: Build Verification follow-up (none);
  JSX scan (n/a — Python); dead-surface (none); contract-drift (none — methods
  match the Protocol signatures); test-coverage observation (7 tests, 100%
  line coverage on `claude.py`); style (clean); CR-10 performance (no
  anti-pattern matches — pure dict lookup + value construction, no loops, no
  IO).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none. PH-02 Size: none (2
  files). PH-03 Safety: none (0 migrations/schemas/secrets/infra). PH-04
  Completeness: none (test ships with change). No PH-03 high → no CR-06
  auto-downgrade.

#### Run details

- **Diff source:** git diff 14afc3da...HEAD (scoped to `plugins/sulis/scripts/`)
- **Neighbour expansion:** git grep on the imported symbols; neighbour ring
  unchanged.
- **Neighbour cap:** not reached (4 neighbours considered).
- **Scanners run:** ruff (lint + format), mypy.
- **Scanners unavailable:** Gitleaks / Semgrep / Trivy not installed — secret
  scan performed by grep over the diff (no secret-shaped strings); dependency
  scan n/a (no new dependencies).
- **Lenses dispatched in parallel:** no — single-reader pass per CR-02
  carve-out.
