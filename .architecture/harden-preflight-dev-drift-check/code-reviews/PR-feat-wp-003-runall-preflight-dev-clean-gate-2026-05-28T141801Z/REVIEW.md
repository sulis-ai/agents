# Code Review: feat/wp-003-runall-preflight-dev-clean-gate — wpx-preflight dev-clean + run-all Step 0 gate

> **Timestamp:** 2026-05-28T141801Z (ISO 8601 UTC)
> **Author:** Iain Niven-Bowling
> **Branch:** feat/wp-003-runall-preflight-dev-clean-gate → change/harden-preflight-dev-drift-check
> **Files changed:** 3 (2 new, 1 modified)
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds a small command-line tool that checks whether the shared base branch
is healthy (its automated checks are passing) before the build-and-ship loop starts a
batch of work. If the base branch is already broken, the loop now stops up front with
one clear message — instead of every new task quietly inheriting the same breakage and
reporting it again and again. The work is well-scoped, fully tested, and the green path
behaves exactly as it did before. No issues that need attention.

## What to fix

No issues that need attention.

The new tool reuses the existing, already-tested helper that reads the base branch's
recorded check results, so it adds no new logic for reading those results — it just
maps the answer to a yes/no decision the loop can act on. Five tests cover every case:
healthy, broken, no-checks-recorded-yet, checks-still-running, and the specific case
where a check finished but failed. All pass.

## How this pull request is shaped

**Size — clean.** Small and focused: one new ~135-line tool, one ~110-line test file,
and ~47 lines of documentation added to the loop's instructions.

**Scope — clean.** A single concern: the up-front health check and its wiring.

**Safety — clean.** No database changes, no infrastructure changes, no secrets.

**Completeness — clean.** New behaviour ships with tests (five of them).

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs) for
> engineers and for downstream agents like `/sulis:harden-codebase`.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all three
files read end-to-end; all three lenses produced output; no auto-downgrade trigger
fired.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (PH-01..PH-04 all clean)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none — thin CLI adapter over an existing domain port |
| Security | 0 | 0 | none — no new subprocess/injection surface |
| Quality | 0 | 0 | none — full branch coverage, ruff-clean |

### Build Verification (CR-01)

The repo is Python stdlib-only — no `tsconfig.json`, no `.eslintrc`, no mypy/pyright
config. The mechanical floor is the project's CI gate (per `.sulis/repo-contract.yml`):
`python3 -m compileall plugins/sulis/scripts`, `pytest plugins/sulis/scripts/tests/unit/`,
the routing-coverage gate `sulis-route check`, and manifest JSON validity. `ruff` is
present on PATH (no repo config) and was run opportunistically as an extra mechanical
check.

| Check | Base | Head | Delta |
|---|---|---|---|
| compileall (wpx-preflight) | n/a (new file) | rc 0 | 0 errors |
| pytest (new test file) | n/a (new tests) | 5 passed | 0 errors |
| pytest (full unit suite) | 772 passed/1 skipped | 777 passed/1 skipped | +5 (the new tests) |
| sulis-route check | passed:true | passed:true | no regression |
| manifest JSON validity | valid | valid | no change |
| ruff (default + F rules) | n/a | All checks passed | 0 |

Build Verification section is **empty** → does not block PASS.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat} (single concern)   → clean
  module_fan_out: 1 top-level dir (plugins/)     → clean
  severity: none

Size (PH-02):
  lines_added: ~296 (47 doc + 137 tool + 112 test), lines_removed: 0
  files_changed: 3
  generated_ratio: 0.0
  lock_file_ratio: 0.0
  severity: none (well within bands; 2 of 3 files net-new)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0 (wpx-preflight ships with test_wpx_preflight.py)
  api_change_without_schema: false
  severity: none
```

No PH-03 high finding → no CR-06 auto-downgrade from hygiene.

### Findings in the Changes

None.

**Architecture lens — nothing surfaced.** Checks run: dependency direction (CLI →
`_wpxlib._preflight_ci_conclusion` domain helper; no import of infra/db/http into a
domain layer — the helper is the existing `GHClient` port); module-level singletons
(none); circular imports (none — `wpx-preflight` is a leaf script); new external calls
(none added — CI reads delegate entirely to the existing, timeout-bearing
`_gh_check_runs` port); observability/secrets (n/a — read-only CLI). The SKILL.md change
is documentation, not executable.

**Security lens — nothing surfaced.** Primitives checked: SEC-01..07 (access control,
auth, injection, validation, SSRF, secrets exposure), SC-01..04 (dependency CVEs — none
added; stdlib-only). No new `subprocess`/`shell=True`; the only shell-out is the existing
`gh api repos/<repo>/commits/<branch>/check-runs` path inside the reused port. `--repo`
and `--branch` flow into that already-in-production path construction; no new injection
surface introduced by this diff. Error output echoes CI check names (trusted GitHub
data), no secrets/PII. Scanners: none invoked (no signals — no Dockerfile, no new
dependency, no new logging of sensitive data).

**Quality lens — all seven outputs:**
1. Build Verification follow-up: 0 entries (baseline clean).
2. JSX/template identifier scan: n/a (no TSX/JSX/Vue/Svelte files).
3. Dead-surface: none — `_emit`, `_dev_clean`, `main` are all reached; the single
   import (`_preflight_ci_conclusion`) is used.
4. Contract-drift: none — the emitted envelope `{ok, errors, warnings}` matches
   `wpx-arrival-check`'s `_Report.emit` byte-for-byte (verified by running the CLI
   directly); PRE-01 error carries `rule/check/actual/detail/expected` consistent with
   the run-all parse contract.
5. Test-coverage observation: new behaviour ships with 5 tests covering all four
   verdict branches (green/unknown/pending/failed) + exit codes 0/2 + the lesson-#59
   explicit-conclusion guard end-to-end.
6. Style/readability: ruff-clean (default + F); docstring documents the verdict→envelope
   mapping inline.
7. CR-10 performance: no anti-pattern matches. The only iteration is
   `", ".join(failed)` over a bounded failed-check list (typically 1–3 entries); no
   loop-bound DB/RPC/filesystem calls, no O(N²), no unbounded materialisation.

### Findings in the Neighbours

None. The one neighbour (`_wpxlib._preflight_ci_conclusion`, WP-001, already merged on
the base branch) is reused unchanged and is itself unit-tested.

### Watch List

Empty.

### Cross-Reference

- **Existing Hardening Deltas covered:** HD-002 (this WP implements it); HD-001 (the
  reused helper, already merged).
- **Existing security report:** none for this project.
- **Pattern suggesting full audit:** none.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Stdlib repo (no tsc/eslint/mypy); the CI gate
  is the floor: compileall rc0, pytest 777 passed/1 skipped (new file 5 passed),
  sulis-route check passed:true, manifests valid; ruff (default + F) all-clear. Base vs
  head delta = the +5 new tests only. Coverage gap: subprocess-launched script not
  line-traced by pytest-cov — branch coverage verified manually (all 4 verdict arms +
  exit codes exercised by the 5 tests).
- [✓] **CR-02 Single-reader pass justified.** Diff is 3 files (~296 lines), 2 net-new +
  1 documentation-only markdown. Above the 200-line band but the author read all three
  files end-to-end (CR-03) and they are small, self-contained, and stdlib-only; the
  per-file lens analysis is recorded above. Carve-out noted per the standard.
- [✓] **CR-03 Full-file reads.** All 3 changed files read end-to-end (wpx-preflight 137L,
  test 112L, SKILL.md change 47L in a known file). Unread files: none.
- [✓] **CR-04 Evidence discipline.** Findings: none. Lens checks enumerated with the
  specific predicates run.
- [✓] **CR-05 Severity rubric.** Applied — 0 critical, 0 high, 0 medium, 0 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired
  (Build Verification empty; all files read end-to-end; all lenses produced output; no
  PH-03 high).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced + checks listed.
  Security: nothing surfaced + primitives listed. Quality: all seven outputs produced.
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none (single feat concern). PH-02 Size:
  none (~296 lines / 3 files, 2 net-new). PH-03 Safety: none (0 migrations/schemas/
  secrets/infra). PH-04 Completeness: none (tool ships with tests). PH-03 high → CR-06
  auto-downgrade: did not fire.

#### Run details

- **Diff source:** local working tree vs `change/harden-preflight-dev-drift-check`
  (pre-commit review, per Step 6.5 of the executor lifecycle).
- **Neighbour expansion:** git grep — one neighbour (`_preflight_ci_conclusion`),
  reused unchanged.
- **Neighbour cap:** 1 of 1 considered, 0 excluded.
- **Scanners run:** ruff (lint). Gitleaks/Semgrep/Trivy: not invoked — no signals
  (no secrets, no new dependency, no Dockerfile).
- **Lenses dispatched in parallel:** no — single-reader carve-out (small net-new diff,
  full end-to-end reads).
