# Code Review: feat/wp-005-cli-step-arg — Migrate sulis-emit-lifecyclerun CLI to --step (deprecate --step-name)

> **Timestamp:** 2026-06-03T153643Z (ISO 8601 UTC)
> **Author:** executor (WP-005)
> **Branch:** feat/wp-005-cli-step-arg → change/feat-product-project-opportunity-evolution
> **Files changed:** 2 (1 code, 1 new test)
>
> **Outcome:** Ready to merge

---

## At a glance

This change finishes a flag migration on the lifecycle-event emitter tool. The
main `--step` option now accepts either a friendly name (like `change-started`)
or a full identifier, and the old `--step-name` option is kept around as a
clearly-labelled deprecated alias that prints a heads-up when used. The change
is small, well-scoped, reuses the existing name-resolution logic rather than
copying it, and ships with five new tests covering every path. No build errors,
nothing to fix.

## What to fix

No issues that need attention.

## How this pull request is shaped

Small and single-purpose: 74 lines across two files (the tool plus its new test
file), one `feat:` concern, no database migrations, no infrastructure files, no
secrets. New behaviour ships with tests. This is the shape a change should have.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high/medium in the diff; Build Verification empty;
the one changed file >50 lines read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings — all primitives clean (CR-09 / PH-01..PH-04)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none — shared `_resolve_step` reused, no map copy |
| Security | 0 | 0 | none — values regex-validated / closed-map resolved |
| Quality | 0 | 0 | none — ruff clean, 5 tests, no perf anti-patterns |

### Build Verification (CR-01)

Configured linter `ruff check` run on both changed files at HEAD: **All checks
passed!** (exit 0). Both files `ast.parse` clean. No PR-introduced errors.
Raw output in `tool-outputs/ruff-check-head.log`.

(`ruff format` is not part of this repo's gate — it flags pre-existing sibling
CLIs too, there is no `[tool.ruff]` config, and the CI gate for
`plugins/sulis/scripts/` is `uv run pytest tests/` only. Formatting matched to
sibling-CLI style per CP-01.)

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):        commit_type_spread: {feat}; module_fan_out: 1 dir   → clean
Size (PH-02):         +66 / -8, total 74; files_changed: 2               → clean
Safety (PH-03):       migrations: 0; schema/idl: 0; infra: 0; secrets: 0 → clean
Completeness (PH-04): new_source_without_test: 0; new_tests: 1           → clean
```

### Findings in the Changes

None.

### Findings in the Neighbours

None. Neighbours examined: `_brain_emit_helper.py` (`_resolve_step`,
`_NAME_TO_STEP_ULID`), `_lifecyclerun_emission.py` (`_STEP_ID_RE`,
`compose_lifecyclerun`, `emit_lifecyclerun`). The diff consumes these
unchanged; no new gap exposed.

### Watch List

- **`--run-id` precedence over the deprecated alias's carried string** (note,
  not a finding). When `--step-name X` is passed together with an explicit
  `--run-id Y`, the explicit `--run-id` wins and `X` is not carried into
  `run_id`. This is intentional and documented (module docstring + inline
  comment at lines 129-132). No action.

### Cross-Reference

- No prior `.security/{project}/` viability report to cite.
- No existing hardening deltas to cite.
- No neighbour pattern suggesting a broader audit.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `ruff check` (the configured linter) on both changed files; base 0 / head 0 errors; no coverage gap (Python; ruff is the project's lint tool).
- [✓] **CR-02 Single-reader pass justified by diff size: 74 lines, 2 files** (≤200 lines AND ≤5 files).
- [✓] **CR-03 Full-file reads.** The one changed file >50 lines (`sulis-emit-lifecyclerun`, 168 lines) read end-to-end. Test file (191 lines) read end-to-end. Unread files: none.
- [✓] **CR-04 Evidence discipline.** All observations cite file:line.
- [✓] **CR-05 Severity rubric applied.** 0 critical, 0 high, 0 medium, 0 low.
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade triggers fired (Build Verification empty; all files read end-to-end; all lenses produced output; no PH-03 high).
- [✓] **CR-07 Lens completion.** Architecture: 0 findings (reuse-first, dependency-direction, no-new-external-call checks run). Security: 0 findings (injection/auth/SSRF/secrets checks run; values regex-validated/closed-map). Quality: 0 findings (build-verification, dead-surface, contract-drift, test-coverage, style, CR-10 perf all run; no anti-pattern matches).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: clean. PH-02 Size: clean (74 lines / 2 files). PH-03 Safety: clean (0 migrations / 0 schemas / 0 secrets / 0 infra). PH-04 Completeness: clean (1 new test for the new behaviour). No PH-03 high → no CR-06 auto-downgrade.

#### Run details

- **Diff source:** working tree vs `change/feat-product-project-opportunity-evolution` (pre-commit review)
- **Neighbour expansion:** git grep on the two imported helper modules
- **Neighbour cap:** 2 of 2 considered; cap not reached
- **Scanners run:** ruff (lint); manual secret-pattern + CR-10 perf grep
- **Scanners unavailable:** Gitleaks/Semgrep/Trivy not installed — manual secret-pattern grep run as substitute (coverage gap noted; diff has no dependency/Docker/secret surface)
- **Lenses dispatched in parallel:** no — single-reader pass per CR-02 carve-out
