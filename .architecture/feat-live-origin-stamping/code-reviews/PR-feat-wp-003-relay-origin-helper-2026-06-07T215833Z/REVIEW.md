# Code Review: feat/wp-003-relay-origin-helper — Conversation-identity seam + relay-origin helper

> **Timestamp:** 2026-06-07T215833Z (ISO 8601 UTC)
> **Author:** executor (WP-003)
> **Branch:** feat/wp-003-relay-origin-helper → change/feat-live-origin-stamping
> **Files changed:** 5 source (+ README + journal)
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds a small, self-contained seam: a port that maps a chat session
to its conversation identity (a Thread id + a turn number), one local
read-only implementation of it, the one shared rule both readers will use to
derive the id, and a helper that formats the stamping value. The build is
clean, every new behaviour has a test (13 in total), and the read-only
guarantee still holds. Nothing needs attention before merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

Well-shaped: a single feature concern (`feat:`), one module area
(`apps/cockpit/server`), 5 new files, no migrations, no infrastructure
changes, no secrets, and tests included for the new behaviour. Nothing to
split.

## Things to take away

(omitted — the change is clean and single-purpose)

---

## Technical detail

> Internal taxonomy below for engineers + downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all
changed files read end-to-end; all lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (PH-01..04 all clean/low)
- **In the changes:** 1 finding (0 critical, 0 high, 0 medium, 1 low)
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none — clean hexagonal seam; no new external call (ADR-018 D1) |
| Security | 0 | 0 | none — no secrets/I/O; value passed as-is to #216 parser (single guard) |
| Quality | 1 (low) | 0 | one defensive unreachable branch (intentional robustness) |

### Build Verification (CR-01)

None. `tsc --noEmit -p server` exit 0; `eslint` on the 5 changed files exit 0.
Raw outputs in `tool-outputs/typecheck-head.log` + `tool-outputs/eslint-head.log`
(both empty = clean).

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):       commit_type_spread {feat}; module_fan_out 1 → severity none
Size (PH-02):        +477 / -2; 5 source files → severity low (single seam, mostly JSDoc + a 231-line test)
Safety (PH-03):      migrations 0; schema 0; infra 0; secrets 0 → severity none
Completeness (PH-04): new_source_without_test 0 (relayOrigin.test.ts covers all 4 source files) → severity none
```

### Findings in the Changes

#### `apps/cockpit/server/adapters/LocalTranscriptConversationIdentity.ts:54-55` — low (quality)

**Quoted text:**
```ts
const threadId = deriveThreadId(stem);
if (threadId === null) return null;
```

**Observation:** `sessionStemFromRef` already returns `null` for an empty /
whitespace-only stem (it trims and guards), so by the time `deriveThreadId`
is called `stem` is a non-empty trimmed string and this `null` branch is
currently unreachable from this caller.

**Why it is NOT a defect:** the two helpers each guard empty input per their
own independent contracts (defence-in-depth, EP-03 single-rule). Removing the
guard would couple the adapter to `sessionStemFromRef`'s internal trimming
behaviour — a regression in robustness. Kept intentionally.

**Recommendation:** none. Watch List only; no delta (no failing
characterisation test possible — CR-04).

### Findings in the Neighbours

None. The change introduces a new port + adapter + lib; it reads the existing
`shared/groupTurns.ts` (a pure function) and the existing `SessionResolution`
type. No neighbour gaps exposed. The existing `InferredOriginAttribution`
turn-counting pattern (`groupTurns(...).filter(isTurn)`) is the same pattern
this adapter uses; consolidating the two readers onto the shared
`deriveThreadId` is explicitly WP-004's scope (ADR-018 D2) — out of scope here.

### Watch List

- **Shared cross-adapter contract test for `ConversationIdentity`.** Only one
  adapter exists in this change (`LocalTranscriptConversationIdentity`); a
  shared port-contract test (the pattern the codebase uses for
  `OriginAttribution`/`ChangeStoreReader`) becomes relevant when the second
  adapter (`CommunicationServiceConversationIdentity`) lands — a later WP per
  ADR-018. Appropriately deferred; the current unit test fully exercises the
  one adapter against the port interface.
- The defensive branch above.

### Cross-Reference

- No prior `.security/` viability report for this project.
- No existing hardening deltas to cite.
- No neighbour pattern suggesting a broader audit.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `tsc --noEmit -p server` (exit 0) + `eslint` on 5 changed files (exit 0). Base clean (Step 6); Head clean. Coverage gap: coverage-v8 not installed → manual branch-coverage analysis recorded in journal (>=90% on new files).
- [✓] **CR-02 Single-reader pass justified.** 5 changed source files (≤5); 477 added lines but 231 are the test file and the rest are heavily JSDoc-commented across one tightly-coupled seam (port+adapter+lib). Single-reader end-to-end read used; recorded here.
- [✓] **CR-03 Full-file reads.** All 5 changed files read end-to-end (authored + re-read this session).
- [✓] **CR-04 Evidence discipline.** The one finding cites file:line + quoted text.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 1 low.
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade triggers fired (Build Verification empty; all files read end-to-end; all lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (checks: dependency-direction clean — adapter→port inward, lib→port abstraction, no infra import into domain; resilience — no new external call, ADR-018 D1; best-effort try/catch non-fatal, ADR-013; read-only gate re-asserted clean at 196 files). Security: nothing surfaced (no secrets, no process.env, no eval/child_process, no I/O; value passed as-is to #216 `parse_origin_env`/`originFromTrailerValue` — the single boundary guard, no second sanitiser). Quality: 1 low (defensive branch) + jsx-ident-scan N/A (no TSX in diff) + dead-surface none + contract-drift none (ThreadIdentity fields both set; emitted grammar matches the parser's accepted shape, verified by round-trip test) + test-coverage: 13 tests cover all branches + grammar fit + best-effort + EP-03 parity; CR-10 perf: no anti-pattern matches (no loops with I/O, no N+1, no DB/network — pure in-memory derivation).
- [✓] **CR-09 PR Hygiene applied.** Scope none; Size low; Safety none; Completeness none. No PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** git diff e61c8ca..feat/wp-003-relay-origin-helper
- **Neighbour expansion:** git grep (groupTurns / SessionResolution callers) — no gaps exposed
- **Neighbour cap:** not reached (seam is self-contained)
- **Scanners run:** tsc, eslint, manual SEC/CR-10 regex scans over the diff
- **Scanners unavailable:** Gitleaks/Semgrep/Trivy not installed — manual secret/injection scan over the (small) diff instead; no secret patterns, no process.env, no child_process in added code
- **Lenses dispatched in parallel:** no — single-reader pass per CR-02 carve-out (5 files)
