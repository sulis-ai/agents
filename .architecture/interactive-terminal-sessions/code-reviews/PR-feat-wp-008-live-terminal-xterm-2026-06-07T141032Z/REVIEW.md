# Code Review: feat/wp-008-live-terminal-xterm — LiveTerminal xterm.js component (3rd tab)

> **Timestamp:** 2026-06-07T141032Z (ISO 8601 UTC)
> **Author:** WP-008 executor
> **Branch:** feat/wp-008-live-terminal-xterm → change/extend-interactive-terminal-sessions
> **Files changed:** 10 (9 source/test + package.json; package-lock excluded from review)
>
> **Outcome:** Ready to merge

---

## At a glance

This pull request adds the live Terminal tab to the cockpit — the third tab
(Chat | Files | Terminal) that shows a real terminal you can watch and type
into. The build is clean (no type or lint errors), every new behaviour has a
test, and the visual styling uses the approved design colours throughout. Two
small robustness points surfaced during review and were both fixed in place
before this report — see "What was fixed". Nothing outstanding needs your
attention.

## What to fix

No issues that need attention. Two small improvements were found and already
applied during the review (below); nothing remains open.

### What was fixed (applied inline during review)

**Worth fixing — keystrokes and resize were "fire and forget" with no error catch**

- *What was happening:* when you type into the terminal, the keystrokes are
  sent to the session. The send was launched without catching the case where
  the session has gone away — which could surface as a stray "unhandled
  error" warning in the browser console.
- *Why it matters:* it's harmless to the user, but unhandled background
  errors are noisy and can mask real problems later.
- *What was done:* the send (and the resize and the tab-close detach) now
  explicitly ignore a failure on purpose — matching the design rule that
  typing into a closed terminal is a safe no-op. A test was added proving a
  failed keystroke send never crashes the component.

**Minor — a test helper option had no test using it**

- *What was happening:* the test file declared a way to simulate "the session
  failed to start" but no test actually used it.
- *What was done:* added a test that simulates a failed start and confirms the
  terminal shows the "disconnected — reconnect" panel instead of a blank pane.

## How this pull request is shaped

**Size — worth looking at, but expected here.** ~1,100 new lines, but roughly
two-thirds is tests (three test files) and the design stylesheet. The actual
component logic is one focused file. This is a single, self-contained feature
— not mixed scope.

**Scope — clean.** One concern (the Terminal tab), one `feat` change type, all
within `apps/cockpit/client`.

**Safety — clean.** No database migrations, no schema changes, no
infrastructure files, no secrets.

**Completeness — clean.** Every new source file ships with tests: the
component, the tab wiring, and the client bridge factory are all covered.

---

## Technical detail

> Internal taxonomy (CR-NN, PH-NN, lens IDs) below for engineers and
> downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all
changed files >50 lines read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — `tsc --noEmit`
  clean on HEAD (server + client); `eslint` clean.
- **PR Hygiene:** 0 blocking findings. Size band medium (mitigated: ~715 of
  1109 added lines are tests); scope/safety/completeness clean (CR-09 /
  PH-01..04).
- **In the changes:** 2 findings (0 critical, 0 high, 2 medium/low) — **both
  resolved inline before report write.**
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0 (both findings fixed in the WP; no deltas queued).

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 1 (resolved) | 0 | Fire-and-forget feed/resize/detach swallowed rejections (best-effort per §2.12.2; now explicitly caught) |
| Security | 0 | 0 | Keystrokes passed verbatim per ADR-003 (gate-at-attach, not byte-filter) — correct; no component-introduced vector |
| Quality | 1 (resolved) | 0 | `openError` test option declared but unused → added a test exercising the open-rejection path |

### Build Verification (CR-01)

No PR-introduced errors. `tool-outputs/typecheck-head.log` and
`tool-outputs/lint-head.log` both clean. BASE also builds (merged change
branch). Mechanical floor satisfied.

### Findings in the Changes

#### F-01 — `apps/cockpit/client/src/components/LiveTerminal.tsx` — medium (architecture/quality) — RESOLVED INLINE

**What:** `feed`, `resize`, and the unmount `detach` were dispatched with bare
`void activeBridge.feed(...)` etc., swallowing any promise rejection.

**Quoted (pre-fix):**
```tsx
sink.onData((data) => {
  void activeBridge.feed(changeId, new TextEncoder().encode(data));
});
```

**Why it matters:** A rejection (e.g. the session died → NO_SESSION mid-feed)
became an unhandled promise rejection. Contract §2.12.2 mandates feed is
"no-op-safe after detach/close (best-effort)", so suppressing the error is
correct — but it must be *caught*, not left to bubble.

**Resolution:** Replaced bare `void` with explicit `.catch(() => {/* best-effort */})`
on feed, resize, and detach. Added a regression test
(`does not throw when a keystroke feed rejects`).

#### F-02 — `apps/cockpit/client/src/components/LiveTerminal.test.tsx` — low (quality) — RESOLVED INLINE

**What:** `FakeBridgeOptions.openError` was wired into the `open()` mock (it
throws when set) but no test passed `openError`, leaving the component's
`open()`-rejection path (→ disconnected) unverified by an explicit test.

**Resolution:** Added `renders the disconnected state when open() rejects
(failed spawn)` exercising `openError: PTY_OPEN_FAILED`.

### Findings in the Neighbours

None. The diff touches `ThreadTabs.tsx` (extended TabId + Terminal slot) and
`ThreadView.tsx` (mount). Both callers/callees were read; the existing Chat/
Files panels are unaffected (one-panel-at-a-time rendering preserved).

### Watch List

- **Live socket transport is not yet wired** (`terminalBridge.ts`
  `notYetWiredTransport` returns `NOT_PTY_SESSION`). This is by design per
  WP-008 Notes — the live wiring + the browser-`Buffer` concern in
  `TerminalBridgeClient`'s base64 codec are WP-010's responsibility (the
  Playwright e2e proves the live round-trip). Not a finding against this WP;
  recorded so WP-010 picks it up.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `npm run typecheck` (tsc server+client) + `npm run lint` (eslint) on HEAD: 0 errors. BASE builds. Coverage gap: none.
- [✓] **CR-02 Dispatch shape.** Diff >200 lines / >5 files. Sub-agent parallel dispatch is unavailable in the executor's Step-6.5 context; performed a thorough single-reviewer pass applying all three lenses with full-file reads. Recorded as the deviation; mitigated by the diff being single-author, single-concern, and freshly written.
- [✓] **CR-03 Full-file reads.** All changed files >50 lines (LiveTerminal.tsx, LiveTerminal.test.tsx, LiveTerminal.module.css, ThreadTabs.tsx, terminalBridge.ts) read end-to-end. Unread: none.
- [✓] **CR-04 Evidence discipline.** Findings cite file + quoted text.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 1 medium, 1 low — both resolved.
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade triggers fired (Build Verification empty; all files read; all lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture: 1 finding (resolved) + dependency/resilience checks. Security: nothing surfaced — keystroke bytes verbatim per ADR-003; no secrets (grep clean); no injection vector introduced. Quality: 1 finding (resolved) + JSX identifier scan (all idents in scope) + CR-10 perf scan (one bounded buffer-flush loop, benign) + dead-surface + test-coverage (full).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: low. PH-02 Size: medium (1109 added; ~715 tests). PH-03 Safety: none (0 migrations/schemas/secrets/infra). PH-04 Completeness: none (all new source tested). No PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** `git diff --cached change/extend-interactive-terminal-sessions`
- **Neighbour expansion:** git grep (ThreadTabs callers, ThreadView mount). 2 neighbours, well under the 20-file cap.
- **Scanners run:** tsc, eslint, prettier, grep-based secret/JSX/CR-10 scans.
- **Lenses dispatched in parallel:** no (executor Step-6.5 single-session; see CR-02 note).
