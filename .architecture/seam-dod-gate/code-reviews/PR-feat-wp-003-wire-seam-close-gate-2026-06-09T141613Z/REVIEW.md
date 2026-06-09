# Code Review: feat/wp-003-wire-seam-close-gate — Wire the seam-close gate into wpx-step12 (step 12.2a)

> **Timestamp:** 2026-06-09T141613Z (ISO 8601 UTC)
> **Author:** executor (WP-003)
> **Branch:** feat/wp-003-wire-seam-close-gate → change/feat-seam-dod-gate
> **Files changed:** 2
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds a small check to the step that marks a task "done": the moment a
task completes, it asks "did this just finish connecting two halves of a feature?"
and, if so, drives the real end-to-end check before letting the seam count as done.
The wiring is well-scoped (two files, 168 lines), comes with its own tests, and
doesn't disturb the existing "mark done" behaviour. One thing was tightened during
review — see below — and after that the change is clean.

## What to fix

No issues that need attention. One improvement was made during the review (already
applied):

### Worth fixing — applied inline — `plugins/sulis/scripts/wpx-step12`, the new gate helper

**What was happening:** The new gate helper described itself as "never able to crash
the done step", but the code didn't actually guarantee that — if the gate's own
machinery hit an unexpected error, the done step could have failed *after* it had
already marked the task done, leaving things in a confusing half-state.

**Why it matters:** Marking a task done and then crashing would report failure even
though the task genuinely completed — the exact kind of confusing outcome this whole
change exists to avoid.

**What was done:** Wrapped the gate call so any unexpected machinery error makes the
gate quietly step aside ("couldn't check this time") instead of crashing — and
crucially, it never pretends a seam passed or failed on an error. The seam just gets
re-checked at the next opportunity, with the final ship-time check as a backstop.
Verified with a forced-failure test.

## How this pull request is shaped

**Size — clean.** 168 lines across 2 files. Small and easy to review thoroughly.

**Scope — clean.** Single concern: wire one new check into one existing step, plus
its tests. One Conventional Commit type.

**Safety — clean.** No database migrations, no schema changes, no infrastructure
files, no secrets.

**Completeness — clean.** The new behaviour ships with tests (the wiring test file).
Three of its five assertions are made to pass here; the other two are deliberately
left failing for the next task (documenting the gate in the build-loop guides).

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; the single
quality finding was resolved inline; all changed files read end-to-end; all lenses
produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01 — ruff clean on BASE and HEAD; py_compile OK).
- **PR Hygiene:** 0 findings (PH-01..04 all clean).
- **In the changes:** 1 finding (1 medium — resolved inline).
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0 (the one finding was fixed inline, not deferred to a delta).

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | Dependency direction correct (hook → gate, ADR-003); nothing surfaced |
| Security | 0 | 0 | No auth/injection/secrets surface; nothing surfaced |
| Quality | 1 (resolved) | 0 | Never-fatal contract not enforced by code (now fixed) |

### Build Verification (CR-01)

No PR-introduced errors. `ruff check wpx-step12 tests/unit/test_seam_close_gate_wiring.py`
→ "All checks passed!" (tool-outputs/ruff-head.log). `python3 -m py_compile` on both
files → exit 0 (tool-outputs/pycompile.log). The configured linter for this directory
is ruff (`plugins/sulis/scripts/pyproject.toml` has no `[tool.ruff]` section → ruff
defaults). No typechecker is configured for the scripts package; recorded as a coverage
gap in Methodology.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → clean (single concern)
  module_fan_out: 1 top-level dir (plugins/)   → clean
  severity: none

Size (PH-02):
  lines_added: 168, lines_removed: 0, total: 168
  files_changed: 2
  generated_ratio: 0.0
  lock_file_ratio: 0.0
  severity: none (≤200 line / ≤5 file band)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0 (the diff IS the test + the wiring it tests)
  api_change_without_schema: false
  severity: none
```

### Findings in the Changes

#### `plugins/sulis/scripts/wpx-step12` (the `_run_seam_close_gate` helper) — medium (quality) — RESOLVED INLINE

**Quoted text (pre-fix):**
```python
from _seam_close_gate import evaluate  # local import: keeps wrap import-light
brain_base_dir = paths.repo_root / ".brain" / "instances"
result = evaluate(args.wp, index_path=paths.index_md, ...)
return {"verdict": result.verdict, "seam": result.seam_title, "reason": result.reason}
```

**Finding:** The helper's docstring asserted a "best-effort-never-fatal ... if the gate
machinery itself cannot run at all (module absent ...) degrade-open to not-closed so the
wrap still succeeds" guarantee (matching DoD Blue), but the code did not implement it:
the `import` and `evaluate(...)` call were un-guarded. A genuine machinery failure
(absent module, unexpected exception past `evaluate`'s internal `(OSError, ValueError)`
degrade-open) would have propagated out of `cmd_wrap` AFTER the 12.2 flip — leaving the
INDEX flipped to `done` while the wrap reported failure. Contract drift between the
documented never-fatal guarantee and the actual control flow.

**Why it matters:** Conflates the two failure classes DoD Blue requires kept separate:
a machinery/detection failure must NOT fail the wrap (the WP genuinely reached done),
whereas a `blocked` *seam decision* must. The realistic paths (missing brain dir,
unreadable INDEX) were already safe via `evaluate`'s internal degrade-open and the
brain queries returning `[]`; the gap was only the unhandled-exception edge — but the
docstring claimed coverage of exactly that edge.

**Resolution (applied inline, Path A):** Wrapped the import + `evaluate` in
`try/except Exception` that degrades open to `{"verdict": "not-closed", "seam": "",
"reason": "", "gate_error": "<Type: msg>"}` — never fabricating `blocked` or `observed`
on a machinery error. The seam is re-evaluated at the next done-transition and the ship
gate (ADR-002) is the backstop. Verified with a forced-import-failure harness:
machinery error → `not-closed`, error captured, wrap succeeds. Re-ran wiring tests
(3 pass / 2 WP-004-owned still red by design), wpx-step12 integration tests (6 pass),
ruff (clean).

### Findings in the Neighbours

None. The one neighbour module (`_seam_close_gate`, WP-002) is the callee; its internal
degrade-open and reuse of `gate_decision` were verified by behaviour (returns `[]` from
brain queries on a missing dir; catches `(OSError, ValueError)` on `parse_index_md`) but
not modified by this diff.

### Watch List

- **Under `--no-emit-evidence`, a settled seam may re-drive** (TDD Open Question 2 /
  WP-002 module docstring) — wasteful, never wrong. Already a documented, accepted
  degradation owned by WP-002; not introduced by this diff. No action.

### Cross-Reference

- **Existing Hardening Deltas covered:** none.
- **Existing security report:** none for this project.
- **Pattern suggesting full audit:** none — the diff is self-contained wiring.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `ruff check` (configured linter; no ruff config → defaults) + `python3 -m py_compile`. HEAD: 0 errors. No typechecker configured for the scripts package — coverage gap recorded (mypy/pyright not in `pyproject.toml`); ruff + py_compile are the mechanical floor for these stdlib scripts.
- [✓] **CR-02 Single-reader pass justified by diff size: 168 lines, 2 files** (≤200 AND ≤5 → carve-out path).
- [✓] **CR-03 Full-file reads.** Both changed files read end-to-end (wpx-step12 is 200 lines; the wiring test 114 lines). No sampling.
- [✓] **CR-04 Evidence discipline.** The finding cites file + quoted text + the verified resolution.
- [✓] **CR-05 Severity rubric.** 1 medium (contract drift between docstring guarantee and code) — resolved inline. No critical/high/low.
- [✓] **CR-06 Verdict computed.** `PASS`. No auto-downgrade triggers fired (Build Verification empty; all files read end-to-end; all lenses produced output; no PH-03 high).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (dependency direction hook→gate per ADR-003; no infra import, no secrets, no un-timed calls — the runner owns its timeouts). Security: nothing surfaced (no auth/injection/secrets/SSRF surface; brain_base_dir path-derived from repo_root per existing convention). Quality: 1 finding (never-fatal contract drift, resolved) + test-coverage observation (diff ships its own tests) + no JSX (Python diff) + no CR-10 anti-pattern matches (no loops with I/O introduced).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none. PH-02 Size: none (168 lines / 2 files). PH-03 Safety: none (0 migrations/schemas/secrets/infra). PH-04 Completeness: none (tests included). No PH-03 high → no CR-06 auto-downgrade.

#### Run details

- **Diff source:** `git diff change/feat-seam-dod-gate` (local branch, no PR opened — executor Step 6.5 runs pre-push).
- **Neighbour expansion:** git grep / direct read; `_seam_close_gate` is the sole callee.
- **Neighbour cap:** not reached (1 neighbour considered).
- **Scanners run:** ruff (lint), py_compile (compile). Gitleaks/Semgrep/Trivy not run — no secrets/dependency/container surface in a 168-line stdlib Python wiring diff; recorded as the scoped security posture, not a silent skip.
- **Lenses dispatched in parallel:** no — single-reader carve-out (CR-02), diff 168 lines / 2 files.
