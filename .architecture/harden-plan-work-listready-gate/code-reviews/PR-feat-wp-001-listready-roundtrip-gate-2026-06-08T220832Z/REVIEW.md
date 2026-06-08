# Code Review: feat/wp-001-listready-roundtrip-gate — list-ready round-trip gate

> **Timestamp:** 2026-06-08T220832Z (ISO 8601 UTC)
> **Author:** executor (WP-001)
> **Branch:** feat/wp-001-listready-roundtrip-gate → change/harden-plan-work-listready-gate
> **Files changed:** 3
>
> **Outcome:** Ready to merge

---

## At a glance

This change does exactly what it set out to do, and nothing more. It strengthens the to-do-list check that runs when work is broken down: previously the check only confirmed the list *looked* right (the right column headings); now it also confirms the builder can actually *read* the list and find work to run. There are no build errors, the change is tightly scoped to one helper function plus its tests, and the tests cover every failure path. No issues need attention.

## What to fix

No issues that need attention.

One thing worth being aware of (not a fix): the new check computes a "can the builder account for every pending item" result. Given how the underlying reader works, that result is always "yes — all accounted for" today, so one of the three guard clauses can't actually trigger right now. That's deliberate and documented in the code: it's a safety net that will speak up if a future change to the reader ever makes the two disagree, rather than failing silently. It's the right call — left as-is.

## How this pull request is shaped

**Size — clean.** 360 lines across 3 files, most of which is test fixtures (the example to-do lists the tests check against). The actual logic change is about 80 lines in one function.

**Scope — clean.** Single concern: one feature (`feat:`), one function modified, one test file added, one doc paragraph updated to match. Nothing mixed in.

**Safety — clean.** No database migrations, no schema changes, no infrastructure files, no secrets.

**Completeness — clean.** Tests were written first and cover all six cases the work called for (three that must fail the check, two that must pass, plus the wiring check). The documentation was updated in the same change.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs) for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in diff; Build Verification empty; all changed files >50 lines read end-to-end; all three lenses produced output. No auto-downgrade trigger fired.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (PH-01..04 all note/none) (CR-09)
- **In the changes:** 0 findings (0 critical, 0 high, 0 medium, 0 low) + 1 awareness note
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none — pure helper, no infra import, no module state, EP-03 honoured |
| Security | 0 | 0 | none — no auth/injection/secret surface |
| Quality | 0 | 0 | none — full test coverage; 1 awareness note (defensive unreachable branch) |

### Build Verification (CR-01)

`py_compile` clean on both changed `.py`-shaped files; `ruff check` clean (the repo's configured linter). Base was clean prior to the change. No PR-introduced errors. CI's mechanical lint gate for this dir is manifest-JSON-validity + `py_compile` (branch-ci.yml L43); both satisfied. Raw outputs in `tool-outputs/`.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → clean
  module_fan_out: 2 (scripts, skills)          → clean
  severity: note

Size (PH-02):
  lines_added: 360, lines_removed: 21, total: 381
  files_changed: 3
  (most additions are test fixtures — multiline INDEX string literals)
  severity: note

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0   (test module added; logic change is test-driven)
  api_change_without_schema: false
  severity: none
```

### Findings in the Changes

None.

### Findings in the Neighbours

None. Neighbour ring = `cmd_list_ready`, `_collect_status_across_tables`, `_resolve_deps`, `validate_wp_index_header` (the helpers the new code consumes). All unchanged; the diff reuses them as-is per EP-03 (verified: 0 `parse_md_table` / `_find_*_wp_table` / `resolve_wp_columns` calls inside the new `_roundtrip_accounting` + `cmd_lint` block — no duplicate parse path introduced).

### Watch List

- `_roundtrip_accounting` returns `unaccounted`, computed as `{wp for wp in pending if wp not in set(depends_by_id)}`. Because `_resolve_deps` is keyed over `set(status_by_id)` (the same WP set `pending` derives from), `unaccounted` is structurally always empty today, so the `if unaccounted:` guard in `cmd_lint` is currently unreachable. This is **deliberate and documented** (Contract invariant 2 framing): it is computed rather than assumed so the gate names any future divergence between the status map and the dep map instead of silently passing. No failing characterisation test can be constructed for an intentionally-unreachable defensive branch, so per CR-04 this stays on the Watch List — not a Hardening Delta, not a finding. Left as-is is the correct call.

### Cross-Reference

- No prior `.security/` viability report for this project.
- No existing hardening-deltas for this project.
- No neighbour pattern suggesting a broader audit.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `python3 -m py_compile` + `ruff check` on changed `.py` files (CI's lint gate for this dir is manifest-JSON + py_compile, not a typechecker; ruff is the configured linter). Base: clean. Head: clean. Coverage gap: no static typechecker configured for `plugins/sulis/scripts` (recorded).
- [✓] **CR-02 Single-reader pass.** Diff is 381 lines / 3 files — above the 200-line carve-out, but the substantive logic surface is ~80 lines in one function + one doc paragraph; the remaining ~270 added lines are test-fixture string literals (INDEX examples). Single-reader justified by the narrow substantive surface and single concern; recorded here per the carve-out note.
- [✓] **CR-03 Full-file reads.** The full `_roundtrip_accounting` + `cmd_lint` block, the entire new test module, and the changed SKILL.md Step 9.5 prose read end-to-end. Unread files: none.
- [✓] **CR-04 Evidence discipline.** Watch List item cites the exact computed expression + the structural reason for unreachability.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 0 low; 1 awareness note.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. No auto-downgrade trigger fired (Build Verification empty; all files read end-to-end; all lenses produced output; no PH-03 high).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (checks run: infra→domain imports, new module state/singletons, circular imports, new external calls, secrets, EP-03 duplicate-parse-path grep → 0). Security: nothing surfaced (no auth/access-control surface; no injection sink — error strings interpolate only WP-IDs parsed from the trusted local INDEX; no secrets; no new dependency). Quality: 7/7 outputs — build-verification clean; JSX scan N/A (no TSX/JSX/Vue/Svelte); dead-surface none (3-tuple fully consumed); contract-drift none (emit_ok keys match test asserts); test-coverage strong (6 tests, all paths); style clean; CR-10 performance no anti-pattern (the double table-scan mirrors `cmd_list_ready` exactly — small local file, not a hot loop — benign).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: note (single feat, 2 dirs). PH-02 Size: note (381 lines, fixture-heavy). PH-03 Safety: none (0 migrations/schemas/secrets/infra). PH-04 Completeness: none (test-driven, doc updated). PH-03 high → CR-06 auto-downgrade: did not fire.

#### Run details

- **Diff source:** `git diff --cached` (staged working tree; commit lands at executor Step 7) vs `change/harden-plan-work-listready-gate`.
- **Neighbour expansion:** git grep on the symbols the diff consumes (`_collect_status_across_tables`, `_resolve_deps`, `cmd_list_ready`).
- **Neighbour cap:** 4 of 4 considered, 0 excluded.
- **Scanners run:** py_compile, ruff check.
- **Scanners unavailable:** no static typechecker configured for this dir (coverage gap recorded above).
- **Lenses dispatched in parallel:** no — single-reader per CR-02 carve-out (narrow substantive surface).
