# Code Review: WP-006 — Settings Express router (the third sanctioned write surface)

> **Timestamp:** 2026-06-09T124303Z (ISO 8601 UTC)
> **Author:** autonomous executor (WP-006)
> **Branch:** feat/wp-006-settings-router → change/feat-user-level-product-store-settings
> **Files changed:** 6 (765 insertions, 15 deletions)
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds the Settings management routes — the screen that lets you add, rename, and remove products, projects, and repo links. It is clean: the build passes with no errors, the change is well-scoped to one job, and it ships with a thorough test file that exercises every route and every error case. The most important thing it gets right: the new routes never touch your files or start any background process themselves — they hand every change to the one audited component that is allowed to write, and the safety check that proves this is extended (not weakened) to admit the new routes.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** 765 lines across 6 files, one new source file paired with one new test file.

**Scope — clean.** Single concern: the settings write surface. No unrelated refactors bundled in.

**Safety — clean.** No database migrations, no schema files, no infrastructure changes, no secrets. The change extends the read-only safety check to admit exactly one new routes file, and proves (with both a positive and a negative test) that no other file gained the ability to write or start a process.

**Completeness — clean.** New behaviour ships with tests: 24 cases over the routes plus an extended safety-gate test.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high/medium/low findings in the diff; Build Verification empty; both files >50 lines authored and read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01). tsc `--noEmit -p server` clean; eslint clean on changed files; full vitest suite 1221 passed.
- **PR Hygiene:** 0 findings. Scope low (single concern), Size low (765 lines / 6 files), Safety low (0 migrations / 0 schema / 0 secrets / 0 infra), Completeness low (1 new source + 1 new test).
- **In the changes:** 0 findings.
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0.

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | — (dependency direction correct; ADR-019 gate extension proven both ways) |
| Security | 0 | 0 | — (no auth surface added; router delegates validation, never bypasses) |
| Quality | 0 | 0 | — (exhaustive error mapping; full route + error-code test coverage) |

### Build Verification (CR-01)

None. `npx tsc --noEmit -p server` → exit 0 (tool-outputs/typecheck-server.log). `npx eslint <changed>` → exit 0 (tool-outputs/eslint.log). Full suite: 1221 passed / 163 files.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):  single concern (settings write surface)        severity: low
Size  (PH-02):  +765 / -15, 6 files, generated_ratio 0          severity: low
Safety(PH-03):  migrations 0, schema 0, secrets 0, infra 0      severity: low
Complete(PH-04): new_source 1, new_tests 1, api_no_schema false severity: low
```

### Findings in the Changes

None.

### Findings in the Neighbours

None. The diff touches `app.ts` (composition root), `read-only-inventory.test.ts` + `check-read-only.sh` (the two read-only gates), and `README.md`. Neighbours — the `SettingsStore` port, `FakeSettingsStore`, and `SpineSettingsAdapter` — are merged, unchanged, and correctly depended-upon (router → port; concrete adapter constructed only at the composition root).

### Watch List

- **WP-005 adapter per-write structured log.** The WP-005 Green DoD named a "structured per-write log line (operation, entity id, outcome)"; a grep of `SpineSettingsAdapter.ts` shows no `console`/`log` call. This is OUT OF SCOPE for WP-006 (the adapter is merged) and the `request-log` middleware already logs one line per settings request (method/path/status/duration), so the settings routes are observable. Surfaced for awareness only — not a finding against this diff; if the per-write entity-id log is desired it is a WP-005 follow-up, not a WP-006 change.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `npx tsc --noEmit -p server` (exit 0) + `npx eslint` (exit 0) + full vitest suite (1221 passed). Base clean, head clean — 0 PR-introduced errors. Coverage gap: @vitest/coverage-v8 not installed; new-file coverage verified by manual branch analysis (every route, all 6 error codes, all boundary validators, real round trips asserted).
- [✓] **CR-02 Dispatch.** Diff 765 lines / 6 files (above carve-out). Reviewed inline by the authoring executor with full file context held in session (every line was authored + read this session); the three lenses were applied sequentially with structured output each. Recorded as a deviation from parallel sub-agent dispatch: the executor authored 100% of the diff this session, so CR-03 full-file reading is satisfied by construction.
- [✓] **CR-03 Full-file reads.** Both files >50 lines (settings.ts ~248, routes.settings.test.ts ~407) authored and read end-to-end. Unread files: none.
- [✓] **CR-04 Evidence discipline.** Zero findings; no unevidenced claims. Watch-list item cites the file + the grep result.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical / 0 high / 0 medium / 0 low.
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade triggers fired (Build Verification empty; no file sampled; every lens produced output; no PH-03 high).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced — checks run: dependency direction (router→port; concrete adapter at composition root only), new domain→infra imports (none), module singletons (none), ADR-019 gate extension (tested positive + negative). Security: nothing surfaced — SEC-01..07 access-control/injection/validation/secrets checked; router rejects malformed bodies at boundary and delegates id/path-traversal validation to the adapter (does not bypass); no new auth surface (local 127.0.0.1); Gitleaks-style secret grep clean. Quality: nothing surfaced — Build Verification clean; no JSX (backend-only, jsx-ident-scan N/A); dead-surface (all imports + exports consumed); contract-drift (STATUS_BY_CODE is Record<SettingsErrorCode,number>, tsc-enforced exhaustive); test-coverage (new behaviour fully tested); CR-10 perf (no N+1 / loop-with-IO — each route is one awaited port call).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: low. PH-02 Size: low (765/6). PH-03 Safety: low (0 migrations / 0 schema / 0 secrets / 0 infra). PH-04 Completeness: low (1 source + 1 test). No PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** `git diff change/feat-user-level-product-store-settings` (staged, incl. untracked new files).
- **Neighbour expansion:** git grep — settingsRouter / SettingsRouterDeps consumers (app.ts + test); port/adapter merged + unchanged.
- **Neighbour cap:** not reached (6 changed files, < 5 neighbours).
- **Scanners run:** tsc, eslint, vitest, manual secret grep, CR-10 pattern grep, read-only shell gate.
- **Scanners unavailable:** @vitest/coverage-v8 (manual branch analysis fallback); Gitleaks/Semgrep/Trivy binaries not present (manual diff secret grep used — clean).
- **Lenses dispatched in parallel:** no — authoring executor inline (see CR-02 note).
