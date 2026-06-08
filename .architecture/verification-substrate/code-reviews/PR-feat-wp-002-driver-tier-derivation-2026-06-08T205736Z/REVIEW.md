# Code Review: WP-002 — Derive driver tier (scripted|agent-step) in _scenario_runtime

> **Timestamp:** 2026-06-08T205736Z (ISO 8601 UTC)
> **Author:** executor (autonomous)
> **Branch:** feat/wp-002-driver-tier-derivation → change/feat-verification-substrate
> **Files changed:** 3
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds a small, pure helper that labels each journey step as either
`scripted` (something the runner can drive deterministically — an HTTP call or
a subprocess) or `agent-step` (something probabilistic an AI agent would drive),
deriving that label from information the system already stores rather than
saving a new copy of it. There are no build errors, the change is well-scoped
(one helper, one new field, two new tests), and the tests cover both the helper
itself and how it flows into the resolved step. No issues that need attention.

## What to fix

No issues that need attention.

## How this pull request is shaped

Small and single-purpose: 129 added lines across three files (the runtime
module, its test file, and one documentation note). One concern only — surfacing
the existing driver kind as a tier label. New behaviour ships with tests. A
leftover unused import in the test file was removed while the file was open.
Nothing about the shape of this change needs attention.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs)
> for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; every
changed file read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — ruff/mypy/compileall all rc=0.
- **PR Hygiene:** 0 findings (PH-01..PH-04 all low).
- **In the changes:** 0 findings.
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0.

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | nothing surfaced |
| Security | 0 | 0 | nothing surfaced |
| Quality | 0 | 0 | nothing surfaced |

### Build Verification (CR-01)

No PR-introduced errors. Mechanical baseline on HEAD:
`ruff check` (rc=0), `mypy _scenario_runtime.py` (rc=0),
`python3 -m compileall` (rc=0). Raw outputs in `tool-outputs/`.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → single concern
  module_fan_out: 1 top-level dir (plugins/sulis) → clean
  severity: low

Size (PH-02):
  lines_added: 129, lines_removed: 3, total: 132
  files_changed: 3
  severity: low (<=200 lines / <=5 files; single-reader carve-out)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: low

Completeness (PH-04):
  new_source_without_test: 0 (no new files; tier_for_kind covered by 2 new tests)
  api_change_without_schema: false
  severity: low
```

### Findings in the Changes

None.

**Quality lens** — Build verification clean. No JSX/template files (N/A). No
dead surface: `tier_for_kind` is consumed by `resolve_journey` + tests;
`SCRIPTED_KINDS`/`AGENT_STEP_KINDS` consumed by `tier_for_kind` + tests;
`ResolvedStep.tier` is intentionally declared-only for the named downstream
consumer WP-003 (documented in the WP rollback note + ADR-001), not orphaned.
No contract drift: the `scripted | agent-step | ""` label set matches ADR-001
exactly, and `test_tier_for_kind_maps_every_kind` asserts the mapping is total
over `IMPLEMENTATION_KINDS` (each kind in exactly one bucket) and the two tier
frozensets are disjoint. Test coverage present: 2 new tests, 96% module
coverage (the 2 uncovered lines are the pre-existing dangling-step branch, not
new surface). Style clean (descriptive names, why-comments cite ADR-001).
CR-10 performance: `tier_for_kind` is two O(1) frozenset membership checks;
`resolve_journey` calls it once per step inside its existing O(N) loop — no
N+1, no nested iteration, no unbounded materialisation. No anti-pattern matches.

**Architecture lens** — REINFORCE-Instrument primitive, scored against
WPB-01/07/12. Pure domain derivation, zero infrastructure dependencies
(stdlib only), no module-level mutable state (frozenset constants are
immutable). The ADR-001 decision — derive the tier from the already-stored
`implementation_kind` rather than persisting a second copy — is correctly
implemented (single source of truth, no drift surface). No new external
calls → no timeout/circuit-breaker/observability gap applies. WPB-12
boy-scout: an unused `import pytest` (F401) in the touched test file was
removed, bounded to scope. Additive to the existing spine: `resolve_journey`
and `driver_for_step` are extended, not rewritten. Nothing surfaced.

**Security lens** — No access-control surface, no user input, no secrets, no
injection vector, no new dependencies (stdlib only). `tier_for_kind` is a
pure string-classification function over a closed enum. Primitives checked:
SEC-01..07, SC-01..04. Nothing surfaced.

### Findings in the Neighbours

None. Direct neighbours are `driver_for_step` (called by `resolve_journey`,
unchanged in contract) and the foundation `IMPLEMENTATION_KINDS` enum (read,
not modified). No pre-existing gaps exposed by this change.

### Watch List

None.

### Cross-Reference

- **Existing Hardening Deltas covered:** none.
- **Existing security report:** none.
- **Pattern suggesting full audit:** none.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `ruff check` + `mypy _scenario_runtime.py` + `python3 -m compileall` (the project's CI lint+typecheck floor per `.github/workflows/branch-ci.yml`). HEAD: 0 errors. Coverage gap: none.
- [✓] **CR-02 Parallel dispatch.** Single-reader pass justified by diff size: 132 lines, 3 files (within the ≤200-line / ≤5-file carve-out).
- [✓] **CR-03 Full-file reads.** All 3 changed files read end-to-end via full `git diff`. Unread files: none.
- [✓] **CR-04 Evidence discipline.** Zero findings; no evidence claims to make. Mechanical-baseline outputs captured in `tool-outputs/`.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 0 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. No auto-downgrade triggers fired (Build Verification empty; all files read end-to-end; all lenses produced output; PH-03 low).
- [✓] **CR-07 Lens completion.** Architecture: 0 findings (checks: dependency direction, module-level state, additive-not-rewrite). Security: nothing surfaced (SEC-01..07, SC-01..04). Quality: 0 findings + build verification + dead-surface + contract-drift + test-coverage + CR-10 performance all run.
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: low (single concern). PH-02 Size: low (132 lines / 3 files). PH-03 Safety: low (0 migrations/schemas/secrets/infra). PH-04 Completeness: low (new behaviour covered by 2 tests). No PH-03 high → no CR-06 auto-downgrade.

#### Run details

- **Diff source:** `git diff change/feat-verification-substrate...feat/wp-002-driver-tier-derivation` (working-tree, pre-commit).
- **Neighbour expansion:** git grep on `tier_for_kind` / `ResolvedStep` / `_scenario_runtime`.
- **Neighbour cap:** 2 of 2 considered, 0 excluded.
- **Scanners run:** ruff, mypy, compileall.
- **Scanners unavailable:** Gitleaks/Semgrep/Trivy not in this environment — security lens performed by manual primitive review of the diff (no secrets/input/deps surface present).
- **Lenses dispatched in parallel:** no (single-reader carve-out justified by size).
