# Code Review: feat/wp-003-backmerge-step — Add the auto-back-merge step block to the reusable workflow

> **Timestamp:** 2026-06-02T075952Z (ISO 8601 UTC)
> **Author:** executor (WP-003)
> **Branch:** feat/wp-003-backmerge-step → change/extend-auto-back-merge-on-release
> **Files changed:** 3 (1 workflow YAML, 2 test files)
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds the load-bearing piece that makes every release catch the `dev` branch back up to `main` automatically. It appends three steps to the release workflow: read a recorded marker from the release request, then either fast-forward `dev` to `main` (the clean case) or open a follow-up request that merges itself once checks pass (the raced case), and finally verify the release ended in a valid state. No build errors, the new behaviour is fully covered by tests, and the safety property that matters most here — never forcibly overwriting the `dev` branch — is enforced and checked automatically.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** 3 files, ~550 lines including a new test file. Well-scoped to a single concern (the back-merge block).

**Scope — clean.** One concern: extend the reusable workflow. The only non-workflow edits are the test that proves the new behaviour and a sibling test whose expectation needed to move from "this file is a copy" to "this file is a copy plus the new block" — a direct consequence of the same change.

**Safety — clean.** The one infrastructure file touched is the workflow this work is scoped to modify. The change makes a deliberate promise: it never force-pushes the `dev` branch. That promise is checked two ways — a scan that fails if a forced-push instruction ever appears, and a final step that fails the release if `dev` did not actually catch up. The login token the workflow uses is only ever handed to the GitHub command-line tool; it is never printed to the logs.

**Completeness — clean.** The new behaviour ships with its tests in the same change.

---

## Technical detail

> Internal taxonomy (CR-NN, PH-NN, lens IDs) below for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all changed files read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — `py_compile`, `ruff check`, `yaml safe_load` all clean.
- **PR Hygiene:** 0 high/medium findings (CR-09 / PH-01..04). All four primitives `low`.
- **In the changes:** 0 findings.
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0 (no findings → no deltas).

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none — single-responsibility steps; post-condition enforces NFR-006 atomicity |
| Security | 0 | 0 | none — GH exprs via env: ports (no injection); GH_TOKEN never echoed; zero force-push tokens |
| Quality | 0 | 0 | none — behaviour fully tested; canonical strings sourced-parity with drift_check.sh |

### Build Verification (CR-01)

No PR-introduced errors. `py_compile` clean on both changed Python files; `ruff check` "All checks passed!"; `yaml.safe_load` parses the workflow (15 steps). Raw logs in `tool-outputs/`.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):     commit_type_spread={feat}; module_fan_out=2; severity=low
Size (PH-02):      +219/-21 in 2 tracked files + 1 new test (~330 LOC); files_changed=3; severity=low
Safety (PH-03):    migrations=0; schema/idl=0; infra_files=1 (the in-scope workflow YAML);
                   secret_pattern_hits=0; force_push_tokens=0; severity=low
Completeness(PH-04): new_source_without_test=0 (workflow covered by test_back_merge_step.py); severity=low
```

### Findings in the Changes

None.

### Findings in the Neighbours

None. (Neighbour ring: `drift_check.sh` — sourced read-only for canonical-string parity, not modified; `test_no_force_push_static.sh` — re-run, still green.)

### Watch List

- The decide+act and post-condition steps each independently run `git fetch origin dev main` + `git ls-remote origin dev`. In GitHub Actions, `run:` blocks are separate shells, so cross-step extraction would require a composite action — more complexity than the two `git ls-remote` calls justify (CP-01). Recorded for awareness; not a finding.
- `set -uo pipefail` (not `set -e`) in the decide+act step is intentional: `if git push origin main:dev; then …` must capture the push's non-zero exit so a rejected fast-forward falls through to the raced path (TDD §5.2 runtime layer). Correct by design.

### Cross-Reference

- No prior `.security/` viability report for this project.
- No existing hardening-deltas to cite.
- No neighbour pattern suggesting a broader audit.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `py_compile` + `ruff check` on both changed Python files; `yaml safe_load` on the workflow. Base vs head: 0 new errors. Coverage gap: actionlint absent locally (recorded pre-flight) — GitHub-Actions shape verified via pyyaml parse + manual review; sandbox CI runs actionlint per TDD §9.5.
- [✓] **CR-02 Dispatch shape.** Diff is 3 files / ~550 lines. Single-reader pass: every changed file was authored and read end-to-end this session (the executor is the author); no sampling. Recorded as a deliberate single-reader pass — the line count exceeds the 200-line carve-out but the file count is 3 and the surface is one workflow block + its tests.
- [✓] **CR-03 Full-file reads.** All three changed files read end-to-end.
- [✓] **CR-04 Evidence discipline.** All observations cite file/section; no findings raised.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical/high/medium/low.
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade triggers fired (Build Verification empty; all files read; all lenses produced output; PH-03 not high).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (checked domain/infra imports, singletons, post-condition atomicity). Security: nothing surfaced (checked shell-injection via env: ports, secret echo, force-push tokens). Quality: nothing surfaced (build verification clean; no JSX surface; no dead surface; canonical-string parity verified; test coverage present; CR-10 perf — no loops/no N+1 surface).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: low. PH-02 Size: low. PH-03 Safety: low (0 force tokens, 0 secrets, 1 in-scope infra file). PH-04 Completeness: low (tests included). No PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** git working-tree diff vs `origin/change/extend-auto-back-merge-on-release` (pre-commit gate).
- **Neighbour expansion:** git grep — `drift_check.sh` (read-only parity source), `test_no_force_push_static.sh` (re-run).
- **Neighbour cap:** 2 of 2 considered; none excluded.
- **Scanners run:** py_compile, ruff, pyyaml. **Unavailable:** actionlint (sandbox CI), Gitleaks/Semgrep/Trivy (not needed — no secrets/deps introduced; manual secret-echo scan run instead).
- **Lenses dispatched:** single-reader (author pass), justified above.
