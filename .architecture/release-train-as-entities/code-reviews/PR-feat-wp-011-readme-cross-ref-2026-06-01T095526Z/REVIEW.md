# Code Review: feat/wp-011-readme-cross-ref — Cross-reference Configuration Vocabulary from marketplace plugin README

> **Timestamp:** 2026-06-01T095526Z (ISO 8601 UTC)
> **Author:** WP-011 executor
> **Branch:** feat/wp-011-readme-cross-ref → change/create-release-train-as-entities
> **Files changed:** 2 (`plugins/sulis/README.md`, new `plugins/sulis/scripts/tests/unit/test_release_train_readme_section.py`)
>
> **Outcome:** Ready to merge

---

## At a glance

Your pull request looks good. It adds a small, well-scoped documentation section to the marketplace plugin's README pointing fork-consumers at the SRD's Configuration Vocabulary section, and pairs it with a structural test that verifies the section is present and the cross-reference link resolves. No build errors, full test suite green, no issues that need attention.

## What to fix

No issues that need attention.

## How this pull request is shaped

Clean across all four hygiene checks — single concern (docs addition with its verification test), small (26 lines added to one file, plus a 153-line test file), no operational risk surface, and the new file IS the test that proves the docs deliverable works.

## Things to take away

Section omitted — the work-package is well-shaped and clean, and there is nothing specific to take away from this PR.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs) for engineers and for downstream agents like `/sulis:harden-codebase`.

### Verdict

`PASS` per CR-06. No critical/high in diff; Build Verification empty; all changed files >50 lines read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings — all four primitives `note` severity (CR-09 / PH-01..PH-04)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | nothing surfaced |
| Security | 0 | 0 | nothing surfaced |
| Quality | 0 | 0 | nothing surfaced |

### Build Verification (CR-01)

`py_compile plugins/sulis/scripts/tests/unit/test_release_train_readme_section.py` → exit 0, no output.

`pytest plugins/sulis/scripts/tests/unit/test_release_train_readme_section.py` → 5 passed in 0.04s.

Full unit suite at HEAD: 1189 passed, 0 failed.

No project-wide ruff/mypy/black config detected in `plugins/sulis/scripts/pyproject.toml`; the only mechanical checks available are py_compile + pytest, both ran clean.

Coverage gap: ruff/mypy not configured at project root, so static-type and style checks beyond stdlib syntax validation were not run. Mitigation: the new test file uses only stdlib + pytest (no third-party imports beyond pytest itself) and mirrors the established `test_agents_dir_has_no_stray_reports.py` pattern.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {docs}                   → single primitive
  module_fan_out: 2 (plugins/sulis/README.md + plugins/sulis/scripts/tests/unit/)
  severity: note

Size (PH-02):
  lines_added: 26 (README) + 153 (new test file)
  files_changed: 1 modified, 1 added
  generated_ratio: 0.00
  lock_file_ratio: 0.00
  severity: note (well within 200-line / 5-file CR-02 carve-out)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: note

Completeness (PH-04):
  new_source_without_test: 0
  api_change_without_schema: false
  severity: note (the new test file IS the docs-prose verification — WP-011 DoD has no runtime tests by design)
```

### Findings in the Changes

None.

#### Architecture lens

Architecture lens: nothing surfaced. Checks run: no new imports added; no new modules; no module-level singletons; no new HTTP/RPC/DB calls (docs + structural test); no new external surface; no observability gaps (no runtime paths); no contract changes; no new ports.

#### Security lens

Security lens: nothing surfaced. Primitives checked: SEC-01..07, SC-01..04, INF-04. No new code-execution surface; no auth boundary touched; no secret patterns; no dependency changes; no Dockerfile / CI changes; no logging surface change; the diff is markdown prose + a stdlib-only structural test.

#### Quality lens

1. **Build Verification follow-up.** None — CR-01 surfaced no errors.
2. **JSX / template identifier scan.** N/A — no TSX/JSX/Vue/Svelte files in diff.
3. **Dead-surface findings.** None — every function in the new test file is invoked by pytest's collection.
4. **Contract-drift findings.** None — the test contract matches the WP DoD verbatim (section heading + cross-ref link + worked examples + future discovery sibling).
5. **Test-coverage observation.** The diff IS its own test. The README addition has a structural test (`test_release_train_readme_section.py`) that asserts all four WP DoD invariants. New source files: 1 (the test itself); new test files: 1 (same file). No source-only files added.
6. **Style / readability.** Test file follows the established `test_agents_dir_has_no_stray_reports.py` pattern (stdlib + pytest, module-level path constants, fixture for shared file read, one assertion per invariant). README section uses the surrounding voice (plain English, table-and-prose mix, fenced anchor links).
7. **Performance procedural checks (CR-10).** N/A — no loops, no DB calls, no I/O hot paths. The test file performs one file read per pytest module run (cached via the `module`-scoped fixture).

### Findings in the Neighbours

None. Neighbour ring scoped to: the SRD at `.specifications/release-train-as-entities/SRD.md` (cross-reference target — verified to contain the `## Configuration Vocabulary` heading the link anchors to); the existing `plugins/sulis/README.md` content (unmodified outside the inserted section, surrounding tone preserved); existing test conventions at `plugins/sulis/scripts/tests/unit/` (pattern matched). No pre-existing gaps the PR exposes.

### Watch List

None.

### Cross-Reference

- **Existing Hardening Deltas covered:** none applicable
- **Existing security report:** none
- **Pattern suggesting full audit:** none

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `py_compile` on the new test file (exit 0); `pytest` on the new test file (5 passed); `pytest` on full unit suite (1189 passed). Coverage gap: no project-wide ruff/mypy configured — recorded above.
- [✓] **CR-02 Parallel dispatch carve-out.** Single-reader pass justified by diff size: 26 lines (README) + 153 lines (new test) across 2 files. Within the 200-line / 5-file carve-out threshold.
- [✓] **CR-03 Full-file reads.** Both changed files read end-to-end: `plugins/sulis/README.md` (93 lines after change), `plugins/sulis/scripts/tests/unit/test_release_train_readme_section.py` (153 lines). Unread files: none.
- [✓] **CR-04 Evidence discipline.** No findings produced; nothing to evidence. Lens completion entries cite checks-run + scan-scope so absence is not silence.
- [✓] **CR-05 Severity rubric.** No findings produced; rubric not exercised on lens output. Hygiene severities scored: PH-01 `note`, PH-02 `note`, PH-03 `note`, PH-04 `note`.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired.
- [✓] **CR-07 Lens completion.** Architecture: explicit "nothing surfaced" + checks-run list. Security: explicit "nothing surfaced" + primitives checked. Quality: all 7 outputs produced (build-verification follow-up = none, JSX scan = N/A, dead-surface = none, contract-drift = none, test-coverage = the diff IS its own test, style = follows established pattern, performance CR-10 = N/A).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: note (single `docs` primitive). PH-02 Size: note (26 + 153 lines across 2 files). PH-03 Safety: note (0 migrations, 0 schemas, 0 secrets, 0 infra). PH-04 Completeness: note (the new file IS the test for the docs change). No PH-03 high → no CR-06 auto-downgrade fired.

#### Run details

- **Diff source:** working-tree diff against HEAD (no commit yet at review time — pre-Step-7 review per executor lifecycle)
- **Neighbour expansion:** manual scan of SRD target + README surrounding text + test-pattern reference
- **Neighbour cap:** 3 files considered, 0 excluded
- **Scanners run:** py_compile, pytest
- **Scanners unavailable:** ruff, mypy, gitleaks, semgrep, trivy (none configured in this WP's scope)
- **Lenses dispatched in parallel:** no — single-reader pass justified by CR-02 carve-out (diff <200 lines / <5 files)
