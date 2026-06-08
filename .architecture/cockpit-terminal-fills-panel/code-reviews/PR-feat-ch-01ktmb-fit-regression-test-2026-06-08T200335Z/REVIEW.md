# Code Review: feat/ch-01ktmb-fit-regression-test — terminal fit-addon regression guard

> **Timestamp:** 2026-06-08T200335Z (ISO 8601 UTC)
> **Author:** autonomous executor (CH-01KTMB)
> **Branch:** feat/ch-01ktmb-fit-regression-test → change/fix-cockpit-terminal-fills-panel
> **Files changed:** 2 (1 modified, 1 added)
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds an automated safety net for the terminal "fills its panel" fix that
shipped earlier. The fix itself was confirmed by hand on a live run; this pull request
adds a test so the same wiring can't quietly break again. The change is tightly scoped:
one source file gains a single keyword so the terminal's set-up code can be tested, and
one new test file pins the four things that have to stay wired (loads the auto-sizer,
sizes on open, re-sizes when the panel changes, cleans up on teardown). No build errors,
no issues that need attention.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** Two files, about 140 lines, almost all of it the new test. Easy to
review in full.

**Scope — clean.** A single concern: a regression test for one behaviour, plus the
minimal export needed to test it.

**Safety — clean.** No database changes, no schema or infrastructure files, no secrets.

**Completeness — clean.** The change *is* the test. The one source-file edit (making the
terminal set-up function visible to tests) is directly exercised by the new test.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high in diff; Build Verification empty; both changed files
read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (CR-09 / PH-01..PH-04 all clean)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | nothing surfaced |
| Security | 0 | 0 | nothing surfaced |
| Quality | 0 | 0 | nothing surfaced |

### Build Verification (CR-01)

`npm run typecheck` (tsc server + client) — clean on HEAD. `npx eslint` on both changed
files — clean. Raw outputs in `tool-outputs/typecheck-head.log` and
`tool-outputs/eslint-changed.log`. No PR-introduced errors.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {test}                   → clean (single concern)
  module_fan_out: 1 top-level dir (apps/cockpit) → clean
  severity: none

Size (PH-02):
  lines_added: ~146, lines_removed: 2
  files_changed: 2
  generated_ratio: 0
  lock_file_ratio: 0
  severity: none (≤200 lines, ≤5 files)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0 (the new file IS the test; the .tsx edit is test-covered)
  api_change_without_schema: false
  severity: none
```

### Findings in the Changes

None.

#### Architecture lens

Nothing surfaced. Checks run: no new imports into domain from infrastructure/db/http;
no new module-level singletons; no new circular imports; no new external HTTP/RPC/DB
calls (the diff adds a test that mocks `@xterm/*` and stubs `ResizeObserver`/`rAF`); no
new ports/adapters; the only source change is widening `createXtermSink` from
module-private to a named export, with an inline rationale comment.

#### Security lens

Nothing surfaced. Primitives checked: SEC-01..07 (access control, auth, injection,
validation, XSS, SSRF, secrets), SC-01..04 (dependency CVEs). No new dependency, no
network/IO, no credential or token-shaped string, no user-input handling. The diff is a
unit test against mocked modules plus an `export` keyword. No scanner signals present.

#### Quality lens

1. **Build Verification follow-up:** none (CR-01 clean).
2. **JSX / template identifier scan:** N/A — the new file is `.ts` (no JSX); the source
   change introduces no new identifier (only the `export` keyword). See
   `tool-outputs/jsx-ident-scan.log`.
3. **Dead-surface:** none. The new export is consumed by `LiveTerminal.fit.test.ts`; the
   `defaultTerminalFactory` in the same module already calls `createXtermSink`.
4. **Contract-drift:** none. No DTO/enum/union changes.
5. **Test-coverage observation:** strong. The change adds four focused tests pinning the
   exact fit-addon wiring (loadAddon(fitAddon), fit-on-open via rAF, ResizeObserver
   observe+re-fit, dispose disconnect+dispose) that previously had zero unit coverage.
6. **Style / readability:** clean. The test extracts a `mountSink()` arrange helper
   (2-consumer threshold), keeps the create-then-open split where a pre-open assertion
   needs it, and carries an explanatory header.
7. **Performance procedural checks (CR-10):** no anti-pattern matches. See
   `tool-outputs/cr10-perf-scan.log`. No loops with IO; the `it()` blocks are not loops.

### Findings in the Neighbours

None. The neighbour ring is `LiveTerminal.tsx` consumers (the cockpit Terminal tab) and
the existing `LiveTerminal.test.tsx`; the existing suite still passes 13/13 unchanged.

### Watch List

None.

### Cross-Reference

- **Existing Hardening Deltas covered:** none.
- **Existing security report:** none for this change.
- **Pattern suggesting full audit:** none.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `npm run typecheck` (tsc server+client);
  `npx eslint` on both changed files. Head: 0 errors. Coverage gap: none.
- [✓] **CR-02 Single-reader pass justified by diff size: ~146 lines, 2 files** (within the
  ≤200-line / ≤5-file carve-out).
- [✓] **CR-03 Full-file reads.** Both changed files read end-to-end (LiveTerminal.tsx 380
  lines; LiveTerminal.fit.test.ts ~146 lines). Unread files: none.
- [✓] **CR-04 Evidence discipline.** No findings; nothing to evidence. Tool outputs saved.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 0 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired.
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (checks listed). Security:
  nothing surfaced (primitives listed). Quality: 7 outputs produced; test-coverage strong.
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none (single `test:` concern). PH-02 Size:
  none (~146 lines / 2 files). PH-03 Safety: none (0 migrations/schemas/secrets/infra).
  PH-04 Completeness: none. PH-03 high → CR-06 auto-downgrade fired: no.

#### Run details

- **Diff source:** `git diff f1118125 -- apps/cockpit` + new untracked test file.
- **Neighbour expansion:** git grep (consumers of `createXtermSink` / `LiveTerminal`).
- **Neighbour cap:** 2 of 2 considered, 0 excluded.
- **Scanners run:** typecheck (tsc), eslint. Security scanners (Gitleaks/Semgrep/Trivy)
  not run — no security-relevant signals in a mocked unit-test diff.
- **Scanners unavailable:** n/a.
- **Lenses dispatched in parallel:** no — single-reader pass under CR-02 carve-out.
