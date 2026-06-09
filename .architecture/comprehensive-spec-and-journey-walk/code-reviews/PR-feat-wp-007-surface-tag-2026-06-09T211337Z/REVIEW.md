# Code Review: feat/wp-007-surface-tag — Add a first-class surface tag to scenario authoring

> **Timestamp:** 2026-06-09T211337Z (ISO 8601 UTC)
> **Author:** WP-007 executor
> **Branch:** feat/wp-007-surface-tag → change/harden-comprehensive-spec-and-journey-walk
> **Files changed:** 3 (89 insertions)
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds an optional `surface` label (either "ui" or "tool") to the
scenario authoring function, so a verification journey can record which kind
of surface it exercises. It is a small, well-scoped change — 89 added lines
across the function, its schema, and four new tests. There are no build
errors, the label defaults safely to the existing behaviour, and the new
tests cover every path. Nothing needs fixing before merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

Well-shaped. The change does one thing — adds the surface label — and adds
tests for it in the same change. Size and scope are both comfortably small.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high/medium/low in the diff; Build Verification
empty; the only source file >50 lines (`_scenario_authoring.py`) read
end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 high, 0 medium, 0 note (CR-09 / PH-01..PH-04)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | nothing surfaced |
| Security | 0 | 0 | nothing surfaced |
| Quality | 0 | 0 | nothing surfaced |

### Build Verification (CR-01)

`uv run ruff check` (configured linter, from `plugins/sulis/scripts`): All
checks passed. `python3 -m compileall -q _scenario_authoring.py`: OK. Full
unit suite (`uv run pytest tests/unit/`): 2431 passed, 9 skipped. No
type-checker configured for this repo (stdlib-only plugin contract) — coverage
gap recorded, no mypy/pyright to run. Base had no errors; head has no errors.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → clean (single concern)
  module_fan_out: 1 top-level dir (plugins)    → clean
  severity: none

Size (PH-02):
  lines_added: 89, lines_removed: 0, total: 89
  files_changed: 3
  severity: none (≤200 line / ≤5 file band)

Safety (PH-03):
  migration_count: 0 (schema change is additive-optional, no data rewrite)
  schema_idl_count: 1 (scenario.schema.json — additive enum property)
  infra_files: 0
  secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0 (4 new tests added with the change)
  api_change_without_schema: false (schema updated in lockstep)
  severity: none
```

### Findings in the Changes

None.

### Findings in the Neighbours

None. Neighbour ring: `_scenario_runner.py`, `_scenario_brief.py`,
`_entity_adapter_local.py` (the schema-validating adapter). The `surface`
field is additive-optional; absent reads as `ui`, so no existing caller or
stored scenario is affected. The adapter validates against the updated schema;
the new enum property is opt-in.

### Watch List

None.

### Cross-Reference

- **Existing Hardening Deltas covered:** none
- **Existing security report:** none
- **Pattern suggesting full audit:** none. The schema edit mirrors the
  WP-001 (verification-substrate) precedent that added `isolation` +
  `verdict_invariant` additively to the same schema.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `uv run ruff check`
  (configured linter), `python3 -m compileall`, full `pytest tests/unit/`.
  Base: 0 errors. Head: 0 errors. Coverage gap: no type-checker configured
  (stdlib-only plugin contract) — recorded, not skipped silently.
- [✓] **CR-02 Single-reader pass justified by diff size: 89 lines, 3 files**
  (within the ≤200-line / ≤5-file carve-out).
- [✓] **CR-03 Full-file reads.** `_scenario_authoring.py` (the only source
  file >50 lines touched) read end-to-end; schema + test diffs read in full.
  Unread files: none.
- [✓] **CR-04 Evidence discipline.** No findings to evidence; diff quoted in
  full during review.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 0 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none
  fired (Build Verification empty; all files read; all lenses produced output;
  PH-03 not high).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (checked:
  cross-layer imports, singletons, circular imports, timeouts/CB/secrets on
  new calls — none present; change is a pure-function signature extension).
  Security: nothing surfaced (primitives checked SEC-01..07 — no auth surface,
  no injection vector, no secrets; `surface` is allowlist-validated before
  persistence; no dependency change). Quality: all 7 outputs produced —
  (1) build verification clean; (2) JSX scan N/A (no TSX/JSX/Vue/Svelte);
  (3) no dead surface (`_SURFACES` + param both consumed); (4) no contract
  drift (schema enum `{ui,tool}` == runtime `_SURFACES` == default `ui`);
  (5) test coverage present (4 new tests); (6) style clean; (7) CR-10 no
  anti-pattern matches (no loops/DB/RPC/FS/materialisation in the diff).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none (single `feat`,
  1 dir). PH-02 Size: none (89 lines / 3 files). PH-03 Safety: none
  (0 migrations; 1 additive-optional schema enum; 0 secrets; 0 infra).
  PH-04 Completeness: none (4 tests added with the change). PH-03 high →
  CR-06 auto-downgrade fired: no.

#### Run details

- **Diff source:** `git diff change/harden-comprehensive-spec-and-journey-walk`
- **Neighbour expansion:** git grep on `assemble_scenario_graph` + `surface`
- **Neighbour cap:** 3 of 3 considered, 0 excluded
- **Scanners run:** ruff (configured linter), compileall, pytest
- **Scanners unavailable:** mypy/pyright (none configured); gitleaks/semgrep/
  trivy not invoked — diff has no secret/dependency/infra surface
- **Lenses dispatched in parallel:** no — single-reader pass per CR-02
  carve-out (89 lines / 3 files)
