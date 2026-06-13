# Code Review: WP-001 — Multi-root Brain read seam

> **Timestamp:** 2026-06-13T192426Z (ISO 8601 UTC)
> **Author:** executor (autonomous)
> **Branch:** wp/extend/wp-001-multi-root-read-seam → change/move-dogfood-central-brain
> **Files changed:** 2
>
> **Outcome:** Ready to merge

---

## At a glance

This change teaches the part of the system that reads saved knowledge to look in
two places at once — a read-only library that ships with the plugin, plus the
live central store — and combine them, with the live store winning if the same
record appears in both. The change is small (160 lines across 2 files),
well-scoped, and comes with three new tests covering the happy path, the
combine-two-places case, and the "live store wins" case. No build errors, no
issues that need attention.

## What to fix

No issues that need attention.

## How this pull request is shaped

Clean across the board:

- **Size** — small (160 lines, 2 files). Easy to review thoroughly.
- **Scope** — single concern (the read seam). One file of code, one file of tests.
- **Safety** — no database migrations, no schema changes, no infrastructure, no secrets.
- **Completeness** — three new tests added for the new behaviour. Existing
  behaviour is preserved exactly (callers that pass a single location keep working
  unchanged).

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; both
changed files read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (CR-09 / PH-01..PH-04)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | nothing surfaced |
| Security | 0 | 0 | nothing surfaced |
| Quality | 0 | 0 | nothing surfaced |

### Build Verification (CR-01)

Configured linter `ruff check` on both changed files: **all checks passed**
(`tool-outputs/ruff-check-head.log`). Behaviour suite
`pytest tests/unit/test_brain_query.py`: **18 passed**
(`tool-outputs/pytest-head.log`). No PR-introduced errors.

> Note: `ruff format --check` reports the file would reformat, but the pristine
> base file already fails `ruff format --check` and no CI workflow runs ruff
> format — the established repo convention is `ruff check` only (CP-01). Not a
> finding.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                    → clean
  module_fan_out: 1 (plugins/sulis/scripts)     → clean
  severity: none

Size (PH-02):
  lines_added: 160, lines_removed: 17, total: 177
  files_changed: 2
  severity: none (within 0-200 line band; 2-file band)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0 (3 tests added for new behaviour)
  api_change_without_schema: false
  severity: none
```

### Findings in the Changes

None.

#### Architecture lens — nothing surfaced

Checks run: new infrastructure→domain imports (none); new module-level
singletons / `getInstance()` (none); new circular imports (none); new
HTTP/RPC/DB/external calls (none — pure in-process filesystem walk); hardcoded
secrets (none); new ports without contract test (none — the change extends an
existing read function). The change **reuses** the existing single tree-walk
(`_iter_one_root`); both the single-root and multi-root public paths delegate to
it, so there is no duplicated traversal (HD-02 `dependency-direction` /
duplication: clean; ADR-001 satisfied).

#### Security lens — nothing surfaced

Primitives checked: SEC-01..07 (access control, auth, injection, validation,
XSS, SSRF, secrets). No new access boundary; `library_root` is a `Path | None`
supplied by trusted in-process callers (plugin-relative), not user input. The
only deserialization is the pre-existing `json.loads(f.read_text())`, unchanged,
already guarded by the silent-skip `except (json.JSONDecodeError, OSError)`. No
new attack surface.

#### Quality lens

1. **Build Verification follow-up:** no CR-01 errors to translate.
2. **JSX/template identifier scan:** N/A — no TSX/JSX/Vue/Svelte files.
3. **Dead-surface:** none. The new `library_root` parameter and the extracted
   `_iter_one_root` helper are both consumed by `iter_entities`.
4. **Contract-drift:** none. The union-by-id + captures-win behaviour matches
   ADR-001 precisely; docstrings describe the implemented contract.
5. **Test-coverage:** 3 new tests for the new behaviour
   (`test_iter_entities_reads_only_one_root` gap-proof,
   `test_multi_root_unions_library_and_captures`,
   `test_captures_win_on_id_collision`). Existing 15 tests still green
   (no signature break).
6. **Style/readability:** explicit types, clear docstrings; no TODO/FIXME added.
   Nothing surfaced.
7. **Performance procedural checks (CR-10):** the two added loops iterate the
   captures-root generator then the library-root generator **sequentially**
   (a union, not a nested/N+1 access) — O(N) over total instances. Collision
   detection uses a `set` (`seen_ids`) for O(1) membership. No anti-pattern
   match.

### Findings in the Neighbours

None. Direct callers (`_verify_environment.py`, `find_entities` within the same
module) call `iter_entities` positionally with `entity_type`/`domain` kwargs;
adding a keyword-only `library_root` with a default of `None` does not change
their behaviour. Verified: all 3367 non-environment tests pass.

### Watch List

None.

### Cross-Reference

- **Existing Hardening Deltas covered:** none.
- **Existing security report:** none for this project.
- **Pattern suggesting full audit:** none.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Command: `ruff check` (configured
  linter per pyproject). HEAD: 0 errors. Behaviour suite: 18 passed. Coverage
  gap: pytest-cov absent → manual branch-coverage analysis (all new branches
  exercised except the defensive non-string-id guard).
- [✓] **CR-02 Single-reader pass justified by diff size: 160 lines, 2 files**
  (within the ≤200-line AND ≤5-file carve-out).
- [✓] **CR-03 Full-file reads.** Both changed files read end-to-end
  (`_brain_query.py`, `test_brain_query.py`). Unread files: none.
- [✓] **CR-04 Evidence discipline.** No findings; nothing to evidence. Lens
  "nothing surfaced" entries list the checks run.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 0 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none
  fired (Build Verification empty; all files read end-to-end; all lenses
  produced output; no PH-03 high).
- [✓] **CR-07 Lens completion.** Architecture: 0 findings + checks listed.
  Security: 0 findings + primitives listed. Quality: 7 outputs produced
  (build follow-up, jsx N/A, dead-surface, contract-drift, test-coverage,
  style, CR-10 perf).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none (single concern). PH-02
  Size: none (160 lines / 2 files). PH-03 Safety: none (0 migrations / 0 schemas
  / 0 secrets / 0 infra). PH-04 Completeness: none (3 tests added). PH-03 high →
  auto-downgrade: did not fire.

#### Run details

- **Diff source:** `git diff change/move-dogfood-central-brain` (working tree).
- **Neighbour expansion:** `git grep` for `iter_entities` callers.
- **Neighbour cap:** not reached (small fan-out).
- **Scanners run:** ruff (lint), pytest (behaviour).
- **Scanners unavailable:** pytest-cov (manual coverage analysis substituted).
- **Lenses dispatched in parallel:** no — single-reader carve-out (CR-02).
