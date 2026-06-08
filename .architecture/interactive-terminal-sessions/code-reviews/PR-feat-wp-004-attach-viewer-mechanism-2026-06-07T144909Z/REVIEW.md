# Code Review: WP-004 — Attach/viewer mechanism + io-mode/viewer-count

> **Timestamp:** 2026-06-07T144909Z (ISO 8601 UTC)
> **Author:** executor (WP-004)
> **Branch:** feat/wp-004-attach-viewer-mechanism → change/extend-interactive-terminal-sessions
> **Files changed:** 6 (2 new, 4 modified)
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds the "watch and type into a live terminal" engine piece: a viewer
can attach to a running terminal session, see what's already on screen plus live
output, type keystrokes in, and detach without killing the session. The code is
well-scoped, every new behaviour has a test, the existing chat path is untouched,
and there are no build, security, or correctness issues. Ready to merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** ~975 lines across 6 files, but most of that is the new viewer
module (with thorough docstrings) and its test file (12 tests). The behavioural
change to existing files is small and additive (125 lines across 4 files).

**Scope — clean.** Single concern: the attach/viewer mechanism and its
observability fields. No mixed refactor/feature.

**Safety — clean.** No database migrations, no schema/IDL changes, no
infrastructure files, no secrets.

**Completeness — clean.** New behaviour is fully tested: 12 tests, 100% line
coverage on the new module, and the existing session suite (104 tests) stays
green, proving the chat path is unchanged.

---

## Technical detail

> Below this point the report uses internal taxonomy for engineers and for
> downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; every
changed file >50 lines read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01). Ruff lint + format
  clean. mypy shows 11 errors in `manager.py` — all pre-existing on BASE
  (identical count on BASE and HEAD); zero introduced by this WP. mypy is not a
  project quality gate (no config in pyproject, not in CI); ruff is.
- **PR Hygiene:** 0 findings. Single concern, additive, no migrations/secrets,
  fully tested.
- **In the changes:** 0 findings (0 critical, 0 high, 0 medium, 0 low).
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0.

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none — registry wired at the spawn seam, deps inward |
| Security | 0 | 0 | none — verbatim keystrokes are ADR-003; auth gate is WP-005's |
| Quality | 0 | 0 | none — 12 tests, 100% coverage on viewer.py |

### Build Verification (CR-01)

No PR-introduced errors. Commands run on HEAD:
- `uv run ruff check _session_manager/ tests/unit/test_viewer.py` → All checks passed.
- `uv run ruff format --check` on the 6 touched files → all formatted.
- `uv run mypy _session_manager/{viewer,manager,state,events}.py --ignore-missing-imports`
  → 11 errors, ALL in pre-existing `manager.py` code (`**tuning: object` dict
  handling at lines 131/139/141/150/157; `rss_by_pid.get` at 344). BASE shows
  the identical 11. Delta = 0. The new attach/viewer/io_mode lines are type-clean.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → clean (single concern)
  module_fan_out: 1 top-level dir (_session_manager + its tests)
  severity: none

Size (PH-02):
  lines_added: ~975 (incl. ~600 docstring+test), files_changed: 6
  behavioural delta to existing files: 125 lines / 4 files
  generated_ratio: 0
  severity: none (new module + tests dominate; behavioural change is small)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0 (viewer.py has test_viewer.py, 100% cov)
  api_change_without_schema: false (io_mode/viewer_count match contract §2.12.5)
  severity: none
```

### Findings in the Changes

None.

### Findings in the Neighbours

None. The diff touches `session.py` (added the `on_pty_output` seam + its fire
method), `manager.py` (attach + registry wiring + field population),
`state.py` (additive defaulted fields), `events.py` (NOT_PTY_SESSION code). All
neighbour code (the pty pump, restart path, status/health) stays green under the
existing suite (104 tests).

### Watch List

- **broadcast cost per master read.** `ViewerRegistry.broadcast` copies the
  viewer list under a lock on every 64 KiB master read. Bounded by the attached
  viewer count (typically 1-2) and skipped entirely for a headless session (the
  `on_pty_output` seam is `None`, so the pump never calls it). No action; noted
  for awareness if a future high-fanout multi-viewer scenario emerges.
- **Restart reattach (§2.12.3).** This WP owns the reattach half (the seam +
  registry survive `replace_process` because they live on the manager keyed by
  session key, and `feed` reads `pty_master_fd` live so it follows the fresh
  master). The pty re-creation half is WP-003's; the joined invariant is proven
  end-to-end by WP-010. No finding — recorded as the documented seam boundary.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** ruff check + format (clean), mypy on
  changed modules (0 PR-introduced; 11 pre-existing on BASE, identical on HEAD).
  Coverage gap: none.
- [✓] **CR-02 Dispatch.** Single-reader pass by the authoring executor, which
  has full end-to-end context on all 6 files (authored this session) and read
  each in full. Diff is new-module + tests dominated; behavioural delta is 125
  lines / 4 files. Inline three-lens scoring applied.
- [✓] **CR-03 Full-file reads.** All 6 changed files read end-to-end (authored
  this session). Unread: none.
- [✓] **CR-04 Evidence discipline.** No findings to evidence; Build Verification
  cites exact mypy line numbers + BASE/HEAD delta.
- [✓] **CR-05 Severity rubric.** Applied — 0 findings at any severity.
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade triggers fired (Build
  Verification empty, all files read, all lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture: WPB-01/07/09/12 + resilience
  checks, nothing surfaced. Security: SEC access/injection/secrets checked,
  nothing surfaced (verbatim keystrokes are ADR-003; attach-auth gate is WP-005).
  Quality: tests present (12, 100% cov), no dead surface, no contract drift,
  CR-10 performance scan (no anti-pattern matches; broadcast cost noted on Watch
  List).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none. PH-02 Size: none. PH-03
  Safety: none. PH-04 Completeness: none. No PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** local git, working tree vs `change/extend-interactive-terminal-sessions`.
- **Neighbour expansion:** session-manager package (the changed module's callers
  + callees: pump, restart, status/health) — all exercised by the existing suite.
- **Scanners run:** ruff (lint + format), mypy (changed modules).
- **Lenses:** inline by authoring executor with full-file context.
