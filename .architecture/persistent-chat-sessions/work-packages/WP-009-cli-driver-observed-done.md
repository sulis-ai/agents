---
id: WP-009
title: Minimal real CLI driver (open→send→read --follow→close) — observed-done gate
kind: backend
primitive: EXPAND-Create
group: expand
status: ready
dependsOn: [WP-004]
estimated_token_cost: { input: ~12k, output: ~10k }
verification:
  adapter: backend
  artifact: "manual: plugins/sulis/scripts/tests/manual/session_driver_observed.md"
---

## Context

The phase brief's observability requirement: Phase 1 must deliver an
**observable, usable thing**, not just unit-green. Per the repo's testable-state
"observed done" gate — a user-facing outcome is done only when **observed
working**, not merely merged. This WP is that gate: a minimal but real CLI that
drives a warm session end-to-end against the **real `claude` CLI**
(`claude` is on PATH, v2.1.165 confirmed).

This is NOT the full Sulis plugin CLI feature set — just enough of a driver to
exercise and prove the core. The full CLI is out of Phase-1 scope.

Module: `plugins/sulis/scripts/sulis_session.py` (mirrors the existing
`sulis_list_changes.py` entrypoint convention).

## Contract

A tiny argparse CLI exposing the six methods against a live `SessionManager`
with the Claude adapter registered:

```
sulis_session.py open  --key K --cwd DIR [--resume-ref REF]   # prints {pid, provider, resumed, state}
sulis_session.py send  --key K --message "..."                # prints the landing offset
sulis_session.py read  --key K [--since N] [--follow]         # streams events to stdout (chunk text live; result; error)
sulis_session.py status                                        # prints the session table
sulis_session.py health --key K                               # prints {alive,state,pid,provider}
sulis_session.py close --key K
```

Because the manager is in-process and the CLI is multiple invocations, Phase 1's
driver runs the **whole flow in one process** for the observable demo (a
`demo`/`chat` subcommand, or a documented single-process script): open → send →
`read --follow` (live-streaming the reply as `claude` writes it) → second send
(proving warm reuse: fast, remembers) → close. Single-process is correct for
Phase 1 — cross-process is the Phase-2 socket server. Note this clearly so it
isn't mistaken for a limitation of the design.

The driver proves the four founder-visible wins (contract Part 1) with real
`claude`: live streaming reply, memory across turns, fast second turn, clean close.

## Definition of Done

### Red (failing first)
- A scripted integration test `tests/integration/test_session_cli_smoke.py` that
  runs the single-process `demo` flow against a **fake fast adapter** (recorded
  child) so CI has a deterministic, claude-free smoke of the CLI wiring:
  `test_cli_demo_streams_open_send_read_close` — asserts stdout shows the
  open result, a landing offset, streamed chunk text, a result, and a clean close.
- (The fake-adapter smoke guards the CLI plumbing in CI; the real-claude run is
  the human/observed gate below.)

### Green
- Implement `sulis_session.py` with argparse, the in-process `SessionManager` +
  Claude adapter, and the single-process `demo` flow. Stream chunks to stdout as
  they arrive (flush per chunk — the whole point is *live*). Boring argparse, no
  framework.

### Blue (refactor + OBSERVED-DONE evidence)
- **Run it against real `claude`** in the worktree and capture the observation:
  `python plugins/sulis/scripts/sulis_session.py demo --key demo1 --cwd <worktree> --message "say hi in 3 words"`
  and watch the reply **stream live**, then a second message proving warm reuse +
  memory. Record the observation (terminal capture / notes) in
  `tests/manual/session_driver_observed.md` — this file IS the phase-exit evidence.
- The observed run must show: (1) reply streaming token-by-token, not a dump;
  (2) the second turn answering with memory of the first; (3) the second turn
  starting fast (no fresh cold-load). Those three are the Phase-1 "it works"
  proof.

## Notes
- This WP is the gate the whole phase is measured against: WP-001..008 can all be
  green and the phase is still NOT done until this driver has been *observed*
  streaming a real `claude` turn end-to-end.
- Keep the surface minimal — resist adding cockpit/socket concerns (Phase 2).
- The destructive-path caution from the verify discipline: `demo` spawns a real
  `claude` with `--dangerously-skip-permissions` in the given cwd; run it against
  a safe message / the worktree, and document that the observed run used a benign
  prompt.
