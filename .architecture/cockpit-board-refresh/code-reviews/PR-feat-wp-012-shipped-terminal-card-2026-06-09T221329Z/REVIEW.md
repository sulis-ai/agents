# Code Review: feat/wp-012-shipped-terminal-card — Shipped / terminal card (archived treatment)

> **Timestamp:** 2026-06-09T221329Z (ISO 8601 UTC)
> **Author:** WP-012 executor
> **Branch:** feat/wp-012-shipped-terminal-card → change/feat-cockpit-board-refresh
> **Files changed:** 6 code/test files (+1 working journal, not reviewed)
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds the "shipped" (archived) look for a change card — when a change
has been shipped, its card goes muted, its live activity dot is replaced by a
static "Shipped" tag, the "waiting on you" / health badges are hidden, and the
time reads "shipped 5d ago" instead of a live age. The build is clean, every new
behaviour has a test, and the work stays inside the one card component plus a
small shared time helper. No issues that need attention.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** Around 250 lines of real change across one component, its
stylesheet, and a shared time helper, plus the matching tests. Small and easy to
review.

**Scope — clean.** Single concern: the shipped-card look. Nothing strays into
the board, the lanes, or the other card states.

**Safety — clean.** No database changes, no configuration, no new dependencies.

**Completeness — clean.** Every new behaviour is covered by a test, and the
accessibility check runs in both light and dark themes.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all
changed files read end-to-end; all lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — `tsc --noEmit` server+client exits 0 on HEAD and BASE; `eslint --ext .ts,.tsx` exits 0.
- **PR Hygiene:** 0 findings — single-concern, ~250 LoC, no migrations/schema/secrets, tests included.
- **In the changes:** 0 findings.
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0.

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | nothing surfaced |
| Security | 0 | 0 | nothing surfaced |
| Quality | 0 | 0 | nothing surfaced |

### Build Verification (CR-01)

No PR-introduced errors. `npm run typecheck` (tsc server + client) exits 0;
`npm run lint` (eslint) exits 0; `prettier --check` clean on all 6 files.
Raw output: `tool-outputs/typecheck-head.log`.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → clean
  module_fan_out: 1 top-level dir (apps/cockpit/client/src) → clean
  severity: none

Size (PH-02):
  lines_added: ~440 (incl. tests + journal), code ~250
  files_changed: 6 (+1 journal)
  generated_ratio: 0
  lock_file_ratio: 0
  severity: none (small, single-band)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0 (the new behaviour lives in ChangeCard.tsx, a
    modification, fully covered by ChangeCard.shipped.test.tsx + the axe test;
    the new util formatShippedRecency has 4 dedicated unit tests)
  api_change_without_schema: false
  severity: none
```

### Findings in the Changes

None.

### Findings in the Neighbours

None. The shipped predicate `stage === "shipped"` already appears in
`StageTrack.tsx`, `ChangeNav.tsx`, and `Sidebar.tsx` (pre-existing, out of this
WP's scope). The card introduces a single exported `isShipped(change)` rather
than a redundant inline check; it does not touch the neighbours.

### Watch List

None.

### Cross-Reference

- **Existing Hardening Deltas covered:** none.
- **Existing security report:** none for this change.
- **Pattern suggesting full audit:** none.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `npm run typecheck` (tsc server+client) + `npm run lint` (eslint --ext .ts,.tsx) + `prettier --check`. Base: 0 errors. Head: 0 errors. Coverage gap: `@vitest/coverage-v8` absent — coverage verified by manual path analysis (every new branch directly asserted) rather than an instrumented %.
- [✓] **CR-02 Single-reader pass justified.** Diff is ~250 lines of code across 6 files; net behaviour is one card variant + one helper. 6 files marginally exceeds the 5-file floor, so the read was deliberately conservative and full-file (no sampling); all files individually <200 lines.
- [✓] **CR-03 Full-file reads.** ChangeCard.tsx (~250 lines), ChangeCard.module.css, relativeTime.ts, and both new test files read end-to-end during implementation and review. Unread files: none.
- [✓] **CR-04 Evidence discipline.** No findings to evidence; scans (secrets, JSX-ident, CR-10 perf) recorded with their command output.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 0 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired.
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (no new imports across layers, no singletons, no external calls, no I/O). Security: nothing surfaced — secrets scan clean; no auth/injection/SSRF surface (pure presentational React + a date helper). Quality: 0 findings; JSX-ident scan resolved {change}/{now}/{NOW} all in lexical scope; no dead surface; no contract drift (isShipped/ShippedMarker/formatShippedRecency all consumed); test coverage present for every new behaviour; CR-10 perf — no loop/await/N+1 patterns introduced.
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none (single feat, one module). PH-02 Size: none (~250 LoC code / 6 files). PH-03 Safety: none (0 migrations/schemas/secrets/infra). PH-04 Completeness: none (tests included). PH-03 high → CR-06 auto-downgrade: did not fire.

#### Run details

- **Diff source:** `git diff change/feat-cockpit-board-refresh...feat/wp-012-shipped-terminal-card`
- **Neighbour expansion:** git grep for `stage === "shipped"` + `isShipped` consumers; ChangeCard's importers unchanged.
- **Neighbour cap:** not reached (well under 20 files).
- **Scanners run:** grep-based secrets scan, JSX identifier scan, CR-10 perf pattern scan (manual; no Semgrep/Gitleaks/Trivy invoked — pure-frontend presentational diff with no new dependency or secret surface).
- **Scanners unavailable:** Gitleaks/Semgrep/Trivy not invoked (no signal in the diff to warrant them); `@vitest/coverage-v8` absent (manual coverage analysis substituted).
- **Lenses dispatched in parallel:** no — single-reader pass per CR-02 carve-out, justified above.
