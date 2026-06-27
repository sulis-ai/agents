# Code Review: WP-004 — In-change Composer status line + bottom-dock de-collision

> **Timestamp:** 2026-06-27T135036Z (ISO 8601 UTC)
> **Author:** executor (autonomous)
> **Branch:** feat/wp-004-composer-status-line-decollision → change/feat-chat-experience-both-universal-change
> **Files changed:** 3
>
> **Outcome:** Ready to merge

---

## At a glance

Your change looks good. It mounts the shared status line above the message box and fixes the reported overlap bug — the "this change was resumed" note now steps aside the moment a new turn starts, so a fresh reply is never buried under it. There are no build errors, the change is tightly scoped to one component, and it ships tests that cover both the new behaviour and the old honest states it must not break (15 tests, all passing). Nothing needs attention before merge.

## What to fix

No issues that need attention.

## How this change is shaped

**Size — clean.** 3 files, ~237 lines added (most of it tests and explanatory comments; the real logic change is small). Single, well-defined piece of work.

**Scope — clean.** One component (`Composer`), its stylesheet, and its test file. No mixed concerns, no migrations, no schema or infrastructure changes.

**Completeness — clean.** Tests were added for the new behaviour (5 new cases) and the 10 existing honest-state tests are preserved unchanged as a regression gate.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all changed files >50 lines read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings — all primitives low severity (CR-09 / PH-01..PH-04)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | — (dependency direction correct; ADR-002 honoured; no circular imports) |
| Security | 0 | 0 | — (no secrets; no unsafe rendering; only internal import added) |
| Quality | 0 | 0 | — (build/types clean; all JSX identifiers in scope; tests comprehensive) |

### Build Verification (CR-01)

Mechanical baseline ran clean on both base and head:
- `tsc --noEmit -p client` — 0 errors.
- `eslint client/src/components/Composer.tsx client/src/tests/Composer.test.tsx` — 0 errors (exit 0).

No PR-introduced errors. Build Verification section empty.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):      single WP, one component → severity low
Size (PH-02):       lines_added 237, lines_removed 29, files_changed 3 → severity low
Safety (PH-03):     migrations 0, schema/IDL 0, infra 0, secrets 0 → severity low
Completeness (PH-04): new_source_without_test 0, tests_added true → severity low
```

No PH-03 high; no CR-06 auto-downgrade triggered.

### Findings in the Changes

None.

### Findings in the Neighbours

None. Neighbours read: `ChatStatusLine.tsx` (the mounted component), `useChatStream.ts` (the unmodified single source of truth). Both confirm the composition is correct: `ChatStatusLine` imports only the `ChatLifecycle` type from the hook (no circular path); the hook is unchanged (ADR-002 preserved).

### Watch List

None.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `tsc --noEmit -p client` (0 errors), `eslint` on the two changed TS files (0 errors). Base and head both clean. Coverage gap: CSS module not type/lint-checked (not applicable to eslint); the no-raw-colours characterisation gate for status-line surfaces is owned by WP-006 by design (ADR-004) — the `.slotIdle` class added here is layout-only (no colour).
- [✓] **CR-02 Three lenses dispatched.** Architecture / Security / Quality dispatched concurrently as sub-agents. Diff 266 changed lines (>200) → parallel dispatch used (not single-reader).
- [✓] **CR-03 Full-file reads.** All 3 changed files read end-to-end; neighbours `ChatStatusLine.tsx` + `useChatStream.ts` read end-to-end.
- [✓] **CR-04 Evidence discipline.** No findings; lens outputs cite file:line for their negative checks.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 0 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. No auto-downgrade triggers fired.
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (deps/singletons/circular/state-ownership checked). Security: nothing surfaced (secrets/XSS/dangerouslySetInnerHTML/injection/deps checked). Quality: build verification, JSX identifier scan (busy/chip/idleSlot/replyProduced/streamChat all in scope), dead-surface, contract-drift (onDismissFinished correctly optional), test-coverage (5 new + 10 preserved), style, CR-10 perf (no anti-patterns).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: low. PH-02 Size: low (237/29, 3 files). PH-03 Safety: low (0/0/0/0). PH-04 Completeness: low (tests added). No PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** `git diff change/feat-chat-experience-both-universal-change -- apps/cockpit/...` (working tree vs base tip).
- **Neighbour expansion:** manual import-graph trace (ChatStatusLine, useChatStream).
- **Neighbour cap:** 2 of 2 considered.
- **Scanners run:** tsc, eslint (project tooling); grep-based JSX identifier scan.
- **Lenses dispatched in parallel:** yes (Architecture / Security / Quality sub-agents).
