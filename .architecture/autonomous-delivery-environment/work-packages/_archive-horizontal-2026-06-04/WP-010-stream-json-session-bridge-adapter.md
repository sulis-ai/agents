---
id: WP-010
title: "StreamJsonSessionBridge — production adapter over headless claude stream-json"
kind: backend
source: feature
change_id: 01KT500K2JTE2EGW6TPPQ4D4VN
parent_phase: chat

atomic_branch: yes
estimate: 8h
blast_radius: medium      # the one process-start site; gated by the read-only allow-list
primitive: EXPAND-Create
group: expand
acceptance_criteria:
  - "adapters/StreamJsonSessionBridge.ts implements SessionBridge by driving `claude -p --output-format stream-json --include-partial-messages` (resume via --resume/--continue or Agent SDK); the interactive-TUI/pty path is NOT used (ADR-002)"
  - "It satisfies the WP-006 contract suite (parity with RecordedSessionBridge)"
  - "Resume restarts the change's most recent session from its persisted transcript; spawn seeds a fresh session with the change's saved context (CONTEXT.md / manifest / stage / decisions) — FR-24/25"
  - "It does NOT synthesise completion: a step incomplete at prior close is handed to the agent to re-run (FR-26/FR-N5)"
  - "Process start lives in THIS file only — the read-only gate's process-start allow-list names it (ADR-003); resolveSession remains side-effect-free (FR-N4)"
  - "Bridge startup timeout enforced; failure surfaces as the relay's SESSION_UNREACHABLE (TDD §3.2)"
test_plan:
  unit: []
  integration:
    - "apps/cockpit/server/tests/session-bridge.streamjson.test.ts (NEW) — runContract(WP-006) against the adapter using a stubbed stream-json child (CI), real claude path verified manually (WP-016)"
  verification:
    - "branch-ci green"
verification_gates: [unit, integration, smoke]
verification:
  adapter: backend
  deferred-to-follow-on: recording-bridge-claude-session
  # the live process path cannot fully bootstrap in CI; the contract is proven
  # via the recorded fixture (WP-007) + manual founder-machine run (WP-016).

derived_from:
  - finding: "ADR-002 StreamJsonSessionBridge (EXPAND-Create, headless stream-json); TDD §2.2; FR-24/25/26"
    found_in: .architecture/autonomous-delivery-environment/adrs/ADR-002-session-bridge-port-resume-spawn.md
    severity_at_discovery: n/a
generated_by:
  activity: plan-work-run/2026-06-03T08:34:19Z
  agent: sulis:engineering-architect
addresses_findings: []
invalidated_by: { activity: null, result: null }

status: pending
depends_on: [WP-006]      # implements the port; parallel to WP-007/008/009 once the port exists

child_wps: []
kinds: null

infrastructure_needs:
  - id: recording-bridge-claude-session
    why: "contract parity is proven against the recorded fixture in CI; the live process is verified manually"

rollback: |
  New adapter + one test. Production wiring (index.ts) selects this adapter;
  revert that selection + the file. The relay falls back to no bridge (chat
  unavailable) without affecting read surfaces. Revert the commit.
---

# StreamJsonSessionBridge — production adapter over headless claude stream-json

## Why

The production `SessionBridge`. ADR-002's validated mechanism is the **headless
stream-json bridge** (`claude -p … --output-format stream-json
--include-partial-messages`), with multi-turn via `--resume`/`--continue` or the
Agent SDK. The interactive-TUI/pty path is explicitly rejected — it is where the
earlier attempt churned. This is **EXPAND-Create**: the public face is our
`SessionBridge` port; the CLI is *called by* this adapter.

## What changes

- `apps/cockpit/server/adapters/StreamJsonSessionBridge.ts` (NEW, EXPAND-Create):
  - `resolveSession` — reuses `probeLiveness` + `locateTranscripts` to classify live / resumable / fresh; **no side effects**.
  - `relay` — **resume** (restart from persisted transcript), **spawn** (seed with saved context), or use-live; maps stream-json events → `ChatStreamEvent` (`stream_event` deltas → `chunk`, lifecycle → `state`, `result/success` → `complete`).
- `apps/cockpit/server/index.ts` (MODIFY) — construct + inject this adapter into `createApp` for production.

The process start is confined to this file (the gate's process-start allow-list,
WP-009). It never synthesises a completion: on a mid-step transcript it hands the
restored state to the agent and lets it re-run (FR-26/FR-N5).

## How

Spawn the headless `claude` child; stream-parse its stdout. Startup bounded by a
timeout (failure → the relay's SESSION_UNREACHABLE). Builds in parallel with
WP-007/008/009 once the port (WP-006) exists — it only `dependsOn` WP-006.

## Tests

`session-bridge.streamjson.test.ts` runs the WP-006 contract suite against the
adapter with a stubbed stream-json child process in CI (deterministic). The real
`claude` resume/spawn path is **deferred** — verified manually on the founder
machine in WP-016 against `recording-bridge-claude-session`.

## Rollback

Revert the index.ts selection + the adapter file. Chat degrades to unavailable;
read surfaces unaffected.
