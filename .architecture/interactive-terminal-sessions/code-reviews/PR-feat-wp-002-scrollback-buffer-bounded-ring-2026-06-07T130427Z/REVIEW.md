# Code Review: PR-feat-wp-002 — Add the bounded scrollback ring as the second content model

> **Timestamp:** 2026-06-07T130427Z (ISO 8601 UTC)
> **Author:** executor (WP-002)
> **Branch:** feat/wp-002-scrollback-buffer-bounded-ring → change/extend-interactive-terminal-sessions
> **Files changed:** 3
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds one small, self-contained building block: a memory-bounded
buffer that holds the most recent terminal output so a freshly-opened terminal
view shows what's already on screen instead of a blank pane. It does one thing,
has a hard memory ceiling so it can never grow without limit, and comes with
tests that prove both of those behaviours. There are no build errors, nothing
risky, and nothing that needs your attention before merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** 122 lines added across 3 files. Small and easy to review
thoroughly.

**Scope — clean.** A single concern: the new buffer plus its tests and the
one line that makes it importable from the package.

**Safety — clean.** No database changes, no infrastructure changes, no secrets.
The one safety-relevant property — the memory ceiling that stops the buffer
growing forever — is the whole point of the change and is tested directly
(2 MB pushed into a 1 MB buffer; the buffer stays at 1 MB).

**Completeness — clean.** The new behaviour ships with its tests (one for the
memory ceiling, one for the output ordering).

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs)
> for engineers and for downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all
files >50 lines read end-to-end (the one >50-line file, `scrollback.py` at 71
lines, was read fully); all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (PH-01..PH-04 all clean)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | None — stdlib-only leaf type, dependency points inward (WPB-01) |
| Security | 0 | 0 | None — the §2.11.3 DoS ceiling is enforced + tested |
| Quality | 0 | 0 | None — tests present, no dead surface, no CR-10 anti-patterns |

### Build Verification (CR-01)

Mechanical baseline ran on the changed files. `ruff check` → "All checks
passed!". `ruff format --check` → "2 files already formatted". `mypy
--follow-imports=silent _session_manager/scrollback.py` → "Success: no issues
found in 1 source file".

Note: a whole-graph `mypy` run surfaces 10 pre-existing errors in
`_session_manager/manager.py`. That file is **byte-identical to the base
branch** (verified via `git show` diff in Step 6) — the errors are pre-existing
debt in a file this PR does not touch, outside the WP Contract scope. Not
PR-introduced; not a Build Verification finding.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → clean (single type)
  module_fan_out: 1 distinct top-level area (_session_manager + its tests)
  severity: none

Size (PH-02):
  lines_added: 122, lines_removed: 0, total: 122
  files_changed: 3
  generated_ratio: 0.0
  lock_file_ratio: 0.0
  severity: none (≤200 lines, ≤5 files)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0 (scrollback.py ships with test_scrollback.py)
  api_change_without_schema: false (the public shape matches contract §2.11)
  severity: none
```

### Findings in the Changes

None.

### Findings in the Neighbours

None. Neighbours are the consumers declared by the WP (`__init__.py` re-export;
WP-003 pty pump and WP-004 viewer not yet built). The re-export is correct and
the only neighbour edit; it introduces no gap.

### Watch List

None.

### Cross-Reference

- **Existing Hardening Deltas covered:** none
- **Existing security report:** none found at `.security/interactive-terminal-sessions/`
- **Pattern suggesting full audit:** none

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `ruff check` + `ruff format --check` + `mypy --follow-imports=silent` on changed files. Base: clean on changed surface. Head: clean. PR-introduced errors: 0. Coverage gap: pytest-cov absent (manual coverage analysis done at Step 3 — new file 100% statement-covered).
- [✓] **CR-02 Single-reader pass justified by diff size: 122 lines, 3 files** (within the ≤200 lines AND ≤5 files carve-out).
- [✓] **CR-03 Full-file reads.** The one changed file >50 lines (`scrollback.py`, 71 lines) read end-to-end; `test_scrollback.py` (48 lines) and the 3-line `__init__.py` delta read in full. Unread files: none.
- [✓] **CR-04 Evidence discipline.** No findings to evidence; lens outputs cite the checks run.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 0 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired (Build Verification empty; all >50-line files read end-to-end; all lenses produced output; no PH-03 high).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced. Checks run: dependency direction (stdlib-only, points inward — WPB-01), module-level singleton scan (none — instance state via `field(default_factory=bytearray)`), new external-call scan (none — pure in-memory), new-port-without-contract-test (n/a — concrete value type, not a port). Security: nothing surfaced. Primitives checked: SEC-01..07 (no auth/injection/secrets surface), SC-01..04 (no dependency changes), DoS ceiling (§2.11.3) enforced + tested. Scanners: none applicable to a stdlib-only value type (no secrets/deps/IO to scan). Quality: jsx-ident-scan n/a (no JSX); dead-surface (ScrollbackBuffer exported + consumed — not dead); contract-drift (public shape matches §2.11 exactly); test-coverage (2 tests for new behaviour); style (clean names, docstrings cite contract); CR-10 performance (no anti-pattern matches — `append` is O(len(data)) amortised, no loops, ring is bounded by design).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none (single `feat`). PH-02 Size: none (122 lines / 3 files). PH-03 Safety: none (0 migrations, 0 schemas, 0 secrets, 0 infra). PH-04 Completeness: none (source ships with tests). PH-03 high → CR-06 auto-downgrade: did not fire.

#### Run details

- **Diff source:** `git diff change/extend-interactive-terminal-sessions` (local worktree, intent-to-add for new files)
- **Neighbour expansion:** git grep for `ScrollbackBuffer` consumers — only the package `__init__.py` re-export exists today
- **Neighbour cap:** 1 of 1 considered, 0 excluded
- **Scanners run:** ruff, mypy (no secrets/dependency/SAST scanners applicable to a stdlib-only value type)
- **Scanners unavailable:** pytest-cov (manual coverage at Step 3)
- **Lenses dispatched in parallel:** no — single-reader pass per CR-02 carve-out (122 lines / 3 files)
