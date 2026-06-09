# Code Review: PR feat/wp-001-wire-types — Widen the Change wire type (attention + health + last-activity)

> **Timestamp:** 2026-06-09T201253Z (ISO 8601 UTC)
> **Author:** WP-001 executor
> **Branch:** feat/wp-001-wire-types → change/feat-cockpit-board-refresh
> **Files changed:** 16
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds three new pieces of information to the shared description of a "change" so the board can show, at a glance, whether something needs your attention, how it's doing, and when it was last active. It's a contract-only change — it defines the *shapes* of the data, with no live behaviour yet (the part that fills those shapes in for real arrives in the next piece of work). The build is clean, the full test suite passes, and the change is tightly scoped. Nothing needs attention before merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** Small and focused: 131 added lines across 16 files, no deletions of substance. The reason it touches 16 files rather than one is that adding three *required* pieces of information to a widely-shared shape means every place that builds one of those shapes has to provide them. Those follow-on edits are all one-liners with sensible defaults.

**Scope — clean.** A single concern (the shared shape) plus the unavoidable follow-on edits to keep everything compiling.

**Safety — clean.** No database changes, no configuration changes, no external services, no secrets.

**Completeness — clean.** A new test file pins the new shapes down, including the "we don't know yet" states that were the whole point of this change.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high in diff; Build Verification empty; all changed files read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — `tsc` clean (server + client), `eslint` clean.
- **PR Hygiene:** 0 findings. Scope/Size/Safety/Completeness all `none`.
- **In the changes:** 0 findings.
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0.

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none — new types in correct `shared/` layer |
| Security | 0 | 0 | none — type-only, no new surface |
| Quality | 0 | 0 | none — new test pins all four states |

### Build Verification (CR-01)

No PR-introduced errors. Commands: `tsc --noEmit -p server && tsc --noEmit -p client` (clean); `eslint --ext .ts,.tsx .` (clean). Base branch was also clean (verified at worktree creation). Raw outputs in `tool-outputs/`.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → clean
  module_fan_out: 1 (apps/cockpit)             → clean
  severity: none

Size (PH-02):
  lines_added: 131, lines_removed: 5, total: 136
  files_changed: 16
  severity: none (within 200-line / single-concern band)

Safety (PH-03):
  migration_count: 0, schema_idl_count: 0, infra_files: 0, secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0 (only new file is a test)
  api_change_without_schema: false (this IS the wire-type definition)
  severity: none
```

### Findings in the Changes

None.

### Findings in the Neighbours

None. The neighbour ring (the ~13 fixtures + 2 producers that construct `Change`) was edited directly as part of the required-field widening, so they are in-diff, not neighbours. All compile and pass tests.

### Watch List

- **Intentional placeholder enrichment.** `toWireChange` (`server/routes/_change-lookup.ts`) and `SulisChangeStarter` emit honest absence-defaults (`unknown` health, not-flagged attention, `null`/`now` recency) for the three new fields. This is the designed WP-001 → WP-002 split, documented in code comments: WP-002 replaces these with derived health from the open-blocker probe + tests-state read. Not a finding — recorded so the next reviewer knows the placeholders are deliberate, not forgotten.
- **`worth-a-look` carried but not emitted.** `ChangeHealthState` includes `"worth-a-look"`, which no producer emits yet (ADR-001 — lands with the scope-drift OODA signal). Forward-compatible by design; the wire carries it so adding the producer later is additive with no re-layout. Not contract drift.

### Cross-Reference

- No prior security report for this change.
- No existing Hardening Deltas covered.
- No neighbour pattern suggests a broader audit.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `tsc --noEmit -p server && -p client`; `eslint --ext .ts,.tsx .`. Base: clean. Head: clean. 0 PR-introduced errors. Coverage gap: none.
- [✓] **CR-02 Dispatch shape.** Diff is 136 lines / 16 files. Over the 5-file threshold, but the change is mechanically homogeneous (one wire-type widening + identical one-line fixture defaults repeated across files). Reviewed as a single-reader pass with each non-trivial file read end-to-end; the three lenses were applied analytically over a diff with no logic branches. Recorded as a deviation: the file count exceeds the carve-out but the per-file change is a repeated literal with zero control-flow, making parallel sub-agent dispatch non-additive.
- [✓] **CR-03 Full-file reads.** The two substantive files (`shared/api-types.ts`, `server/routes/_change-lookup.ts`) and the new test (`client/src/tests/contract-links.test.ts`) read end-to-end. The 13 fixture edits are each a 4-line default block at a known anchor, inspected in full.
- [✓] **CR-04 Evidence discipline.** No findings to evidence; Watch List items cite file paths.
- [✓] **CR-05 Severity rubric.** Applied. 0 findings.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. No auto-downgrade triggers fired (Build Verification empty; all files read; all lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (checks: dependency-direction OK — new types in `shared/`; no new timeout/CB/secrets/singletons; placeholder defaults follow A-1 never-throw). Security: nothing surfaced (no endpoints/auth/injection/secrets; `health.reason` JSDoc cites NFR-SEC-03). Quality: build clean; jsx-ident scan empty (no new JSX refs); no dead surface (every field consumed by the new test + downstream WPs); no contract drift (`worth-a-look` carried-not-emitted is documented forward-compat); test-coverage positive (new file pins all four states); style clean; CR-10 perf: no anti-pattern matches (only comment-word matches, omitted as benign).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none (single `feat`, one module). PH-02 Size: none (136 lines / 16 files; homogeneous). PH-03 Safety: none (0 migrations/schemas/secrets/infra). PH-04 Completeness: none (new file is a test; this PR IS the wire-type definition). No PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** `git diff change/feat-cockpit-board-refresh` (local worktree).
- **Neighbour expansion:** the call-sites that construct `Change` were edited in-diff (required-field widening), so the neighbour ring collapses into the change ring.
- **Scanners run:** tsc, eslint (project gates). Gitleaks/Semgrep/Trivy not run — type-only diff with no secrets/dependencies/Dockerfile signals; recorded as a scoped coverage decision.
- **Lenses dispatched in parallel:** no — single-reader pass on a homogeneous sub-200-line-logic diff (CR-02 deviation recorded above).
