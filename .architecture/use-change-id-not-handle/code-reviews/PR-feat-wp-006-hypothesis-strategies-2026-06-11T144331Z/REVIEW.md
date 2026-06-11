# Code Review: WP-006 — Hypothesis strategies module + dev-dependency wiring

> **Timestamp:** 2026-06-11T144331Z (ISO 8601 UTC)
> **Author:** autonomous executor
> **Branch:** feat/wp-006-hypothesis-strategies → change/fix-use-change-id-not-handle
> **Files changed:** 4 (2 authored Python files, pyproject.toml, generated uv.lock)
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds the test-only foundation for a property-based testing layer: a
reusable strategies module that generates change identifiers with controllable
collision structure, plus the one-line wiring that makes the Hypothesis testing
library available in tests (and only in tests). There are no build errors, the
change is tightly scoped to test infrastructure, and every generator is pinned
by its own self-test. One improvement was applied during review — see below.

## What to fix

No issues that need attention. One worth-fixing item was found and already
fixed in this same change (see "Things to take away").

## How this pull request is shaped

**Size — clean.** 322 lines of authored code across two new test files, plus a
one-line dependency addition and its auto-generated lock entry. Well within a
size that can be reviewed thoroughly.

**Scope — clean.** Single concern: stand up the property-test foundation. No
mixing of unrelated changes.

**Safety — clean.** No database migrations, no schema changes, no infrastructure
files, no secrets. The new dependency is test-only; the shipped command-line
tools stay free of it.

**Completeness — clean.** The change is itself test code, and each of the four
generators it exports is pinned by a self-test that proves it does what it
claims.

## Things to take away

1. **An exported helper is part of your public surface even when your own tests
   don't call it.** This change exports four generators; the original self-tests
   pinned three of them plus a derived helper, but left `change_record`
   (consumed later by the next two pieces of work) without a test of its own.
   The fix was to add a small self-test that proves `change_record` produces the
   right shape and a matching handle. Worth doing because the next authors will
   build on it — a foundation everyone depends on earns a test for every piece
   they'll reach for.

---

## Technical detail

> Below this point uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; both
authored files read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (CR-09 / PH-01..PH-04 all `none`)
- **In the changes:** 1 finding (1 medium — resolved inline)
- **In the neighbours:** 0 findings
- **Draft fixes:** 0 (the single finding was fixed inline, not deferred to a delta)

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | nothing surfaced |
| Security | 0 | 0 | nothing surfaced |
| Quality | 1 (resolved) | 0 | `change_record` export unpinned by a self-test |

### Build Verification (CR-01)

No PR-introduced errors. `ruff check` clean on both authored files; `python3 -m
compileall` clean. No type-checker is configured for this repo (branch-ci.yml
line 53: "no type-checker configured"). Tool outputs in `tool-outputs/`.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):    commit_type_spread {feat}; module_fan_out 1   → none
Size (PH-02):     authored 322 lines / 2 files (+ generated lock) → none
Safety (PH-03):   migrations 0; schema 0; infra 0; secrets 0      → none
Completeness(PH-04): new_source_without_test 0                    → none
```

### Findings in the Changes

#### `tests/unit/_change_identity_strategies.py` (export) — medium (quality) — RESOLVED INLINE

**What:** `change_record` is exported as part of the strategies module's public
surface (named in the WP Contract, consumed by WP-007/008) but was not pinned by
any assertion in the self-test (`valid_ulid`, `colliding_ulid_group`,
`change_set`, `planned_collision_groups` were). Its core (`_record_from_id`) is
exercised indirectly via `change_set`, but the `change_record` entry point and
its explicit-`change_id` path were untested.

**Why it matters:** Downstream WPs rely on `change_record`'s shape + handle
agreement; an untested public export can drift silently.

**Resolution (inline, Path A):** Added `test_change_record_shape_and_handle_agree`
— asserts the drawn dict has exactly the six store keys and that
`record["handle"] == ulid_handle(record["change_id"])`. Re-ran the suite (5
passed) and the mechanical baseline (clean). Zero findings remain.

### Findings in the Neighbours

None. The only non-test symbol the diff reaches is `_wpxlib.ulid_handle` /
`validate_change_ulid`, imported read-only as the generators' oracle; not
modified.

### Watch List

None.

### Cross-Reference

- No prior `.security/use-change-id-not-handle/` viability report.
- No existing hardening deltas to cite.
- No neighbour pattern suggesting a broader audit.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `ruff check` + `python3 -m compileall`
  on both authored files. Base + Head both clean; 0 PR-introduced errors. No
  type-checker configured for this repo (documented in branch-ci.yml).
- [✓] **CR-02 Dispatch shape.** Single-reader pass. Justified: only 2 authored
  files (322 lines); the remaining diff is a one-line pyproject change + its
  auto-generated lock entry. File count (2 authored) well under the 5-file bar;
  every line authored by this executor and read end-to-end.
- [✓] **CR-03 Full-file reads.** Both authored files (234 + 88 lines) read
  end-to-end. No sampling.
- [✓] **CR-04 Evidence discipline.** The one finding cites file + the specific
  unpinned export, with the resolving test named.
- [✓] **CR-05 Severity rubric.** 1 medium (test-gap on a public export). No
  inflation.
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade triggers fired
  (Build Verification empty; all files read; all lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (no
  domain→infra import; no singleton/cycle; no HTTP/RPC/DB/timeout/retry/CB
  surface; runtime stays stdlib-only). Security: nothing surfaced (test-only
  dep; no secrets/auth/injection/network; hypothesis is a widely-used dev
  testing engine). Quality: all 7 outputs produced — build follow-up (empty),
  JSX scan (N/A, no templates), dead-surface (1 finding, resolved),
  contract-drift (record shape matches `_changes_matching_handle`'s reads),
  test-coverage (present), style (ruff clean), CR-10 performance (no anti-
  pattern matches — only bounded in-memory list comprehensions, no I/O/N+1/
  O(N²)/unbounded materialisation).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope none; PH-02 Size none; PH-03
  Safety none; PH-04 Completeness none. No PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** `git diff --cached change/fix-use-change-id-not-handle`
- **Neighbour expansion:** git grep on the two imported oracle symbols; both
  read-only, unmodified.
- **Neighbour cap:** not reached (0 neighbour findings).
- **Scanners run:** ruff, compileall. Gitleaks/Semgrep/Trivy not run — no
  secret/injection/CVE surface in a test-only diff (dev dependency only).
- **Lenses dispatched in parallel:** no — single-reader pass per CR-02 carve-out.
