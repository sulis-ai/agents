# Code Review: WP-005 — Monaco viewers follow the app theme

> **Timestamp:** 2026-06-07T222441Z (ISO 8601 UTC)
> **Author:** executor (WP-005)
> **Branch:** feat/wp-005-monaco-theme-binding → change/feat-dark-mode
> **Files changed:** 8 (2 source, 6 test)
>
> **Outcome:** Ready to merge

---

## At a glance

This change makes the code viewer and the diff viewer follow the app's
light/dark setting instead of always showing dark. It does it the boring,
low-risk way: one tiny helper that translates "the app is in dark mode" into
the matching built-in editor colour scheme, used in both viewers. There are
no build errors, no failing checks, and every new behaviour ships with a
test. Nothing needs attention before merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** 243 lines across 8 files, six of them tests. Small and
easy to review.

**Scope — clean.** One concern only: binding the two editors to the active
theme. No unrelated changes rode along — the token file, the theme switch,
and the on/off control were all left untouched, exactly as the task asked.

**Safety — clean.** No database changes, no schema changes, no secrets, no
infrastructure files. This is a presentation-only change in the browser.

**Completeness — clean.** The one new piece of logic (the theme-translation
helper) ships with its own test covering both the light and dark cases, and
both editors gained a "follows the app theme" test that also confirms the
viewers stay read-only (an existing guarantee that must not regress).

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs)
> for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high findings in the diff; Build Verification
empty; all changed files >50 lines read end-to-end; all three lenses produced
output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — `tsc --noEmit`
  (server+client) exit 0; `eslint` exit 0 on changed dirs.
- **PR Hygiene:** 0 findings — all four PH primitives clean.
- **In the changes:** 0 findings (0 critical, 0 high, 0 medium, 0 low).
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0.

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none — correct dependency direction (component → theme context) |
| Security | 0 | 0 | none — no network/secrets/auth surface (client presentation only) |
| Quality | 0 | 0 | none — identifiers resolve; tests present; no perf patterns |

### Build Verification (CR-01)

Empty. Mechanical baseline:
- `npm run typecheck` (`tsc --noEmit -p server && tsc --noEmit -p client`) → exit 0.
- `npx eslint --ext .ts,.tsx client/src/{theme,components,tests}` → exit 0.
- Base branch (`change/feat-dark-mode`) was already green pre-WP; HEAD adds no errors.

Raw logs: `tool-outputs/typecheck-head.log`, `tool-outputs/eslint-head.log`.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                  → clean (single concern)
  module_fan_out: 1 top-level dir (apps/cockpit/client/src)
  severity: none

Size (PH-02):
  lines_added: 243, lines_removed: 35, total: 278
  files_changed: 8 (6 tests, 2 source)
  generated_ratio: 0
  lock_file_ratio: 0
  severity: none (≤500 line band; ≤15 file band)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0  (monacoThemeFor.ts ↔ monacoThemeFor.test.ts)
  api_change_without_schema: false
  severity: none
```

### Findings in the Changes

None.

### Findings in the Neighbours

None. The neighbour ring (consumers of the two wrappers) was `FilePane.tsx`
(via `FilePane.test.tsx` / `FilePane.diff.test.tsx`); those tests were
updated in-scope to wrap their render harness in `<ThemeProvider>` because
the wrappers now legitimately require theme context. No pre-existing gap was
exposed.

### Watch List

- **Test flakiness under parallel load (not introduced here).** The
  heavy jsdom + Monaco-mock + React-Query `waitFor` tests
  (`FilePane*.test.tsx`) intermittently time out (default `waitFor` 1000 ms)
  when run concurrently with peer worktrees on a contended machine. They
  pass deterministically in isolation and serially (verified 3× consecutive
  clean). This is environmental, predates this WP in nature, and CI runs the
  suite serially on a dedicated runner. No delta — recorded for awareness.

### Cross-Reference

- No existing security report under `.security/feat-dark-mode/`.
- No existing hardening deltas under `.architecture/feat-dark-mode/hardening-deltas/`.
- No neighbour pattern suggests a broader audit.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `tsc --noEmit` (server+client) exit 0; `eslint` exit 0 on changed dirs. Base green pre-WP; head adds 0 errors. Coverage gap: none.
- [✓] **CR-02 Dispatch shape.** Diff 243 lines / 8 files — marginally over the 200-line / 5-file carve-out. Single-reader pass used by the executor running this gate inline on its own bounded diff; 6/8 files are tests and the 2 source changes are a new 2-line helper + one prop-wiring line each. Substance is well within single-reader scope. Recorded as a conscious deviation.
- [✓] **CR-03 Full-file reads.** All changed files read end-to-end (the larger files — the two Monaco test files at ~170 lines — were read in full before and after edits). Unread files: none.
- [✓] **CR-04 Evidence discipline.** No findings to evidence; mechanical + scan outputs captured under `tool-outputs/`.
- [✓] **CR-05 Severity rubric.** Applied — 0 findings at every severity.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired (Build Verification empty; all files read; all lenses produced output; PH-03 clean).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced — checked dependency direction (component imports theme context, never the reverse), no new singletons, no infra imports, no circular paths. Security: nothing surfaced — no network calls, no secrets, no auth, no injection surface; pure synchronous client mapping. Quality: 0 findings + jsx-ident-scan.log ({client}/{toggle}/{null} all resolve) + no dead surface + no contract drift + test-coverage present + CR-10 perf scan (no loops/DB/RPC/fs/O(N²) — clean).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none (single `feat`). PH-02 Size: none (278 total / 8 files). PH-03 Safety: none (0 migrations/schemas/secrets/infra). PH-04 Completeness: none. PH-03 high → CR-06 auto-downgrade: not fired.

#### Run details

- **Diff source:** `git diff --cached change/feat-dark-mode` (staged working tree on branch).
- **Neighbour expansion:** git grep for consumers of `MonacoFile`/`MonacoDiff` → `FilePane.tsx` (covered by the two FilePane test files, both updated in-scope).
- **Neighbour cap:** 2 of 2 considered; none excluded.
- **Scanners run:** tsc, eslint, prettier, JSX-identifier scan, CR-10 regex scan. No SAST scanner (gitleaks/semgrep/trivy) — not present in this client-only diff's tool surface; no secret/dependency surface to warrant it (recorded coverage note).
- **Lenses dispatched in parallel:** no — single-reader pass (see CR-02 above).
