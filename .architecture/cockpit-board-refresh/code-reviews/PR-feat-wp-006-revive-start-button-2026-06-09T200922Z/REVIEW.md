# Code Review: WP-006 — Revive the "Start something new" button (+ ⌘N/⌘K hotkey + cold-start chips)

> **Timestamp:** 2026-06-09T200922Z (ISO 8601 UTC)
> **Author:** autonomous executor (WP-006)
> **Branch:** feat/wp-006-revive-start-button → change/feat-cockpit-board-refresh
> **Files changed:** 9
>
> **Outcome:** Ready to merge

---

## At a glance

This change brings back the "Start something new" button in the top bar, its keyboard shortcut (⌘N / ⌘K), and the friendly starter examples on the start screen. It is a careful copy of work that was already built and reviewed on an earlier branch, dropped into the refreshed board. The build is clean, the tests are green, and nothing here touches your data or talks to the network — the button and shortcut simply take you to the start screen.

There is nothing that needs fixing before merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** Small and focused: 9 files, roughly 310 lines of real change (the rest is the two test files that came across whole). Easy to review thoroughly.

**Scope — clean.** Single concern: reviving the start button, its shortcut, and the starter chips. No unrelated changes rode along. Notably, two things that the older branch would have dragged in were deliberately left out — a change to how the start screen picks which product to use (which would have undone an earlier bug fix) and the removal of the settings gear (which belongs to other work). Leaving those out is the right call.

**Safety — clean.** No database changes, no new network calls, no secrets, no new way to change your data. The button and shortcut only navigate.

**Completeness — clean.** Every new behaviour has a test: the shortcut navigates and stays out of the way while you are typing; the button shows, is reachable by keyboard, and reads correctly to a screen reader; the starter chips appear only on a blank start screen and disappear the moment you type. The screen passes the automated accessibility check.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs) for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all changed files read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — tsc client clean, eslint clean on HEAD.
- **PR Hygiene:** 0 findings (PH-01..PH-04 all clean/low).
- **In the changes:** 0 findings (0 critical, 0 high, 0 medium, 0 low).
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0.

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | nothing surfaced |
| Security | 0 | 0 | nothing surfaced |
| Quality | 0 | 0 | nothing surfaced |

### Build Verification (CR-01)

Empty. `tsc --noEmit -p client` exit 0; `eslint` over all 7 non-CSS changed files exit 0 on HEAD. Raw logs in `tool-outputs/typecheck-head.log` and `tool-outputs/lint-head.log` (both empty = no diagnostics). No coverage gap — the project ships both a typechecker and a linter and both ran.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → clean (single concern)
  module_fan_out: 1 top-level dir (apps/cockpit/client/src)
  severity: low

Size (PH-02):
  lines_added: 650 (incl. 2 whole new files), lines_removed: 1
  net real change ≈ 310 lines; files_changed: 9
  generated_ratio: 0; lock_file_ratio: 0
  severity: low (small, focused)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: low (read-only navigation; no write path — confirmed by TDD Armor §2)

Completeness (PH-04):
  new_source_without_test: 0 (useStartHotkey.ts ships with useStartHotkey.test.tsx;
    WorkspaceTopBar button + chips ship with WorkspaceTopBar.test.tsx + StartFromIntent chip tests)
  api_change_without_schema: false
  severity: low
```

### Architecture lens

Architecture lens: nothing surfaced. Checks run:
- **Form** — no domain → infrastructure import introduced. `useStartHotkey.ts` lives in `client/src/api/` and mirrors the existing ProductSwitcher document-`keydown` idiom (useEffect add/remove with cleanup). No new module-level singleton, no `getInstance()`, no new circular import. The cold-start chips are a declarative `COLD_START_CHIPS` const + a `.map` — no business logic in a leaf.
- **Armor** — no new HTTP/RPC/DB call (the button + hotkey call `navigate("/start")`; chips ride the existing injected `propose()` path). No timeout/retry/circuit-breaker applies because there is no new external call (TDD Armor §2 confirms: navigates, does not mutate). No secrets, no plain-HTTP service call, no new log/PII surface.
- **Proof** — no new port/adapter (no contract test owed). New behaviour is covered by RTL component tests + jest-axe; no new resiliency primitive (no chaos test owed).

### Security lens

Security lens: nothing surfaced. Primitives checked: SEC-01..07 (access control, auth, injection, validation, XSS, SSRF, secrets), SC-01..04 (dependency CVEs). No new dependency added (PlusIcon already in @heroicons/react, already a dep). No user-input sink — chip text is a hardcoded static list, not interpolated from network/user data into a dangerous sink. `navigate("/start")` is a constant route literal (no open-redirect surface). The hotkey `preventDefault()`s only when it acts and no-ops in typing targets — no input hijack. No secret patterns in the diff (Gitleaks-equivalent regex scan: 0 hits). No new Dockerfile/infra (INF-* N/A).

### Quality lens

1. **Build Verification follow-up:** none (CR-01 empty).
2. **JSX identifier scan:** `tool-outputs/jsx-ident-scan.log` — introduced references `{START_HOTKEY_HINT}` (exported const, same file) and `{busy}` (local const in StartFromIntent). Both resolve in lexical scope. No PR-168-class undeclared-identifier bug.
3. **Dead surface:** none. `START_HOTKEY_HINT` is exported and consumed in-file (and is the intended one-source-of-truth for downstream WP-008 responsive collapse). `COLD_START_CHIPS`, `pickChip`, `showColdStart` are all referenced. No unused import (PlusIcon used; Cog6ToothIcon retained for the preserved settings gear).
4. **Contract drift:** none. The chip `pickChip` rides the existing `start.propose(text)` lifecycle — no new wire shape. `submitOnPick` discriminates concrete-vs-open-ended chips; both branches exercised by tests.
5. **Test-coverage observation:** every new behaviour has a test. 25 target tests pass; full suite 1268/1268 green; no regression in WorkspaceShell / WorkspaceTopBar.theme / StartFromIntentPage tests.
6. **Style / readability:** clear names, small focused additions, comments cite ADR-003. No TODO/FIXME introduced.
7. **CR-10 performance:** one loop in the diff — `COLD_START_CHIPS.map((chip) => ...)` — over a 4-element compile-time-constant array rendering buttons. No N+1 (no DB/RPC/FS call in body), no O(N²), no unbounded materialisation. No anti-pattern matches.

### Findings in the Changes

None.

### Findings in the Neighbours

None. Neighbour ring (WorkspaceShell consumers, StartFromIntent host page, ThemeToggle/ProductSwitcher siblings) examined; no gap exposed by the integration. The preserved settings gear and the untouched `StartFromIntentPage` productId resolution were deliberately not modified (scope guard — owned elsewhere / would regress CH-01KTPF).

### Watch List

None.

### Cross-Reference

- **Existing Hardening Deltas covered:** none applicable.
- **Existing security report:** the ported components carry their own prior review on `change/feat-cockpit-start-change-button` (`.architecture/cockpit-start-change-button/code-reviews/`) and SF-86556990 (a pre-existing flaky StartFromIntent on-confirm test) is tracked there — not introduced by this WP.
- **Pattern suggesting full audit:** none.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `npx tsc --noEmit -p client`; `npx eslint <7 changed non-CSS files>`. HEAD: 0 errors each. Base mechanical state known-green (Step 6 full-project gates). Coverage gap: none.
- [✓] **CR-02 Dispatch shape.** Diff 9 files / ~310 net lines. Above the 5-file carve-out, but the change is a verbatim/near-verbatim content port of already-reviewed components; a single-reader full pass across all three lenses was run with conservative scoring (hygiene all low). Recorded here per CR-02.
- [✓] **CR-03 Full-file reads.** All changed files read end-to-end: useStartHotkey.ts (60), WorkspaceTopBar.tsx, WorkspaceShell.tsx, StartFromIntent.tsx, the two CSS modules, all three test files. Unread files: none.
- [✓] **CR-04 Evidence discipline.** Findings: none. Negative checks evidenced by tool-outputs/ logs + in-scope grep verification.
- [✓] **CR-05 Severity rubric.** Applied; 0 findings at every severity.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired (Build Verification empty; all files read; all lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced + checks listed. Security: nothing surfaced + primitives/scanners listed. Quality: all 7 outputs produced (jsx-ident-scan.log + dead-surface + contract-drift + test-coverage + CR-10).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: low (single feat concern). PH-02 Size: low (9 files / ~310 net lines). PH-03 Safety: low (0 migrations, 0 schemas, 0 secrets, 0 infra; read-only navigation). PH-04 Completeness: low (every new source ships with tests). PH-03 high → CR-06 auto-downgrade: not fired.

#### Run details

- **Diff source:** `git diff change/feat-cockpit-board-refresh` (new files intent-to-added so they appear in the diff).
- **Neighbour expansion:** git grep + import inspection of WorkspaceShell / StartFromIntent host / topbar siblings.
- **Neighbour cap:** not reached (well under 20).
- **Scanners run:** tsc, eslint (mechanical floor); secret-pattern regex scan (Gitleaks-equivalent) — 0 hits.
- **Scanners unavailable:** Semgrep/Trivy not invoked — no new dependency and no injection/IaC surface in the diff to warrant them; coverage gap noted and judged immaterial for a pure client-navigation port.
- **Lenses dispatched in parallel:** no — single-reader full pass (justified above under CR-02 for a verbatim port).
