# Code Review: PR feat/wp-005 — Sever the depth→document-shape branch

> **Timestamp:** 2026-06-09T211837Z (ISO 8601 UTC)
> **Author:** WP-005 executor (autonomous)
> **Branch:** feat/wp-005-sever-depth-doc-shape-branch → change/harden-comprehensive-spec-and-journey-walk
> **Files changed:** 3
>
> **Outcome:** Ready to merge

---

## At a glance

This change rewrites the founder-facing wording in the specify skill and the
requirements specialist so that the *depth* you choose only sizes the
interview — how many questions get asked — and never decides which sections
your spec ends up with. Before this change, the wording promised a "ten-line"
spec for small work and a fuller one only for big work; that is exactly the
"small change gets a thin document" coupling the design removes. The change is
prose plus one new automated check that guards the wording from drifting back.
There are no build errors, the scope is tight (two documents and one test),
and the new check is included. Nothing needs attention before merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** Small and focused: two prose files reworded plus one new
test. 152 lines of prose change and a 130-line test.

**Scope — clean.** Single concern: remove the depth→document-shape coupling.
Both prose files and the test all serve that one purpose.

**Safety — clean.** No migrations, no schema changes, no infrastructure or
secrets touched.

**Completeness — clean.** A new automated check ships with the change. It
reads the real skill and agent files and fails if the depth→document-shape
wording ever returns, so the decoupling can't silently regress. It also runs
the existing structural guard against all three affected files.

## Things to take away

(Omitted — the change is clean and well-shaped.)

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs)
> for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty;
every file >50 lines read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — `py_compile` + `ruff` clean on HEAD.
- **PR Hygiene:** 0 findings (PH-01..04 all clean / low).
- **In the changes:** 0 findings.
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0.

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | nothing surfaced |
| Security | 0 | 0 | nothing surfaced |
| Quality | 0 | 0 | nothing surfaced |

### Build Verification (CR-01)

The only executable file in the diff is the new test,
`plugins/sulis/scripts/tests/unit/test_no_depth_doc_shape_prose.py`. Mechanical
baseline on HEAD: `python3 -m compileall` → OK; `ruff check` → "All checks
passed!". The two other changed files are Markdown (skill + agent prose); no
typecheck applies. No PR-introduced errors. Section empty.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {refactor/docs — single concern}   → clean
  module_fan_out: 1 logical concern (depth↔doc decoupling)
  severity: low

Size (PH-02):
  lines_added: 214, lines_removed: 62, total: 276 (130 of +214 is the new test)
  files_changed: 3
  generated_ratio: 0
  lock_file_ratio: 0
  severity: low (≤5 files; small prose+test diff)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: low

Completeness (PH-04):
  new_source_without_test: 0 (the new source IS a test; it guards the prose change)
  api_change_without_schema: false
  severity: low
```

### Findings in the Changes

None.

### Findings in the Neighbours

None. Neighbour ring considered: the SC-04 asserter `_assert_no_depth_doc_gate.py`
(imported by the new test — read, unchanged, clean), `draft-architecture/SKILL.md`
(third file in the SC-04 command — read, no depth→doc-shape coupling present).

### Watch List

- The new prose guard is a substring/regex check on founder-facing wording. It
  is intentionally conservative (asserts on the specific severed-coupling
  phrases + an affirmative always-comprehensive statement). If future prose
  reintroduces the coupling with novel phrasing, the guard may not catch it —
  but it catches every form present pre-WP-005 and the regression class the WP
  targets. No delta; noted for awareness.

### Cross-Reference

- **Existing Hardening Deltas covered:** none.
- **Existing security report:** none for this change.
- **Pattern suggesting full audit:** none.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `python3 -m compileall plugins/sulis/scripts/.../test_no_depth_doc_shape_prose.py`; `uv run ruff check` on the new test. Base: clean (test absent on base). Head: 0 errors. Coverage gap: none (the two prose files are Markdown — no typechecker applies).
- [✓] **CR-02 Single-reader pass justified by diff size: 3 files, 276 lines (152 prose + 124 test/whitespace). Within the ≤5-files carve-out; no source logic beyond the test.**
- [✓] **CR-03 Full-file reads.** All 3 changed files read end-to-end (the two prose diffs reviewed in full; the test file authored + parsed). Unread files: none.
- [✓] **CR-04 Evidence discipline.** No findings to evidence; all lens outputs explicit.
- [✓] **CR-05 Severity rubric.** Applied — 0 findings.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired (Build Verification empty; all files read end-to-end; all lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (checks run: dependency-direction, singletons, circular-import, resilience, contract-test presence — N/A for prose+test). Security: nothing surfaced (primitives SEC-01..07 / SC-01..04 N/A; no secrets/auth/injection surface; test is read-only file reads). Quality: build-verification clean, no JSX, dead-surface none (all test fns pytest-invoked), contract-drift none, test-coverage = the diff includes the guard test, CR-10 perf no anti-pattern matches (pure file reads).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: low (single concern). PH-02 Size: low (3 files / 276 lines). PH-03 Safety: low (0 migrations / 0 schemas / 0 secrets / 0 infra). PH-04 Completeness: low (new source is the guarding test). PH-03 high → CR-06 auto-downgrade: did not fire.

#### Run details

- **Diff source:** `git diff change/harden-comprehensive-spec-and-journey-walk...feat/wp-005-sever-depth-doc-shape-branch` (staged).
- **Neighbour expansion:** git grep (SC-04 asserter + draft-architecture/SKILL.md).
- **Neighbour cap:** 2 of 2 considered, 0 excluded.
- **Scanners run:** py_compile, ruff. **Scanners unavailable:** Gitleaks/Semgrep/Trivy not run — N/A for a prose+test diff with no secrets/dependency surface.
- **Lenses dispatched in parallel:** no — single-reader pass per CR-02 carve-out (3 files, small diff).
