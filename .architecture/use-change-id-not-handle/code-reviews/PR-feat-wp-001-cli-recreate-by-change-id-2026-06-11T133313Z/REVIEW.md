# Code Review: WP-001 — sulis-change recreate resolves by --change-id

> **Timestamp:** 2026-06-11T133313Z (ISO 8601 UTC)
> **Author:** executor (WP-001)
> **Branch:** feat/wp-001-cli-recreate-by-change-id → change/fix-use-change-id-not-handle
> **Files changed:** 2 (1 source, 1 new test)
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds a precise way to re-open a change's workspace — by its unique id
rather than its shareable short label. It's small, well-scoped, and fully tested.
No build errors, no risky patterns, and the existing label-based path keeps working
exactly as before. Nothing needs attention before merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** 58 lines of code change in one file, plus a focused 253-line test
file. Easy to review in full.

**Scope — clean.** A single concern: give the recreate command a precise selector.

**Safety — clean.** No database migrations, no schema changes, no infrastructure or
secrets touched. Pure local resolution logic.

**Completeness — clean.** Six new tests cover the new behaviour, including the
unhappy paths (an unknown id, a malformed id) and the shared lookup helper's
fallback. New behaviour ships with its safety net.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; both
changed files read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (PH-01..PH-04 all clean)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | nothing surfaced |
| Security | 0 | 0 | nothing surfaced |
| Quality | 0 | 0 | nothing surfaced |

### Build Verification (CR-01)

Empty. `python3 -m py_compile` clean on both changed files. `ruff check` reports 4
F401 unused-import findings on `sulis-change` — all 4 present on BASE
(`_gh_ref_sha`, `add_common_args`, `emit_internal_error`, `parse_change_branch`),
**none PR-introduced** (BASE F401 count = HEAD F401 count = 4). The PR's single added
import (`validate_change_ulid`) is used at line 2048. New test file: zero ruff
findings.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                  → clean (single concern)
  module_fan_out: 1 top-level dir (plugins/)  → clean
  severity: none

Size (PH-02):
  lines_added: 58, lines_removed: 4 (source); +253 new test file
  files_changed: 2
  generated_ratio: 0
  lock_file_ratio: 0
  severity: none (well under bands)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0 (6 tests added for the new behaviour)
  api_change_without_schema: false
  severity: none
```

### Findings in the Changes

None.

#### Architecture lens

Nothing surfaced. Checks run:
- **Form** — `_resolve_record_by_id` extracted as the single record-lookup-by-id
  authority (ADR-001, 2-consumer threshold: recreate + mark-shipped). No new
  infra→domain imports, no new module-level singletons, no circular imports. The
  `if change_id / elif args.handle / else slug` precedence preserves the existing
  handle/slug behaviour byte-for-byte (verified: 132 change-related tests green).
- **Armor** — id path validates input up front (`validate_change_ulid`) before any
  store lookup; malformed → clean `emit_error`; unknown id → clean `emit_error`
  with an operator hint, no worktree side-effect. No new external calls, retries,
  or timeouts introduced (local store reads only). No secrets, no PII logging.
- **Proof** — new behaviour backed by behavioural tests against a real temp
  `SULIS_STATE_DIR` store + a real git worktree (MEA-09; the sole `monkeypatch` is
  deliberate fault-injection to force the direct-read miss and exercise the scan
  fallback). The shared helper carries its own 3 unit tests (direct hit / scan
  fallback / none).

#### Security lens

Nothing surfaced. Primitives checked: SEC-01 (access control — n/a, local), SEC-04
(input validation — `validate_change_ulid` constrains the id to 26-char Crockford
before it reaches `change_dir(change_id)`, closing any path-traversal-shaped input
on the recreate path), SEC-06 (secrets exposure — none). No auth boundary crossed.
No new dependencies (SC-01..04 n/a). Scanners: not invoked (pure local stdlib logic,
no new third-party surface).

#### Quality lens

1. **Build Verification follow-up** — none (baseline clean).
2. **JSX/template identifier scan** — n/a (no TSX/JSX/Vue/Svelte in diff).
3. **Dead-surface findings** — none. The added import is used; the new helper has
   two consumers; the new argparse arg is consumed in `cmd_recreate`.
4. **Contract-drift findings** — none. The recreate JSON output keeps `branch`/
   `recreated` shape; `handle` remains a display field (Contract honoured).
5. **Test-coverage observation** — strong. 6 tests, including both Contract-named
   Red tests plus a malformed-id hardening test and 3 helper unit tests.
6. **Style/readability** — clean. Docstrings explain the why (ADR-001, #56, #101);
   comments are purposeful, not noise.
7. **Performance procedural checks (CR-10)** — no anti-pattern matches. The one
   loop (`for r in list_all_changes()` in the fallback) is a single in-memory linear
   scan over an already-loaded list, runs only on a direct-read miss, is not nested,
   and issues no per-iteration store hit. Benign (see `tool-outputs/cr10-scan.log`).

### Findings in the Neighbours

None. Neighbours examined: `cmd_mark_shipped` (now shares `_resolve_record_by_id`),
`_select_change_id_refusing_conflict`, `read_change_record` / `list_all_changes`
(`_change_state.py`), `validate_change_ulid` (`_wpxlib.py`). The 4 pre-existing F401
unused imports in `sulis-change` are noted for awareness but not introduced by this
PR — recommend a separate import-hygiene pass if desired (out of this WP's scope per
EP-07).

### Watch List

None.

### Cross-Reference

- **Existing Hardening Deltas covered:** none
- **Existing security report:** none found under `.security/use-change-id-not-handle/`
- **Pattern suggesting full audit:** the 4 pre-existing F401 imports suggest a small
  import-hygiene cleanup could be worthwhile repo-wide, but this is drift, not a
  PR-introduced gap — out of scope here.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `python3 -m py_compile <changed>`;
  `ruff check <changed>`. Base: 4 F401 (pre-existing). Head: 4 F401 (identical set).
  PR-introduced errors: 0. Coverage gap: none (no type-checker configured per plugin
  contract — stdlib-only tooling).
- [✓] **CR-02 Dispatch shape.** Single-reader pass justified by diff size: 58 source
  lines / 2 files, single Python module + its test. Both files read end-to-end.
- [✓] **CR-03 Full-file reads.** Source diff read in full; the 253-line new test file
  read end-to-end. Unread files: none.
- [✓] **CR-04 Evidence discipline.** No findings to evidence; baseline + CR-10 outputs
  saved under `tool-outputs/`.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 0 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired
  (Build Verification empty; all files read end-to-end; all lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (Form/Armor/Proof
  checks listed). Security: nothing surfaced (SEC-01/04/06 checked, scanners n/a —
  no new third-party surface). Quality: all 7 outputs produced (items 2/6/7 explicitly
  empty with reasons).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none (single feat concern). PH-02
  Size: none (58 source lines / 2 files). PH-03 Safety: none (0 migrations/schemas/
  secrets/infra). PH-04 Completeness: none (6 tests for new behaviour). No PH-03 high
  → no CR-06 auto-downgrade.

#### Run details

- **Diff source:** `git diff change/fix-use-change-id-not-handle` (local branch)
- **Neighbour expansion:** git grep / direct read (caller = cmd_recreate,
  cmd_mark_shipped; callees = read_change_record, list_all_changes,
  validate_change_ulid)
- **Neighbour cap:** 5 of 5 considered, 0 excluded
- **Scanners run:** ruff (lint), py_compile (build). Gitleaks/Trivy/Semgrep not run —
  no new third-party or secret-shaped surface in a pure local-logic diff.
- **Scanners unavailable:** pytest-cov absent (coverage verified by manual branch
  analysis — every new branch exercised by a test).
- **Single-reader pass:** yes (CR-02 carve-out — small single-module diff)
