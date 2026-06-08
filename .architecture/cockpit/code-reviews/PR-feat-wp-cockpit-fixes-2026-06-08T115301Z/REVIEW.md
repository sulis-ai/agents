# Code Review: feat/cockpit-topbar-and-list-timeout — two cockpit fixes

> **Timestamp:** 2026-06-08T115301Z (ISO 8601 UTC)
> **Author:** Iain Niven-Bowling
> **Branch:** feat/cockpit-topbar-and-list-timeout → main
> **Files changed:** 6 (148 insertions, 4 deletions)
>
> **Outcome:** Ready to merge

---

## At a glance

Two small, well-scoped cockpit fixes. The product selector no longer pokes out
above the top bar (a spacing fix), and the dashboard no longer shows a
"Something went wrong loading your changes" error on a slow first load (a
timeout that was too tight for listing many changes is now generous). Both
fixes have tests, the build is clean, and nothing risky was touched. No issues
that need attention.

## What to fix

No issues that need attention.

## How this pull request is shaped

Small and single-purpose — one `fix:` concern (two related cockpit fixes
requested together), 6 files, ~150 lines, mostly added tests. No database
changes, no infrastructure changes, no new dependencies, no secrets. Both
behaviour changes are covered by tests. This is a clean, easy-to-review
change.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high in diff; Build Verification empty; all
changed files read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — `tsc --noEmit -p server && -p client` exit 0; `eslint --ext .ts,.tsx` exit 0.
- **PR Hygiene:** 0 findings — scope/size/safety/completeness all low.
- **In the changes:** 0 findings.
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0.

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none — dedicated timeout is the correct pattern |
| Security | 0 | 0 | none |
| Quality | 0 | 0 | none (1 awareness note) |

### Build Verification (CR-01)

No PR-introduced typecheck or lint errors. Raw outputs in
`tool-outputs/typecheck-head.log` (exit 0) and `tool-outputs/eslint-head.log`
(exit 0).

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):       commit_type {fix}; module_fan_out 1 (apps/cockpit); severity low
Size (PH-02):        +148 / -4; files 6; generated 0; locks 0; severity low
Safety (PH-03):      migrations 0; schema/idl 0; infra 0; secrets 0; severity low
Completeness (PH-04):new_source_without_test 0; api_change_without_schema false; severity low
```

### Findings in the Changes

None.

### Findings in the Neighbours

None. Neighbour ring (callers/callees of the changed symbols): `createApp`
(receives `gitTimeoutMs` for diff/changed/origin routes — confirmed still
fed the tight `CONFIG.gitTimeoutMs`, NOT the new generous budget — the
separation the fix intends is preserved); `SulisChangeStoreReader`
constructor (accepts `timeoutMs`, default 5000 — unchanged). No gaps
exposed.

### Watch List

- **Adapter generous-budget test is a weak guard in isolation**
  (`change-store-reader.adapter.test.ts`): a reader given
  `CONFIG.changeListTimeoutMs` and a 250 ms stub passes — but it would also
  pass at the old 5000 ms default, so it does not independently prove the
  generous value is wired. It is paired with the load-bearing
  `config.test.ts` which pins `changeListTimeoutMs === 30_000` and
  `> gitTimeoutMs`, and `index.ts` wiring is read directly in this review.
  Acceptable as a behavioural companion; noted for awareness, no change
  required. No failing characterisation test → no Hardening Delta (CR-04).

### Cross-Reference

- Existing Hardening Deltas covered: none.
- Existing security report: none for cockpit.
- Pattern suggesting full audit: none.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `tsc --noEmit -p server && -p client` (exit 0); `eslint --ext .ts,.tsx .` (exit 0). Base (origin/main) and Head both clean; 0 PR-introduced errors. Coverage gap: none.
- [✓] **CR-02 Dispatch shape.** Single-reader pass justified by diff size: 148 lines (mostly additive tests), 6 small cohesive files (4 source/test + the new config test), one logical concern. Just over the 5-file count but well under the 200-line threshold; the change is read end-to-end below.
- [✓] **CR-03 Full-file reads.** All changed files read end-to-end (config.ts 98 L, index.ts diff hunks + surrounding context, ProductSwitcher.module.css 183 L, the two test files). Unread files: none.
- [✓] **CR-04 Evidence discipline.** All observations cite file + the quoted diff. The one awareness item has no failing test → Watch List, not a delta.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 0 low.
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade triggers fired (Build Verification empty; all files read end-to-end; all lenses emitted output).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced — dedicated per-workload timeout is the correct resilience pattern (mirrors `chatBridgeStartupTimeoutMs`); no cross-layer imports; the only resilience-relevant change IS a timeout tuning. Security: nothing surfaced — env knob routed through `parsePositiveIntEnv` (rejects zero/negative/non-integer, preventing a typo from zeroing the watchdog); no secrets/injection/new auth path. Quality: 0 findings; JSX identifier scan N/A (CSS + TS config only); dead-surface none (new config field consumed at 2 sites); contract-drift none; test-coverage — both behaviour changes have tests; CR-10 performance — no loops/queries/materialisation added, 0 matches.
- [✓] **CR-09 PR Hygiene applied.** PH-01 low; PH-02 low; PH-03 low (0 migrations/schemas/secrets/infra); PH-04 low (tests included). No PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** `git diff origin/main` (local branch, pre-push).
- **Neighbour expansion:** git grep over `SulisChangeStoreReader` constructions + `gitTimeoutMs`/`changeListTimeoutMs` consumers.
- **Neighbour cap:** not reached (< 20).
- **Scanners run:** tsc, eslint (project mechanical floor). Gitleaks/Semgrep/Trivy not run — no new secrets/dependency/Docker surface in the diff; recorded as coverage scope, not a gap (diff is CSS + a numeric config constant + its wiring + tests).
- **Lenses dispatched in parallel:** no — single-reader carve-out (see CR-02).
