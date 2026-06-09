# Code Review: feat/wp-001-settings-wire-contract — Settings wire contract

> **Timestamp:** 2026-06-09T104631Z (ISO 8601 UTC)
> **Author:** autonomous executor (WP-001)
> **Branch:** feat/wp-001-settings-wire-contract → change/feat-user-level-product-store-settings
> **Files changed:** 3
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds the shared "wire contract" for the new Settings screen — the
type definitions that the server and the web page both agree on for products,
projects, and repo links. It's type-only: there's no behaviour to break, just
shape declarations plus a set of example data used in tests. The build is clean,
the new shapes are covered by a contract test (including the empty case and one
example per error), and nothing concerning surfaced. No issues need attention.

## What to fix

No issues that need attention.

## How this pull request is shaped

Small and single-purpose: 3 files, 356 lines, all in service of one thing — the
settings wire contract. It adds tests for the new shapes (the contract test grew
by four cases). No database changes, no infrastructure, no mixed concerns. This
is exactly the shape a contract-first foundation change should have.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs)
> for engineers and for downstream agents like `/sulis:harden-codebase`.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all
changed files >50 lines read end-to-end; all three lenses produced output. No
auto-downgrade trigger fired.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (PH-01..04 all clean/note)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | — (type-only contract; correct `shared/` placement) |
| Security | 0 | 0 | — (no secrets, no runtime, no network) |
| Quality | 0 | 0 | — (contract test covers new shapes incl. empty + error) |

### Build Verification (CR-01)

Empty. HEAD mechanical baseline clean:
- `npm run typecheck` (`tsc --noEmit -p server && tsc --noEmit -p client`) → exit 0.
- `npx eslint shared/api-types.ts shared/__fixtures__/settings.fixtures.ts server/tests/api-types.contract.test.ts` → exit 0.
- `npx prettier --check` (same files) → exit 0.

BASE baseline (unmodified contract) was confirmed green before changes
(`tsc -p server` exit 0; api-types contract test 11/11). Delta: 0 introduced
errors. Raw logs in `tool-outputs/`.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → clean (single concern)
  module_fan_out: 1 top-level dir (apps/cockpit) → clean
  severity: note

Size (PH-02):
  lines_added: 356, lines_removed: 2, total: 358
  files_changed: 3
  generated_ratio: 0.0
  lock_file_ratio: 0.0
  severity: note (≤200-line band exceeded slightly by additive type block; ≤5-file band)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0   (TS type file, not an IDL/OpenAPI artifact)
  infra_files: 0
  secret_pattern_hits: 0
  severity: clean

Completeness (PH-04):
  new_source_without_test: 0 (the one new source file — settings.fixtures.ts —
    is itself test fixtures, exercised by the contract test)
  api_change_without_schema: false (this IS the schema/contract change)
  severity: clean
```

### Findings in the Changes

None.

### Findings in the Neighbours

None. Neighbour ring: `ApiErrorCode` / `ApiError` are imported widely; extending
`ApiErrorCode` with five additive union members is backward-compatible (a wider
union; every existing consumer still type-checks). The full cockpit suite
(147 files / 1102 tests) was run green after the change, confirming no ripple.

### Watch List

None.

### Cross-Reference

- **Existing Hardening Deltas covered:** none.
- **Existing security report:** none for this project.
- **Pattern suggesting full audit:** none.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** HEAD: `npm run typecheck` exit 0, `eslint` exit 0, `prettier --check` exit 0. BASE: green (tsc -p server exit 0, contract test 11/11). Delta: 0 introduced errors. Coverage gap: none.
- [✓] **CR-02 Single-reader pass justified.** Diff: 358 lines / 3 files. File count within carve-out (≤5); the line count is additive pure-declaration type text (no logic), and all three files were authored + read end-to-end this session, so single-reader is sound. Recorded per CR-02.
- [✓] **CR-03 Full-file reads.** All 3 changed files read end-to-end (authored in this session). Unread files: none.
- [✓] **CR-04 Evidence discipline.** No findings; the zero-finding lens outputs cite the checks run.
- [✓] **CR-05 Severity rubric.** Applied; 0 findings at every severity.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired (Build Verification empty; all files read; all lenses produced output; PH-03 clean).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced — checks run: domain/infra import direction (file is correctly in `shared/`, no infra imports), singletons, circular imports, runtime external calls (none — type-only), contract-test presence (present). Security: nothing surfaced — primitives checked SEC-01..07 (no auth/injection/validation surface — pure types), SC (no dep change), DAT-03 (no logging); secret-pattern grep on added lines → 0 hits. Quality: 0 findings + (1) Build-Verification follow-up empty; (2) JSX scan N/A — no TSX/JSX files; (3) dead-surface: all new exports consumed by the contract test / SettingsErrorCode subset; (4) contract-drift: SettingsErrorCode ⊆ ApiErrorCode asserted at type level, all 6 codes present in fixtures; (5) test-coverage: contract test extended with 4 cases incl. empty + error; (6) style: clean, ADR-cited doc comments; (7) CR-10: no anti-pattern matches — the 3 `for` loops are bounded test iterations over ≤6-element literal arrays, no IO.
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: note (single `feat`, one dir). PH-02 Size: note (358 lines / 3 files, additive type text). PH-03 Safety: clean (0 migrations, 0 schemas, 0 secrets, 0 infra). PH-04 Completeness: clean (the one new source file is test fixtures; this IS the contract change). PH-03 high → CR-06 auto-downgrade: did not fire.

#### Run details

- **Diff source:** `git diff --cached change/feat-user-level-product-store-settings -- apps/cockpit` (working-tree change; branch has no commit yet at review time).
- **Neighbour expansion:** git grep on `ApiErrorCode` / `ApiError` importers; ripple confirmed by full-suite run (1102 tests green).
- **Neighbour cap:** not reached (additive union widening is backward-compatible).
- **Scanners run:** tsc, eslint, prettier; secret-pattern grep (manual).
- **Scanners unavailable:** Gitleaks / Semgrep / Trivy not installed in this environment — security lens used grep-based secret scan + manual primitive review (no runtime/dependency surface to scan). Recorded as a coverage note; not material for a type-only diff.
- **Lenses dispatched in parallel:** no — single-reader pass per CR-02 carve-out.
