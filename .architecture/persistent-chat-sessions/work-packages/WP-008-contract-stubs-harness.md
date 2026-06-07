---
id: WP-008
title: Contract-stub fixtures (§2.10) + Python contract-test harness
kind: backend
primitive: REINFORCE-Test
group: reinforce
status: ready
dependsOn: [WP-003]
estimated_token_cost: { input: ~14k, output: ~12k }
verification:
  adapter: backend
  artifact: "plugins/sulis/scripts/tests/integration/test_session_manager_contract.py"
---

## Context

Contract §2.10 (the required stub set) + CF-04/CF-09 (error+empty stubs, recorded
streaming stubs). This is the **Proof** pillar's cross-WP conformance gate: the
seven §2.10 scenarios encoded as recorded-NDJSON fixtures feeding the *real*
Python manager. It is the single suite that proves the contract holds across the
whole capability — and it is the suite Phase-2's cockpit socket-client will run
the equivalent of (`runSessionBridgeContract`).

REINFORCE-Test primitive: it adds verification over already-built behaviour. It
`dependsOn: WP-003` (needs the adapter + recorded fixtures) but its tests are
written *as each upstream WP lands* — the harness is built once, scenarios are
enabled as WP-004..007 make them pass.

Modules/paths:
- `tests/fixtures/session_manager/stubs/` — the recorded NDJSON sequences, one
  directory per §2.10 scenario.
- `tests/integration/test_session_manager_contract.py` — the harness.

## Contract — the seven §2.10 stubs (each a recorded NDJSON fixture + a test)

1. **happy turn** — `open(resumed:false)` → `send` → `chunk*` → `result`.
2. **resumed turn** — `open(resumed:true)` then a turn (proves §2.7 honesty).
3. **reconnect mid-turn** — `read(since=N, follow)` after a drop yields the tail
   then live (proves §2.5 nothing-lost).
4. **two viewers** — two `read`s with different `since` over one turn.
5. **queued send** — second `send` while one in flight runs after the first
   `result` (proves §2.6).
6. **death + restart** — process dies mid-turn → restart-on-death → `error` Event
   then continuation (proves §2.7).
7. **error cases** — `NO_SESSION`, `OFFSET_EVICTED`, `SPAWN_FAILED` (CF-04 error
   stubs, not happy-path only).

The fixtures are **recorded reality** (real `claude` stream-json captured once, or
a faithful scripted child replaying recorded lines) — never hand-authored mocks
that drift (MEA-09). The harness spawns the manager with a fixture-backed adapter
that replays the recorded sequence over a real child process.

## Definition of Done

### Red (failing tests first — one per scenario)
- `test_contract_happy_turn`
- `test_contract_resumed_turn`
- `test_contract_reconnect_mid_turn`
- `test_contract_two_viewers`
- `test_contract_queued_send`
- `test_contract_death_and_restart`
- `test_contract_error_no_session`
- `test_contract_error_offset_evicted`
- `test_contract_error_spawn_failed`

Each drives the real `SessionManager` (not a mock) through the public six-method
surface and asserts the observable Event sequence / error matches the scenario.

### Green
- Build the fixture-replay adapter (a `ProviderAdapter` whose `spawn_argv` starts a
  scripted child replaying a named recorded NDJSON file; `decode` is the real
  Claude decode from WP-003).
- Record/author the nine fixture files under `tests/fixtures/session_manager/stubs/`.
- Implement the harness as a parametrised pytest module so a new scenario = a new
  fixture dir + a row, not new harness code.

### Blue (refactor)
- Factor the "spawn manager + replay fixture + collect events" boilerplate into one
  helper so each scenario test is a few lines (the scenario, not the plumbing).
- Tag this suite so Phase 2 can point the cockpit socket-client's
  `runSessionBridgeContract` at the *same fixture set* (shared asset, §2.8.3).

## Notes
- Scenarios 5/6 depend on WP-004 (queue) and WP-005 (restart) being merged; write
  the fixture + test alongside those WPs landing. Scenarios 1/2/3/4/7 are
  available once WP-004 lands. The harness file itself depends only on WP-003.
- This suite is the contract's living proof — if a future adapter or refactor
  breaks the seam, these fail first.
