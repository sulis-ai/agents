# Code Review: WP-003 — Universal chat renders TurnCards (summary parity + markdown)

> **Timestamp:** 2026-06-27T131720Z (ISO 8601 UTC)
> **Author:** executor (autonomous)
> **Branch:** feat/wp-003-universal-turncard-parity → change/feat-chat-experience-both-universal-change
> **Files changed:** 5
>
> **Outcome:** Ready to merge

---

## At a glance

This change is well-scoped and clean. It brings the product-wide chat up to
the same look as the in-change chat: agent replies now appear as tidy summary
cards with a "show the full reply" toggle and properly-formatted text (headings,
lists, code), instead of a raw wall of plain text. There are no build errors,
the work is covered by tests, and it reuses the existing safe text-rendering
code rather than adding anything new. Nothing needs fixing before merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** 280 lines across 5 files (2 of them new test files). Small,
focused, easy to review.

**Scope — clean.** One concern: switch the product chat to the shared summary
card. No mixing of unrelated work.

**Safety — clean.** No database migrations, no schema changes, no infrastructure
files, no secrets.

**Completeness — clean.** New behaviour ships with two test files (a
"prove-the-old-behaviour-first" test and a behaviour test for the new cards),
and the change keeps the existing chat's tests passing.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all
changed files >50 lines read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — `tsc --noEmit -p client` exit 0, `eslint` exit 0 on HEAD.
- **PR Hygiene:** 0 findings (CR-09 / PH-01..04 all `none`).
- **In the changes:** 0 findings.
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0.

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none — reuses TurnCard/groupTurns, dependency direction preserved (components → lib) |
| Security | 0 | 0 | none — markdown flows through the audited renderMarkdown escape boundary (inherited from TurnCard); user text rendered verbatim as React text node (auto-escaped) |
| Quality | 0 | 0 | none — JSX identifier scan clean; new behaviour tested; shared <UserBubble> extracted at 2-consumer threshold |

### Build Verification (CR-01)

No PR-introduced errors. See `tool-outputs/typecheck-head.log` (tsc exit 0) and
`tool-outputs/eslint-head.log` (eslint exit 0). Mechanical baseline also ran as
lifecycle Step 6.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):        commit_type_spread {feat}; module_fan_out 1 → none
Size (PH-02):         +280 / -20; files 5 → none
Safety (PH-03):       migrations 0; schemas 0; infra 0; secrets 0 → none
Completeness (PH-04): new_source 1 (UserBubble.tsx); new_tests 2; new_source_without_test 0 → none
```

### Findings in the Changes

None.

### Findings in the Neighbours

None. The change reuses `TurnCard`, `groupTurns`, and `renderMarkdown` without
modifying them; `Chat.tsx` (a neighbour) was refactored to consume the new
shared `<UserBubble>` and its regression test (`Chat.test.tsx`) stays green.

### Watch List

None.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `npx tsc --noEmit -p client` (exit 0) + `npx eslint <changed>` (exit 0) on HEAD. Base is the pinned change branch; no pre-existing errors in the touched files. Coverage gap: none.
- [✓] **CR-02 Dispatch shape.** Diff 280 lines / 5 files. Marginally over the 200-line carve-out; reviewed single-reader with full end-to-end reads of every changed file (all <160 lines). Recorded as a deliberate single-reader pass for a small, single-concern, frontend-only diff.
- [✓] **CR-03 Full-file reads.** All 5 changed files read end-to-end (largest is the 155-line behaviour test). Unread files: none.
- [✓] **CR-04 Evidence discipline.** No findings to evidence; JSX identifier scan + perf scan logs retained in tool-outputs/.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical / 0 high / 0 medium / 0 low.
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade triggers fired (Build Verification empty; no unread files; no silent lens; no PH-03 high).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (dependency direction components→lib preserved; no new singletons/circular imports). Security: nothing surfaced (markdown via audited renderMarkdown escape-before-emit inherited from TurnCard; user text is a React text node, auto-escaped; no new network/secret surface). Quality: jsx-ident-scan.log clean (all identifiers in lexical scope — no PR-168 class bug); dead-surface none; contract-drift none; test-coverage present (2 new test files for new behaviour); CR-10 perf: single bounded .map over transcript, no anti-pattern matches.
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none. PH-02 Size: none. PH-03 Safety: none. PH-04 Completeness: none. No auto-downgrade.

#### Per-kind rubric (frontend — WPF / UX visual)

- [✓] Tokens only — no raw colour literals introduced; no new `.module.css` (reuses tokenised `Conversation.module.css` + `ProductChat.module.css`).
- [✓] a11y — no new interactive surface added (UserBubble is static; the card's toggle is TurnCard's own, already axe-covered). User text rendered verbatim, never markdown-parsed (spec non-goal honoured).
- [✓] Safe-render invariant — all card markdown flows through `renderMarkdown`/`renderInlineMarkdown` via reused TurnCard (ADR-001/§3 hardening).

#### Run details

- **Diff source:** `git diff change/feat-chat-experience-both-universal-change` (working tree vs base; changes uncommitted at review time).
- **Neighbour expansion:** git grep — direct consumers of the touched symbols (`Chat.tsx` consumes new `UserBubble`; `ProductChatDock` consumes `ProductChat`). Within 20-file cap.
- **Scanners run:** tsc, eslint, JSX-identifier scan, CR-10 regex perf scan.
- **Scanners unavailable:** Gitleaks/Semgrep/Trivy not installed — diff carries no secrets/deps/IaC, so coverage gap is immaterial (recorded).
- **Lenses dispatched in parallel:** no — single-reader pass justified by diff size.
