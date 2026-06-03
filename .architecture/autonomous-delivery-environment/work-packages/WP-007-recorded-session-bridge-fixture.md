---
id: WP-007
title: "RecordedSessionBridge fixture adapter (live/resume/spawn/mid-step)"
kind: backend
source: feature
change_id: 01KT500K2JTE2EGW6TPPQ4D4VN
parent_phase: chat

atomic_branch: yes
estimate: 6h
blast_radius: low
primitive: EXPAND-Create
group: expand
acceptance_criteria:
  - "adapters/RecordedSessionBridge.ts replays a recorded stream-json session from a fixture; it satisfies the SessionBridge contract suite (WP-006) — parity with the prod adapter (MEA-09: recorded real stream, replayed, NOT a mock)"
  - "The recording-bridge-claude-session fixture covers ALL FOUR cases: live, resume-from-transcript, spawn-grounded-in-context, AND a mid-step transcript (FR-24/25/26/FR-N5)"
  - "On the mid-step fixture, relay surfaces the resumed-and-re-running behaviour (complete.resumed=true; the incomplete step is re-run, never reported done — FR-N5)"
  - "Replaying the fixture starts no real claude process (CI-safe)"
test_plan:
  unit: []
  integration:
    - "apps/cockpit/server/tests/session-bridge.recorded.test.ts (NEW) — runs runContract(WP-006) against RecordedSessionBridge over all four fixture cases"
  verification:
    - "branch-ci green"
verification_gates: [unit, integration, smoke]
verification:
  adapter: backend
  deferred-to-follow-on: recording-bridge-claude-session

derived_from:
  - finding: "TDD §4.2 recorded-bridge fixture; ADR-002 consequences; SRD deferred need recording-bridge-claude-session"
    found_in: .architecture/autonomous-delivery-environment/TDD.md
    severity_at_discovery: n/a
generated_by:
  activity: plan-work-run/2026-06-03T08:34:19Z
  agent: sulis:engineering-architect
addresses_findings: []
invalidated_by: { activity: null, result: null }

status: pending
depends_on: [WP-006]

child_wps: []
kinds: null

infrastructure_needs:
  - id: recording-bridge-claude-session
    why: "recorded/replayable stream-json session covering live + resume-from-transcript + spawn-grounded-in-context + mid-step, so the relay + resolution + guards are CI-testable without a live agent"

rollback: |
  New test adapter + fixture data + one test. Remove them; revert. No prod path
  touched.
---

# RecordedSessionBridge fixture adapter (live/resume/spawn/mid-step)

## Why

The chat relay + session resolution + binding/lock guards must be testable in CI
**without a live `claude`** (TDD §4.2, MEA-09). The answer is a *recorded real*
stream-json session, replayed — not a mock. This adapter + its fixture are what
let WP-008 (binding/lock) and WP-009 (relay route) run their behavioural API
tests in CI. The real live path is verified manually on the founder machine
(WP-016).

## What changes

- `apps/cockpit/server/adapters/RecordedSessionBridge.ts` (NEW, EXPAND-Create) — a `SessionBridge` whose `resolveSession`/`relay` replay a recorded fixture rather than driving a process.
- Fixture data for `recording-bridge-claude-session` (deferred need) under the test fixtures tree, covering the four cases.
- `apps/cockpit/server/tests/session-bridge.recorded.test.ts` (NEW) — `runContract("recorded", recordedFactory)` plus the FR-N5 mid-step assertion.

## How

Build the fixture by recording a real headless stream-json session (per ADR-002 /
the SRD spike), then trimming to the four canonical resolutions. The adapter is
deterministic over the fixture so CI is stable.

`verification:` is **deferred** — the artifact ships against the recorded fixture
now; the full live path is the follow-on (`recording-bridge-claude-session` →
manual on founder machine, WP-016).

## Tests

`session-bridge.recorded.test.ts` — the WP-006 contract suite over all four
fixture cases; plus the explicit FR-N5 check: a mid-step transcript ⇒
`complete.resumed=true`, incomplete step re-run, never reported done.

## Rollback

Remove adapter + fixture + test; revert.
