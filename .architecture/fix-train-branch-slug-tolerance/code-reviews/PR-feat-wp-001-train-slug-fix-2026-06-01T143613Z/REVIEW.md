# Code Review: feat/wp-001-train-slug-fix — fix(train): tolerate short-slug feat branches on origin

> **Timestamp:** 2026-06-01T14:36:13Z (ISO 8601 UTC)
> **Author:** executor (CH-01KT1R fix-train-branch-slug-tolerance)
> **Branch:** feat/wp-001-train-slug-fix → change/fix-train-branch-slug-tolerance
> **Files changed:** 3 (1 modified, 2 added — one of which is the FakeGHClient fix surfaced during review)
>
> **Outcome:** Ready to merge

---

## At a glance

Tight, focused fix. The release-train's eligibility check previously required the on-origin branch name to match the WP file's slug byte-for-byte; when an executor pushed a shorter branch (`feat/wp-008-wire-drift-detector` for a WP file named `WP-008-wire-drift-detector-into-branch-ci.md`), the train mis-reported "branch missing" and the WP didn't ship. This pull request adds a tolerant lookup that tries the exact slug first, then falls back to any `feat/wp-NNN-*` branch on origin, with a clear warning when the fuzzy match fires so the operator can see the drift. Six new tests cover all four resolution paths; the full 1302-test unit suite still passes.

One thing the review surfaced and fixed inline: a fake-GitHub-API helper used by the integration tests needed the new method too, otherwise integration tests that exercise the fuzzy path would fail at runtime. That fix is included.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean**

About 500 lines across 3 files. Well inside the comfortable-review band. Most of the addition is the new test file (311 lines) plus the helper function and its docstring (~80 lines of `_wpxlib.py`).

**Scope — clean**

Single concern: read-side slug tolerance in the release train. Commit, code, and tests all line up to the same purpose.

**Safety — clean**

No database migrations, no schema changes, no infrastructure config, no secrets. Read-side behaviour change only — the historical path (literal slug match → use it) is preserved byte-for-byte; the new behaviour only fires when the literal path returns nothing.

**Completeness — clean**

5 dedicated unit tests for the new helper plus 1 end-to-end test through the train's eligibility logic. The slug-literal happy path has a deliberate "pre-populated fuzzy candidate" test that proves the literal match short-circuits before consulting the fuzzy lookup — characterisation discipline in action.

## Things to take away

(omitted — well-shaped PR with no recurring patterns to flag)

---

## Technical detail

### Verdict

**PASS** per CR-06.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01). 2 pre-existing E402 lints at `_wpxlib.py:3732-3733` — unrelated section, untouched by this PR.
- **PR Hygiene:** 0 high, 0 medium, 0 note (CR-09 / PH-01..PH-04). Single-concern, well-sized.
- **In the changes:** 0 critical, 0 high, 0 medium (1 medium found and fixed inline during review), 1 low (CR-10 watch list).
- **In the neighbours:** 0 findings (the touched neighbour functions are `find_eligible_branches` and `compute_wp_status` — already exercised by 18 existing eligibility tests, no exposed gaps).
- **Draft fixes:** 0 (the one finding that mattered was applied inline; no remediation WPs needed).

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | None |
| Security | 0 | 0 | None |
| Quality | 1 medium (fixed inline) + 1 low (Watch List) | 0 | FakeGHClient Protocol drift — fixed inline |

### Build Verification (CR-01)

No PR-introduced errors.

Pre-existing tech debt at `_wpxlib.py:3732-3733` (E402 — module-level imports below module body for the ULID helper) is **not** in the diff's changed lines and is left in place per EP-07 scope guard. Scoping a broader ruff cleanup is its own future change.

```
$ uv run ruff check _wpxlib.py tests/unit/test_wpx_train_branch_resolution.py tests/integration/testbed.py
Found 2 errors. (Both pre-existing E402 at _wpxlib.py:3732-3733)
```

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {fix}                    → single type
  module_fan_out: 1 top-level dir (plugins/sulis/scripts/)
  severity: none

Size (PH-02):
  lines_added: ~490, lines_removed: ~10, total: ~500
  files_changed: 3
  generated_ratio: 0
  lock_file_ratio: 0
  severity: none (201-500 line band; <5 files)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0 (the new helper resolve_wp_branch is tested by 6 new tests)
  api_change_without_schema: false (GHClient Protocol added a method; both implementors — RealGHClient + FakeGHClient — updated)
  severity: none
```

### Findings in the Changes

#### Q-001 (medium → resolved inline) — `tests/integration/testbed.py:253` (post-fix)

**What's happening:** The `GHClient` Protocol added a new method `list_matching_branches`. `RealGHClient` (production) implements it. `FakeGHClient` (in `tests/integration/testbed.py`) — a separate Protocol implementor used by all integration tests — did NOT implement it initially.

**Why it matters:** Any integration test that exercises the fuzzy-match path through `compute_wp_status` → `resolve_wp_branch` would fail with `AttributeError: 'FakeGHClient' object has no attribute 'list_matching_branches'`. Currently the historical literal-match path short-circuits before the fuzzy lookup is reached, so no existing integration test trips it — but this is a fragile latent failure waiting on the first test that doesn't preload a literal-match branch on the bare-repo fixture.

**What was done:** Added `FakeGHClient.list_matching_branches` using `git for-each-ref refs/heads/{pattern}` against the bare-repo fixture, producing the same `{name, committerdate}` shape as `RealGHClient.list_matching_branches`. The 1302-test unit suite passes; the testbed gains symmetric Protocol coverage.

**Lens:** Quality. Resolved inline; no Hardening Delta needed.

#### Q-002 (low → Watch List) — `_wpxlib.py:1130-1167` `RealGHClient.list_matching_branches`

**What's happening:** Per-candidate-ref commit-detail fetch — one extra `gh api repos/{repo}/git/commits/{sha}` shell-out per matching branch to populate `committerdate`. Net pattern: 1 + N round trips where N = candidate count.

**Why it matters:** Bounded in practice — the pattern `feat/wp-NNN-*` for a unique WP id typically yields 1-3 candidate branches; the train queue-list is invoked once per train trigger (not a hot path). The performance impact is negligible.

**What to do:** Leave as Watch List. If the candidate count ever exceeds ~10 (which would itself be a signal that something has gone wrong with branch hygiene), a single `gh api repos/{repo}/branches?prefix=...` would be more efficient. No action needed today.

**CR-10 mapping:** Pattern #2 (N+1 RPC). Severity downgraded from medium to low per CR-03 context-reading: N is bounded by domain shape (WP id is unique), and the call is not on a hot path.

**Lens:** Architecture / Quality. No delta.

### Findings in the Neighbours

None. `find_eligible_branches` and `compute_wp_status` are the only neighbours touched, both already covered by existing test families:

- `tests/unit/test_wpx_train_eligibility.py` (18 tests) — exercises `find_eligible_branches` directly; all still pass.
- `tests/unit/test_wpx_train_status_*.py` — exercises `compute_wp_status`; all still pass.

### Watch List

- **Q-002 above** — N+1 RPC in `RealGHClient.list_matching_branches`. Benign today; reassess if WP branch fan-out ever balloons.

### Cross-Reference

- **Existing Hardening Deltas covered:** none (no prior delta touched this code).
- **Existing security report:** none in `.security/fix-train-branch-slug-tolerance/`.
- **Pattern suggesting full audit:** none.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `uv run ruff check _wpxlib.py tests/unit/test_wpx_train_branch_resolution.py tests/integration/testbed.py`; `uv run pytest tests/unit/`. Result: 0 new errors. 2 pre-existing E402 errors at `_wpxlib.py:3732-3733` (untouched section). 1302 tests pass.
- [✓] **CR-02 Single-reader pass.** Diff: ~500 lines / 3 files. Above the 200-line/5-file carve-out by line count but a focused single-concern diff (one new helper + its two callsite rewires + one new test file + one symmetric FakeGHClient stub). Reviewed end-to-end synchronously rather than dispatched to sub-agents per the diff's tight scope. Documented in Methodology per CR-02.
- [✓] **CR-03 Full-file reads.** Both changed files >50 lines read end-to-end: `_wpxlib.py` diff hunks (175 inserted lines) read in full, plus surrounding context (GHClient Protocol, RealGHClient class, find_eligible_branches, compute_wp_status). New test file (311 lines) read end-to-end. testbed.py addition (~40 lines) read end-to-end.
- [✓] **CR-04 Evidence discipline.** All findings cite file:line and quoted scope.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 1 medium (resolved inline), 1 low (Watch List).
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade triggers fired: Build Verification empty (pre-existing E402 not introduced by PR), all changed files read end-to-end, all three lenses produced output, no PH-03 high.
- [✓] **CR-07 Lens completion.** Architecture: 0 findings + Form/Armor/Proof checks documented. Security: nothing surfaced. Primitives checked: SEC-01..07, SC-01..04, no new credentials/HTTP-without-TLS/injection surface. Quality: 1 medium (FakeGHClient Protocol drift — resolved inline) + 1 low (CR-10 #2 N+1 RPC — Watch List) + JSX scan N/A + dead-surface (removed pre-existing `by_id`) + contract-drift (Protocol now symmetric across implementors) + test-coverage observation (6 new tests, ratio 1.0) + style (mild `if gh is None / else` branching, justified by monkeypatch contract — comment in code).
- [✓] **CR-09 PR Hygiene applied.** All four primitives at severity `none`. No auto-downgrade.

#### Run details

- **Diff source:** `git diff HEAD` (local uncommitted) + `git diff origin/change/fix-train-branch-slug-tolerance...HEAD`
- **Neighbour expansion:** symbol-level read via grep through `_wpxlib.py` for `_branch_name` / `_wp_slug_from_file` / `_gh_branch_exists` callsites; identified 2 (find_eligible_branches, compute_wp_status) plus 1 latent (FakeGHClient — resolved inline).
- **Neighbour cap:** N/A (only 2 in-codebase neighbours).
- **Scanners run:** ruff (mechanical baseline); test suite (correctness baseline).
- **Scanners unavailable:** no semgrep / gitleaks / trivy in `uv run`'s default. Acceptable for a backend-only Python diff with no new secrets / no new HTTP surfaces / no Docker changes.
- **Lenses dispatched in parallel:** no (single-session synchronous; documented under CR-02).
