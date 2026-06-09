# Code Review: PR-feat/wp-007 — Typed settings client fetcher

> **Timestamp:** 2026-06-09T112457Z (ISO 8601 UTC)
> **Author:** executor (WP-007)
> **Branch:** feat/wp-007-settings-client-fetcher → change/feat-user-level-product-store-settings
> **Files changed:** 3
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds the typed access layer the Settings screen will use to read and update products, projects, and repo links. It is logic-only — no screens, no styling. The build is clean (no type or lint errors), every function is covered by a test (100%), and the code follows the project's existing rule that all network calls go through one shared place. Nothing needs fixing.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — fine.** Three files, about 386 new lines, most of which is the test file. Single, coherent concern (one data-access module plus its tests plus one small shared helper).

**Scope — fine.** One purpose: the settings data client. One commit type (`feat`).

**Safety — fine.** No database migrations, no schema or infrastructure files, no secrets.

**Completeness — fine.** Tests ship with the code (14 tests; full coverage of the new module).

---

## Technical detail

> Internal taxonomy below for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all changed files >50 lines read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — typecheck clean, eslint clean.
- **PR Hygiene:** 0 findings (PH-01..04 all low).
- **In the changes:** 0 findings.
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0.

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none — clean dependency direction (types from shared/api-types; runtime via the client funnel) |
| Security | 0 | 0 | none — every interpolated id/path is encodeURIComponent-escaped; no secrets; no authz logic on the client (WPF show/hide divergence) |
| Quality | 0 | 0 | none — 100% coverage on the new module; no dead surface; no contract drift |

### Build Verification (CR-01)

Typecheck (`tsc --noEmit -p client`): 0 errors on HEAD. ESLint (changed files): 0 errors. No PR-introduced errors. Raw logs in `tool-outputs/`.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):        commit_type_spread: {feat}; module_fan_out: 1 dir  → severity low
Size (PH-02):         lines_added: 386; files_changed: 3                  → severity low
Safety (PH-03):       migrations: 0; schemas: 0; secrets: 0; infra: 0     → severity low
Completeness (PH-04): new_source_without_test: 0; api_change_no_schema: false → severity low
```

### Findings in the Changes

None.

#### Architecture lens — nothing surfaced

Checks run: dependency-direction (types imported verbatim from `shared/api-types` per CF-02; runtime only via `./client` funnel — no domain→infra inversion), singletons (none), circular imports (none), resilience (errors-are-values: expected ApiError → typed Result; transport failure propagates as the page's generic retry state per the WP Contract invariant — consistent with existing `apiGet`/`apiPost`, not a new untimed call this WP introduces), verification (new module has a shared contract-style test against the WP-001 fixtures; 100% line/branch coverage).

#### Security lens — nothing surfaced

Primitives checked: SEC-01 (access control — N/A, client only shows/hides; real gate is the backend per WPF authorization divergence), SEC-03 (injection — every interpolated `id`/`projectId`/`localPath` goes through `encodeURIComponent`, no URL injection), SEC-06 (secrets exposure — none in diff). No new Dockerfile/logging/network-protocol signals. No scanners required for a logic-only client diff with no secret/dependency surface.

#### Quality lens — all seven outputs

1. **Build verification follow-up:** none (CR-01 clean).
2. **JSX/template identifier scan:** N/A — no TSX/JSX in the diff (logic-only).
3. **Dead surface:** none. All 7 exported methods are the WP Contract's public API (consumed by WP-008/009). `SETTINGS_ERROR_CODES`, `toSettingsError`, and `request<T>` are all referenced.
4. **Contract drift:** none. `SettingsError.code` is the `SettingsErrorCode` union; an unrecognised/absent wire code maps deterministically to `WRITE_FAILED` (a valid member), so the union is fully honoured and no consumer can receive an off-union code.
5. **Test-coverage observation:** tests ship with the code — 14 tests; 100% statements/branches/lines/functions on `settings.ts`; the new `apiDelete` funnel helper is exercised (both 2xx and non-2xx branches) via the remove/unlink tests.
6. **Style/readability:** clear names, small methods, each a one-liner over the shared `request` wrapper. No TODO/FIXME.
7. **Performance (CR-10):** no anti-pattern matches. No loops, no N+1 (each method is a single funnel call), no O(N²), no unbounded materialisation.

### Findings in the Neighbours

None. The one touched neighbour is `client.ts` (the funnel), extended with `apiDelete` mirroring the existing `apiPost` exactly — the established funnel-extension pattern (each prior client WP added its verb there). The inventory gate (only `client.ts` may call `fetch`) still passes.

### Watch List

None.

### Cross-Reference

- Existing Hardening Deltas covered: none.
- Existing security report: none for this project.
- Pattern suggesting full audit: none.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `npx tsc --noEmit -p client` (0 errors); `npx eslint <changed>` (0 errors). HEAD clean; no delta to compute. Logs in tool-outputs/.
- [✓] **CR-02 Dispatch shape.** Diff 386 lines / 3 files. Above the 200-line line-count threshold but a single coherent logic-only concern across 3 tightly-coupled files (a fetcher, its test, one funnel helper), all authored and read end-to-end by the reviewer. Single-reader pass with full-file reads; the three lenses applied analytically. Recorded honestly: line count exceeds the carve-out, file count (3) is within it.
- [✓] **CR-03 Full-file reads.** All 3 changed files read end-to-end (settings.ts 137L, settings.test.ts 228L, client.ts diff 21L in a fully-read file). No sampling.
- [✓] **CR-04 Evidence discipline.** No findings to evidence; lens "nothing surfaced" entries list the checks run.
- [✓] **CR-05 Severity rubric.** Applied — 0 findings at every severity.
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade triggers fired (Build Verification empty; all files read end-to-end; all lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture, Security, Quality each produced explicit output above.
- [✓] **CR-09 PR Hygiene applied.** PH-01 low, PH-02 low, PH-03 low, PH-04 low. No PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** git diff change/feat-user-level-product-store-settings...HEAD (new files staged with `git add -N` to include them).
- **Neighbour expansion:** git grep — funnel (`client.ts`) is the sole neighbour; the inventory gate confirms no other fetch callers.
- **Neighbour cap:** 1 of 1; none excluded.
- **Scanners run:** typecheck (tsc), lint (eslint). Secret grep over the diff (0 hits).
- **Lenses dispatched in parallel:** no — single-reader pass (see CR-02 note).
