# Code Review: feat/wp-009-concierge-ask-roundtrip — concierge investigation containment (fix-forward)

> **Timestamp:** 2026-06-04T141501Z (ISO 8601 UTC)
> **Author:** Iain Niven-Bowling
> **Branch:** feat/wp-009-concierge-ask-roundtrip → change/create-autonomous-delivery-environment
> **Files changed:** 5 (2 source, 2 test, 1 doc)
>
> **Outcome:** Ready to merge

---

## At a glance

This change makes the concierge reliably treat any "look into / investigate / why is X failing" request as a *new piece of work to start* — never something it quietly investigates on the spot. Before, the concierge would sometimes start digging through your repos inline (the live failure: "Can you look into why the deploy keeps failing?" had it reading deploy configs in chat). Now the decision is made by a fixed, predictable rule before the AI is ever asked to answer, and the AI answer-path is skipped entirely for those requests. There are no build errors, the change is small and well-scoped, and both problem phrasings are now pinned by tests so they can't quietly regress.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** 174 lines across 5 files, one concern (containment of investigation intent). Easy to review thoroughly.

**Scope — clean.** Single `fix:` concern. No mixed refactor + feature.

**Safety — clean.** No database migrations, no schema changes, no infrastructure files, no secrets. The change actually *narrows* what the system does on its own (it asks the AI to do less, not more).

**Completeness — clean.** Both new behaviours ship with tests: a table of investigation phrasings that must route to "start a change", and a table of genuine read-only questions that must stay answered inline. The live examples that drove the fix are in the tests verbatim.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high in diff; Build Verification empty; all changed files read end-to-end; all three lenses produced output; no auto-downgrade trigger fired.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — typecheck + eslint + read-only gate (135 files) + full suite (655 tests) all clean.
- **PR Hygiene:** 0 findings (PH-01..04 all `none`).
- **In the changes:** 0 findings.
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0.

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none — short-circuit reuses existing `openSseHeaders`/`writeSseFrame` |
| Security | 0 | 0 | none — change reduces LLM-reached surface; read-only gate clean |
| Quality | 0 | 0 | none — both behaviours pinned by deterministic table tests |

### Build Verification (CR-01)

No PR-introduced errors. See `tool-outputs/mechanical-floor.log`. BASE (fc0b4e0) and HEAD both typecheck/lint clean; delta empty.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):        commit_type_spread: {fix}; module_fan_out: 1 → none
Size (PH-02):         174 lines / 5 files → none
Safety (PH-03):       migrations: 0, schema: 0, infra: 0, secrets: 0 → none
Completeness (PH-04): new_source_without_test: 0; api_change_without_schema: false → none
```

### Findings in the Changes

None.

The change has two parts, both reviewed end-to-end:

1. `conciergeRead.ts` — `detectRoute` broadened: added investigation phrases
   (`diagnose`, `debug`, `troubleshoot`, `find out why`, `figure out why`,
   `root cause`, `what's going wrong`, …) to `CONSEQUENTIAL_PHRASES`, plus a new
   anchored `SYMPTOM_INTERROGATIVE` regex catching "why is/are/does/do … <fail|
   broken|slow|dropping|erroring|…>". The regex is `^`-anchored with a single
   `.*` between two fixed alternation groups — no nested quantifier, so no
   catastrophic-backtracking (ReDoS) exposure. Leading-only anchoring keeps
   read-only questions that merely mention a symptom noun ("which change fixed
   the failing webhook?") classified as read-only.

2. `chat.ts` — `handleConcierge` now SHORT-CIRCUITS the bridge when
   `route !== null`: it emits `complete{route}` and returns WITHOUT calling
   `sessionBridge.relay`. This is the load-bearing fix — the inline read-only
   relay (the LLM answer path) is never started for a consequential intent, so
   investigation cannot run loose. The read-only (`route === null`) path is
   unchanged. Reuses existing `openSseHeaders` + `writeSseFrame` (no new SSE
   plumbing). No new write/spawn/IO verb introduced — read-only invariant intact.

### Findings in the Neighbours

None. The client (`ConciergeChat.tsx`) already gates the OFFER on `route !== null`
and never acts inline — its contract is unchanged by this fix and remains correct.

### Watch List

None.

### Cross-Reference

- Prior WP-009 review bundle (Step 6.5 first pass) exists in this directory tree;
  this is the fix-forward re-review on the broadened+contained behaviour.
- No security viability report to cite; no existing hardening deltas duplicated.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `npm run typecheck`, `npm run lint`, `npm run check:read-only`, `npx vitest run`. BASE clean, HEAD clean. Delta: 0 errors. See `tool-outputs/mechanical-floor.log`.
- [✓] **CR-02 Dispatch shape.** Single-reader pass justified by diff size: 174 lines, 5 files (within carve-out of ≤200 lines AND ≤5 files).
- [✓] **CR-03 Full-file reads.** Both changed source files (`conciergeRead.ts` 200 lines, `chat.ts` ~490 lines) read end-to-end; both test files read end-to-end. No sampling.
- [✓] **CR-04 Evidence discipline.** No findings to evidence; the two changed surfaces are described with file + behaviour.
- [✓] **CR-05 Severity rubric.** Applied — 0 findings at any severity.
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade trigger fired (Build Verification empty; no file >50 lines unread; all lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (no dependency-direction/singleton/circular-import change; reuses existing helpers). Security: nothing surfaced (no new write/spawn/io; read-only gate clean 135 files; bounded regex, no ReDoS). Quality: nothing surfaced (typecheck/lint clean; both behaviours pinned by deterministic table tests; no dead surface; no contract drift; CR-10 perf clean — no loops/IO added).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none. PH-02 Size: none (174/5). PH-03 Safety: none (0 migrations/schema/infra/secrets). PH-04 Completeness: none (tests included). No PH-03 high → no CR-06 auto-downgrade.

#### Run details

- **Diff source:** `git diff fc0b4e0..working-tree` (fix-forward, pre-commit).
- **Neighbour expansion:** git grep over concierge symbols; client `ConciergeChat.tsx` inspected (1 file, well under 20-file cap).
- **Scanners run:** project typecheck (tsc), eslint, read-only inventory gate, vitest.
- **Lenses dispatched in parallel:** no — single-reader per CR-02 carve-out.
