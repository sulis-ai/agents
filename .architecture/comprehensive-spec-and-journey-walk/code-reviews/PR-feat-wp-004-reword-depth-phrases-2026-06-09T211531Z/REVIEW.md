# Code Review: WP-004 — Reword the depth proposal phrases to describe interview size

> **Timestamp:** 2026-06-09T211531Z (ISO 8601 UTC)
> **Author:** autonomous executor (WP-004)
> **Branch:** feat/wp-004-reword-depth-phrases → change/harden-comprehensive-spec-and-journey-walk
> **Files changed:** 2
>
> **Outcome:** Ready to merge

---

## At a glance

This change reworks the small set of plain-English phrases the assistant uses when it proposes how to run the specify conversation. Before, those phrases described how *short the document* would be ("a quick lite spec, three lines"); now they describe how *short the conversation* will be ("a few quick questions"). That is exactly the intended fix. There are no build errors, the change is tiny and well-scoped, and it ships with two tests that lock the new wording in place. Nothing needs your attention before merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

Small and single-purpose. Two files: the phrase definitions and their tests. One concern (the wording), one type of change (a wording refactor). This is the ideal shape — easy to review, easy to roll back if ever needed.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high findings in the diff; Build Verification empty; both changed files read end-to-end; all lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (PH-01..PH-04 all clean)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | nothing surfaced |
| Security | 0 | 0 | nothing surfaced |
| Quality | 0 | 0 | nothing surfaced |

### Build Verification (CR-01)

`python3 -m compileall` — OK on both files. `ruff check` — All checks passed. No PR-introduced errors.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {refactor}               → clean (single concern)
  module_fan_out: 1 distinct top-level dir (plugins/sulis/scripts)
  severity: none

Size (PH-02):
  lines_added: 77, lines_removed: 6, total: 83
  files_changed: 2
  generated_ratio: 0.0
  lock_file_ratio: 0.0
  severity: none (<=200 line / <=5 file carve-out)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0 (source change ships with 2 new tests)
  api_change_without_schema: false
  severity: none
```

### Findings in the Changes

None.

Lens notes:
- **Architecture lens: nothing surfaced.** Checks run: no new imports, no singletons, no I/O, no external calls, no resilience primitives. The change is two string-literal dicts (`_DEPTH_PHRASE`, `_DEPTH_ALT`) in a pure, deterministic module (C-03 preserved). `classify_depth` signature/behaviour untouched.
- **Security lens: nothing surfaced.** Primitives checked: SEC-01..07, SC-01..04. No secrets (scan clean), no injection surface, no auth surface, no new dependencies. Diff is founder-facing prose only.
- **Quality lens:** (1) Build Verification: 0 errors. (2) JSX scan: n/a (no TSX/JSX/Vue/Svelte). (3) Dead-surface: none — both reworded dicts are consumed by `proposal_sentence`. (4) Contract-drift: none — keys (`lite`/`standard`/`deep`) unchanged; only values reworded. (5) Test coverage: source change ships with a characterisation test pinning all 6 strings + a behavioural test asserting the FR-04 invariant; the existing founder-English test (`test_proposal_sentence_is_founder_english_for_lite`) still passes (the reworded lite phrase keeps "quick"). (6) Style: clean, ruff green; added a short rationale comment citing FR-04. (7) Performance (CR-10): no anti-pattern matches; the only loop is a bounded 3-element iteration inside the new test.

### Findings in the Neighbours

None. The one neighbour — `proposal_sentence()` — composes `decision.reason` + the reworded phrase + alt. Note for awareness (not a finding for this WP): the `classify_depth` `reason` strings still contain document-shape language ("three-line spec", "the standard spec"). That is explicitly outside this WP's named scope (`_DEPTH_PHRASE`/`_DEPTH_ALT` only) and is owned by WP-005 (sever the depth→doc-shape branch, TDD §7.3). Surfaced once here for traceability; no action in this WP.

### Watch List

- The composed `proposal_sentence` output still embeds the WP-005-owned `reason` doc-shape wording. Tracked by WP-005; no delta drafted (no failing characterisation test belongs in this WP per CR-04).

### Cross-Reference

- **Existing Hardening Deltas covered:** none
- **Existing security report:** none
- **Pattern suggesting full audit:** none

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `python3 -m compileall` (OK), `ruff check` (All checks passed). Base + Head both clean; 0 PR-introduced errors. Full unit suite (2429 passed, 9 skipped) run at Step 6. Coverage gap: none.
- [✓] **CR-02 Single-reader pass justified by diff size: 83 lines, 2 files** (within ≤200 line / ≤5 file carve-out).
- [✓] **CR-03 Full-file reads.** Both changed files read end-to-end (source 261 lines, test 222 lines). Unread files: none.
- [✓] **CR-04 Evidence discipline.** No findings to evidence; lens notes cite the exact symbols + scope reasons.
- [✓] **CR-05 Severity rubric.** Applied; 0 findings at any severity.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. No auto-downgrade triggers fired (Build Verification empty; all files read end-to-end; all lenses produced output; PH-03 clean).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced + reason. Security: nothing surfaced + primitives listed. Quality: all 7 outputs produced.
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none (single `refactor` concern). PH-02 Size: none (83 lines / 2 files). PH-03 Safety: none (0 migrations/schemas/secrets/infra). PH-04 Completeness: none (source ships with tests). PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** `git diff change/harden-comprehensive-spec-and-journey-walk` (local branch, no PR yet — branch-CI is the gate)
- **Neighbour expansion:** git grep — only `proposal_sentence` consumes the changed dicts; no other consumers of `_DEPTH_PHRASE`/`_DEPTH_ALT` exist
- **Neighbour cap:** 1 of 1 considered (well under 20)
- **Scanners run:** ruff, compileall, manual secret-pattern grep
- **Scanners unavailable:** Gitleaks/Semgrep/Trivy not installed (stdlib-only repo); manual grep substitute run — no secret patterns
- **Lenses dispatched in parallel:** no — single-reader pass per CR-02 carve-out
