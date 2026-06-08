# Code Review: feat/wp-002-global-start-hotkey — Global ⌘N / ⌘K start hotkey

> **Timestamp:** 2026-06-08T223050Z (ISO 8601 UTC)
> **Author:** executor (WP-002)
> **Branch:** feat/wp-002-global-start-hotkey → change/feat-cockpit-start-change-button
> **Files changed:** 3 source (+ 1 internal journal, excluded from review)
>
> **Outcome:** Ready to merge

---

## At a glance

This pull request adds a small keyboard shortcut: pressing ⌘N or ⌘K (Ctrl on Windows/Linux) from anywhere in the workspace opens the "start something new" screen. It is mounted once at the top of the workspace so it works on every page, and it deliberately does nothing while you are typing in a text box, so it never steals a keystroke from the composer or the intent box.

There are no build errors, the changes are well-scoped to one new file plus a single line wiring it in, and it ships with eight tests covering both shortcuts, the Windows/Linux variants, the "don't fire while typing" rule, and clean-up when the screen unmounts. Nothing needs fixing.

## What to fix

No issues that need attention.

## How this pull request is shaped

Small and single-purpose: one new shortcut hook plus a one-line mount in the workspace shell. New behaviour ships with its own tests. This is exactly the shape a change like this should take — no split needed, nothing bundled in that doesn't belong.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs) for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all changed files read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (small, single-concern, tests-included)
- **In the changes:** 1 finding (0 critical, 0 high, 0 medium, 1 low/awareness)
- **In the neighbours:** 0 findings
- **Draft fixes:** 0 (the single low item is awareness-only and matches the WP Contract verbatim — no delta)

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | Nothing surfaced — dependency direction clean, no module state, no network |
| Security | 0 | 0 | Nothing surfaced — pure client navigation, no inputs, no secrets |
| Quality | 1 (low) | 0 | Case-sensitive `e.key` comparison (matches Contract; awareness only) |

### Build Verification (CR-01)

`npx tsc --noEmit -p client` → exit 0 (head). `npx eslint` on the three touched files → exit 0. `prettier --check` → clean. No PR-introduced errors. Raw logs in `tool-outputs/`.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → clean (single concern)
  module_fan_out: 2 dirs (api/, layouts/)      → clean
  severity: none
Size (PH-02):
  lines_added: ~180 (source), files_changed: 3 → clean
  severity: none (well under 200-line / 5-file band)
Safety (PH-03):
  migration_count: 0, schema_idl_count: 0, infra_files: 0, secret_pattern_hits: 0
  severity: none
Completeness (PH-04):
  new_source_without_test: 0 (useStartHotkey.ts ships useStartHotkey.test.tsx)
  api_change_without_schema: false
  severity: none
```

### Findings in the Changes

#### `apps/cockpit/client/src/api/useStartHotkey.ts:36` — low (quality)

**Quoted text:**
```typescript
(e.metaKey || e.ctrlKey) && (e.key === "n" || e.key === "k");
```

**Observation:** The chord match compares `e.key` against lowercase `"n"`/`"k"`. With Caps Lock on or Shift held, `e.key` reports `"N"`/`"K"` and the chord would not fire. This is **not a defect**: (a) it matches the WP Contract verbatim (`key === "n"`, `key === "k"`), (b) it mirrors the established `ProductSwitcher` keydown idiom which also compares `e.key` exactly, and (c) ⌘-Shift-N / ⌘-Shift-K are commonly bound to other browser actions, so claiming them would be more surprising than not. Recorded for awareness only; no change recommended and no delta drafted.

**Lens:** quality

### Findings in the Neighbours

None. The only neighbour is `WorkspaceShell.tsx` (the mount site), itself in the diff. `WorkspaceShell.test.tsx` regression passes unchanged.

### Watch List

None.

### Cross-Reference

- **Existing Hardening Deltas covered:** none
- **Existing security report:** none in `.security/cockpit-start-change-button/`
- **Pattern suggesting full audit:** none

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `npx tsc --noEmit -p client` (exit 0) + `npx eslint` on changed files (exit 0) + `prettier --check` (clean) on HEAD. Base has neither the net-new hook nor its test (both `--diff-filter=A`), and the one-line WorkspaceShell mount cannot introduce errors elsewhere; delta = 0 PR-introduced errors. Coverage gap: none.
- [✓] **CR-02 Single-reader pass justified by diff size: ~180 source lines, 3 files** (within the ≤200-line AND ≤5-file carve-out).
- [✓] **CR-03 Full-file reads.** All 3 changed files read end-to-end (useStartHotkey.ts, WorkspaceShell.tsx, useStartHotkey.test.tsx). Unread files: none.
- [✓] **CR-04 Evidence discipline.** The single finding cites file:line + quoted text.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 1 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired (Build Verification empty; all files read end-to-end; all lenses produced output; PH-03 not high).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced — checks run: dependency-direction (imports react + react-router-dom only, no infra/db/http), module-singletons (none; comment asserts no module-level state), circular imports (none), resilience (pure client nav, TDD Armor: no network → no timeout/CB/retry applies), secrets (none), observability (no new handler/log). Security: nothing surfaced — primitives checked: SEC-01..07 (no access-control surface, no injection vector — `navigate("/start")` is a static literal, no validation surface, no XSS/SSRF, no secrets exposure), SC-01..04 (no dependency changes). Scanners: none required (no new deps, no secret-shaped strings). Quality: 1 finding + jsx-ident-scan (no undeclared identifiers introduced) + dead-surface (none — export consumed by WorkspaceShell, isTypingTarget used) + contract-drift (none) + test-coverage observation (8 tests present, all branches) + CR-10 performance (no anti-pattern matches — pure event handler, no loops/queries).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none (single `feat`, 2 dirs). PH-02 Size: none (~180 lines / 3 files). PH-03 Safety: none (0 migrations, 0 schemas, 0 secrets, 0 infra). PH-04 Completeness: none (new source ships its test). PH-03 high → CR-06 auto-downgrade fired: no.

#### Run details

- **Diff source:** `git diff change/feat-cockpit-start-change-button` (staged), source scope `apps/cockpit/client/src`
- **Neighbour expansion:** git grep — only neighbour is the in-diff mount site
- **Neighbour cap:** 1 of 1 considered, 0 excluded
- **Scanners run:** tsc, eslint, prettier (mechanical floor)
- **Scanners unavailable:** Gitleaks/Semgrep/Trivy not invoked — no new dependencies and no secret-shaped strings in a pure-UI client-navigation diff (coverage gap noted; risk negligible)
- **Lenses dispatched in parallel:** no — single-reader pass per CR-02 carve-out
