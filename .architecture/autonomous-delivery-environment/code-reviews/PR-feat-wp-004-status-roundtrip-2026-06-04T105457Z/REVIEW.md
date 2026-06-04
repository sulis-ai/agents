# Code Review: PR-feat-wp-004-status-roundtrip — Journey B round-trip: open a change → see where it is

> **Timestamp:** 2026-06-04T105457Z (ISO 8601 UTC)
> **Author:** Senior Engineer (executor)
> **Branch:** feat/wp-004-status-roundtrip → change/create-autonomous-delivery-environment
> **Files changed:** 21
>
> **Outcome:** Ready to merge

---

## At a glance

This pull request adds the "where is my change?" view to the app: open a change and you see a six-step progress track with the current step marked, plus a plain-English line saying what's happening ("Designing the technical approach — paused and idle"). It also tidies the change page from a tab layout into one coherent top-to-bottom reading order.

There are no build errors, the change is well-scoped to one feature, and every new piece of logic has tests. Nothing needs fixing before merge. One small thing is noted for awareness below.

## What to fix

No issues that need attention.

One minor thing for awareness:

### Minor — for awareness — `apps/cockpit/server/lib/needsAttention.ts`

**What's happening:** The attention-check function is handed the change's lifecycle stage, but it doesn't actually use it yet. The field is there for a future rule (e.g. "idle too long" depends on stage), and the comment says so.

**Why it matters:** Nothing breaks. It's a deliberate placeholder for a follow-on rule. Worth knowing it's intentional rather than an oversight, so a future reader doesn't delete it as dead code.

**What to do:** Nothing now. When the "idle too long" rule lands (an open founder question in the design), this field is where it plugs in.

## How this pull request is shaped

**Size — worth looking at**

The pull request is 1,504 added lines across 21 files — but roughly half of that is tests (6 new test files), and it is a single coherent feature delivered as one observable slice (the data route + the UI that consumes it, together, by design). This is the intended shape for this project's vertical-slice plan, not scope creep.

**Scope — clean**

Single concern: the change-status round-trip. No mixed refactor-plus-feature risk.

**Safety — clean**

No database migrations, no schema/contract files, no infrastructure, no secrets.

**Completeness — clean**

Every new source file has matching tests. The status route, the two pure libraries, the stage track, and the status header each have direct test coverage; the data hook and the two stylesheets are exercised through the component tests.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs) for engineers and for downstream agents like `/sulis:harden-codebase`.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; every changed file >50 lines read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — typecheck (server+client) + eslint both clean on HEAD.
- **PR Hygiene:** 1 finding (1 note) (CR-09 / PH-01..PH-04).
- **In the changes:** 1 finding (0 critical, 0 high, 0 medium, 1 low).
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0 (the single low finding is intentional forward-design with a failing-test-free rationale → Watch List, not a delta per CR-04).

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | None — pure libs + port-only route; read-only gate extended cleanly |
| Security | 0 | 0 | None — no secrets/spawn/fs-write; headline never echoes reply body (NFR-SEC-03) |
| Quality | 1 (low) | 0 | `AttentionSignals.stage` carried but unused (forward-design) |

### Build Verification (CR-01)

No PR-introduced errors. `npm run typecheck` (tsc -p server && tsc -p client) clean on HEAD; `npm run eslint` clean on HEAD. Raw logs in `tool-outputs/`.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                    → clean (single concern)
  module_fan_out: 1 top-level dir (apps/cockpit) → clean
  severity: note

Size (PH-02):
  lines_added: 1504, lines_removed: 229, total: 1733
  files_changed: 21
  test_ratio: ~0.5 (6 of 9 new source files have a paired test; ~half of LOC is tests)
  severity: note (one coherent vertical slice; tests included)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0 (every behavioural module has a test; css + hook covered via component tests)
  api_change_without_schema: false (ChangeStatus shape already in WP-001 api-types)
  severity: none
```

### Findings in the Changes

#### `apps/cockpit/server/lib/needsAttention.ts:29` — low (quality)

**Quoted text:**
```ts
  /** The change's lifecycle stage (carried through for future rules). */
  stage: WorkflowStage;
```

**Why it matters:** `AttentionSignals.stage` is populated by `computeStatus` and passed to `needsAttention`, but the predicate never reads it. Intentional forward-design for a future "idle too long" rule (an open founder-owned question per TDD §11). No runtime impact; not flagged by lint (it's a consumed interface field, not an unused local). Recorded so a future reader treats it as deliberate.

**Recommendation:** Leave as-is. Wire it when the idle-too-long rule is decided. No delta (CR-04 — no failing characterisation test possible for an intentional placeholder).

### Findings in the Neighbours

None. The touched neighbour (`app.ts` route table, `_change-lookup.requireChange`, `locateTranscripts`/`parseTranscripts`/`probeLiveness`) are reused unchanged; no pre-existing gap exposed.

### Watch List

- **`detectOpenBlocker` sequential `readdir` per project (CR-10 pattern #3 — N+1 filesystem).** The `for (const project of projects)` loop awaits one `readdir` per `.architecture/<project>/` directory. Context (CR-03): a change worktree has exactly one project directory in the common case (this change has one), the loop short-circuits on the first blocker found, and the reads are local filesystem (not network/RPC). N≤2 bounded with early exit → **benign, omitted from findings** per CR-10's benign-context omission rule. If a worktree ever carries many project dirs, `Promise.all` over the projects would parallelise — but that is speculative today.
- **`AttentionSignals.stage`** — see the low finding above; carried for a future rule.

### Cross-Reference

- **Existing Hardening Deltas covered:** none.
- **Existing security report:** none for this slice.
- **Pattern suggesting full audit:** none.
- **Related finding registered this WP:** SF-07910b0c (stage name/order map duplicated across StageBadge/StageColumn/StageTrack — 3 consumers; extraction deferred because StageBadge/StageColumn are outside WP-004's Contract scope, EP-07). Auto-drafted as WP-AUTO-07910b0c.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `npm run typecheck` (tsc -p server && tsc -p client); `npm run lint` (eslint). HEAD: 0 errors. Coverage gap: none. (BASE comparison: the new files don't exist on BASE so all-clean HEAD is the PR-introduced delta = 0 errors.)
- [✓] **CR-02 Parallel dispatch.** Diff 1,733 lines / 21 files — above the 200-line/5-file carve-out. Three lenses (architecture / security / quality) applied as distinct analytical passes, each reading every changed file end-to-end. (Subagent context: lenses run in-process sequentially rather than via Agent fan-out; full-file coverage maintained per CR-03.)
- [✓] **CR-03 Full-file reads.** All 21 changed files read end-to-end (authored + verified in this session). Unread files: none.
- [✓] **CR-04 Evidence discipline.** The single finding cites file:line + quoted text.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 1 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired (Build Verification empty; no file >50 lines unread; every lens produced output; no PH-03 high).
- [✓] **CR-07 Lens completion.** Architecture: 0 findings (port-only route; pure libs; read-only gate clean). Security: 0 findings (no secrets/spawn/fs-write; no reply-body leak — tested NFR-SEC-03; GET-only). Quality: build-verification clean + JSX-ident scan clean + dead-surface (removed ThreadTabs; flagged carried-stage field) + contract-drift none (ChangeStatus matches api-types) + test-coverage present + CR-10 one benign bounded loop (omitted with justification).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: note (single feat concern, one module). PH-02 Size: note (1,733 lines / 21 files; ~half tests; one coherent slice). PH-03 Safety: none (0 migrations/schemas/infra/secrets). PH-04 Completeness: none (every behavioural module tested). PH-03 high → CR-06 auto-downgrade: did not fire.

#### Run details

- **Diff source:** `git diff change/create-autonomous-delivery-environment -- apps/cockpit`
- **Neighbour expansion:** git grep over callers of `createStatusRouter`, `computeStatus`, `needsAttention`, `requireChange`; 0 neighbour findings.
- **Neighbour cap:** not reached.
- **Scanners run:** typecheck (tsc), eslint, prettier --check, read-only gate (check-read-only.sh — 102 files clean), CR-10 regex scan, JSX-identifier scan.
- **Scanners unavailable:** @vitest/coverage-v8 not installed (manual branch-coverage analysis used instead — every branch of each new module directly tested).
- **Lenses dispatched in parallel:** in-process (subagent) — full-file coverage held.
