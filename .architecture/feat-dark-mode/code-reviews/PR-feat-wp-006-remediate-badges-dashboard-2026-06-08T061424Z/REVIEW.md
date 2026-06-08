# Code Review: feat/wp-006-remediate-badges-dashboard — Tokenise the dashboard change-card surface

> **Timestamp:** 2026-06-08T061424Z (ISO 8601 UTC)
> **Author:** executor (WP-006)
> **Branch:** feat/wp-006-remediate-badges-dashboard → change/feat-dark-mode
> **Files changed:** 4 (3 CSS + 1 new test)
>
> **Outcome:** Ready to merge

---

## At a glance

This change swaps the hard-coded colours in the stage badges and the dashboard
error banner for named theme colours, so they switch correctly between light
and dark mode. Light mode looks identical to before for the badges (the new
light values are the exact same colours that were there). There are no build
errors, the change is tightly scoped to the two files it was meant to touch,
and it ships with a test that proves no raw colours are left behind. Nothing
needs fixing.

## What to fix

No issues that need attention.

One thing worth knowing (not a problem): the dashboard *error banner* now uses
the project's standard "error" colour as a solid fill. Previously it was a
soft pink tint. In light mode that means the error banner is now a stronger
red than before — this is the intended result of mapping it to the shared
error colour the rest of the app uses, and the task description asked for
exactly that mapping. The stage badges (the part the task required to look
pixel-identical in light mode) are unchanged.

## How this pull request is shaped

**Size — clean.** 4 files, ~45 lines of real change plus one focused test
file. Small and easy to review.

**Scope — clean.** Single concern: replacing raw colours with theme tokens in
the dashboard change-card surface. No unrelated changes mixed in.

**Safety — clean.** No migrations, no schema changes, no infrastructure, no
secrets. Presentation-layer CSS only.

**Completeness — clean.** Ships with its own test
(`no-raw-colours.badges.test.ts`) that pins both the "no raw colours" rule and
the exact light + dark colour values.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs)
> for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all
files read end-to-end (the only file >50 lines is the authored test, read in
full); all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — `tsc --noEmit -p client` exit 0, `eslint` exit 0.
- **PR Hygiene:** 0 findings (PH-01..04 all clean/low).
- **In the changes:** 0 findings (0 critical, 0 high, 0 medium, 0 low).
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0.

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | nothing surfaced |
| Security | 0 | 0 | nothing surfaced |
| Quality | 0 | 0 | nothing surfaced (1 design observation, non-finding) |

### Build Verification (CR-01)

No PR-introduced typecheck or lint errors. `tool-outputs/typecheck-head.log`
and `tool-outputs/eslint-head.log` are both empty (clean). One TS2532
strict-index error was introduced and fixed during Step 6 before this review
(see the WP journal self-heal log); it is not present at review time.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {refactor}               → clean (single concern: tokenisation)
  module_fan_out: 1 top-level dir (apps/cockpit/client/src)
  severity: low

Size (PH-02):
  lines_added: ~331 (296 = the new test file), lines_removed: 10
  files_changed: 4
  generated_ratio: 0
  lock_file_ratio: 0
  severity: low (real CSS change ~45 lines; bulk is the focused test)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: low

Completeness (PH-04):
  new_source_without_test: 0 (the change ships its own test)
  api_change_without_schema: false
  severity: low
```

PH-03 high → CR-06 auto-downgrade: not fired.

### Findings in the Changes

None.

### Findings in the Neighbours

None. The badge classes `.shipped` / `.unknown` (terminal stages, out of WP
scope) already use `var(--muted*)` tokens and are correct; they were not
touched. `StageBadge.tsx` and `Dashboard.tsx` consume these classes by name
and are unaffected by the value/token swap.

### Watch List

- **Light-mode error-banner appearance change (design observation, not a
  finding).** `Dashboard.module.css .errorBox` moved from a soft pink tint
  (`#ffeef0` bg / `#fdb8c0` border / `#86181d` text) to the shared destructive
  token family (`var(--destructive)` filled / `var(--destructive-foreground)`
  text). This is the boring, in-Contract mapping the WP-006 Contract specified
  ("map dashboard error colours to the existing `--destructive*` tokens") — no
  soft-tint destructive token exists in `tokens.css`, so the filled-banner form
  is the established convention. The WP makes light-mode-pixel-unchanged an
  explicit requirement only for the *badges*, not the error chrome. Both light
  (`#DC2626` bg / white text) and dark (`#f0686b` bg / `#1a0b0c` text) pairings
  clear WCAG AA. No action required; recorded for awareness in case the founder
  prefers a softer tinted error surface, which would be a separate token-design
  WP.

### Cross-Reference

- **Existing Hardening Deltas covered:** none.
- **Existing security report:** none.
- **Pattern suggesting full audit:** none. (The broader 32-site raw-colour
  remediation is already decomposed across WP-006/007/008 per TDD §2.)

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `npx tsc --noEmit -p client` (exit 0); `npx eslint client/src/tests/no-raw-colours.badges.test.ts` (exit 0). Working-tree HEAD vs base `change/feat-dark-mode`. 0 PR-introduced errors. Coverage gap: none (CSS files have no typechecker; covered by the parsing test instead).
- [✓] **CR-02 Single-reader pass.** Diff: 4 files, ~45 lines of real CSS change + 1 authored 296-line test. The only >50-line file is the test the reviewer authored and read end-to-end. Justified by file count (4 ≤ 5) and the trivial, mechanical nature of the CSS diff (literal → var() swap + token additions with values pinned by the test).
- [✓] **CR-03 Full-file reads.** All changed files read end-to-end: tokens.css, StageBadge.module.css, Dashboard.module.css, no-raw-colours.badges.test.ts (296 lines). Unread files: none.
- [✓] **CR-04 Evidence discipline.** No findings raised; the one design observation cites file + exact before/after values.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 0 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired.
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced — checks run: dependency-direction (no imports), singletons (none), circular imports (none), external calls/timeouts/CB (none — CSS only), observability (n/a). Security: nothing surfaced — primitives checked SEC-01..07 (no auth/injection/validation/secrets surface — CSS custom properties only), SC-01..04 (no dependency change). Scanners: n/a for a CSS-only diff (no secret/dep surface); recorded as coverage note. Quality: (1) Build Verification follow-up — none; (2) JSX/template identifier scan — n/a (no TSX/JSX in diff; the test is plain TS); (3) dead-surface — none (all six new token trios are referenced by StageBadge; all referenced tokens are defined); (4) contract-drift — none (token names match between tokens.css definitions and StageBadge var() refs, verified by the test); (5) test-coverage — the change ships its own test covering all new behaviour; (6) style/readability — clean, comments present and accurate; (7) CR-10 performance — no anti-pattern matches (no loops, queries, or hot paths in a CSS diff).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: low (single refactor concern). PH-02 Size: low (4 files; real change ~45 lines). PH-03 Safety: low (0 migrations/schemas/secrets/infra). PH-04 Completeness: low (ships its own test). PH-03 high → CR-06 auto-downgrade fired: no.

#### Run details

- **Diff source:** `git diff change/feat-dark-mode` (working tree — uncommitted; Step 7 commits after this gate).
- **Neighbour expansion:** manual — StageBadge.tsx + Dashboard.tsx (consumers of the changed CSS-module class names) inspected; both unaffected by a value/token swap. tokens.dark.test.ts (set-equality over the colour tokens) re-run green.
- **Neighbour cap:** not reached (3 neighbours considered).
- **Scanners run:** tsc, eslint. Gitleaks/Semgrep/Trivy: not run — no secret/code/dependency surface in a CSS + CSS-parsing-test diff (coverage note, not a gap).
- **Lenses dispatched in parallel:** no — single-reader pass per CR-02 carve-out (justified above).
