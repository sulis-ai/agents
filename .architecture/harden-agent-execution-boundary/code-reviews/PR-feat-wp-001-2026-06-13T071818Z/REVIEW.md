# Code Review: PR-feat-wp-001 — L1 contract ports + secret-pattern extract

> **Timestamp:** 2026-06-13T071818Z (ISO 8601 UTC)
> **Author:** autonomous executor (WP-001)
> **Branch:** feat/wp-001-l1-contract-ports-and-secret-pattern-extract → change/harden-agent-execution-boundary
> **Files changed:** 7 (1 modified, 6 new — 3 source + 3 test)
>
> **Outcome:** Ready to merge

---

## At a glance

This change pulls the secret-detection patterns out of the existing privacy
tool into a small shared module so two parts of the system can use one list
of patterns instead of each keeping its own copy. It also writes down the
"shape" of the upcoming safe-fetch feature (what a request and a reply look
like) before that feature is built. There are no build errors, the change is
well-scoped to one purpose, and every new piece of code has tests. The
existing privacy tool was protected by a before-and-after test that proves
its behaviour did not change. Nothing needs fixing.

## What to fix

No issues that need attention.

One housekeeping note (not a code problem): a `.coverage` file (a test-run
byproduct) was produced in the working folder. It should be left out of the
commit — it is a temporary artifact, not part of the change.

## How this pull request is shaped

**Size — clean.** Small and focused: about 300 lines of new code plus 480
lines of tests, across 7 files, all for one purpose.

**Scope — clean.** A single concern: extract the shared pattern list and pin
the contract. One `feat`/`refactor`-shaped change, no mixing.

**Safety — clean.** No database migrations, no schema changes, no
infrastructure files, no secrets in the diff (the test fixtures that look
like keys are stored reversed so no real-looking secret is ever committed).

**Completeness — clean.** 3 new source files, 3 new test files. New
behaviour is tested; the refactor of the existing tool is guarded by a
characterisation test.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs)
> for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high/medium/low in the diff; Build Verification
empty; all files >50 lines read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (PH-01..04 all clean / note-level)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none — dependency-inward respected, ports domain-owned, contract test present |
| Security | 0 | 0 | none — pure data modules, no hardcoded secrets, honest format-based limit documented |
| Quality | 0 | 0 | none — O(N) scans, 100% coverage on new files, no dead surface or drift |

### Build Verification (CR-01)

Mechanical baseline (the repo's CI gate per `.github/workflows/branch-ci.yml`):
`python3 -m py_compile` + `ruff check`. No type-checker configured (CI echoes
"no type-checker configured for this repo"); `ruff format` is NOT a repo gate
and was not run (CP-01 — follow the established convention).

- `py_compile` on all 7 changed files: OK.
- `ruff check` on the 7 changed files: All checks passed (exit 0).
- Note: `ruff check tests/unit/` (whole dir) reports 59 pre-existing errors in
  OTHER, unrelated test files — none in the PR-introduced files. Not
  PR-introduced; out of scope (neighbour ring, surfaced once for awareness).

PR-introduced errors: **0**. Build Verification section empty.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat/refactor — single concern}   → clean
  module_fan_out: 1 top-level dir (plugins/sulis/scripts) → clean
  severity: note

Size (PH-02):
  lines_added: ~774 (296 source + 478 test), lines_removed: 70
  files_changed: 7
  generated_ratio: 0
  severity: note (well within bands)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0 (fixtures reversed in source)
  severity: clean

Completeness (PH-04):
  new_source_without_test: 0  (every new module has a test)
  api_change_without_schema: false
  severity: clean
```

### Findings in the Changes

None.

### Findings in the Neighbours

None. The only non-test importer of `_anonymiser` (`_issue_descriptors.py`)
references it in a docstring only — no live dependency on the extracted
internals. Public surface of `_anonymiser` confirmed intact (`anonymise`,
`AnonymisationContext`, `AnonymisationResult`, `Redaction`,
`PUBLIC_DOMAIN_ALLOWLIST`, `_url_has_userinfo`). Neighbour test suites
(`test_anonymiser.py`, `test_sulis_issues.py`, `test_collision_schedule.py`)
all green (97 pass).

### Watch List

- The secret catalogue is format-based (prefix-anchored), so a novel secret
  shape it does not recognise can pass. This is documented in
  `_secret_patterns.py`'s docstring and ADR-002; the real L1 control is the
  Rule-of-Two credential exclusion (WP-002/003), with the scrub as
  defence-in-depth. No action for this WP — recorded so it is not mistaken
  for a gap.

### Cross-Reference

- No prior `.security/` viability report for this project.
- No existing hardening-deltas to cite.
- No neighbour pattern suggesting a broader audit (the 59 pre-existing ruff
  errors in unrelated test files are a separate hygiene matter, not within
  this WP's contract).

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `py_compile` + `ruff check`
  (the repo's CI gate). Base behaviour preserved; HEAD: 0 new errors on
  PR-introduced files. Coverage gap: no type-checker configured in-repo
  (recorded, matches CI).
- [✓] **CR-02 Dispatch shape.** Diff is 7 files / ~774 added lines — above the
  single-reader carve-out. Reviewed each changed file end-to-end as a single
  reader rather than dispatching three concurrent sub-agents; justified by the
  tight single-concern coupling (one contract WP: one catalogue module + one
  ports module + their tests) and the absence of cross-module fan-out. Recorded
  here as the honest deviation note per CR-02.
- [✓] **CR-03 Full-file reads.** All changed files read end-to-end:
  `_secret_patterns.py` (191), `_safe_fetch/ports.py` (92),
  `_safe_fetch/__init__.py` (13), `_anonymiser.py` diff (22/-70), and the 3
  test files (141/148/189). Unread files: none.
- [✓] **CR-04 Evidence discipline.** No findings to evidence; the
  characterisation test (`test_anonymiser_characterisation.py`) is the
  grounding artifact for the extract.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical / 0 high / 0 medium / 0 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. No auto-downgrade triggers
  fired (Build Verification empty; all files read end-to-end; all lenses
  produced output; no PH-03 high).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (checks:
  dependency-direction, domain-owned ports, contract-test presence, no
  infra→domain import, no new singletons). Security: nothing surfaced
  (checks: hardcoded secrets — none, fixtures reversed; injection/SSRF — N/A,
  pure data; format-based limit documented). Quality: 0 findings + CR-10 perf
  scan (O(N) finditer loops, no N+1/O(N²)) + dead-surface (none) +
  contract-drift (ports match WP pinned surface) + test-coverage (100% on new
  files, 109 tests).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: note (single concern). PH-02
  Size: note (7 files / ~774 lines). PH-03 Safety: clean (0 migrations / 0
  schemas / 0 secrets / 0 infra). PH-04 Completeness: clean (every new module
  has a test). PH-03 high → CR-06 auto-downgrade: did not fire.

#### Run details

- **Diff source:** `git diff change/harden-agent-execution-boundary...HEAD`
  (working tree — pre-commit).
- **Neighbour expansion:** `grep` for importers of the changed modules; 3
  neighbours found, all tested green.
- **Neighbour cap:** 3 of 3 considered, none excluded.
- **Scanners run:** py_compile, ruff check, grep-based secret/perf scan.
- **Scanners unavailable:** gitleaks/semgrep/trivy not installed; substituted
  grep-based literal-secret + CR-10 perf scan on the new source (coverage gap
  recorded).
- **Lenses dispatched in parallel:** no — single-reader, justified above.
