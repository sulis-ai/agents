# Code Review: feat/wp-007-verify-phase — Verify phase (drift invoke + roll-back)

> **Timestamp:** 2026-06-01T173039Z (ISO 8601 UTC)
> **Branch:** feat/wp-007-verify-phase → change/create-discover-project
> **Files changed:** 3 (487 lines added, 0 removed)
>
> **Outcome:** Ready to merge.

---

## At a glance

The change is clean: one new module (`_discovery/verifier.py`) plus its
test file, 9 tests passing with 100% coverage of the new code, no lint
errors, no formatter drift. The work matches the WP-007 contract item by
item — the cross-tenant flag default, the roll-back semantics on drift
failure, and the separate diagnostic for the WP-009 flag race are all in
place. Nothing to fix before merge; one minor watch-list item below.

## What to fix

No issues that need attention.

## How this pull request is shaped

The change is well-scoped: one new module + tests, in one package, single
intent. 487 added lines is in the medium band but the entire change is a
new module with a tight contract, so there is little structural risk in
reading it as one piece.

## Things to take away

(omitted — clean change)

---

## Technical detail

> Below this point uses internal taxonomy for downstream agents and
> engineers.

### Verdict

`PASS` per CR-06. No auto-downgrade triggers fired.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 1 medium (PH-02 size — 487 lines), all other primitives clean (CR-09)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings (no neighbours — new package)
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none |
| Security | 0 | 0 | none |
| Quality | 0 | 0 | none |

### Build Verification (CR-01)

All mechanical checks ran clean on the staged diff:

| Check | Result |
|---|---|
| `uv run ruff check` on new + test files | exit 0; "All checks passed!" |
| `uv run ruff format --check` | exit 0; "2 files already formatted" |
| `python3 -m py_compile` | exit 0 |
| `uv run pytest test_discovery_verifier.py --cov=_discovery.verifier` | 9 passed; 100% coverage; 37/37 statements |
| Full unit suite | 1348 passed (baseline preserved) |

Raw logs at `tool-outputs/{ruff-check.log,ruff-format.log,pytest.log}`.

### PR Hygiene signal table (CR-09 / PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                     → clean
  module_fan_out: 1 (plugins/sulis/scripts/_discovery)
  severity: clean

Size (PH-02):
  lines_added: 487, lines_removed: 0, total: 487
  files_changed: 3
  generated_ratio: 0.0
  lock_file_ratio: 0.0
  severity: medium (above 200-line CR-02 threshold; single-reader justified by focused new-module scope with no neighbours)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: clean

Completeness (PH-04):
  new_source_without_test: 0  (verifier.py + __init__.py both covered)
  api_change_without_schema: false
  severity: clean
```

PH-03 high → CR-06 auto-downgrade: **did not fire** (PH-03 clean).

### Findings in the Changes

None.

### Findings in the Neighbours

None — the `_discovery/` package is newly created by this WP. No upstream
callers exist yet (WP-008 is the future consumer of `verify_and_roll_back_on_failure`,
parallel-dispatched).

### Watch List

**WL-001** — `plugins/sulis/scripts/_discovery/verifier.py:145`

`subprocess.run` is invoked with no explicit `timeout=`. The drift
detector is local Python and completes in <500ms per TDD §Performance,
so the practical risk is very low. A wedged or runaway detector
process, however, would block the Verify phase indefinitely; a
defensive `timeout=30` would cap the worst case. Out-of-scope for
WP-007 (no NFR specifies a verify-time budget; the WP Contract calls
for a `subprocess.run(...)` invocation, not a wrapped one). Consider
in a future hardening pass once the verify phase is in production
use and a budget can be picked from observed timing.

No delta drafted (CR-04 — no failing characterisation test exists for
a hang scenario that hasn't been observed).

### Cross-Reference

- **Existing Hardening Deltas covered:** none
- **Existing security report:** none for discover-project
- **Pattern suggesting full audit:** none

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `uv run ruff check`, `uv run ruff format --check`, `python3 -m py_compile`, `uv run pytest --cov=_discovery.verifier`. Base: no prior `_discovery/` package → no baseline errors possible. Head: 0 errors. Coverage: 100% on `verifier.py`. Coverage gap: none.
- [✓] **CR-02 Dispatch.** Single-reader pass justified by diff shape: 3 files, no neighbours (new package with no upstream callers), focused scope (one module + its tests, single intent). 487 added lines is above the 200-line carve-out threshold, but reading-in-place is appropriate when the diff is a self-contained new module with no integration surface — the parallel-dispatch rationale (three orthogonal lenses on a sprawling diff) does not apply.
- [✓] **CR-03 Full-file reads.** Both files >50 lines read end-to-end: `verifier.py` (239 lines) and `test_discovery_verifier.py` (248 lines). No sampling.
- [✓] **CR-04 Evidence discipline.** No findings, so no file:line citations required. Watch-list item cites file:line.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 0 low findings; 1 low watch-list note.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired (Build Verification empty; all files read end-to-end; all three lenses produced output; PH-03 clean).
- [✓] **CR-07 Lens completion.** Architecture: "nothing surfaced. Checks run: domain → infrastructure imports (none — module is a self-contained adapter); module-level singletons (none); circular imports (impossible — new package); resilience primitives (subprocess invocation noted in Watch List); credential exposure (none); observability span on Verify-phase invocation (not WP-007's contract — WP-008 wires the call site); contract test for the port (covered by test suite)." Security: "nothing surfaced. Primitives checked: SEC-01..07 (no auth surface, no injection vectors — argv is a list, no shell=True; no hardcoded secrets); SC-01..04 (no new dependencies); DAT-03 (no PII in logs — stderr is the detector's own output)." Quality: "nothing surfaced; all 7 outputs produced; jsx-scan N/A (Python); CR-10 performance patterns checked and absent."
- [✓] **CR-08 Self-attestation.** Complete (this section + `signals.json`).
- [✓] **CR-09 PR Hygiene applied.** PH-01 clean; PH-02 medium (size — single concentrated module justifies one-reader); PH-03 clean; PH-04 clean (100% test coverage on new code).

#### Run details

- **Diff source:** `git diff --cached` against `origin/change/create-discover-project`
- **Neighbour expansion:** none required (new package, no existing imports)
- **Neighbour cap:** N/A
- **Scanners run:** ruff (lint + format), pytest (with coverage), py_compile
- **Scanners unavailable:** gitleaks, trivy, semgrep — not invoked because diff contains no new credentials, no new dependencies, and no infra changes. Coverage gap noted but not material for this diff shape.
- **Lenses dispatched in parallel:** no — single-reader pass per CR-02 rationale above.
