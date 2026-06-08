# Observed-done evidence — session driver end-to-end vs real `claude`

> **WP-009** · change `persistent-chat-sessions` (CH-01KTAD) · Phase 1
> **This file IS the phase-exit evidence.** The phase is not done when the unit
> tests are green — it is done when a human (or CI driving the real binary) has
> watched `open → send → read --follow → close` stream a live turn end-to-end
> against the real `claude` CLI. This is that observation.

---

## What was run

```
$ unset SULIS_SESSION_CLAUDE_ARGV          # real claude, NOT the test stub
$ python plugins/sulis/scripts/sulis_session.py demo \
    --key observed2 \
    --cwd /Users/iain/.sulis/changes/01KTAD9GEHD5NANDWSP0M86GJZ/wp-009-worktree \
    --message "say hi in 3 words"
```

- **Date observed:** 2026-06-05T16:34Z
- **`claude` version:** 2.1.165 (Claude Code), resolved on `PATH`
- **Wall clock (whole demo, two turns):** ~10.0s real
- **Prompt:** `"say hi in 3 words"` — a benign, side-effect-free message. The
  demo spawns a real `claude` with `--dangerously-skip-permissions` in the
  given `--cwd`, so the prompt and directory are kept deliberately safe
  (destructive-path caution, per the WP).

## What was observed (verbatim terminal capture)

```
open: {"key": "observed2", "pid": 52567, "provider": "claude", "resumed": false, "state": "ready"}
send: {"offset": 0, "turn": 1}
read (turn 1, follow): Hi there friend!
result: {"duration_ms": 3304, "input_tokens": 9074, "output_tokens": 9, "stop_reason": "end_turn"}
turn1_seconds: 6.435
send: {"offset": 3, "turn": 2}
read (turn 2, follow): You said: "say hi in 3 words"
result: {"duration_ms": 2503, "input_tokens": 319, "output_tokens": 15, "stop_reason": "end_turn"}
turn2_seconds: 2.516
status: [{"key": "observed2", "log_len": 6, "memory_bytes": 242761728, "pid": 52567, "provider": "claude", "state": "ready"}]
health: {"alive": true, "pid": 52567, "provider": "claude", "state": "ready"}
close: {"key": "observed2"}
```

## The three Phase-1 "it works" proofs

| Proof | Evidence in the capture |
|---|---|
| **1. The reply streams live, token-by-token (not a dump).** | `read (turn 1, follow): Hi there friend!` was written to the terminal as `claude` produced each `content_block_delta` chunk — each chunk flushed the moment it arrived (the CLI flushes per chunk), then the turn-terminal `result` line. The reply appeared progressively, not as one blob after a silence. |
| **2. The second turn answers with memory of the first.** | Turn 2 sent `"what did I just say?"` (the demo's fixed second message). The reply — `You said: "say hi in 3 words"` — quotes the first turn's prompt back. The warm session carried the conversation; nothing was thrown away between turns. |
| **3. The second turn starts fast (no fresh cold-load).** | Turn 1 paid the one-time warm-up: `input_tokens: 9074`, `duration_ms: 3304`, `turn1_seconds: 6.435`. Turn 2 reused the warm process: `input_tokens` fell to **319**, `duration_ms` to **2503**, `turn2_seconds` to **2.516** — roughly 2.5× faster and a 28× smaller input-token load. Both turns ran on the **same pid 52567** (see the `status`/`health` lines), proving the warm process was reused, not respawned. |

Clean close at the end (`close: {"key": "observed2"}`) released the process and
log — no orphaned `claude` left behind.

> **Single-process is correct for Phase 1, not a limitation.** The manager is
> in-process and the demo runs the whole flow in one process so the warm session
> survives across the two turns. Cross-process serving (the Unix-domain-socket
> NDJSON server the cockpit consumes) is Phase 2 — the same `SessionManager`
> instance, wrapped by a socket server. See the contract §2.8 and the INDEX
> "Phase 2 — deferred" section.

## A real defect this gate caught (and fixed)

The first real-`claude` run of this demo **failed** — the child process died
mid-turn before emitting any text:

```
read (turn 1, follow):
error: {"category": "protocol", "code": "STDIN_BROKEN", "message": "session process died mid-turn; restarting"}
```

Reproduced directly against the binary:

```
$ printf '{"type":"user","message":{"role":"user","content":"say hi in 3 words"}}\n' \
  | claude -p --input-format stream-json --output-format stream-json \
           --include-partial-messages --dangerously-skip-permissions
Error: When using --print, --output-format=stream-json requires --verbose
```

**Root cause:** the Claude adapter's spawn argv
(`_session_manager/adapters/claude.py` `_BASE_ARGV`) omitted `--verbose`, which
`claude` v2.1.165 **mandates** with `-p` + `--output-format=stream-json`. The
child exited 1 before producing a line, surfaced by the manager as
`STDIN_BROKEN`. The recorded-fixture unit tests could not see this — they decode
captured stream-json and never spawn the real binary. **This is exactly the
class of bug the observed-done gate exists to catch.**

**Fix:** added `--verbose` to `_BASE_ARGV` (one token), pinned it with a
regression assertion in
`tests/unit/test_claude_adapter.py::test_spawn_argv_streaming_flags`, and
registered the finding (`SF-896624ac`) so future provider adapters learn to
validate their spawn argv against the live CLI, not only recorded fixtures.
The capture above is the re-run **after** the fix.

## Reproducing this yourself

```
# Real claude (the observed-done gate):
unset SULIS_SESSION_CLAUDE_ARGV
python plugins/sulis/scripts/sulis_session.py demo \
  --key demo1 --cwd "$(pwd)" --message "say hi in 3 words"

# CI / claude-free smoke (deterministic, no model, runs in ~0.5s):
pytest plugins/sulis/scripts/tests/integration/test_session_cli_smoke.py
pytest plugins/sulis/scripts/tests/unit/test_session_cli.py
```

The CI smoke injects a deterministic scripted child via
`SULIS_SESSION_CLAUDE_ARGV` that speaks the same real `claude` stream-json wire,
so the CLI's plumbing — and the real `ClaudeAdapter.decode` path — is proven
without depending on (or paying for) the real model.
