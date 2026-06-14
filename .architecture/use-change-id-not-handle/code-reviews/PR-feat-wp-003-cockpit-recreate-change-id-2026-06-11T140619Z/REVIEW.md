# Code Review: feat/wp-003-cockpit-recreate-change-id — Cockpit recreate drives by change_id

> **Timestamp:** 2026-06-11T140619Z (ISO 8601 UTC)
> **Author:** autonomous executor (WP-003)
> **Branch:** feat/wp-003-cockpit-recreate-change-id → change/fix-use-change-id-not-handle
> **Files changed:** 9
>
> **Outcome:** Ready to merge

---

## At a glance

This change fixes the cockpit so that when it rebuilds a shipped change's workspace, it asks for that change by its unique id instead of its short label. The short label is shared by several different changes in the live data, so asking by it could rebuild the wrong one — this closes that gap on the cockpit side. The change is small, tightly scoped to the rebuild path, and every new behaviour is covered by a test. No build errors, no security concerns, nothing to fix.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** 9 files, ~230 changed lines, all in the same rebuild-path cluster (one port, two adapters, the call site, the security guard, and their tests).

**Scope — clean.** A single concern: move the rebuild key from the shared label to the unique id.

**Safety — clean.** No database migrations, no schema/IDL changes, no infrastructure files, no secrets.

**Completeness — clean.** No new source file ships without a test; the new behaviour (rebuild-by-id, the test helper that records the carried key, the safety check that refuses a malformed id) is all exercised.

---

## Technical detail

> Internal taxonomy below for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all changed files >50 lines read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — `tsc --noEmit -p server && -p client` clean; `eslint` clean.
- **PR Hygiene:** 0 findings (PH-01..04 all low).
- **In the changes:** 0 findings (0 critical, 0 high, 0 medium, 0 low).
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0.

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none surfaced |
| Security | 0 | 0 | none surfaced |
| Quality | 0 | 0 | none surfaced |

### Build Verification (CR-01)

None. `tool-outputs/typecheck-head.log` and `tool-outputs/eslint-head.log` both clean (exit 0). Mechanical baseline run on HEAD; the change branch BASE was independently green at Step 6.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):       commit_type_spread {fix}; module_fan_out 1 (apps/cockpit/server); severity low
Size (PH-02):        lines_added 166, lines_removed 64, files_changed 9; severity low
Safety (PH-03):      migrations 0, schema/idl 0, infra 0, secrets 0; severity low
Completeness (PH-04): new_source_without_test 0; api_change_without_schema false; severity low
```

### Findings in the Changes

None.

Lens detail:

- **Architecture: nothing surfaced.** Checks run: dependency direction (no new domain→infra import), singletons/getInstance (none added), circular imports (none), resilience (bounded-timeout + argv-spawn discipline untouched; pre-spawn shape-guard is additive defence-in-depth), read-only-by-composition (gate clean — 240 files, no mutating ops), verification (port retains its FakeRecreateRunner contract twin; both adapters implement the re-keyed signature).
- **Security: nothing surfaced.** Primitives checked: SEC-01..07 (access control / injection / validation / secrets). The shape-guard now validates the value that actually crosses the spawn seam (`record.changeId`) rather than the no-longer-spawned `record.handle` — a net strengthening. argv-array spawn (shell:false) + leading-hyphen flag-confusion rejection retained. `JSON.stringify(changeId)` appears only in a logged detail string, never in a command line. No new external call, no secret, no CVE surface.
- **Quality: 0 findings + all seven outputs.** (1) Build Verification follow-up: none. (2) JSX/template scan: N/A (no TSX/JSX in diff). (3) Dead surface: `lastArg` getter is referenced by the HD-004 test; `isSafeChangeHandle` import is used. (4) Contract drift: port signature change applied consistently across both adapters, the serving call site, and the serving guard. (5) Test coverage: new behaviour fully tested (HD-004 carried-key assertion, adapter guard-reject behaviour test, serving-path malformed-id test, all carried-arg assertions flipped to changeId). (6) Style: doc comments updated coherently; predicate-name-kept rationale documented. (7) CR-10 performance: no new loops / DB / RPC / filesystem patterns — no anti-pattern matches.

### Findings in the Neighbours

None. Neighbours considered: `_contract-manifest.ts`, `_change-lookup.ts`, `ChangeStoreReader.ts`, `app.ts`, `FakeChangeStoreReader.ts` — all consume the re-keyed surface without assumption drift.

### Watch List

None.

### Cross-Reference

- Existing Hardening Deltas covered: none applicable.
- Existing security report: none present under `.security/use-change-id-not-handle/`.
- Pattern suggesting full audit: none.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `npm run typecheck` (tsc server+client) + `eslint` on the 9 changed files. HEAD: 0 errors. BASE green at Step 6. Coverage gap: none.
- [✓] **CR-02 Dispatch shape.** Single-reader pass. Justified: 9 files but only ~230 changed lines, all one tight recreate-seam cluster (one logical change — a port-key correction). Line count well under threshold; file count marginally over (9 vs 5) but cohesion is total. Recorded per CR-02.
- [✓] **CR-03 Full-file reads.** All changed files read end-to-end (the four source files >50 lines: SulisChangeRecreator.ts, contract.ts, changeHandleGuard.ts, recreate-on-demand.test.ts). Unread: none.
- [✓] **CR-04 Evidence discipline.** Findings: none; lens outputs cite the checks run.
- [✓] **CR-05 Severity rubric.** Applied; 0 findings at every severity.
- [✓] **CR-06 Verdict computed.** PASS. Auto-downgrade triggers: none fired (Build Verification empty; all >50-line files read; all lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture / Security / Quality each produced explicit output (above).
- [✓] **CR-09 PR Hygiene applied.** PH-01 low, PH-02 low, PH-03 low, PH-04 low. No PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** staged working tree vs change/fix-use-change-id-not-handle (pre-commit review at Step 6.5).
- **Neighbour expansion:** git grep on the re-keyed symbols (`recreate(`, `RecreateRunner`, `record.handle`/`record.changeId`).
- **Neighbour cap:** 5 of 5 considered, 0 excluded.
- **Scanners run:** tsc, eslint (project mechanical floor). Gitleaks/Semgrep/Trivy not invoked — diff carries no secret/dependency surface; recorded as scoped coverage.
- **Single-reader pass:** yes (CR-02 cohesion justification above).
