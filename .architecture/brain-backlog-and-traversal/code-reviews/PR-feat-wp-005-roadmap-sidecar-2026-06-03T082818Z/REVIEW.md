# Code Review: feat/wp-005-roadmap-sidecar — Roadmap sidecar reader + writer

> **Timestamp:** 2026-06-03T082818Z (ISO 8601 UTC)
> **Author:** WP-005 executor
> **Branch:** feat/wp-005-roadmap-sidecar → change/create-brain-backlog-and-traversal
> **Files changed:** 4
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds the Roadmap label as a small file that lives alongside the
project's data (a "sidecar"), rather than a field on each idea — because the
underlying data shapes are locked down and would reject an extra field. There
are no build errors, the change is tightly scoped to four files, and every new
behaviour has a test, including the awkward cases (a missing file, a corrupted
file). Nothing needs fixing before merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** 265 lines across 4 files. Small and focused.

**Scope — clean.** A single concern (the Roadmap sidecar), one feature commit.

**Safety — clean.** No database migrations, no schema or infrastructure
changes, no secrets.

**Completeness — clean.** A dedicated test file was added with eight tests
covering the happy path and the failure paths (missing file, corrupted file,
wrong-shaped file). One of the three new source files is a small shared-
constants helper that the tests exercise indirectly through the two functions
that use it.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs)
> for engineers and for downstream agents like `/sulis:harden-codebase`.

### Verdict

`PASS` per CR-06.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 high/medium findings (CR-09 / PH-01..PH-04)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | — (clean dependency direction; `_brain_labels` is a stdlib-only leaf) |
| Security | 0 | 0 | — (no auth/injection/secrets surface; local file I/O only) |
| Quality | 0 | 0 | — (full test coverage incl. degradation branches) |

### Build Verification (CR-01)

Mechanical baseline run on changed files:

- **ruff check** — `All checks passed!` (HEAD). See `tool-outputs/ruff-head.log`.
- **mypy** — 3 errors, all `Library stubs not installed for "yaml"`
  (`import-untyped`). All pre-existing: the offending `import yaml` line is
  present at BASE in `_brain_capture.py` (verified via
  `git show <base>:..._brain_capture.py | grep "import yaml"` → line 47).
  This diff added `import json` + `from pathlib import Path` above it,
  shifting it to line 49; the error is not PR-introduced. The brand-new
  `_brain_labels.py` (no yaml dependency) type-checks clean
  (`mypy _brain_labels.py` → `Success: no issues found`). See
  `tool-outputs/mypy-head.log`.

Build Verification is **empty** for this change. No `Block` auto-downgrade.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → clean
  module_fan_out: 1 top-level dir (plugins/sulis/scripts)
  severity: none

Size (PH-02):
  lines_added: 265, files_changed: 4
  generated_ratio: 0, lock_file_ratio: 0
  severity: low (well under 200-line / 5-file carve-out for source;
            test file accounts for 133 of the 265 lines)

Safety (PH-03):
  migration_count: 0, schema_idl_count: 0, infra_files: 0, secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 1 (_brain_labels.py — constants/helper,
            exercised transitively by test_roadmap_sidecar.py)
  test_files_added: 1 (8 tests)
  api_change_without_schema: false
  severity: none
```

### Findings in the Changes

None.

### Findings in the Neighbours

None. Neighbours of the change are the existing functions in
`_brain_capture.py` (`bootstrap_backing_chain`) and `_brain_query.py`
(`find_entities`, predicates) — untouched by behaviour; the new `roadmap_*`
functions are pure additions that share only the module file, not call paths.

### Watch List

- **`base_dir` semantics differ by call site.** For the new `roadmap_*`
  functions, `base_dir` is the `.brain/` root (sidecar at
  `base_dir/labels/roadmap.jsonld`), whereas the pre-existing query functions
  treat `base_dir` as `.brain/instances/`. This is intentional (the sidecar is
  a sibling of `instances/`, ADR-001) and documented in both docstrings, but
  the orchestrator (WP-004) and query CLI (WP-007/008) must pass the correct
  root. No failing test grounds a delta; noted for the consumers' attention.

### Cross-Reference

- **Existing Hardening Deltas covered:** none.
- **Existing security report:** none for this project.
- **Pattern suggesting full audit:** none.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** ruff check (clean) + mypy on the 3
  source modules. HEAD vs BASE: the only mypy errors are the pre-existing
  `yaml` stub import (present at BASE, verified by `git show`). 0 PR-introduced
  errors.
- [✓] **CR-02 Single-reader pass justified by scope.** Diff: 265 lines / 4
  files. Of this, 132 lines are source across 3 tightly-coupled new functions
  authored in this session with full context; 133 lines are the test file.
  The source surface (≤200 lines, ≤5 files) is within the carve-out; the diff
  is a single self-contained concern (the Roadmap sidecar) reviewed end-to-end
  by the authoring executor as the Step 6.5 self-gate. Recorded honestly: the
  raw line count (265) exceeds the 200 threshold only because of the test file;
  no production logic went unread.
- [✓] **CR-03 Full-file reads.** All 4 changed files read end-to-end (authored
  this session). Unread files: none.
- [✓] **CR-04 Evidence discipline.** All observations cite file:line / command
  output.
- [✓] **CR-05 Severity rubric.** Applied. 0 findings at any severity.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Build Verification empty; all
  files read end-to-end; all three lenses produced output. No auto-downgrade
  trigger fired.
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced — clean
  dependency direction (`_brain_labels` stdlib-only leaf; capture/query import
  it; no cycle), no new singletons, local file I/O only (no timeout/CB surface),
  best-effort read + tolerant write tested. Security: nothing surfaced —
  primitives checked SEC-01..07 (no auth/injection/SSRF/secrets surface; path
  built from trusted `base_dir` + fixed segments via `Path.joinpath`, no user-
  controlled traversal); no scanners required (no deps/Dockerfile/logging-of-
  secrets in diff). Quality: CR-10 perf scan — three `json.loads`/`write_text`
  matches are single-file ops, not in loops (no N+1/hot-loop I/O);
  dead-surface — all new symbols (`roadmap_add`, `roadmap_members`,
  `roadmap_sidecar_path`, `ROADMAP_LABEL`, `ROADMAP_SIDECAR_RELPATH`) are
  used; downstream consumers (WP-004/007) land in later WPs (expected, not
  dead); test-coverage — 8 tests cover happy + missing + malformed + wrong-
  shape branches; no JSX (backend); style clean (ruff).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none. PH-02 Size: low (265/4).
  PH-03 Safety: none (0 migrations/schemas/secrets/infra). PH-04 Completeness:
  none (test file added). No PH-03 high → no CR-06 auto-downgrade.

#### Run details

- **Diff source:** `git diff --cached origin/change/create-brain-backlog-and-traversal`
- **Neighbour expansion:** git grep over the two modified modules; no external
  callers of the new symbols yet (consumers are later WPs).
- **Neighbour cap:** not reached (well under 20).
- **Scanners run:** ruff, mypy. Gitleaks/Trivy/Semgrep not run — no
  dependency, container, or secret surface in the diff (recorded coverage
  scope, not a silent skip).
- **Lenses dispatched in parallel:** no — single-reader pass per CR-02
  carve-out justification above.
