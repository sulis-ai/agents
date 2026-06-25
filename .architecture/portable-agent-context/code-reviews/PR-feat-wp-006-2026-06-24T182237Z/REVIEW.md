# Code Review: PR feat/wp-006 — Cockpit raw view reads our durable store

> **Timestamp:** 2026-06-24T182237Z (ISO 8601 UTC)
> **Author:** executor (CH-GJ9KQR WP-006)
> **Branch:** wp/create-portable-agent-context/wp-006-cockpit-raw-view-repoint → change/create-portable-agent-context
> **Files changed:** 7 (4 modified, 3 new); journal excluded
>
> **Outcome:** Ready to merge

---

## At a glance

This change re-points the cockpit's raw conversation view to read from the
cockpit's own durable record first, and only fall back to Claude's session
files when no durable record exists yet. It is small, well-scoped, and fully
tested — new behaviour has new tests, the build is clean, and the read-only
guarantee still holds. There is one thing worth being aware of (how the
durable record is read into memory), but it matches how the view already
worked, so nothing needs to change before merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

Clean across the board. One feature concern, seven files, 140 lines added.
New behaviour ships with its own tests (a server-side reader test, a route
test for both the new path and the fallback, and a hook test). No database
migrations, no schema changes, no infrastructure files, no secrets.

---

## Technical detail

> Internal taxonomy below for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the changes; Build Verification empty;
all changed files read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — tsc + eslint clean on HEAD.
- **PR Hygiene:** 0 findings (CR-09 / PH-01..04 all clean).
- **In the changes:** 1 finding (0 critical, 0 high, 0 medium, 1 low).
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0 (the one low finding is a Watch List note — no failing test to ground a delta, CR-04).

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none — store read is a pure lib, no infra import into domain; dependency direction respected |
| Security | 0 | 0 | none — traversal guard mirrors store's validate_store_id; read-only; redaction already applied on write |
| Quality | 1 (low) | 0 | whole-file read vs the streaming sibling (Watch List) |

### Build Verification (CR-01)

None. `npx tsc --noEmit -p server` rc=0; `npx eslint <changed>` rc=0 (tool-outputs/).

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):        commit_type_spread: {feat}; module_fan_out: 1 (apps/cockpit) → clean
Size (PH-02):         +140 / -4; files: 7 → clean (well under bands)
Safety (PH-03):       migrations: 0; schema/idl: 0; infra: 0; secrets: 0 → clean
Completeness (PH-04): new_source_without_test: 0 (readThreadStore.ts ↔ readThreadStore.test.ts) → clean
```

### Findings in the Changes

#### Architecture lens — nothing surfaced
Checks run: domain↔infrastructure import direction (readThreadStore is a pure
`server/lib` reader, imports only `node:fs/promises`, `node:path`, and the
shared wire type — no reach into infra/db beyond the filesystem seam it owns,
matching the existing locateTranscripts/parseTranscripts libs); no new
singletons; no new circular imports; new external read has graceful ENOENT/error
degrade to `[]` (no unhandled rejection); ADR-002 local-binding seam honoured
(reads the on-disk contract the Python store writes, no cross-language coupling).

#### Security lens — nothing surfaced
Primitives checked: SEC-01 (path traversal) — `SAFE_ID` regex `^[A-Za-z0-9_-]+$`
mirrors the store's `validate_store_id` (thread_contract.py); a traversing
changeId returns `[]` rather than escaping the threads dir (asserted by test
"refuses a change id that is not a safe path component"). SEC (secrets exposure)
— redaction runs on WRITE in the Python store; the reader surfaces already-
scrubbed bytes; no new secret surface. DAT — read-only (the cockpit read-only
gate scanned 259 files clean). No injection/SSRF/auth surface in a local
filesystem read. No new dependencies (SC-01..04 N/A).

#### Quality lens

1. **Build Verification follow-up:** none (CR-01 empty).
2. **JSX / template identifier scan:** N/A — the one TSX-adjacent file
   (useTranscript.test.ts) uses `React.createElement`, no JSX template
   identifiers introduced.
3. **Dead-surface:** none. `StoredThreadMessage` fields used in projection;
   `sulisStateDir` consumed in route + app.ts wiring.
4. **Contract-drift:** none. Projection emits the `TranscriptMessage` union
   (user | assistant) field-for-field; `participant_type` maps to kind; the
   wire shape matches what the existing renderers consume.
5. **Test-coverage observation:** strong. readThreadStore.test.ts (6 cases:
   projection, ordering, empty, malformed-skip, traversal-refusal, both
   participant kinds); routes.transcript.test.ts adds store-first + fallback
   cases; useTranscript.test.ts (3 cases) proves the hook renders the served
   shape. Full suite 1613/1613 green.
6. **Style/readability:** clear names, small focused functions, header
   comments document the strangle + removal plan. No issues.
7. **Performance procedural checks (CR-10):** one low note (see Watch List).
   No N+1 (single file read per request), no O(N^2), no loop-invariant
   recomputation, no synchronous waterfall.

### Findings in the Neighbours

None. Direct neighbours: transcript.ts (modified, in-diff), app.ts mount
(modified, in-diff), parseTranscripts/locateTranscripts (callees, unchanged,
still the fallback). No pre-existing gap exposed.

### Watch List

- **`server/lib/readThreadStore.ts` — whole-file read (low / awareness).**
  The reader does `readFile(...)` then `split("\n")`, materialising the whole
  durable log in memory, whereas the sibling `parseTranscripts` streams via
  `readline` for multi-MB Claude transcripts. Context (CR-03): the route this
  replaces ALSO accumulated all `TranscriptMessage` objects in memory
  (parseTranscripts returns the full array), so the response was already
  O(messages); the durable log is one change's redacted message history, far
  smaller than a raw provider transcript. The memory profile matches the
  existing route, so this is not a regression. If the durable log grows
  unbounded in a future change, switch to a streaming read + the contract's
  `since`/`limit` slice (already on the store's `get_messages` read op). No
  failing characterisation test grounds a delta now (CR-04) → Watch List, not
  a delta.

### Cross-Reference

- Existing Hardening Deltas covered: none.
- Existing security report: none for this change.
- Pattern suggesting full audit: none.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `npx tsc --noEmit -p server` (rc=0), `npx eslint <changed>` (rc=0). HEAD clean; base was clean (full suite green pre-change). Coverage gap: none. Outputs in tool-outputs/.
- [✓] **CR-02 Single-reader pass justified by diff size:** 140 lines, 7 files (4 modified + 3 new), under the 200-line / 5-source-file carve-out.
- [✓] **CR-03 Full-file reads.** All changed files read end-to-end (readThreadStore.ts 138 lines, transcript.ts 62 lines, the two test files, app.ts mount block, README row). Unread: none.
- [✓] **CR-04 Evidence discipline.** Findings cite file + quoted behaviour; the one note explains why no delta.
- [✓] **CR-05 Severity rubric.** Applied: 0 critical, 0 high, 0 medium, 1 low.
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade triggers fired (Build Verification empty; all files read; all lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (checks listed). Security: nothing surfaced (primitives listed). Quality: all 7 outputs produced (1 low finding).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope clean; PH-02 Size clean; PH-03 Safety clean (0 migrations/schemas/secrets/infra); PH-04 Completeness clean (new source has tests). No PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** `git diff change/create-portable-agent-context` (working tree; uncommitted, pre-Step-7).
- **Neighbour expansion:** git grep — transcript.ts callers (app.ts), callees (parseTranscripts/locateTranscripts/readThreadStore).
- **Neighbour cap:** not reached (well under 20).
- **Scanners run:** tsc, eslint, cockpit read-only gate (259 files clean).
- **Lenses dispatched in parallel:** no — single-reader pass (CR-02 carve-out).
