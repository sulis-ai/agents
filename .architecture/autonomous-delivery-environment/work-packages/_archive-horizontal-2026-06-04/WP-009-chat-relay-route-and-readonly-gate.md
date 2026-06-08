---
id: WP-009
title: "POST /api/changes/:id/chat (SSE relay) + read-only-gate extension"
kind: backend
source: feature
change_id: 01KT500K2JTE2EGW6TPPQ4D4VN
parent_phase: chat

atomic_branch: yes
estimate: 8h
blast_radius: high        # the app's first write path; extends the load-bearing read-only gate
primitive: EXPAND-Create
group: expand
acceptance_criteria:
  - "POST /api/changes/:id/chat runs the load-bearing order (TDD §3.1): acquire lock → resolveSession → bind → act → stream SSE → release"
  - "Second send mid-stream ⇒ 409 SESSION_BUSY (FR-20); binding fail ⇒ 422 SESSION_CHANGE_MISMATCH, zero bytes, no process touched (FR-21); resume/spawn cannot start ⇒ 502 SESSION_UNREACHABLE, message NOT marked delivered (FR-19, FR-N3)"
  - "SSE response sets Content-Type text/event-stream, no-cache, keep-alive, unbuffered; emits state→chunk*→complete (ADR-001); mid-stream drop ⇒ partial preserved + interrupted (FR-22, NFR-REL-02)"
  - "Relay logs ONE structured line per send {changeId, resolution, outcome, code?} — never the message body or reply text (NFR-SEC-03)"
  - "check-read-only.sh + read-only-inventory.test.ts EXTENDED: relay route file is the only app.post exception; bridge adapter file is the only process-start exception; a NEW rule flags process-start anywhere else; loading any read surface starts no process (ADR-003, FR-N1, NFR-SEC-05, NFR-ARCH-02)"
  - "Bridge startup timeout + idle-stream watchdog close a stalled bridge so the lock cannot leak (TDD §3.2)"
test_plan:
  unit: []
  integration:
    - "apps/cockpit/server/tests/routes.chat.test.ts (NEW) — supertest with RecordedSessionBridge: SESSION_BUSY, SESSION_CHANGE_MISMATCH(zero bytes), SESSION_UNREACHABLE(not delivered), state→chunk→complete, mid-stream drop→interrupted+partial"
    - "apps/cockpit/server/tests/read-only-inventory.test.ts (EXTEND) — exactly one module starts a process; reads start none"
    - "apps/cockpit/server/tests/check-read-only-script.test.ts (EXTEND) — the new process-start rule + the allow-listed relay/bridge"
  verification:
    - "bash apps/cockpit/scripts/check-read-only.sh exits 0"
    - "branch-ci green"
verification_gates: [unit, integration, smoke]
verification:
  adapter: backend
  artifact: "apps/cockpit/server/tests/routes.chat.test.ts"
  # the binding/lock/failure logic is concrete against the recorded fixture now;
  # the LIVE resume/spawn path is deferred (WP-016, recording-bridge-claude-session).

derived_from:
  - finding: "ADR-001 SSE; ADR-003 single sanctioned write path + gate extension; TDD §3.1/§3.2/§3.4/§3.5; FR-16..23, FR-N1/N3, NFR-SEC-03/05, NFR-REL-02/03"
    found_in: .architecture/autonomous-delivery-environment/adrs/ADR-003-chat-is-the-single-sanctioned-write-path.md
    severity_at_discovery: n/a
generated_by:
  activity: plan-work-run/2026-06-03T08:34:19Z
  agent: sulis:engineering-architect
addresses_findings: []
invalidated_by: { activity: null, result: null }

status: pending
depends_on: [WP-001, WP-006, WP-007, WP-008]

child_wps: []
kinds: null

# NFR-SEC constraints carried on the sensitive write/act path:
security_constraints:
  - "Act only on the targeted change's session; binding (WP-008) runs before any process start (NFR-SEC-06)"
  - "Every other surface stays provably read-only; gate fails on any new mutation elsewhere (FR-N1)"
  - "No message body / reply text in logs (NFR-SEC-03)"

rollback: |
  New relay route + SSE plumbing + gate-rule additions + tests. Remove the
  app.use mount, revert the gate-script + inventory-test edits, revert the
  commit. The gate returns to forbidding ALL mutations (its prior, stricter
  state) — safe by construction.

verifies_scenario: "dna:scenario:YY4RJ7JS8KT55BS61BD0ER3ZNF"   # Talk to the agent about a change
---

# POST /api/changes/:id/chat (SSE relay) + read-only-gate extension

## Why

The app's **first write/act path** (ADR-003) and where all the Armor
concentrates. Two things become "writes" the current gate forbids: an HTTP
mutation verb, and a **process start** (resume/spawn launches a `claude`
session). This WP adds the relay and narrows the gate to allow-list *exactly*
this one seam — keeping the app provably read-only everywhere else, which is why
a non-technical founder can trust it.

## What changes

- `apps/cockpit/server/routes/chat.ts` (NEW, EXPAND-Create) — the one `router.post`; runs lock → resolve → bind → act → stream → release (TDD §3.1); SSE headers + unbuffered write; maps bridge events → `ChatStreamEvent`; maps the three failure codes to 409/422/502.
- `apps/cockpit/server/app.ts` (MODIFY) — mount the relay router; allow OPTIONS+POST CORS for this one route.
- `apps/cockpit/scripts/check-read-only.sh` (MODIFY) — (a) relay file in the `app.post` exception set, (b) bridge adapter file in a NEW process-start exception set, (c) a NEW rule flagging process-start elsewhere.
- `apps/cockpit/server/tests/read-only-inventory.test.ts` + `check-read-only-script.test.ts` (MODIFY) — assert exactly-one-process-start; reads start none.

The relay accepts the `SessionBridge` as an injected dependency (the prod adapter
from WP-010 in production; the recorded fixture from WP-007 in tests).

## How

Compose the WP-008 lock + binding and the WP-006 port. SSE per ADR-001. The
startup timeout parallels the existing 5s git timeout; the idle watchdog closes a
stalled bridge so the lock releases. Logging reuses the existing `request-log`
no-bodies discipline (NFR-SEC-03).

## Tests

`routes.chat.test.ts` drives the relay against `RecordedSessionBridge` (WP-007):
the three error codes (incl. zero-bytes on mismatch, not-delivered on
unreachable), the happy `state→chunk→complete`, and a mid-stream drop ⇒ partial
preserved + interrupted. The gate tests assert the allow-list is exactly the
relay + bridge and the new process-start rule fires elsewhere.

`verification:` — the binding/lock/failure logic is **concrete** against the
fixture now; the **live** resume/spawn end-to-end is **deferred** to WP-016
(manual, `recording-bridge-claude-session`).

## Rollback

Remove the mount + relay file; revert the gate-script and inventory-test edits.
The gate reverts to its stricter all-mutations-forbidden state — safe.
