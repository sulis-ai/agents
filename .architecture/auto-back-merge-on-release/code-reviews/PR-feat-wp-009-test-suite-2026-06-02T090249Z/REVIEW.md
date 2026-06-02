# Code Review: feat/wp-009-test-suite — Author the full auto-back-merge test suite

> **Timestamp:** 2026-06-02T090249Z (ISO 8601 UTC)
> **Author:** executor (WP-009)
> **Branch:** feat/wp-009-test-suite → change/extend-auto-back-merge-on-release
> **Files changed:** 19 (1569 insertions, 37 deletions)
>
> **Outcome:** Ready to merge

---

## At a glance

This pull request is the final piece of the auto-back-merge change — the test
suite that proves the whole mechanism works end-to-end. It is all test code,
fixtures, and docs; it ships no production behaviour. The build is clean, every
new test was checked to actually catch the bug it claims to catch (by
temporarily breaking the thing it watches and confirming it goes red), and the
full test run is green. Two small tidy-ups surfaced during review and were both
fixed in place.

## What to fix

No issues remain that need attention — the two minor items found during review
were fixed as part of this pull request:

- An unused leftover variable in the race-condition test was removed.
- A shared test helper (a fake `gh` command) had been written but wasn't used
  by any test yet. Rather than delete it, it was wired into a new small test
  that also fills a real gap — it now checks the part of the drift detector
  that looks up whether a back-merge pull request is already open.

## How this pull request is shaped

**Size — for awareness.** It is large (about 1,600 lines) but that is by
design: the test suite is one logical unit, and the work package explicitly
records that splitting it into seven per-component test fragments would just
duplicate the shared fixtures and orchestrator. All of it is test code, fixtures,
and documentation — the lowest-risk category of change.

**Safety — clean.** No database migrations, no schema changes, no infrastructure
files, no secrets. The SHA-shaped strings in the tests are deterministic fake
test data, not real credentials.

**Completeness — this IS the tests.** There is nothing to flag about missing
tests, because the work package is the tests. Coverage was verified the rigorous
way: each regression-guard and chaos test was proven to fail when its subject is
broken.

## Things to take away

Nothing to add — the suite follows the project's existing shell-test conventions,
sources every shared string from a single declaration, and proves each test
catches its regression. Clean work.

---

## Technical detail

> Below this point uses internal taxonomy (CR-NN, PH-NN, lens IDs) for engineers
> and downstream agents.

### Verdict

`PASS` per CR-06. Build Verification empty; no critical/high in the diff; all
changed files >50 lines read end-to-end; all three lenses produced output; both
`low` findings addressed inline; full suite green after fixes.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — `bash -n` clean on all
  13 changed shell files; `py_compile` clean on the one new Python file.
- **PR Hygiene:** size `medium-note` (1569+/37-, 19 files — single logical unit,
  documented SHOULD-deviation in DECOMPOSE_VALIDATION); scope/safety/completeness
  `low`.
- **In the changes:** 2 findings (0 critical, 0 high, 0 medium, 2 low) — both
  fixed inline.
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0 (both findings fixed in the PR, not deferred).

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | nothing surfaced |
| Security | 0 | 0 | nothing surfaced |
| Quality | 2 (fixed) | 0 | dead variable + dead-surface shared stub |

### Build Verification (CR-01)

No PR-introduced errors. Mechanical baseline: `bash -n` on every changed shell
file (clean — see `tool-outputs/bash-syntax.log`); `python3 -m compileall` on
`tests/unit/test_abm_shell_suite.py` (clean — see `tool-outputs/py-compile.log`).
No tsc/eslint/mypy/ruff configured for this repo (stdlib-only tooling per the
plugin contract); recorded as the project's mechanical floor.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):        commit_type_spread: {test}            → severity low
Size  (PH-02):        +1569 / -37, files: 19, generated: 0  → medium-note
                      (single logical unit — the test suite; per WP-009
                       DECOMPOSE_VALIDATION the 7-fragment alternative would
                       duplicate fixtures + orchestrator)
Safety (PH-03):       migrations: 0, schemas: 0, infra: 0, secrets: 0 → low
Completeness (PH-04): new_source_without_test: 0 (this WP is the tests) → low
```

### Findings in the Changes

#### F-01 — low (quality) — `chaos/test_race_window.sh:74` — FIXED INLINE

**Quoted text (before):**
```bash
) > "$TMP/step_stdout" 2>&1
STEP_RC=$?
```
**Evidence:** `STEP_RC` is assigned but never read; the test's assertions read
the recorded call log, not the step's exit code. Dead surface.
**Resolution:** removed the assignment; the subshell now ends `|| true` with a
comment explaining the step exit code is intentionally not asserted on.

#### F-02 — low (quality) — `fixtures/drift_check/gh-stubs/gh` — FIXED INLINE

**Evidence:** the shared STUB_MODE-driven `gh` stub was authored to satisfy the
WP-009 DoD Blue requirement ("stub gh lives in one place ... reused across
tests") but no test consumed it — `grep -rln gh-stubs` over the tests returned
only the fixture's own README. Dead surface, and a partial miss of the DoD
intent.
**Resolution:** wired the shared stub into a new test,
`integration/test_drift_message_uses_shared_gh_stub.sh`, which exercises
`drift_check.sh`'s `gh`-dependent recovery-message branch (`STUB_MODE=pr-open`
→ "an open back-integrate PR is waiting"). This branch was previously untested
(the exit-code smoke test covers the drift/clean codes but not the gh-driven
message), so the fix both removes the dead surface AND adds real coverage.
Meta-revert verified: breaking drift_check.sh's PR-open message turns the new
test red.

### Findings in the Neighbours

None. The diff is self-contained in `plugins/sulis/scripts/tests/`; the
production code it exercises (drift_check.sh, the reusable workflow, the shim,
the release-train SKILL.md, GIT-12, branch-ci.yml) is read by the tests but not
modified.

### Watch List

- `fixtures/drift_check/setup.sh` is referenced only from the README, not
  invoked by any test. Acceptable: per the WP-009 DoD Blue it is the
  *reproducibility recipe* for the inline-built fixture remotes (so CI can
  rebuild them deterministically), not a runtime test dependency. The drift
  unit tests build their own remotes in `mktemp` for parallel-safety.

### Cross-Reference

- No prior `.security/` viability report for this branch.
- No existing hardening-deltas to cite.
- No neighbour pattern suggesting a broader audit.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `bash -n` (13 files, clean) +
  `py_compile` (1 file, clean). No tsc/eslint/mypy configured (stdlib-only
  plugin contract) — recorded, not skipped silently. 0 PR-introduced errors.
- [✓] **CR-02 Dispatch shape.** Diff >200 lines / >5 files; reviewed across all
  three lenses by the reviewing agent over the full diff (single agent, all
  files read end-to-end — the diff is homogeneous test code, no sampling).
- [✓] **CR-03 Full-file reads.** All 19 changed files read end-to-end (authored
  in this session). No sampling.
- [✓] **CR-04 Evidence discipline.** Both findings cite file:line + quoted text
  / grep evidence.
- [✓] **CR-05 Severity rubric.** Applied — 0 critical, 0 high, 0 medium, 2 low.
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade triggers fired (Build
  Verification empty; all files read; all lenses produced output; PH-03 not
  high).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (no
  domain→infra imports; this is test code). Security: nothing surfaced
  (no real secrets — the only `sk_live_` hit is in a pre-existing neighbour,
  test_anonymiser.py, intentional anonymiser test data). Quality: 2 findings
  (dead variable, dead-surface stub) + test-coverage observation (the WP is the
  tests; coverage proven by meta-revert) + CR-10 perf (loops in fixtures build
  git remotes — benign for fixtures).
- [✓] **CR-09 PR Hygiene applied.** PH-01 low, PH-02 medium-note (single logical
  unit), PH-03 low, PH-04 low. No PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** `git diff --cached origin/change/extend-auto-back-merge-on-release`
- **Neighbour expansion:** git grep over the tests dir; no production code modified.
- **Scanners run:** bash -n, py_compile, grep secret-pattern scan.
- **Scanners unavailable:** gitleaks / trivy / semgrep not installed — coverage gap
  noted; manual secret-pattern grep run as the floor (no real secrets found).
