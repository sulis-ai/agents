# Code Review: PR feat/wp-007 — Wire the enriched feed into the redesigned card on the live board

> **Timestamp:** 2026-06-09T210820Z (ISO 8601 UTC)
> **Author:** autonomous executor (WP-007)
> **Branch:** feat/wp-007-wire-enriched-card-into-board → change/feat-cockpit-board-refresh
> **Files changed:** 2
>
> **Outcome:** Ready to merge

---

## At a glance

This change connects the live "changes in flight" board to the richer feed
behind it, so each card shows the real "waiting on you" or health read and
the real last-activity time — and it makes the board behave well when the
background refresh hits a hiccup. No build errors, the change is tightly
scoped to the board and its tests, and every new behaviour is covered by a
test. There is nothing that needs attention before merge.

The one genuinely load-bearing change: when a background refresh fails
mid-session, the board now keeps showing the last good view instead of
flickering to a full-screen error. That is exactly the behaviour the work
called for, and it is proven by a test that fails without the fix.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** 300 lines added, 14 removed, across 2 files. Most of the
addition is the new test suite; the live-code change in the board itself is
about 40 lines, mostly explanatory comments around a small render rule.

**Scope — clean.** A single, well-defined change: wire the real feed through
to the card and own the board's loading / error / empty behaviour against
the wider data. One concern, one purpose.

**Safety — clean.** No database changes, no schema or infrastructure files,
no secrets.

**Completeness — clean.** Eight new tests accompany the change, covering the
field flow-through, the feed-failure retry, the keep-last-good-on-poll-failure
behaviour, the filter-narrows-the-same-board behaviour, and the
shipped-change-drops-off behaviour.

---

## Technical detail

> Below this point the report uses internal taxonomy for engineers and
> downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty;
both changed files read end-to-end; all three lenses produced output.

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

`tsc --noEmit -p client` → 0 errors (HEAD). `eslint client/src/pages/Board.tsx
client/src/tests/Board.test.tsx` → 0 errors (HEAD). Base was already clean;
delta empty. Raw logs in `tool-outputs/`.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):    commit_type_spread: {feat}; module_fan_out: 1 dir → severity none
Size (PH-02):     +300 / -14; files: 2; generated_ratio: 0 → severity none
Safety (PH-03):   migrations: 0; schema/idl: 0; infra: 0; secrets: 0 → severity none
Completeness(PH-04): new_source_without_test: 0; api_change_without_schema: false → severity none
```

### Findings in the Changes

None.

#### Architecture lens — nothing surfaced

Checks run: domain↔infrastructure import direction (no new infra imports;
the only new import is `LIVENESS_POLL_MS`, a config constant, in the test);
new singletons / `getInstance` (none); circular imports (none); new
HTTP/RPC/DB calls / timeouts / circuit breakers (none — the change is pure
client render-gating); secrets (none); observability (n/a for this surface).
The EF-3 last-good-on-failed-poll behaviour is itself a resilience
improvement (the board degrades gracefully instead of dropping to an error).

#### Security lens — nothing surfaced

Primitives checked: SEC-01..07 (access control, auth, injection, validation,
XSS, SSRF, secrets). No new request handling, no user-input sink, no secret
material, no new external origin. The board renders data already validated by
the typed client funnel (`apiGet`); the foot-verdict `why` text is drawn from
an enumerable reason set (NFR-SEC-03, in the unchanged ChangeCard), never an
echoed reply body. SC-01..04 (dependency CVEs): no dependency changes.

#### Quality lens

1. **Build Verification follow-up:** none (CR-01 clean).
2. **JSX identifier scan:** the diff introduced no new `{ident}` / `${ident}`
   JSX references requiring scope verification; the render change swaps
   `active.isSuccess` for the locally-declared `hasData`. `jsx-ident-scan.log`
   empty.
3. **Dead surface:** `data` and `hasData` are both consumed (four render
   sites + the column computation). No unused props/exports/imports.
4. **Contract drift:** none — the change consumes the existing
   `active.data: Change[] | undefined` shape; no enum/DTO field assumptions.
5. **Test coverage:** strong. Eight new tests cover field flow-through
   (waiting XOR health, probe recency), EF-1 (feed-fail + retry), EF-3
   (poll-fail keeps last-good, no error-box flicker, manual Refresh),
   UC-6 (filter narrows the same six-lane board, clearing restores),
   AF-5 (shipped drops off on next poll), NFR-POLL-1 (one feed poll).
   jest-axe assertion on the populated board retained (WPF-06).
6. **Style / readability:** clear. The `hasData` rule is named and documented;
   the header comment explains why the render gates on data presence rather
   than the success flag.
7. **Performance procedural checks (CR-10):** no anti-pattern matches. The
   only loops are over `BOARD_STAGES` (6 fixed lanes) and `columns` (6) —
   bounded, no per-item fetch/DB/RPC/FS call. No N+1, no unbounded
   materialisation, no per-render invariant recomputation in a hot path.

### Findings in the Neighbours

None. Neighbours (StageColumn, ChangeCard, useChangesWithLiveness, useSearch)
were read; the diff threads the existing `Change` shape through them
untouched. No pre-existing gap exposed by the integration.

### Watch List

Empty.

### Cross-Reference

- No prior security viability report for this project at `.security/`.
- No existing accepted hardening deltas relevant to this diff.
- No neighbour pattern suggesting a broader audit.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `tsc --noEmit -p client` + `eslint
  <changed>` from `apps/cockpit`. Base clean; head clean; delta empty.
- [✓] **CR-02 Dispatch shape.** Single-reader pass justified: live-code change
  is ~40 lines in 1 production file; the rest is the test file. Both files
  read end-to-end. (The 300-line total is dominated by the new test suite,
  which the reviewer authored and read in full.)
- [✓] **CR-03 Full-file reads.** Both changed files (Board.tsx, Board.test.tsx)
  read end-to-end. No sampling.
- [✓] **CR-04 Evidence discipline.** No findings; nothing to evidence. Negative
  checks recorded per lens.
- [✓] **CR-05 Severity rubric.** Applied; 0 findings at every severity.
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade trigger fired
  (Build Verification empty; all files read end-to-end; all lenses produced
  output; no PH-03 high).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (checks
  listed). Security: nothing surfaced (primitives listed). Quality: all seven
  outputs produced (items 1-5 + 7 explicit; item 6 clean).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none. PH-02 Size: none.
  PH-03 Safety: none. PH-04 Completeness: none. No auto-downgrade.

#### Run details

- **Diff source:** `git diff change/feat-cockpit-board-refresh` (local worktree).
- **Neighbour expansion:** git grep / direct read (StageColumn, ChangeCard,
  useChangesWithLiveness, useSearch, RefreshButton, LivenessProbe,
  ChangeHealthBadge, WaitingOnYou).
- **Neighbour cap:** not reached (8 files considered).
- **Scanners run:** tsc, eslint (project gates). Gitleaks/Semgrep/Trivy not
  run — no secret-shaped or dependency surface in the diff (coverage gap noted;
  the diff is two TSX files with no new external origin or dependency).
- **Lenses dispatched in parallel:** no — single-reader pass per CR-02
  (live-code change under threshold).
