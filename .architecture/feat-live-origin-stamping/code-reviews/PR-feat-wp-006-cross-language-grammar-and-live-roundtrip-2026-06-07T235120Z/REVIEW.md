# Code Review: WP-006 — Cross-language grammar conformance + live round-trip runbook

> **Timestamp:** 2026-06-07T235120Z (ISO 8601 UTC)
> **Author:** executor (WP-006)
> **Branch:** feat/wp-006-cross-language-grammar-and-live-roundtrip → change/feat-live-origin-stamping
> **Files changed:** 2 reviewable (1 Python test, 1 markdown runbook); 1 bookkeeping journal excluded
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds one Python test and one runbook. The test locks the cross-language
seam: it proves the exact `SULIS_ORIGIN` strings the cockpit (TypeScript) side emits
are parsed back correctly by the Python commit hook, so the two languages cannot
silently drift apart. The runbook is a step-by-step checklist for the founder to
verify the real "likely → exact" flip on their own machine (which can't be tested in
CI). No production code changes, no build errors, and the test strengthens an existing
security guard rather than weakening it. There is nothing that needs attention.

## What to fix

No issues that need attention.

## How this pull request is shaped

Well-scoped and small. Two files, a single concern (verify the cross-language seam +
prepare the live-verification runbook). One commit type (`test:`). No migrations, no
schema changes, no infrastructure, no secrets. The change is a test plus its
companion runbook — exactly the shape expected for a "prove it works end-to-end" work
package.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs) for
> engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; both
reviewable files read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (CR-09 / PH-01..PH-04)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | — (test-only; no new ports/adapters/calls) |
| Security | 0 | 0 | — (test re-asserts #216 trailer-injection guard) |
| Quality | 0 | 0 | — (all imports used; test is the coverage) |

### Build Verification (CR-01)

`ruff check`: All checks passed (`tool-outputs/ruff-check-head.log`).
`ruff format --check`: already formatted (`tool-outputs/ruff-format-head.log`).
`pytest`: 14 passed (`tool-outputs/pytest-head.log`).
No type checker applies (plain pytest module; sys.path set by conftest). No
PR-introduced errors.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {test}                   → clean
  module_fan_out: 2 (plugins/sulis/scripts/tests, .architecture)  → clean
  severity: none
Size (PH-02):
  lines_added: ~177 (test) + ~150 (runbook)
  files_changed: 2 reviewable
  severity: none (<200-line band per file; ≤5 files)
Safety (PH-03):
  migration_count: 0; schema_idl_count: 0; infra_files: 0; secret_pattern_hits: 0
  severity: none
Completeness (PH-04):
  new_source_without_test: 0 (the new source IS a test)
  api_change_without_schema: false
  severity: none
```

### Findings in the Changes

None.

### Findings in the Neighbours

None. Neighbour ring: `_origin_stamp.py` (the parser under test — unchanged by this
WP), `test_executor_autonomous_origin.py`, `relayOrigin.ts` (the TS producer the
fixtures mirror). The conformance test deliberately couples to these by asserting
their grammar — that coupling is the WP's purpose, not a gap.

### Watch List

None.

### Cross-Reference

- No prior security report for this change under `.security/`.
- No existing hardening deltas to cite.
- Neighbour patterns suggesting a broader audit: none.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `ruff check` + `ruff format --check` + `pytest` on HEAD. Base: clean. Head: clean (0 new errors). Coverage gap: no type checker for plain pytest module (sys.path via conftest) — recorded, not skipped silently.
- [✓] **CR-02 Single-reader pass justified by diff size: 177 lines (test) + ~150 (runbook), 2 reviewable files — within the ≤200-line AND ≤5-file carve-out.**
- [✓] **CR-03 Full-file reads.** Both reviewable files read end-to-end (test_assisted_grammar_conformance.py 177 lines; LIVE_VERIFICATION.md in full). Unread: none.
- [✓] **CR-04 Evidence discipline.** No findings to evidence; tool outputs captured under `tool-outputs/`.
- [✓] **CR-05 Severity rubric.** Applied; 0 findings at every severity.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired (Build Verification empty; all files read; all lenses produced output; no PH-03 high).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (no new ports/adapters/imports/external calls; the change is a Proof-primitive contract test). Security: nothing surfaced (test re-asserts #216 control-char/trailer-injection guard; no secrets; ULID is a test constant; no PII logging). Quality: Build Verification clean; JSX scan N/A (no TSX/JSX); dead-surface none (all 3 imports used — pytest x1, autonomous_env x4, parse_origin_env x15); contract-drift none (test-only, pins the existing grammar); test-coverage — the change IS the test; style clean (no TODO/FIXME); CR-10 performance — no loops with DB/RPC/FS calls (the only for/while tokens are in comments).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none. PH-02 Size: none. PH-03 Safety: none (0 migrations, 0 schemas, 0 secrets, 0 infra). PH-04 Completeness: none. PH-03 high → CR-06 auto-downgrade: no.

#### Run details

- **Diff source:** local working tree vs `change/feat-live-origin-stamping` (uncommitted; commit is the executor's next step).
- **Neighbour expansion:** git grep (ast-grep not required at this size).
- **Neighbour cap:** 3 of 3 considered, 0 excluded.
- **Scanners run:** ruff (lint + format), pytest. Gitleaks/Semgrep/Trivy not run — no new external surface, secrets, or dependencies; security lens scoped to the diff's re-assertion of the existing #216 boundary guard.
- **Lenses dispatched in parallel:** no — single-reader pass per CR-02 carve-out (diff within threshold).
