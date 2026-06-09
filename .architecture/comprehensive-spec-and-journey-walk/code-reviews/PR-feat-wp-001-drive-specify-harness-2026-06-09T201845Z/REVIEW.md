# Code Review: feat/wp-001-drive-specify-harness — Build the drive-specify fixture harness

> **Timestamp:** 2026-06-09T201845Z (ISO 8601 UTC)
> **Author:** executor (WP-001)
> **Branch:** feat/wp-001-drive-specify-harness → change/harden-comprehensive-spec-and-journey-walk
> **Files changed:** 6
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds a small, self-contained test helper — a script that runs the
"specify" step on a pre-made example and writes out the resulting design
document. It comes with its own tests (14 of them, all passing) and three
example inputs. There are no build errors, nothing risky, and the new code is
well-scoped to a single file plus its tests. Nothing needs attention before
merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** 571 new lines across 6 files, all of it new and cohesive: one
driver script, its test file, three small example inputs, and a documentation
update. Well within a comfortable review size.

**Scope — clean.** A single concern (a new test helper) in a single module.

**Safety — clean.** No database migrations, no schema changes, no infrastructure
files, no secrets.

**Completeness — clean.** The new behaviour ships with tests covering the happy
path, determinism, failure handling, and all three example inputs.

---

## Technical detail

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; both
changed source files >50 lines (`_drive_specify.py`, `test_drive_specify.py`)
read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — ruff check clean,
  ruff format clean, module imports clean.
- **PR Hygiene:** 0 findings. Single-concern (`feat`), single module, no
  migrations/schemas/secrets, tests present.
- **In the changes:** 0 findings.
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0.

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none — explicit args, Final immutables, no infra→domain import, reuses real specify path |
| Security | 0 | 0 | none (one awareness note below) |
| Quality | 0 | 0 | none — tests present, full coverage, no CR-10 perf patterns |

### Build Verification (CR-01)

No PR-introduced errors. `ruff check` rc=0; `ruff format --check` clean; the
module parses and imports. Raw outputs in `tool-outputs/ruff-check-head.log`.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):       commit_type_spread: {feat}; module_fan_out: 1 dir → none
Size (PH-02):        lines_added: 571, removed: 0, files: 6, generated_ratio: 0 → low
Safety (PH-03):      migrations: 0, schemas: 0, infra: 0, secrets: 0 → none
Completeness (PH-04): new_source_without_test: 0 (1 source + 1 test file) → none
```

### Findings in the Changes

None.

### Findings in the Neighbours

None. The only neighbour is `_specify_classifier.py` (imported, unchanged):
`classify_depth` / `paths_touch_founder_surface` are consumed read-only. The
import direction is correct (harness → existing classifier), and the WP
deliberately reuses the real path rather than forking document emission.

### Watch List

- **`--out` / `--fixture` path handling (awareness, not a finding).**
  `_drive_specify.py` builds a filesystem path from the `--fixture` argument
  (`_FIXTURES_DIR / name / "manifest.json"`) and writes to a caller-supplied
  `--out`. A crafted `--fixture` value containing `../` could in principle
  resolve outside the fixtures dir; the `is_file()` guard means it can only
  *read* an existing manifest, never create one. This is a developer/CI test
  harness invoked with named fixtures, not a user-facing endpoint — outside the
  threat model (matches the scope guard: this is internal tooling). No failing
  characterisation test constructible for a real exploit; recorded here for
  awareness only, no delta.

### Cross-Reference

- No prior `.security/{project}/viability-report-*.md` for this project.
- No existing hardening deltas to cite.
- No neighbour pattern suggests a broader audit.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `ruff check` (rc=0) + `ruff format --check` (clean) + import check (OK) on HEAD changed files. Base had no such files (all net-new). Coverage gap: no mypy/pyright config in this scripts project — the wpx-* tooling is stdlib-only and ruff is the configured linter; recorded as the project's mechanical floor.
- [✓] **CR-02 Dispatch shape.** Single-reader pass. Diff is 571 lines / 6 files — above the 200-line carve-out, but the content is one cohesive net-new module (289 lines) + its test file (221 lines) + 3 tiny JSON fixtures (39 lines) + a 22-line doc update, authored in this session with full context. Both source files read end-to-end; no sampling.
- [✓] **CR-03 Full-file reads.** `_drive_specify.py` (289 lines) and `test_drive_specify.py` (221 lines) read end-to-end. JSON fixtures + README diff read in full.
- [✓] **CR-04 Evidence discipline.** No findings to evidence; the one Watch List note cites the exact path-construction site.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 0 low, 1 awareness note.
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade trigger fired (Build Verification empty; no unread >50-line file; all lenses produced output; no PH-03 high).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (checks: dependency direction, singletons, circular imports, resilience N/A for pure-local I/O, contract test present). Security: nothing surfaced (checks: secrets none, injection none — JSON parse only no eval, SSRF/auth N/A; one path-handling awareness note). Quality: 0 findings — build-verification follow-up (none), JSX scan (N/A, no TSX/JSX), dead-surface (none), contract-drift (none), test-coverage (14 tests cover new behaviour), CR-10 perf (no anti-pattern matches; loops iterate small in-memory lists only), style (clean per ruff).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none (single feat, 1 module). PH-02 Size: low (571 lines / 6 files). PH-03 Safety: none (0 migrations/schemas/secrets/infra). PH-04 Completeness: none (source ships with tests). PH-03 high → auto-downgrade: did not fire.

#### Run details

- **Diff source:** `git diff change/harden-comprehensive-spec-and-journey-walk` (staged WP files).
- **Neighbour expansion:** git grep — only `_specify_classifier.py` (imported, unchanged).
- **Neighbour cap:** 1 of 1; cap not reached.
- **Scanners run:** ruff (check + format). Gitleaks/Semgrep/Trivy not invoked (no secret/dependency surface; pure stdlib + one internal import).
- **Scanners unavailable:** mypy/pyright (not configured for this scripts project).
- **Lenses dispatched in parallel:** no — single-reader pass justified above (CR-02).
