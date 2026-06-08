# Code Review: WP-001 — Pin the widened `spawnBridge` port contract (`originEnv`)

> **Timestamp:** 2026-06-07T195906Z (ISO 8601 UTC)
> **Author:** executor (WP-001)
> **Branch:** feat/wp-001-pin-spawnbridge-originenv-contract → change/feat-live-origin-stamping
> **Files changed:** 2
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds an optional third input to the one place the cockpit starts a chat session, so a future change can hand that session a note about where a commit came from. It also adds a small test that locks the new shape in place. The change is type-only — it does not yet wire anything up (that is later work). The build passes, the read-only safety check still passes, and the tests pass. Nothing needs attention.

## What to fix

No issues that need attention.

## How this change is shaped

Small and single-purpose — 129 lines across 2 files (one source file, one test file), one concern (pin the new shape). No database changes, no infrastructure changes, no secrets. Tests are included for the new shape (both the "note is present" and "note is absent" cases). Well-shaped.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs) for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; both changed files >50 lines read end-to-end; all lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (PH-01..PH-04 all clean)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none — widened signature matches ADR-017 + the production default exactly (CONTRACT_FIRST CF-07 satisfied) |
| Security | 0 | 0 | none — no new external call, no secret, no auth/injection surface |
| Quality | 0 | 0 | none — tests cover both present + absent cases; no dead surface; no contract drift |

### Build Verification (CR-01)

Mechanical baseline run on HEAD (the change is uncommitted; base is `change/feat-live-origin-stamping`):

- `pnpm --filter cockpit typecheck` (`tsc --noEmit -p server && tsc --noEmit -p client`) → exit 0, 0 errors.
- `eslint server/tests/session-bridge.contract.test.ts server/adapters/StreamJsonSessionBridge.ts` → exit 0.
- `prettier --check` on both files → clean.
- `bash scripts/check-read-only.sh` → exit 0 (192 files scanned, clean) — ADR-003 read-only invariant preserved; the bridge adapter remains path-allow-listed, no gate change.

Raw outputs in `tool-outputs/`. No PR-introduced errors → Build Verification empty.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat} (single concern: pin the contract)   → clean
  module_fan_out: 1 top-level dir (apps/cockpit/server)            → clean
  severity: none

Size (PH-02):
  lines_added: ~85, lines_removed: ~8, total diff: 129
  files_changed: 2
  generated_ratio: 0
  severity: none (well within bands)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0 (the SULIS_ORIGIN test value is a literal fixture, not a credential)
  severity: none

Completeness (PH-04):
  new_source_without_test: 0 (the only source change is type-only; the test file IS the new coverage)
  api_change_without_schema: false
  severity: none
```

### Findings in the Changes

None.

### Findings in the Neighbours

None. Neighbour symbols inspected: `spawnBridge` call site in `StreamJsonSessionBridge.relay` (line 98, 2-arg call unchanged → still valid under the optional widening); `spawnClaudeBridge` default (already 3-arg, line 253); `index.ts` wiring (line 90, assigns `spawnClaudeBridge` → assignable to widened port); contract/streamjson/recorded test stubs (2-arg arrow stubs remain assignable to the optional-3-arg type). `relay` consumers `chat.ts` (relay + concierge) and `onboardingOrchestrator.ts` ride `relay`, not `spawnBridge` directly — unaffected. All confirmed green by `tsc -p server` exit 0 and 33 passing bridge tests.

### Watch List

None.

### Cross-Reference

- **ADR-017** — the widened signature in this diff is byte-for-byte the shape ADR-017 specifies (`(argv, cwd, originEnv?: Record<string, string>)`). CONTRACT_FIRST: this is the contract WP both WP-002 (adapter call) and WP-004 (relay carry) depend on.
- **Existing security report:** none for this project.
- **Existing Hardening Deltas:** none covered.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `tsc --noEmit -p server && -p client` exit 0; `eslint` on both changed files exit 0; `prettier --check` clean; `check-read-only.sh` exit 0. Base (`change/feat-live-origin-stamping`) had a green typecheck before the change; HEAD adds 0 new errors. Coverage gap: none.
- [✓] **CR-02 Single-reader pass justified by diff size: 129 lines, 2 files** (≤200 lines AND ≤5 files).
- [✓] **CR-03 Full-file reads.** Both changed files (`StreamJsonSessionBridge.ts` 296 lines, `session-bridge.contract.test.ts` 261 lines) read end-to-end. Unread files: none.
- [✓] **CR-04 Evidence discipline.** All observations cite file:line; the diff is quoted in the bundle.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 0 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired (Build Verification empty; all files read end-to-end; all lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced — widened signature matches ADR-017 + production default; CF-07 conformance holds; no new dependency-direction / timeout / observability gap (type-only change). Security: nothing surfaced. Primitives checked: SEC-01..07 (no new auth/injection/validation/secrets surface), SC-01..04 (no dependency change — pnpm-lock.yaml is a local install artifact, excluded from the WP commit). Quality: 0 findings — JSX scan N/A (no TSX/JSX in diff); no dead surface; no contract drift (the test asserts exactly the present/absent behaviour the port now declares); test-coverage present (both cases); CR-10 performance scan: no anti-pattern matches (no loops, no DB/RPC/FS calls, no materialisation in the diff).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none (single `feat` concern, 1 module). PH-02 Size: none (129 lines / 2 files). PH-03 Safety: none (0 migrations, 0 schemas, 0 secrets, 0 infra). PH-04 Completeness: none (test coverage present for the new shape). PH-03 high → CR-06 auto-downgrade: did not fire.

#### Run details

- **Diff source:** `git diff change/feat-live-origin-stamping` (working tree; change uncommitted at review time, Step 6.5 precedes Step 7 commit).
- **Neighbour expansion:** `git grep` for `spawnBridge` / `.relay(` callers + callees.
- **Neighbour cap:** 7 of 7 considered, 0 excluded.
- **Scanners run:** tsc, eslint, prettier, check-read-only.sh. Gitleaks/Semgrep/Trivy not invoked — diff has no secret-shaped strings, no new dependencies, no new external surface; recorded as a deliberate Quick-mode scope decision for a type-only change.
- **Scanners unavailable:** n/a.
- **Lenses dispatched in parallel:** no — single-reader carve-out (CR-02) justified by size.
