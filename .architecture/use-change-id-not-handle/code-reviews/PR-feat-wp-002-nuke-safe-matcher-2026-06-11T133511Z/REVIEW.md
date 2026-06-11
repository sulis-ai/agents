# Code Review: PR feat/wp-002-nuke-safe-matcher — nuke resolves via the safe matcher; retire the dead head-prefix rung

> **Timestamp:** 2026-06-11T133511Z (ISO 8601 UTC)
> **Author:** sulis-execution executor (WP-002)
> **Branch:** feat/wp-002-nuke-safe-matcher → change/fix-use-change-id-not-handle
> **Files changed:** 3 (1 logic, 1 test, 1 docs)
>
> **Outcome:** Ready to merge

---

## At a glance

This change routes the `nuke` command through the same safe lookup the other
change commands already use, and removes a dead piece of code that could never
match anything. The build is clean — no errors, and 42 tests pass including
4 new ones written for this change. Nothing needs fixing before merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** 414 added / 102 removed across 3 files. Most of the
"removed" lines are a dead helper function and its docstring; most of the
"added" lines are the new test file and clearer docstrings. Single, focused
concern.

**Scope — clean.** One concern: make `nuke` resolve a change the safe way and
drop the dead lookup rung. No unrelated changes bundled in.

**Safety — clean.** No database migrations, no schema/IDL changes, no infra
files, no secrets. The change actually *strengthens* safety: when a short
handle is shared by more than one change, `nuke` now refuses and lists the
candidates (with each change's readable name) instead of risking the wrong one.

**Completeness — clean.** 4 new tests for the new behaviour: a characterisation
test pinning the dead rung before removal, a test that a new-style handle
resolves to its exact change, a test that a colliding handle refuses with the
readable-name list, and a test for the new exact-id selector.

---

## Technical detail

> Below this point uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; the
one logic file was read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01). ruff: BASE 4 / HEAD 4
  (identical pre-existing F401 set, unrelated to the touched functions). pytest:
  42 passed across the change/nuke/safe-resolution/collision suites.
- **PR Hygiene:** 0 high, 0 medium (CR-09 / PH-01..PH-04). Single concern,
  small, no migrations/schemas/secrets, tests included.
- **In the changes:** 0 findings.
- **In the neighbours:** 1 note (pre-existing, no delta).
- **Draft fixes:** 0.

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | — (improves WPB-04 single-source-of-truth: one handle matcher across all four verbs) |
| Security | 0 | 0 | — (`--change-id` never builds a path; no injection surface) |
| Quality | 0 | 1 | pre-existing per-branch `list_all_changes()` scan (bounded-N benign) |

### Build Verification (CR-01)

None. ruff error count identical on BASE and HEAD (4 pre-existing F401 unused
imports: `_gh_ref_sha`, `add_common_args`, `emit_internal_error`,
`parse_change_branch` — none in the touched functions; left untouched to avoid
colliding with WP-001's concurrent edit of the same file's import block). New
test file passes ruff check + format clean. 42 tests green.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):      single concern (WP-002)                       → severity low
Size (PH-02):       +414 / -102, 3 files                          → severity low
Safety (PH-03):     migrations 0, schemas 0, secrets 0, infra 0   → severity none
Completeness (PH-04): new_source_without_test 0, new_tests 1      → severity none
```

### Findings in the Changes

None.

### Findings in the Neighbours

#### `_resolve_change_id` rung-0 loop — note (CR-10 pattern: repeated full-store scan in a loop)

`_resolve_nuke_target` enumerates branches and calls `_resolve_change_id` per
branch; rung 0 of `_resolve_change_id` iterates `list_all_changes()` (a full
state-store scan reading every `change.json`). This is **pre-existing** — the
base code already called `_resolve_change_id` per candidate. This PR adds one
*additional* `list_all_changes()` call (the `intents` map) but outside the loop,
so it is O(changes) once, not per-branch. Context (CR-03 read): `nuke` is an
interactive, rare destructive operation over a realistically small change count
(the SPEC's live state is 26 changes); not a hot path. Downgraded to a note per
CR-10 (benign, bounded N). No delta. If the store ever grows large, a single
`list_all_changes()` hoisted and shared across the loop would remove the
per-branch repetition — recommend a future `/sulis:codebase-audit` only if the
change count grows by an order of magnitude.

### Watch List

- The 4 pre-existing F401 unused imports in `sulis-change` are real but
  out-of-scope here (shared import-block territory with WP-001). A dedicated
  import-cleanup WP after both Wave-1 WPs merge would close them without merge
  conflict.

### Cross-Reference

- No prior `.security/{project}/viability-report-*.md`.
- No existing hardening-deltas to cite.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** ruff check on BASE (4) vs HEAD (4) — 0 PR-introduced; pytest 42 passed. Coverage gap: none (coverage tool absent; correctness floor via full pass of the touched suites).
- [✓] **CR-02 Dispatch shape.** Diff 622 lines / 3 files. Above the line threshold; however only ONE file carries logic (`sulis-change`); the other two are a new test file + markdown docs. The single logic file (208-line diff) was read end-to-end by all three lenses sequentially in this session rather than via parallel sub-agents — justified: 2 of 3 files are non-logic, lens work concentrated on one cohesive function cluster. Recorded as the conservative read.
- [✓] **CR-03 Full-file reads.** `sulis-change` diff read end-to-end; the new test file authored in-session (fully known); SKILL.md docs edit is a 7-line additive paragraph.
- [✓] **CR-04 Evidence discipline.** The one neighbour note cites the function + the base-vs-head provenance.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical / 0 high / 0 medium / 0 low in changes; 1 neighbour note.
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade triggers fired (Build Verification empty; all files read; all lenses produced output; no PH-03 high).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced — checked WPB-01..12 (no new ports/adapters/external calls/secrets; change improves WPB-04). Security: nothing surfaced — SEC-01..07 (no injection/path-traversal: `--change-id` is match-only + label-only, never path-constructing; no secret/PII exposure). Quality: nothing surfaced — 7/7 outputs (build clean, JSX N/A, no dead surface, no contract drift, tests present, style clean, CR-10 perf = 1 pre-existing benign note).
- [✓] **CR-09 PR Hygiene applied.** PH-01 low, PH-02 low, PH-03 none, PH-04 none. No auto-downgrade.

#### Run details

- **Diff source:** git diff change/fix-use-change-id-not-handle...feat/wp-002-nuke-safe-matcher
- **Neighbour expansion:** git grep for callers of `_resolve_change_id`, `_scan_state_dir_by_prefix`, `_emit_ambiguous_match`, `_changes_matching_handle` — confirmed sole/updated callers.
- **Neighbour cap:** not reached.
- **Scanners run:** ruff (lint), pytest (correctness). Gitleaks/Semgrep/Trivy not invoked — diff carries no dependency/secret/Docker surface (manual SEC review against the 25 primitives, scoped to the diff, found no applicable signal).
- **Scanners unavailable:** coverage tool (manual analysis used at Step 4).
