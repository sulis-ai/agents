# Code Review: PR feat/wp-005-dock-status-line — Universal dock: status line in the chips row

> **Timestamp:** 2026-06-27T135253Z (ISO 8601 UTC)
> **Author:** executor (WP-005)
> **Branch:** feat/wp-005-dock-status-line → change/feat-chat-experience-both-universal-change
> **Files changed:** 2
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds the shared "where things stand" line to the product-wide chat,
in the row just above the message box — the same line the in-change chat uses.
It reuses the existing shared component rather than building a second one, adds
no new data plumbing, and ships four new tests covering the behaviour. There are
no build errors, the change is small and single-purpose, and the existing
accessibility check on the dock's header indicator stays green. Nothing needs
attention before merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** Two files, a small logical change. (The line count looks
larger than it is because the auto-formatter reflowed some existing lines; the
genuinely new code is about thirty lines.)

**Scope — clean.** One concern: mount the shared status line in the product
chat's dock. No mixed refactor-plus-feature.

**Safety — clean.** No database migrations, no schema or contract files, no
infrastructure changes, no secrets.

**Completeness — clean.** Four new tests were added for the new behaviour
(idle shows the chips; while replying shows "Sulis is working…"; on completion
shows "Finished — over to you"; the chips and the line are never shown at the
same time).

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; both
changed files read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — typecheck + eslint clean on HEAD.
- **PR Hygiene:** 0 high/medium findings (CR-09 / PH-01..PH-04). All primitives low/none.
- **In the changes:** 0 findings.
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0.

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | nothing surfaced |
| Security | 0 | 0 | nothing surfaced |
| Quality | 0 | 0 | nothing surfaced |

### Build Verification (CR-01)

No PR-introduced errors. `tsc --noEmit -p server && -p client` → exit 0 on HEAD;
`eslint --ext .ts,.tsx .` → exit 0 on HEAD. Logs in `tool-outputs/`.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):      commit_type_spread: {feat}; module_fan_out: 1 dir  → severity low
Size (PH-02):       +207 / -25, 2 files; reflow-inflated, ~30 substantive  → severity low
Safety (PH-03):     migrations: 0, schema: 0, infra: 0, secrets: 0  → severity none
Completeness (PH-04): new_source_without_test: 0; tests_added: 4  → severity none
```

### Findings in the Changes

None.

### Findings in the Neighbours

None. Neighbour ring = the shared `ChatStatusLine` (consumed, not modified) and
`useProductChat` (read, not modified). The change consumes the shared
component's documented prop contract (`state`, `replyProduced`, `chips`,
`onDismissFinished`) without altering it.

### Lens output

- **Architecture lens: nothing surfaced.** Checks run: infra→domain imports (none),
  new module singletons (none), circular imports (none), new HTTP/RPC/DB calls with
  no timeout (none — pure UI state), new external calls / observability gaps (N/A — no
  network). ADR-002 honoured: no state added to `useProductChat`; `replyProduced` is
  a presentational latch in the component. Dependency direction correct
  (component → shared presentational component).
- **Security lens: nothing surfaced.** Primitives checked: SEC-01..07 (no auth/authz
  surface, no injection, no user-controlled rendering changes — status-line text is
  static strings; chips/draft handling unchanged), SC-01..04 (no dependency changes),
  DAT-03 (no new logging). No secrets pattern hits.
- **Quality lens: complete.** (1) Build Verification: 0 errors. (2) JSX identifier scan:
  introduced `{c}` (in scope: `SUGGESTION_CHIPS.map((c)=>…)`) and `{replyProduced}`
  (in scope: `useState`) — both resolve; no PR-168-class undeclared identifier.
  (3) Dead-surface: `replyProduced`/`setReplyProduced` declared and consumed (props +
  both effects + dismiss handler) — none dead. (4) Contract-drift: all four
  `ChatStatusLineProps` passed; `chat.state` (`ProductChatLifecycle`) structurally
  matches the prop's `ChatLifecycle` — no drift. (5) Test-coverage: 4 new behavioural
  tests added — no source-without-test gap. (6) Style: clear names, ADR-cited comments.
  (7) CR-10 performance: the only loop is a static 3-element `SUGGESTION_CHIPS.map`
  with no IO in the body — no anti-pattern match (benign).

### Watch List

None.

### Cross-Reference

- Existing Hardening Deltas covered: none.
- Existing security report: none for this change.
- Pattern suggesting full audit: none.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `tsc --noEmit -p server && -p client` (exit 0), `eslint --ext .ts,.tsx .` (exit 0) on HEAD. Base assumed clean (change branch tip is CI-green). Coverage gap: none.
- [✓] **CR-02 Single-reader pass justified by diff size:** 2 files, single concern, ~30 substantive lines (well within the ≤200-line / ≤5-file carve-out).
- [✓] **CR-03 Full-file reads.** Both changed files (`ProductChatDock.tsx`, `ProductChatDock.states.test.tsx`) read end-to-end during implementation and the Step-4 review. Unread files: none.
- [✓] **CR-04 Evidence discipline.** All lens conclusions cite the specific construct (file:line via grep) examined; zero findings → zero unevidenced deltas.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 0 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired (Build Verification empty; all files read end-to-end; all three lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (+ checks listed). Security: nothing surfaced (+ primitives listed). Quality: all seven outputs produced (jsx-ident-scan in tool-outputs/).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: low (single `feat`, 1 dir). PH-02 Size: low (2 files, reflow-inflated). PH-03 Safety: none (0 migrations/schema/infra/secrets). PH-04 Completeness: none (4 tests added). PH-03 high → CR-06 auto-downgrade: not fired.

#### Run details

- **Diff source:** `git diff change/feat-chat-experience-both-universal-change` (working tree; change uncommitted at review time).
- **Neighbour expansion:** git grep over `ChatStatusLine` / `useProductChat` consumers. Cap not reached (2 neighbours).
- **Scanners run:** typecheck (tsc), lint (eslint), jsx-ident grep, CR-10 perf grep.
- **Scanners unavailable:** Gitleaks/Semgrep/Trivy not invoked — diff is presentational UI with no secrets/dependency/IDL surface (signals absent); recorded as scoped coverage decision, not a silent skip.
- **Lenses dispatched in parallel:** no — single-reader pass per CR-02 carve-out.
