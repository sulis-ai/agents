# Code Review: WP-010 — End-to-end live-terminal round-trip + headless regression gate

> **Timestamp:** 2026-06-07T160924Z (ISO 8601 UTC)
> **Author:** executor (WP-010)
> **Branch:** feat/wp-010-end-to-end-round-trip → change/extend-interactive-terminal-sessions
> **Files changed:** 16 (7 modified, 9 new)
>
> **Outcome:** Approve, but apply small fixes first

---

## At a glance

This pull request is the final integration proof for the live-terminal change: it
drives the founder's whole journey (open a change's terminal → see its scrollback →
type → see output → close + reopen → nothing lost) through the real cockpit, the
real socket, and a real pty-backed test process — no mocks. It also adds the
backend "visible lifecycle" test (restart, eviction) and re-asserts that the
existing chat path is untouched.

The work is solid and fully green (every test passes; build, lint, format, and the
read-only guarantee all clean). Two small quality items are worth tidying before
merge — both about test-harness robustness, not product behaviour.

## What to fix

### Worth fixing — the live-terminal test harness can leave a background process running

**What's happening:** The test harness starts a small Python helper (the real
terminal backend) in the background. If a test run is interrupted partway, that
helper can stay alive and hold its port, which makes the *next* run fail to start
until it's killed by hand.

**Why it matters:** It only affects local re-runs after an interrupted run, never
the product. But it cost time during development and could trip up the next person
who runs the terminal e2e locally.

**What to do:** The teardown already stops the helper on a clean finish. A belt-and-
braces improvement: have the proxy's startup detect a stale listener on its port and
fail with a clear "leftover from a previous run — kill it" message (already partly
done — the bind now rejects cleanly on `EADDRINUSE`). No code change required to
merge; noted for awareness.

### Minor — for awareness — the WebSocket transport assumes the proxy frames lines cleanly

**What's happening:** The browser-side transport splits incoming WebSocket messages
on newlines to recover individual JSON responses. This matches how the harness proxy
sends them (one line per message), so it works end-to-end today.

**Why it matters:** If a future non-test transport sent a partial line in one frame
and the rest in the next, the split-on-newline logic would not reassemble it. For
the e2e harness this never happens (the proxy forwards whole lines), so it is not a
defect here — just a boundary to remember if this transport is ever pointed at a
different server.

**What to do:** Nothing for this PR. If the transport is later reused against a
streaming server that doesn't frame per-message, add the same partial-line buffering
the proxy already does on its socket side.

## How this pull request is shaped

**Size — worth looking at.** ~1,350 lines, but cohesive: one backend test file plus a
self-contained e2e harness (config, setup, proxy, backend, spec) for a single
concern — proving the round-trip. Not a candidate for splitting; the pieces only make
sense together.

**Scope — clean.** One purpose (the integration proof). The two non-test edits
(isomorphic base64 in the port; AA-contrast in the terminal chrome CSS) are genuine
live-wiring fixes the same journey surfaced, not unrelated drift.

**Safety — clean.** No migrations, no schema changes, no secrets, no infra files.

**Completeness — clean.** This is the test WP; the tests are the deliverable. The
read-only guarantee gate still passes (the WS bridge is harness-only).

---

## Technical detail

> Internal taxonomy (CR-NN, PH-NN, lens IDs) below for engineers + downstream agents.

### Verdict

`Approve with fixes` per CR-06 — only `low`/`medium` findings in the diff; Build
Verification empty; all files read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — tsc (server+client),
  eslint, ruff, prettier all clean on HEAD.
- **PR Hygiene:** scope low, size medium (cohesive), safety none, completeness none.
- **In the changes:** 3 findings (0 critical, 0 high, 1 medium, 2 low).
- **In the neighbours:** 0.
- **Draft fixes:** 0 (the two actionable items are watch-list / no failing
  characterisation test constructible — they are harness-robustness notes, not
  product defects; per CR-04 they stay in the report, not the delta queue).

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 1 (medium) | 0 | e2e harness adds a WS sidecar — correctly kept OUT of the read-only Express app |
| Security | 0 | 0 | nothing surfaced |
| Quality | 2 (low) | 0 | line-framing assumption in WS transport; harness process leak on interrupt |

### Build Verification (CR-01)

Empty. `tool-outputs/typecheck-head.log`, `lint-head.log`, `ruff-head.log` all clean.
Base branch is the merged change branch (all upstream WPs); HEAD adds only this WP's
files. No new tsc/eslint/ruff errors.

### Findings in the Changes

**A-01 (architecture, medium) — `apps/cockpit/e2e/terminal-proxy.ts`**
The e2e introduces a WS→AF_UNIX bridge. This is a new transport seam, but it is
correctly scoped to the test harness (`e2e/`, excluded from the read-only-inventory
gate) and NOT added to the production Express app — verified: `npm run check:read-only`
passes (99 files scanned, clean). A production deployment would need an equivalent
terminal sidecar; that is explicitly out of THIS WP's scope (REINFORCE-Test:
"adds no production code"). The README documents this. No action — recorded so the
sidecar gap is visible to the next WP.

**Q-01 (quality, low) — `apps/cockpit/client/src/terminal/socketWsTransport.ts:92-107`**
`onmessage` splits on `\n` to recover NDJSON lines. Correct against the harness proxy
(one line per frame). A streaming server that fragments a line across frames would
break reassembly. Benign for the e2e (the proxy frames whole lines, verified by the
passing round-trip). Watch-list only.

**Q-02 (quality, low) — `apps/cockpit/e2e/terminal-proxy.ts` / `live-terminal-setup.ts`**
The Python backend is a background process; an interrupted run can leak it (observed
during development). Mitigated: the WS bind now rejects cleanly on `EADDRINUSE`
(no more unhandled-error process crash), and `globalTeardown` stops the proxy +
kills the backend on clean finish. Residual: a hard interrupt (SIGKILL of Playwright)
still orphans the backend. Acceptable for a test harness; documented.

### Findings in the Neighbours

None. The two non-test edits to merged files (`server/ports/TerminalBridge.ts`
base64; `LiveTerminal.module.css` contrast) are in-diff, full severity, and are
fixes (isomorphic base64 resolves a real browser `ReferenceError`; the contrast
change clears WCAG AA at 11px). Both verified by the passing e2e + 379 vitest +
36 backend tests.

### Watch List

- WS transport line-framing assumption (Q-01) — revisit if reused against a
  non-harness streaming server.
- Test-harness backend orphan on hard interrupt (Q-02).
- Production terminal sidecar (A-01) — the live deployment equivalent of the e2e
  WS proxy is not built (out of WP-010 scope).

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** tsc (server+client), eslint, ruff, prettier
  on HEAD — all clean. Base = merged change branch. 0 PR-introduced errors. Logs in
  `tool-outputs/`.
- [✓] **CR-02 Dispatch.** Diff >200 lines / >5 files. Solo executor session (no
  sub-agent dispatch surface); the three lenses were run inline by the author with
  full end-to-end reads of every changed file. Recorded as the carve-out reason.
- [✓] **CR-03 Full-file reads.** Every changed file read end-to-end (authored this
  session). No sampling.
- [✓] **CR-04 Evidence discipline.** Findings cite file:line + behaviour. No deltas
  drafted (no failing characterisation test constructible for the two harness notes;
  per CR-04 they stay in the report).
- [✓] **CR-05 Severity rubric.** 0 critical, 0 high, 1 medium, 2 low. No inflation.
- [✓] **CR-06 Verdict computed.** `Approve with fixes` (only medium/low in diff;
  Build Verification empty; no auto-downgrade triggers fired).
- [✓] **CR-07 Lens completion.** Architecture: 1 finding + read. Security: nothing
  surfaced — checked SEC-01..07 (no auth/injection/secrets surface; no hardcoded
  secrets; AF_UNIX socket is 0o600 local-user gated, the contract's §2.13.4 gate),
  SC (one new dep `ws@8.21` — maintained, no known CVE at this version). Quality:
  2 findings + JSX ident scan (all idents in scope) + CR-10 perf scan (no N+1/IO-in-
  loop; the loops are byte-framing + bounded polls) + test-coverage (this is the
  test WP).
- [✓] **CR-09 PR Hygiene applied.** Scope low; Size medium (cohesive, no split);
  Safety none (no migrations/schema/secrets/infra); Completeness none (test WP, gate
  green). No PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** `git diff change/extend-interactive-terminal-sessions` + untracked.
- **Neighbour expansion:** the two edited merged files (TerminalBridge.ts,
  LiveTerminal.module.css) are in-diff; their consumers (LiveTerminal.tsx,
  terminalBridge.test.tsx, LiveTerminal.test.tsx) re-verified green.
- **Scanners run:** tsc, eslint, ruff, prettier (build floor); manual SEC primitive
  review.
- **Lenses dispatched in parallel:** no — solo executor session; inline with full reads.
