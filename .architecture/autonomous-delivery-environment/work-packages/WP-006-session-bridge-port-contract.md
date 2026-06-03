---
id: WP-006
title: "SessionBridge port + contract test (resolve + relay seam)"
kind: backend
source: feature
change_id: 01KT500K2JTE2EGW6TPPQ4D4VN
parent_phase: chat

atomic_branch: yes
estimate: 5h
blast_radius: medium      # the chat path's keystone; relay + adapters + fixture all bind to it
primitive: EXPAND-Create
group: expand
acceptance_criteria:
  - "ports/SessionBridge.ts defines resolveSession(changeId) → SessionResolution ({kind: live|resumable|fresh}) and relay(changeId, prompt, sink) → RelayOutcome (ADR-002)"
  - "session-bridge.contract.test.ts defines the behaviour suite every adapter satisfies: resolve returns live/resumable/fresh correctly; relay emits state→chunk*→complete; resolveSession is side-effect-free (starts no process — FR-N4)"
  - "The contract suite is import-and-run (runContract pattern, like change-store-reader.contract.test.ts) so the prod adapter (WP-010) and recorded fixture (WP-007) both satisfy it — parity discipline (MEA)"
  - "Port + contract introduce no process start themselves; read-only gate green"
test_plan:
  unit: []
  integration:
    - "apps/cockpit/server/tests/session-bridge.contract.test.ts (NEW) — the reusable runContract suite (no adapter wired yet; self-suite asserts it exports runContract)"
  verification:
    - "branch-ci green"
verification_gates: [unit, integration, smoke]
verification:
  adapter: backend
  artifact: "apps/cockpit/server/tests/session-bridge.contract.test.ts"

derived_from:
  - finding: "ADR-002 SessionBridge port (EXPAND-Create); TDD §2.1/§2.2; FR-24/25"
    found_in: .architecture/autonomous-delivery-environment/adrs/ADR-002-session-bridge-port-resume-spawn.md
    severity_at_discovery: n/a
generated_by:
  activity: plan-work-run/2026-06-03T08:34:19Z
  agent: sulis:engineering-architect
addresses_findings: []
invalidated_by: { activity: null, result: null }

status: pending
depends_on: [WP-001]

child_wps: []
kinds: null

rollback: |
  New port interface + one contract-test file. Nothing implements it yet.
  Remove both; revert the commit.
---

# SessionBridge port + contract test (resolve + relay seam)

## Why

ADR-002: "it just works" (FR-24/25) is the founder never choosing resume vs
spawn. The server resolves a session and relays — through a domain-owned port,
the same way every other capability is reached (MEA-01). This is **EXPAND-Create**
(an adapter for a port *we* own), not a wrap of the `claude` CLI. This WP lands
the port + the contract suite first so the relay route (WP-009), the prod
adapter (WP-010), and the recorded fixture (WP-007) all build against a fixed
interface.

## What changes

- `apps/cockpit/server/ports/SessionBridge.ts` (NEW, EXPAND-Create):

```
type SessionResolution =
  | { kind: "live"; session: SessionRef }
  | { kind: "resumable"; lastSessionRef: SessionRef }
  | { kind: "fresh" };

interface SessionBridge {
  resolveSession(changeId: string): Promise<SessionResolution>;   // side-effect-free
  relay(changeId: string, prompt: string, sink: ChatStreamSink): Promise<RelayOutcome>;
}
```

`sink` receives `ChatStreamEvent`s (WP-001 shape). `resolveSession` reuses
`probeLiveness` (signal-0) + `locateTranscripts` — no new side effects on read.

- `apps/cockpit/server/tests/session-bridge.contract.test.ts` (NEW): `runContract(name, factory)` exporting the behaviour suite — mirrors `change-store-reader.contract.test.ts`. Asserts: resolveSession returns the right kind for live / prior-transcript / never-had-session worlds; relay emits `state → chunk* → complete`; resolveSession starts no process.

## How

Pure interface + reusable test suite. No adapter here (WP-007 fixture +
WP-010 prod adapter import `runContract`). The contract is the parity contract:
fixture and prod adapter must behave identically on the recorded inputs.

## Tests

`session-bridge.contract.test.ts` is itself the deliverable (a trivial
self-suite asserts it exports `runContract`, like the existing change-store
contract module). Substantive coverage runs through WP-007 + WP-010.

## Rollback

Remove the port + contract file; revert. Nothing depends on it yet at merge time
beyond WP-007/009/010 which are later.
