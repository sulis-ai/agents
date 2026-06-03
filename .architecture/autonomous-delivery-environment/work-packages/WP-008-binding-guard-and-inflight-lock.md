---
id: WP-008
title: "Session-to-change binding guard + one-in-flight lock (pure libs)"
kind: backend
source: feature
change_id: 01KT500K2JTE2EGW6TPPQ4D4VN
parent_phase: chat

atomic_branch: yes
estimate: 4h
blast_radius: medium      # the load-bearing safety of the whole change
primitive: EXPAND-Create
group: expand
acceptance_criteria:
  - "lib/sessionBinding.ts is a pure function (requestedChangeRecord, resolvedSessionRecord) → bound | mismatch; proves change_id-equality AND cwd/worktreePath-equality before any delivery (ADR-004, FR-21, NFR-SEC-02)"
  - "Fail-closed: cannot positively confirm BOTH ⇒ mismatch (SESSION_CHANGE_MISMATCH); zero bytes implied, no process touched"
  - "The guard returns the same verdict for live / resumed / spawned session records (NFR-SEC-02 across all three)"
  - "lib/inFlightLock.ts is a per-change in-memory lock: acquire returns false if held; release frees it; second acquire mid-hold ⇒ SESSION_BUSY semantics (FR-20, NFR-REL-03)"
test_plan:
  unit:
    - "apps/cockpit/server/tests/sessionBinding.test.ts (NEW) — A-request→B-session ⇒ mismatch; A→A ⇒ bound; resumed + spawned records both checked; cwd-mismatch ⇒ mismatch"
    - "apps/cockpit/server/tests/inFlightLock.test.ts (NEW) — acquire/held/release; double-acquire ⇒ busy; release after complete frees"
  integration: []
  verification:
    - "branch-ci green"
verification_gates: [unit, integration, smoke]
verification:
  adapter: backend
  artifact: "apps/cockpit/server/tests/sessionBinding.test.ts"

derived_from:
  - finding: "ADR-004 positive binding guard; ADR-001 one-in-flight lock; FR-20/21, FR-N2, NFR-SEC-02/06, NFR-REL-03"
    found_in: .architecture/autonomous-delivery-environment/adrs/ADR-004-session-to-change-binding-guard.md
    severity_at_discovery: n/a
generated_by:
  activity: plan-work-run/2026-06-03T08:34:19Z
  agent: sulis:engineering-architect
addresses_findings: []
invalidated_by: { activity: null, result: null }

status: pending
depends_on: [WP-006]      # binding operates over the SessionBridge SessionRef/record shapes

child_wps: []
kinds: null

rollback: |
  Two new pure lib files + their unit tests. Nothing calls them until WP-009.
  Remove and revert.
---

# Session-to-change binding guard + one-in-flight lock (pure libs)

## Why

The single most dangerous failure for a multi-change cockpit is delivering a
message to the **wrong change's** agent (ADR-004). The guard makes binding a
positive, fail-closed precondition that runs **before** any process start or
prompt delivery — identical for live / resumed / spawned sessions (NFR-SEC-02,
NFR-SEC-06, FR-N2). The one-in-flight lock (ADR-001) prevents interleaving a
second message into the same change while a reply streams (FR-20, NFR-REL-03)
and doubles as a resource bulkhead.

These are split out as **pure libs** so they are unit-testable without a live
agent and so the relay route (WP-009) composes them in the load-bearing order:
**lock → resolve → bind → act → stream → release** (TDD §3.1).

## What changes

- `apps/cockpit/server/lib/sessionBinding.ts` (NEW, EXPAND-Create) — pure: proves `resolved.change_id === requested.changeId` AND `resolved.cwd === requested.worktreePath` (the same cwd-equality failsafe `locateTranscripts` uses). Either unconfirmed ⇒ mismatch.
- `apps/cockpit/server/lib/inFlightLock.ts` (NEW, EXPAND-Create) — per-change in-memory lock; `acquire(changeId): boolean`, `release(changeId)`.

## How

Both pure / in-process. The binding guard takes already-read records (no I/O) so
it is trivially testable. The lock is a `Map<changeId, true>` with acquire/release;
released on complete/break/fail by the relay (WP-009).

## Tests

- `sessionBinding.test.ts` — NFR-SEC-02 acceptance verbatim (A-request → B-session ⇒ mismatch, zero bytes); A→A ⇒ bound; checks resumed AND spawned session records; cwd-mismatch alone ⇒ mismatch.
- `inFlightLock.test.ts` — acquire when free ⇒ true; while held ⇒ false (busy); release ⇒ re-acquirable.

## Rollback

Remove both libs + tests; revert.
