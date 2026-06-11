# Code Review: feat/wp-005-fallback-worktree-id-keyed — keep two changes from sharing a worktree

> **Timestamp:** 2026-06-11T135836Z (ISO 8601 UTC)
> **Author:** executor (WP-005)
> **Branch:** feat/wp-005-fallback-worktree-id-keyed → change/fix-use-change-id-not-handle
> **Files changed:** 1 (plus 1 new test file)
>
> **Outcome:** Ready to merge

---

## At a glance

This is a small, well-scoped change. It teaches one helper (the function that
works out where a piece of work's files live on disk) to use a unique-per-change
identifier when one is available, so two pieces of work that happen to share the
same short name can never end up pointing at the same folder. The build is clean,
nothing risky is touched, and the change comes with five new tests covering both
the new behaviour and the old behaviour it preserves.

## What to fix

No issues that need attention.

## How this pull request is shaped

Small and single-purpose — 22 lines in one file, plus a new test file. Nothing to
flag on size, scope, safety, or completeness. Tests were included for the new
behaviour, which is exactly what you want.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs)
> for engineers and for downstream agents.

### Verdict

`PASS` per CR-06. No critical/high/medium/low in the diff; Build Verification
empty; the single changed file read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (CR-09 / PH-01..PH-04 all `none`)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none — lazy import mirrors existing pattern |
| Security | 0 | 0 | none — new param dormant, ULID-validated upstream when wired |
| Quality | 0 | 0 | none — both branches tested |

### Build Verification (CR-01)

`compileall` (the project CI lint gate per `.github/workflows/branch-ci.yml`)
passes on both changed files. `ruff check` delta: 0 new errors. The two E402
errors ruff reports on `_wpxlib.py` are at lines 4154-4155 — pre-existing on
the base branch, outside the edit region (4373-4397). The function-body lazy
import added by this change is not module-level and is correctly not flagged.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):        commit_type_spread: {refactor}; module_fan_out: 1 → severity none
Size (PH-02):         +19 / -3, 1 file changed, +1 new test file → severity none
Safety (PH-03):       migrations: 0, schemas: 0, infra: 0, secrets: 0 → severity none
Completeness (PH-04): new_source_without_test: 0 (tests included) → severity none
```

### Findings in the Changes

None.

### Findings in the Neighbours

None. Callers of `change_worktree_path` (`sulis-change` lines 190/817/1539/1969,
`_wpxlib.py:5145`) all use the legacy two-argument form, which the change
preserves byte-for-byte (the new `change_id` kwarg defaults to `None`). No
neighbour is altered or exposed.

### Watch List

- The `change_id` parameter is currently dormant — no caller passes it yet.
  This is intentional: WP-005 is opportunistic defence-in-depth, and wiring the
  recreate fallback to pass the id is deliberately out of this WP's file scope
  (the distinct-file guard reserves `sulis-change` for sibling WPs). The
  infrastructure lands here; the wiring is a separate change. Not a defect.

### Cross-Reference

- No prior security report under `.security/use-change-id-not-handle/`.
- No existing hardening deltas to cite.
- No neighbour pattern suggesting a broader audit.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `python3 -m compileall` (CI gate) + `ruff check` on HEAD and BASE. Base: 3 pre-existing ruff hits on `_wpxlib.py`; Head: same 2 (E402 4154-4155). 0 introduced. compileall passes. Coverage: full.
- [✓] **CR-02 Single-reader pass justified by diff size: 22 lines, 1 changed file (+1 new test file). Below the 200-line / 5-file threshold.
- [✓] **CR-03 Full-file reads.** The changed function and the full new test file read end-to-end. No file >50 lines sampled.
- [✓] **CR-04 Evidence discipline.** Findings: none; build-verification + hygiene cite file:line.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 0 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. No auto-downgrade triggers fired (Build Verification empty; all files read end-to-end; all lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (checked: dependency direction, new external calls, resilience, verification). Security: nothing surfaced (checked SEC access/injection/secrets/path-traversal on the change_id→path flow; no untrusted input). Quality: 0 findings + dead-surface (dormant param, intentional) + contract-drift (none, default None) + test-coverage (5 new tests) + CR-10 (no anti-pattern matches).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none. PH-02 Size: none (22 lines / 1 file). PH-03 Safety: none (0 migrations/schemas/secrets/infra). PH-04 Completeness: none (tests included). No PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** `git diff change/fix-use-change-id-not-handle` (new test file untracked, reviewed directly)
- **Neighbour expansion:** `git grep change_worktree_path(` — 5 call sites, all legacy-form, none altered
- **Neighbour cap:** 5 of 5 considered, none excluded
- **Scanners run:** compileall, ruff (no secrets/dependency scanner applicable — no new deps, no secrets surface)
- **Lenses dispatched:** single-reader (CR-02 carve-out)
