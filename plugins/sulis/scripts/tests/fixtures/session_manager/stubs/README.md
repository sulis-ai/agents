# §2.10 contract-stub fixture set

These are the recorded-NDJSON stubs for the seven `SESSION_MANAGER_CONTRACT.md`
§2.10 scenarios (CF-04 / CF-09). They feed the contract-conformance harness at
`tests/integration/test_session_manager_contract.py` (WP-008), which drives the
**real** `SessionManager` through its public six-method surface and asserts the
observable event sequence / error for each scenario.

This is the single suite that proves the whole capability holds against the
contract, and the **shared asset** Phase-2's cockpit socket-client points
`runSessionBridgeContract` at (§2.8.3) — the same fixtures, two consumers.

## Recorded reality, not hand-mocked JSON (MEA-09)

Each scenario directory holds one or more `turn-<N>.jsonl` files — the recorded
`claude` stream-json a scripted replay child emits onto its stdout for the Nth
submitted turn. The lines reuse the **verbatim shape** of the real CLI capture
in `../claude/happy.jsonl` (recorded from `claude` v2.1.165), so the **real**
`ClaudeAdapter.decode()` maps them exactly as it maps live CLI output. The
mapping rules are proven against reality, not against a stub that can drift.

- `happy_turn/` and `resumed_turn/` reuse the verbatim `happy.jsonl` recording.
- The multi-chunk / two-turn / die-mid blocks reuse the recorded line *shapes*
  (`content_block_start` → `content_block_delta`* → `content_block_stop` →
  `result`), differing only in the streamed text — shape is the reality the
  decode contract depends on.

## The scenarios

| Directory | §2.10 | Turn blocks | What it proves |
|---|---|---|---|
| `happy_turn/` | #1 | `turn-1` | `open(resumed:false)` → `send` → `chunk*` → `result`. |
| `resumed_turn/` | #2 | `turn-1` | `open(resumed:true)` then a turn — honest `resumed` (§2.7). |
| `reconnect_mid_turn/` | #3 | `turn-1` (multi-chunk) | A reader drops mid-turn; a reconnect from its last offset gets the tail then live — nothing lost (§2.5). |
| `two_viewers/` | #4 | `turn-1` (multi-chunk) | Two readers, different `since`, one turn — per-reader cursors, no interference (§2.5). |
| `queued_send/` | #5 | `turn-1`, `turn-2` | A second send while one is in flight runs after the first `result` (§2.6). |
| `death_and_restart/` | #6 | `turn-1` (die-mid), `turn-2` | Process dies mid-turn → restart-on-death → `error` event then continuation (§2.7). |
| (no dir) | #7 | — | Error cases driven at the manager surface: `NO_SESSION` (never opened), `OFFSET_EVICTED` (forced retention cap), `SPAWN_FAILED` (real Popen failure on a bad argv). |

## The die-sentinel (the only non-`claude` line)

A turn block whose final non-blank line is `{"__die__": "<mode>"}` makes the
replay child exit instead of finishing the turn — `before` (no output) or `mid`
(one chunk, then exit, no `result`). This reproduces the §2.10 #6 mid-turn death
against a **real** process the manager must detect and restart. It is the only
line the child interprets; every other line is replayed verbatim.

## Turn counter persists across a restart

The replay child persists its turn counter in a per-session sidecar file, so a
restarted child (after a `die=mid`) resumes at the **next** recorded block, not
the one that just died — exactly how a resumed `claude` behaves (§2.7: a restart
resumes from transcript, it does not re-execute the prior turn).

## Adding a scenario

A new scenario is **data, not code**: add a directory with `turn-<N>.jsonl`
blocks and a parametrised row / test in the harness — the
`_running_manager` + `_collect` plumbing is shared, so each test stays the
scenario, not the setup.
