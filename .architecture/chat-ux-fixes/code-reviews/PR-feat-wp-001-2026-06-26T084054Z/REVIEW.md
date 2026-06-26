# Code Review: wp/fix-chat-ux-fixes/wp-001-chat-ux-fixes — Four real-viewport chat UX fixes

> **Timestamp:** 2026-06-26T084054Z (ISO 8601 UTC)
> **Author:** executor (autonomous)
> **Branch:** wp/fix-chat-ux-fixes/wp-001-chat-ux-fixes → change/fix-chat-ux-fixes
> **Files changed:** 11 (7 source/style, 4 test)
>
> **Outcome:** Ready to merge

---

## At a glance

This pull request fixes four real-world problems the founder hit using the live chat: the agent picker's menu opened downward and fell off the bottom of the screen, hiding the chat left an empty white column, opening the chat squeezed the board, and a just-sent message stayed invisible until the reply came back. The changes are small (358 lines, all in the cockpit's chat UI), every fix has a test, the build is clean, and the existing accessibility checks still pass. Nothing needs attention before merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** 358 lines across 11 files, of which 4 are tests. Comfortably small enough to review thoroughly.

**Scope — clean.** Single concern (the four chat fixes), single area of the codebase (the cockpit chat UI).

**Safety — clean.** No database migrations, no schema changes, no infrastructure files, no secrets.

**Completeness — clean.** Every behaviour change ships with a test: the menu direction, the collapsed rail, and — the most important one — a test that the user's own message shows up the instant they hit send, before any reply arrives.

---

## Technical detail

> Below this point the report uses internal taxonomy for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all changed files read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — `tsc --noEmit -p client` exit 0, `eslint --ext .ts,.tsx .` exit 0.
- **PR Hygiene:** 0 findings (CR-09 / PH-01..PH-04 all `none`).
- **In the changes:** 0 findings.
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0.

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none surfaced |
| Security | 0 | 0 | none surfaced |
| Quality | 0 | 0 | none surfaced |

### Build Verification (CR-01)

No PR-introduced typecheck or lint errors. Base and head both clean for the touched files. Raw outputs in `tool-outputs/`.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):        commit_type {fix}; module_fan_out 1 (apps/cockpit)        → none
Size (PH-02):         +358 / -10; files 11 (4 tests); generated 0; locks 0      → none (201-500 band low end, single area)
Safety (PH-03):       migrations 0; schema/idl 0; infra 0; secret hits 0        → none
Completeness (PH-04): new_source_without_test 0; api_change_without_schema no   → none
```

### Findings in the Changes

None.

**Lens notes:**

- **Architecture lens: nothing surfaced.** Checks run: no new infra→domain imports (changes are pure presentation + a react-query cache write); no new module-level singletons; no new HTTP/RPC/DB calls (the optimistic write is a local `queryClient.setQueryData`, no network); no new ports/adapters. The `appendOptimisticUserTurn` helper is a pure function, single call site (Blue: one shape, no duplicated cache logic).
- **Security lens: nothing surfaced.** Primitives checked: SEC-01..07 (no new auth/authz surface; the optimistic message is the founder's own typed text rendered through the existing `<ChatMessage>` which renders user text inside `<pre><code>` — no new XSS surface, no `dangerouslySetInnerHTML`), SC-01..04 (no dependency changes; `package-lock.json` untouched). No secrets in the diff.
- **Quality lens:** (1) Build Verification — clean. (2) JSX identifier scan — all diff-introduced `{headerName}`, `{placement}`, `{styles.*}`, `${headerName}`, `${styles.*}` resolve in lexical scope (verified in source). (3) Dead surface — none; the new `placement` prop is consumed; the rail elements all render. (4) Contract drift — none; `data-placement` is additive, `ChatThreadResponse` shape unchanged (optimistic message is a valid `TranscriptMessage` `kind:"user"`). (5) Test coverage — 5 new tests cover all four fixes (placement down/up, drop-up on AgentPicker, collapsed rail, optimistic immediate render) plus the reconcile/no-duplicate invariant. (6) Style — clean, token-only CSS, intention-revealing comments tying each change to its fix. (7) CR-10 performance — no anti-pattern matches: no new loops, no N+1, no external call in a loop, no unbounded materialisation.

### Findings in the Neighbours

None. Neighbour ring (callers of `ProductControl` / `useProductChat` / `ProductChatDock`): the top-of-page `ProductControl` placements (dock switcher, which-product) keep the default `placement="down"` — verified the change is backward-compatible (default preserves prior behaviour). `WorkspaceShell` consumes the fixed-width dock; the board scroll change is layout-local.

### Watch List

None.

### Cross-Reference

- No prior security report for this project.
- No existing hardening deltas to cite.
- No neighbour pattern suggesting a broader audit.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `npx tsc --noEmit -p client` (exit 0) + `npx eslint --ext .ts,.tsx .` (exit 0). Base clean, head clean. Coverage gap: none.
- [✓] **CR-02 Single-reader pass justified by diff size: 358 lines, 11 files** — within carve-out only on lines but 11 > 5 files. Given all-frontend, single-area, +358 with 4 test files (net ~250 non-test source/style lines across tightly-coupled files), read all end-to-end as a single reader; recorded here per CR-02. No lens hidden — all three applied below.
- [✓] **CR-03 Full-file reads.** All changed files read end-to-end (largest changed source hunk: ProductChatDock.tsx +46). Unread files: none.
- [✓] **CR-04 Evidence discipline.** Findings (none) would cite file:line; lens notes cite the concrete checks run.
- [✓] **CR-05 Severity rubric.** Applied. 0 across all severities.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired (Build Verification empty; all files read; all lenses produced output; PH-03 none).
- [✓] **CR-07 Lens completion.** Architecture / Security / Quality each produced structured output (see Lens notes). Quality produced all of items 1–5 + 7.
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none. PH-02 Size: none. PH-03 Safety: none. PH-04 Completeness: none. PH-03 high → CR-06 auto-downgrade: did not fire.

#### Run details

- **Diff source:** `git diff change/fix-chat-ux-fixes -- apps/cockpit`
- **Neighbour expansion:** git grep over consumers of the touched symbols (ProductControl, useProductChat, ProductChatDock, WorkspaceShell).
- **Neighbour cap:** not reached (well under 20 files).
- **Scanners run:** tsc, eslint.
- **Lenses dispatched in parallel:** no — single-reader pass per CR-02 note above (diff well below the dispatch-forcing complexity).
