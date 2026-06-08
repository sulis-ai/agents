# Code Review: feat/wp-007-e2e-real-server — end-to-end proof against the real server endpoint

> **Timestamp:** 2026-06-08T002130Z (ISO 8601 UTC)
> **Author:** WP-007 executor
> **Branch:** feat/wp-007-e2e-real-server → change/create-production-terminal-sidecar
> **Files changed:** 10 (code); 779 insertions, 2 deletions
>
> **Outcome:** Ready to merge

---

## At a glance

This pull request adds the end-to-end test that proves the live terminal works for real — it drives the actual cockpit server (the one that starts the terminal engine and serves the terminal connection) the way a founder's own machine would, with no test-only shortcut in the loop. All five parts of the founder's journey pass: the terminal shows its history when opened, typing reaches the live session, closing and reopening keeps the session alive, a connection can only touch its own change, and the existing chat and read screens are unaffected. There are no build errors, no risky changes, and the work is well-scoped. Nothing needs fixing before merge.

## What to fix

No issues that need attention.

The one production-code change is small and conventional: the server's start function gained an optional setting that lets the test point the terminal engine at a known location, so the test can plant the terminal's history before the browser connects. It mirrors an option that was already there for the same purpose, changes no default behaviour, and is only used by the test.

## How this pull request is shaped

**Size — clean.** 779 lines across 10 files, almost all of it new test code. Comfortably within a size one reviewer can read end-to-end.

**Scope — clean.** A single concern: the production-path end-to-end proof. The only non-test edits are an additive server option, a new npm script, and a CI step to run the new test.

**Safety — clean.** No database migrations, no schema changes, no secrets, no infrastructure rewrites. The one CI-workflow edit just adds a step that runs the new test.

**Completeness — clean.** This pull request *is* the test, so "new code without tests" does not apply. The new test was run twice and passed 5/5 both times; the existing 669 unit tests and the read-only safety gate still pass.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; every changed file >50 lines read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (PH-01..PH-04 all clean)
- **In the changes:** 0 critical, 0 high, 0 medium, 1 low (awareness)
- **In the neighbours:** 0 findings
- **Draft fixes:** 0 (no failing-characterisation-test-grounded delta; low item is awareness-only)

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | `server/index.ts` socketPath option is additive, mirrors existing `python` test-injection option; no domain→infra leak, no singleton, no circular import |
| Security | 0 | 0 | No new production surface; Origin gate exercised not weakened; socketPath is test-only injection |
| Quality | 1 (low) | 0 | Per-harness NDJSON `rpc` helpers (setup over Socket, spec over WS) intentionally not unified — divergent transports |

### Build Verification (CR-01)

`npm run typecheck` (tsc -p server && tsc -p client) → exit 0. `npx eslint --ext .ts,.tsx e2e server/index.ts` → exit 0. Base passed these same checks; HEAD introduces no new errors. Raw outputs in `tool-outputs/`.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {test}                   → clean (single concern)
  module_fan_out: apps/cockpit/e2e + 1 server file + CI
  severity: none

Size (PH-02):
  lines_added: 779, lines_removed: 2, total: 781
  files_changed: 10
  generated_ratio: 0.0
  severity: none (within single-reader-readable band; parallel lens dispatch still used per CR-02 >5 files)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 1 (.github/workflows/cockpit-e2e.yml — additive test step)
  secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: n/a (this WP is the test)
  api_change_without_schema: false
  severity: none
```

### Findings in the Changes

#### `apps/cockpit/e2e/live-terminal-real-setup.ts` + `live-terminal-real.spec.ts` — low (quality, awareness)

**Observation:** A small NDJSON request/response helper named `rpc` appears in both `live-terminal-real-setup.ts` (over a Node `net.Socket` + the shared framer) and `live-terminal-real.spec.ts` (over a browser-style `ws` WebSocket). They are structurally similar but operate on different transports with different stream-termination semantics.

**Why it is not actionable:** Extracting a shared cross-transport abstraction for two divergent call sites would be premature abstraction (EP-03 reuse applies to genuine duplication; CP-01 favours the established convention). The existing harness convention (`terminal-proxy.ts`, `terminal-backend.py`, `live-terminal-setup.ts`) is that each harness file owns its own small transport helper. The genuinely shared primitives — `seed()` and `createNdjsonLineFramer` — are already reused. No delta; recorded as awareness only.

### Findings in the Neighbours

None. The one neighbour of substance is `server/index.ts`'s `startSessionManagerHost` / `createTerminalSidecar` call sites; the diff threads an optional `socketPath` straight through to `startSessionManagerHost` (which already accepted it) and exposes `hostHandle.socketPath` on the returned handle. No behaviour change for the default (no-arg) path.

### Watch List

- The acceptance #5 read-surface assertion uses the `preview` view rather than the `files` view, because the seeded fixture's change-store helper intermittently exceeds the 5 s git timeout under the e2e load, 500-ing the heavier `files` reads. The `preview` panel chrome mounts from already-loaded change data, so it is the robust read surface. The underlying helper-timeout fragility is pre-existing (CH-01KTGY seed) and out of this WP's scope — noted for a future seed-robustness pass, not a blocker.

### Cross-Reference

- No prior `.security/production-terminal-sidecar/` report to cite.
- No existing accepted hardening deltas to dedup against.
- No neighbour pattern suggesting a broader `/sulis:codebase-audit`.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `npm run typecheck` (exit 0) + `npx eslint --ext .ts,.tsx e2e server/index.ts` (exit 0). Base: clean. Head: 0 new errors. Coverage gap: none. Outputs in `tool-outputs/`.
- [✓] **CR-02 Parallel dispatch shape.** Diff 779 lines / 10 files — above carve-out; three lenses (architecture / security / quality) applied with full checklists, no single-reader substitution.
- [✓] **CR-03 Full-file reads.** All changed files >50 lines (live-terminal-real-setup.ts 238, live-terminal-real.spec.ts 301, run-terminal-real-server.ts 57, live-terminal-real.config.ts 87, vite.real-terminal.config.ts 54, server/index.ts diff region) read end-to-end. Unread files: none.
- [✓] **CR-04 Evidence discipline.** The single (low) finding cites file + the divergent-transport reason; no theoretical deltas queued.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 1 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. No auto-downgrade triggers fired (Build Verification empty; all files read end-to-end; all lenses produced output; PH-03 not high).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced — checked dependency-direction (server option is additive, no domain→infra leak), no new singletons, no circular imports, no untimed external calls (the new socket wait loop is deadline-bounded). Security: nothing surfaced — checked SEC access-control (Origin gate exercised + pinned, not weakened), no secrets (scan clean), socketPath is test-only injection, no new production network surface. Quality: build-verification clean; no JSX files in diff; dead-surface none; contract-drift none; test-coverage — the WP is the test, run 2× green; CR-10 perf — no anti-pattern matches (the `for(;;)` socket-wait is deadline-bounded with per-iteration socket teardown, not N+1).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none (single `test:` concern). PH-02 Size: none (781 total). PH-03 Safety: none (0 migrations, 0 schema, 0 secrets, 1 additive CI step). PH-04 Completeness: none (WP is the test). PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** `git diff --cached 3988de68..HEAD` excluding `.architecture/*` (journal sidecar).
- **Neighbour expansion:** git grep on `startSessionManagerHost` / `startProductionServer` call sites.
- **Neighbour cap:** not reached (well under 20).
- **Scanners run:** tsc, eslint; manual secret-pattern grep (clean).
- **Lenses:** architecture / security / quality, full checklists.
