# Code Review: change/fix-fix-train-abort-and-rollback — fix wpx-train abort NameError + roll back step-7-shipping on early error

> **Timestamp:** 2026-05-28T161121Z (ISO 8601 UTC)
> **Author:** Iain Niven-Bowling
> **Branch:** change/fix-fix-train-abort-and-rollback → dev
> **Files changed:** 2 source (wpx-train +68 lines; new test file +186 lines)
>
> **Outcome:** Ready to merge

---

## At a glance

This change fixes two failure-recovery bugs in the train runner. First, the
`abort` command was crashing because it referred to a status label
(`step-7-held`) that was never imported into the file — a one-line import
fixes every place that used it. Second, when a train run hit an error early
(before anything was merged), it left behind a leftover state file that made
the system think the work was still "shipping" — so the next run wrongly
reported there was nothing to do. The fix cleans up that leftover state, but
only in the genuinely-abandoned cases, deliberately leaving the intentional
"paused" state alone so the founder can still resume or abort it.

The change is small, well-scoped, test-first (two regression tests that fail
on the old code and pass on the new), and the full test suite (911 tests)
stays green. Nothing needs attention before merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** 2 files, ~254 lines including tests. Small and focused.

**Scope — clean.** Single concern (`fix:` for one GitHub issue, #62), even
though it addresses two related bugs in the same function family. They share
the same root area (train failure recovery) and the same test file, so they
belong together.

**Safety — clean.** No migrations, no schema/IDL changes, no infra files, no
secrets. Pure stdlib Python logic change.

**Completeness — clean.** New behaviour is covered by two new regression
tests, each confirmed to fail on the current code (one with the exact
`NameError`, one proving the stranded state) and pass after the fix.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high in diff; Build Verification empty; both
changed files read end-to-end; all lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (PH-01..PH-04 all clean)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | None — reuses `cleanup_train_state`; new `frozenset` mirrors existing `_IN_FLIGHT_TRAIN_PHASES`/`TERMINAL_PHASES` style |
| Security | 0 | 0 | None — no new external calls, secrets, subprocess, or I/O beyond existing state-file unlink |
| Quality | 0 | 0 | None — test-first; bounded iteration only |

### Build Verification (CR-01)

Project gate per `.github/workflows/branch-ci.yml` is `python3 -m compileall
plugins/sulis/scripts` (no ruff/mypy configured — "no type-checker configured
for this repo"). Ran on HEAD: exit 0. `wpx-train` and the new test file both
compile. Informational ruff on the new test file: all checks passed. Ruff on
`wpx-train` shows 14 findings — identical to the `dev` baseline (verified via
`git show dev:…/wpx-train` → ruff), so **zero PR-introduced** lint findings.
The pre-existing findings (F541 f-strings, F821 `WpxPaths` annotation) are
outside the changed lines and out of scope per EP-07 (Boy Scout scoped to
touched lines).

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {fix}                    → clean
  module_fan_out: 1 top-level dir (plugins/)   → clean
  severity: clean

Size (PH-02):
  lines_added: 254 (wpx-train +68, test +186), lines_removed: 0
  files_changed: 2
  generated_ratio: 0
  lock_file_ratio: 0
  severity: clean (≤200-line source-change band; 2-file band)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: clean

Completeness (PH-04):
  new_source_without_test: 0 (the source change ships with 2 regression tests)
  api_change_without_schema: false
  severity: clean
```

### Findings in the Changes

None.

The single iteration introduced (`any(e.get("merge_sha_on_dev") for e in
state.get("bundle", []))`) is bounded by the train batch size (`max_batch_size`,
default-capped at ~10), short-circuiting, over an already in-memory dict. Not a
CR-10 anti-pattern (no N+1, no unbounded materialisation, no nested loop).

### Findings in the Neighbours

None. The change reuses `cleanup_train_state` (the same primitive every
terminal path calls) rather than duplicating unlink logic, and reads via the
existing `read_train_state` / `train_state_path` helpers — no new coupling.

### Watch List

- The `except SystemExit` handler in `cmd_run` now calls
  `_rollback_pre_merge_train_state` on **every** exit, including the normal
  success path (where `_finalise_success` raises `SystemExit(0)`). This is a
  guarded no-op on success (the state is already cleaned up or in a
  post-merge/terminal phase, so the phase-membership guard returns `False`),
  confirmed by the happy-path + gate-handoff tests still passing. No action
  needed; noted for future readers.

### Cross-Reference

- **Existing Hardening Deltas covered:** none.
- **Existing security report:** none found under `.security/agents/`.
- **Pattern suggesting full audit:** none.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Command: `python3 -m compileall
  plugins/sulis/scripts` (project gate; no typechecker configured). Base: clean.
  Head: clean (exit 0). Informational ruff: new test file clean; wpx-train
  findings == dev baseline (0 introduced). Coverage gap: no typechecker
  configured for this repo (documented in branch-ci.yml).
- [✓] **CR-02 Single-reader pass justified by diff size:** 68 source lines /
  2 files — within the ≤200-line, ≤5-file carve-out.
- [✓] **CR-03 Full-file reads.** Both changed files read end-to-end
  (wpx-train relevant regions + entire new test file). Unread files: none.
- [✓] **CR-04 Evidence discipline.** No findings to evidence; bounded-iteration
  note cites the exact line.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 0 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none
  fired (Build Verification empty; all files read end-to-end; all lenses
  produced output; PH-03 clean).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (checked
  dependency-direction, new singletons, reuse vs duplication — reuses
  cleanup_train_state). Security: nothing surfaced (no new external calls /
  secrets / subprocess / network; scanners not run — no signals present).
  Quality: 0 findings + test-coverage observation (tests present, RED→GREEN
  confirmed) + dead-surface (helper called from 3 sites) + contract-drift
  (none) + CR-10 (no anti-pattern matches).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: clean (single `fix:`, one
  dir). PH-02 Size: clean (254 lines / 2 files). PH-03 Safety: clean (0
  migrations/schemas/secrets/infra). PH-04 Completeness: clean (source ships
  with tests). PH-03 high → CR-06 auto-downgrade: did not fire.

#### Run details

- **Diff source:** `git diff dev...change/fix-fix-train-abort-and-rollback`
  (working tree, pre-commit).
- **Neighbour expansion:** git grep over train-state helpers
  (cleanup_train_state, compute_wp_status, _in_flight_train_has_wp,
  _pause_train_state, _handle_post_merge_failure).
- **Neighbour cap:** not reached (well under 20).
- **Scanners run:** compileall (gate), ruff (informational). Gitleaks/
  Semgrep/Trivy: not run — no security signals in a stdlib logic diff.
- **Scanners unavailable:** n/a.
- **Lenses dispatched in parallel:** no — single-reader carve-out (CR-02).
