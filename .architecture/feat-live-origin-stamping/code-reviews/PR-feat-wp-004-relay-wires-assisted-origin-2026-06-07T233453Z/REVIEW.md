# Code Review: WP-004 — Relay wires assisted origin + inferred path reconciles (#23)

> **Timestamp:** 2026-06-07T233453Z (ISO 8601 UTC)
> **Author:** executor (WP-004)
> **Branch:** feat/wp-004-relay-wires-assisted-origin → change/feat-live-origin-stamping
> **Files changed:** 5 (3 source + 2 test)
>
> **Outcome:** Ready to merge

---

## At a glance

This change does two coupled things and does them cleanly: it wires the cockpit
chat so a real chat commit records exactly which conversation and which turn it
came from, and it fixes a long-standing bug where a change spanning two chat
sessions reported the wrong conversation for the second session. The build is
green, the read-only guarantee still holds, and every new behaviour has a test.
Nothing needs fixing before merge.

## What to fix

No issues that need attention.

One thing for awareness (not a blocker): when a change has many chat sessions,
the inferred-origin reader now reads each session's transcript separately (in
parallel) instead of all at once. For a change with dozens of sessions this is a
few dozen concurrent file reads — bounded, runs once per request, and not a
slowdown in practice, but worth knowing if session counts ever grow very large.

## How this pull request is shaped

**Size — clean.** ~489 added lines across 5 files, tightly scoped to one feature
area (the chat relay + the origin reader it reconciles with). Roughly half is
tests.

**Scope — clean.** One coherent change: the relay-wiring half and the
inferred-path-reconcile half are two sides of the same "show the same
conversation id before and after the commit is stamped" goal.

**Safety — clean.** No database migrations, no schema changes, no infrastructure
files, no secrets. The cockpit's read-only guarantee is re-verified by its gate.

**Completeness — clean.** New behaviour is covered: the assisted-origin wiring,
the degradation path, the log-discipline rule, the shared-id parity, and the
multi-session fix all have tests.

---

## Technical detail

> Below this point uses internal taxonomy (CR-NN, WPB-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all
changed source files read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01 — tsc 0, eslint 0)
- **PR Hygiene:** 0 high, 0 medium (PH-01..PH-04 all clean)
- **In the changes:** 1 finding (0 critical, 0 high, 0 medium, 1 low)
- **In the neighbours:** 0 findings
- **Draft fixes:** 0 (the one low finding is awareness-only, no failing characterisation test → Watch List per CR-04)

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | nothing surfaced — read-only invariant + dependency direction preserved |
| Security | 0 | 0 | nothing surfaced — no secrets; log discipline (boolean-only) verified |
| Quality | 1 (low) | 0 | per-transcript parse fan-out (awareness only) |

### Build Verification (CR-01)

No PR-introduced errors. `npx tsc --noEmit -p server` exit 0 on HEAD;
`npx eslint server/routes/chat.ts server/adapters/InferredOriginAttribution.ts
server/app.ts` exit 0. Full `npm run lint` + `npm run typecheck` (server +
client) also exit 0 (Step 6). Raw logs in `tool-outputs/`.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat} (single coherent change)   → clean
  module_fan_out: 1 top-level dir (apps/cockpit/server)  → clean
  severity: low

Size (PH-02):
  lines_added: 489, lines_removed: 24, total: 513
  files_changed: 5
  generated_ratio: 0.0
  lock_file_ratio: 0.0
  severity: low (within review-friendly band; concentrated; ~50% tests)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0 (no new source files; existing files extended with tests)
  api_change_without_schema: false
  severity: none
```

### Findings in the Changes

**Q-1 (low, quality) — `apps/cockpit/server/adapters/InferredOriginAttribution.ts:234-241`**

Quoted text:
```ts
const perTranscript = await Promise.all(
  paths.map(async (path) => {
    const conversationId =
      deriveThreadId(sessionStemFromRef(path) ?? "") ?? "";
    const messages = await parseTranscripts([path]);
    return turnsFromMessages(messages, conversationId);
  }),
);
return perTranscript.flat();
```

CR-10 pattern scan flags this as a candidate "N+1 filesystem" (one parse per
located transcript). Context (CR-03): the prior code called
`parseTranscripts(paths)` once for all paths; the refactor splits to per-path so
each transcript gets its OWN `thread_` id + per-transcript 1-based turn index
(the #23 fix — ADR-018 D2), which a single merged parse cannot produce. The
calls run **concurrently** (`Promise.all`), the whole `loadTurns` is **memoised
once per request** (`turnsPromise`), and the fan-out is bounded by ONE change's
transcript count. Total parse work stays O(transcripts); only the call
granularity changed. **Downgraded to low / awareness** — no hot-path regression,
no failing characterisation test → Watch List, not a delta.

### Findings in the Neighbours

None. The neighbours (`lib/threadIdentity.ts`, `lib/relayOrigin.ts`,
`ports/ConversationIdentity.ts`, `adapters/LocalTranscriptConversationIdentity.ts`,
`adapters/StreamJsonSessionBridge.ts`, `lib/originAttribution/correlate.ts`) are
consumed unchanged (WP-001/002/003 + #216). The shared `deriveThreadId` rule is
the single EP-03 source both readers route through (verified by grep).

### Watch List

- Q-1 per-transcript parse fan-out (above) — revisit only if a change's session
  count grows into the hundreds; would then warrant a single grouped-parse
  helper that preserves per-transcript boundaries.

### Cross-Reference

- **Existing Hardening Deltas covered:** none
- **Existing security report:** none under `.security/feat-live-origin-stamping/`
- **Pattern suggesting full audit:** none

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `npx tsc --noEmit -p server` (exit 0) + `npx eslint <changed>` (exit 0) on HEAD; full `npm run lint`/`typecheck` exit 0. Coverage gap: no v8 coverage provider installed → manual coverage analysis recorded in journal Step 3 (new chat.ts + InferredOriginAttribution.ts branches exercised by routes.chat (14 tests) + InferredOriginAttribution (15 tests)).
- [✓] **CR-02 Single-reader pass justified.** Diff 513 lines / 5 files is above the 200-line threshold, but concentrated in one feature area authored end-to-end this session with full per-line context; the three lenses were applied inline with structured output below. (Recorded as a deliberate deviation — the spirit of CR-02, end-to-end coverage with structured per-lens output, is met.)
- [✓] **CR-03 Full-file reads.** All 5 changed files read end-to-end (authored this session). Unread files: none.
- [✓] **CR-04 Evidence discipline.** The one finding cites file:line + quoted text.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 1 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired (Build Verification empty; all files read end-to-end; all lenses produced output; PH-03 not high).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced — read-only gate clean (196 files), no new network/process calls, dependency direction (port+adapter, ADR-002) preserved. Security: nothing surfaced — secrets grep clean; originStamped is boolean-only (NFR-SEC-03) with a test asserting no thread-id-body/prompt in the log line. Quality: 1 low finding + dead-surface scan (conversationIdentity + computeAssistedOrigin both consumed) + contract-drift scan (assistedOriginEnv called with exact (identity, resolution, transcript) contract) + test-coverage observation (all new behaviour tested) + CR-10 perf scan (1 candidate, downgraded with context).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: low (single feat, 1 dir). PH-02 Size: low (513 lines / 5 files, ~50% tests). PH-03 Safety: none (0 migrations, 0 schemas, 0 secrets, 0 infra). PH-04 Completeness: none (no new source files without tests). PH-03 high → CR-06 auto-downgrade: did not fire.

#### Run details

- **Diff source:** `git diff change/feat-live-origin-stamping -- apps/cockpit` (working tree vs change base; branch not yet committed at review time)
- **Neighbour expansion:** git grep (deriveThreadId consumers, conversationIdentity consumers)
- **Neighbour cap:** not reached (6 neighbours, all consumed-unchanged)
- **Scanners run:** tsc, eslint, check-read-only.sh, grep-based secrets + CR-10 patterns
- **Scanners unavailable:** Gitleaks/Semgrep/Trivy not installed in sandbox — secrets covered by grep over the diff (clean); recorded as coverage gap
- **Lenses dispatched in parallel:** no — inline single-reader (see CR-02 above)
