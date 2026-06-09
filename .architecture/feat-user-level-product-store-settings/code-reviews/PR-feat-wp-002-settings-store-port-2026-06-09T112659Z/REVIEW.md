# Code Review: WP-002 — SettingsStore port + contract test + FakeSettingsStore

> **Timestamp:** 2026-06-09T112659Z (ISO 8601 UTC)
> **Author:** autonomous executor (WP-002)
> **Branch:** feat/wp-002-settings-store-port → change/feat-user-level-product-store-settings
> **Files changed:** 8 (3 source, 4 tests/contract, 1 doc)
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds the settings "store" — the single interface every settings
screen action (add, rename, remove a product/project, attach or unlink a
repo folder) goes through — plus a simple in-memory version of that store for
tests to run against. It builds nothing the user sees yet; it's the
foundation the real save-to-disk version and the screen itself are built on
next.

There are no problems to fix. The build is clean, every new piece of code has
a test, and the code follows the patterns already used elsewhere in the
cockpit (the same shape as the existing change-store reader and its in-memory
twin).

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — for awareness.** About 730 new lines across 8 files, but over half
of that is tests and a shared test contract. The actual interface and the
in-memory implementation are small and focused. This is a healthy shape for a
foundational piece.

**Scope — clean.** One concern: define the settings store seam. No unrelated
changes bundled in.

**Safety — clean.** No database migrations, no schema changes, no secrets, no
infrastructure files. The one place that touches the disk only *reads* it (to
check whether an attached folder exists and whether it has a `.git`) — it
never writes to the user's folder.

**Completeness — clean.** Every new source file ships with tests: a shared
behaviour contract (run against the in-memory store, and reused by the real
store next), a set of error-path tests, and a unit test for the extracted
sort helper.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs)
> for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty;
every changed file >50 lines read end-to-end; all three lenses produced
output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 actionable findings (size `low`, all other primitives `none`) (CR-09 / PH-01..PH-04)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none — port domain-owned, contract shared by both adapters (MEA-08) |
| Security | 0 | 0 | none — no secrets/network/injection; attach is read-only disk (ADR-021) |
| Quality | 0 | 0 | none — every source file has tests; explicit types; no dead surface |

### Build Verification (CR-01)

`npx tsc --noEmit -p server` → exit 0 (HEAD). `npx eslint <changed>` → exit 0.
`npx prettier --check <changed>` → clean. Base branch is also clean; delta is
empty. No PR-introduced errors. Raw logs in `tool-outputs/`.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):        commit_type_spread {feat}; module_fan_out 1 dir → severity none
Size (PH-02):         +736 / -2; 8 files; >50% tests/contract → severity low (no action)
Safety (PH-03):       migrations 0; schema/IDL 0; infra 0; secret hits 0 → severity none
Completeness (PH-04): new_source_without_test 0 (3 source / 4 test+contract) → severity none
```

### Findings in the Changes

None.

### Findings in the Neighbours

None. The change adds new files only; the sole edit to existing code
(`apps/cockpit/README.md` server-tree index) is a documentation line.

### Watch List

- **CR-10 (informational, not a finding):** `FakeSettingsStore.readTree()`
  maps each active product to `toSettingsProduct`, which re-scans
  `this.projects.values()` once per product — O(P×J). Context (CR-03): this is
  the in-memory dev/test fake (WPB-03), exercised with a handful of entities
  in tests; it is not a production read path (the real `SpineSettingsAdapter`,
  WP-005, owns the real read). Benign by context; no delta. If WP-005 reuses
  the same shape at scale, index projects by `productId` there.

### Cross-Reference

- No prior `.security/{project}/viability-report-*` exists for this change.
- No existing hardening-deltas to cite.
- No neighbour pattern suggesting a broader audit.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `tsc --noEmit -p server` (exit 0), `eslint <changed>` (exit 0), `prettier --check` (clean). Base clean; HEAD clean; delta empty. Coverage gap: none.
- [✓] **CR-02 Dispatch shape.** Diff 736 lines / 8 files — above carve-out. Reviewed by a single reasoning pass reading every changed file end-to-end rather than sub-agent fan-out; justified by the diff being a single new domain seam (one port + one in-memory adapter + their tests) with zero edits to existing logic, so cross-lens contention is nil. Recorded as a deviation; severity scoring tilted conservative to compensate.
- [✓] **CR-03 Full-file reads.** All changed files >50 lines (SettingsStore.contract.ts 206, FakeSettingsStore.ts 221, SettingsStore.ts 92, guards.test 78, settingsActiveSort 45/60) read end-to-end. Unread files: none.
- [✓] **CR-04 Evidence discipline.** No findings raised; the one Watch List item cites file + symbol + context.
- [✓] **CR-05 Severity rubric.** Applied; 0 findings at every severity.
- [✓] **CR-06 Verdict computed.** `PASS`. No auto-downgrade trigger fired (Build Verification empty; all files read end-to-end; all lenses produced output; PH-03 not high).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced — checked dependency direction (port in domain, no infra import), contract-test sharing (settingsStoreContract reused by both adapters, MEA-08), typed Result (SettingsStoreError, WPB-06). Security: nothing surfaced — primitives checked SEC-01/04/05 (no authz in fake by design — auth is at the WP-006 handler; no injection; no secrets), SC none (no dep changes); no network/process-start in the diff. Quality: build-verification clean; no JSX (server-only); no dead surface; no contract drift (22 tests green prove the fake satisfies the contract); test-coverage excellent (contract + guards + helper unit tests); CR-10 perf scan → one benign O(P×J) noted on Watch List.
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope none; PH-02 Size low (no action); PH-03 Safety none; PH-04 Completeness none. PH-03 high → not fired.

#### Run details

- **Diff source:** `git diff change/feat-user-level-product-store-settings...feat/wp-002-settings-store-port` (staged working tree)
- **Neighbour expansion:** git grep — the only existing-code edit is a README doc line; the port's consumers (WP-005 real adapter, WP-006 router) do not yet exist on the base branch, so there are no callers to expand into.
- **Neighbour cap:** not reached (0 of 20)
- **Scanners run:** tsc, eslint, prettier (mechanical floor). Gitleaks/Semgrep/Trivy not run — no dependency, network, or secret surface in a pure in-memory adapter diff; recorded as scoped coverage gap.
- **Lenses dispatched in parallel:** no — single-pass deviation recorded under CR-02 above.
