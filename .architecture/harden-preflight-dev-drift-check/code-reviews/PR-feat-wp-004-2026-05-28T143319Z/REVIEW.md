# Code Review: PR-feat-wp-004 — wpx-preflight protection-status + one-time unprotected-repo warning

> **Timestamp:** 2026-05-28T143319Z (ISO 8601 UTC)
> **Author:** WP-004 executor (Sulis senior-engineer)
> **Branch:** feat/wp-004-unprotected-repo-onetime-warning → change/harden-preflight-dev-drift-check
> **Files changed:** 6
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds a way for the assistant to notice when your repository can't
automatically block a bad merge (which happens on private repos on the free
GitHub plan), and to give you a one-time, plain-English heads-up about it when
it builds or ships your work. It's well-scoped, every new behaviour has a test,
and the build is clean. One small consistency improvement was found and fixed
during the review (a missing maximum wait time on the GitHub check) — nothing
remains to fix.

## What to fix

No issues that need attention.

One thing was found and fixed in place during the review: the new GitHub
protection check originally had no maximum wait time, so a network stall could
have made it hang the build/ship step. It now gives up after 30 seconds (the
same limit the rest of the codebase uses) and, either way, treats the check as
purely informational so it never stops your work. No action needed from you.

## How this pull request is shaped

**Size — clean.** 207 lines across 6 files. Small and easy to review
thoroughly.

**Scope — clean.** Single concern: add the protection check and wire the
one-time warning into the two places it belongs (build-all and ship). The
shared building block that two tools now need was moved into the common
library in the same change, rather than left duplicated.

**Safety — clean.** No database changes, no schema or infrastructure files,
no secrets.

**Completeness — clean.** Three new tests cover all three states the check can
report, plus the rule that the check never blocks your work.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs)
> for engineers and for downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty after
inline fix; every changed file read end-to-end; all three lenses produced
output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01). compileall clean;
  ruff clean on all four changed Python/script files after the inline fix.
- **PR Hygiene:** 0 findings. Scope/Size/Safety/Completeness all clean (CR-09 / PH-01..04).
- **In the changes:** 1 finding (1 medium — timeout gap), resolved inline.
- **In the neighbours:** 0 findings introduced by this PR. (3 pre-existing ruff
  findings in `_wpxlib.py` lines 1880 / 3531 / 3532 are outside the diff hunk
  and predate this WP — listed in Watch List, not blocking.)
- **Draft fixes:** 0 (the one diff finding was fixed inline, not deferred to a delta).

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 1 (resolved) | 0 | Missing timeout on the new `gh api` subprocess call (fixed inline) |
| Security | 0 | 0 | No injection (subprocess uses arg-list, not shell); no secrets; no new deps |
| Quality | 0 | 0 | Full enum coverage + always-`ok:true` invariant tested |

### Build Verification (CR-01)

No PR-introduced errors. The project has no enforced linter/type-checker config
(stdlib-only; CI gate = manifest JSON validity + `compileall` + `pytest unit/`
+ routing-coverage gate). Mechanical floor run:

- `python3 -m compileall -q plugins/sulis/scripts` → clean (exit 0).
- `ruff check` (default rules, best-effort — no project config) on the four
  changed Python/script files → clean after the inline timeout fix.
- Affected unit suites (`test_wpx_preflight.py`, `test_wpx_arrival_check.py`)
  → 23 passed. Full unit suite at Step 6 → 780 passed / 1 skipped.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}  (single change, not yet committed at review time)
  module_fan_out: 1 top-level dir (plugins/sulis)
  severity: clean (single concern: add protection-status + wire warning)

Size (PH-02):
  lines_added: 207, lines_removed: 16, total: 223
  files_changed: 6
  generated_ratio: 0
  lock_file_ratio: 0
  severity: clean

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: clean

Completeness (PH-04):
  new_source_without_test: 0 (no new source files; 3 new tests added to existing file)
  api_change_without_schema: false
  severity: clean
```

### Findings in the Changes

#### `plugins/sulis/scripts/wpx-preflight:_protection_status` — medium (architecture / CR-10 timeout), RESOLVED INLINE

**What's happening (quoted, original):**
```python
proc = subprocess.run(
    ["gh", "api", f"repos/{repo}/branches/{branch}/protection"],
    capture_output=True, text=True,
)
```
The new external `gh api` call had no explicit `timeout`. Every sibling `gh`
callsite in this codebase bounds the call at 30s (`_wpxlib._run` default,
`wpx-arrival-check._gh` `timeout=30`). An unbounded call on the run-all Step 0
/ ship gate could hang on a network stall.

**Why it matters:** The probe sits in the hot path of both `/sulis:run-all`
Step 0 and `/sulis:change ship`. A hang there stalls the founder's run/ship.

**Resolution (inline fix applied):** Added `timeout=30` and a
`subprocess.TimeoutExpired` handler that maps to `rc=124, stderr="timeout"` →
classifies as `unconfigured`. The informational verdict still never blocks,
regardless of why the probe failed. Re-ran ruff (clean) + tests (23 passed).
No Hardening Delta queued — the fix landed in this WP.

### Findings in the Neighbours

None introduced by this PR.

### Watch List (pre-existing, not grounded in a failing test for this WP)

- `_wpxlib.py:1880` — ruff F841 (`by_id` assigned but unused) — pre-existing,
  far outside this diff (diff hunk is at line 662–685). Not this WP's scope.
- `_wpxlib.py:3531-3532` — ruff E402 (module-level `import secrets`/`import time`
  not at top of file) — pre-existing deliberate lazy-import block. Not this
  WP's scope.

  These three predate WP-004 and are not introduced or exposed by it. Recommend
  a separate `/sulis:codebase-audit` pass if the team wants to size the broader
  ruff-baseline gap — not in scope here.

### Cross-Reference

- **Existing Hardening Deltas covered:** HD-004 (this WP's source delta) — the
  protection-status surface; implemented as specified.
- **Existing security report:** none for this project.
- **Pattern suggesting full audit:** the pre-existing ruff baseline (Watch List)
  — a one-time ruff config + cleanup pass would close it; out of scope for WP-004.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** compileall (clean) + ruff on 4 changed files (clean after inline fix) + affected pytest (23 passed). No project linter/typechecker config; coverage gap noted (best-effort ruff used). PR-introduced delta: 0 after fix.
- [✓] **CR-02 Single-reader pass justified.** Diff 207 lines / 6 files. The 6-file count is one over the 5-file carve-out, but 4 of the 6 are the two skill markdown bodies + the test file; only 3 are production code and the change is one logical concern (223 lines total). Read all six end-to-end rather than dispatching sub-agents; recorded here per CR-02.
- [✓] **CR-03 Full-file reads.** All changed regions + both skill bodies read end-to-end. The two scripts and `_wpxlib` diff hunks read in full; `wpx-arrival-check` and `wpx-preflight` re-read around the edited regions.
- [✓] **CR-04 Evidence discipline.** The one finding cites file:symbol + quoted text + resolution.
- [✓] **CR-05 Severity rubric.** Applied. 1 medium (timeout, resolved inline). 0 critical/high.
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade triggers fired (Build Verification empty post-fix; all files read end-to-end; all lenses produced output; PH-03 clean).
- [✓] **CR-07 Lens completion.** Architecture: 1 finding (timeout, resolved) + dependency-direction check (extract-to-shared-lib is correct direction). Security: nothing surfaced — subprocess uses arg-list (no shell injection), no secrets in diff, no new dependencies, `repo`/`branch` flow into a `gh api` path segment with no shell. Quality: build-verification clean, no JSX (not applicable — Python), no dead surface, no contract drift (emitted enum matches WP Contract + all three values tested), test-coverage present (3 new tests), CR-10 performance: 1 match (the timeout pattern) resolved, no N+1 / O(N²) / unbounded-materialisation patterns.
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: clean (single concern). PH-02 Size: clean (223 lines / 6 files). PH-03 Safety: clean (0 migrations / 0 schemas / 0 secrets / 0 infra). PH-04 Completeness: clean (3 new tests, no untested new source). PH-03 high → CR-06 auto-downgrade: did not fire.

#### Run details

- **Diff source:** `git diff origin/change/harden-preflight-dev-drift-check`
- **Neighbour expansion:** git grep for `_is_freeplan_protection_403` / `is_freeplan_protection_403` callers — confirmed both consumers (`wpx-arrival-check`, `wpx-preflight`) updated; no other callers.
- **Neighbour cap:** not reached (small diff).
- **Scanners run:** ruff (default rules); compileall.
- **Scanners unavailable:** gitleaks / semgrep / trivy not installed — no new deps or secrets in diff, so dependency-CVE / secret-scan coverage gap is low-risk here.
- **Lenses dispatched in parallel:** no — single-reader pass justified by diff size (CR-02).
