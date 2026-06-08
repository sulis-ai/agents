# Design brief — persistent chat sessions (CH-01KTAD)

> Carried over from the session that triggered this change. This is the
> root-cause analysis + the agreed architecture + the exact integration map,
> so this change starts from the design, not from scratch.

## Context — why this change exists

Driving a change from the cockpit's **web chat** feels like a "blackbox": you
send a message, ~40–60s of silence, and you have to refresh to see the reply.
Founder's words: *"as Claude starts thinking and then responding, I don't see
that automatically… it loses which process it's working with and goes into a
blackbox of not responding."*

Root cause (investigated in code): the chat bridge is **stateless — it spawns a
brand-new `claude` process for every message** and throws it away. That single
choice causes four compounding faults:

| # | Fault | Evidence | Symptom |
|---|---|---|---|
| RC-1 | `live` sessions spawn fresh with **no `--resume`** (`buildArgv` only resumes `resumable`) → every message is a new, context-less conversation | `lib/resolveSession.ts` (`running`→`live`) + `adapters/StreamJsonSessionBridge.ts` `buildArgv` | "loses which process it's working with" |
| RC-2 | Spawn-per-message + **full project cold-load** (~40–60s, measured) before the first token | bridge spawns per message in the worktree cwd; no `--bare`/`--strict-mcp-config` | the ~60s silence |
| RC-3 | **60s startup watchdog races the ~60s cold-load** → a slow-but-healthy spawn is killed → "unreachable" | `config.ts` `chatBridgeStartupTimeoutMs=60_000` + `consume()` kills on no-chunk-by-deadline | "blackbox of not responding" |
| RC-4 | **No heartbeat** — one leading `state` event, then nothing until the first chunk | `relay()` emits `leadingStateFor` then waits | the blackbox *feeling* |
| RC-5 | One-in-flight lock blocks a second message | `lib/inFlightLock.ts` | "can't post while waiting" |

The deep cause beneath RC-1..RC-4: **no warm, persistent session per change.**

## The fix — a persistent, server-owned Claude session per change

The CLI already supports the needed primitive (confirmed via `claude --help`):

```
claude -p --input-format stream-json --output-format stream-json \
  --include-partial-messages --dangerously-skip-permissions
```

`--input-format stream-json` is **realtime streaming input** — keep ONE process
alive and feed it many user messages over stdin (NDJSON), reading streamed
responses over stdout. **Cold-load is paid once on spawn; every message after is
fast.** This is the same "own + monitor a long-lived process" pattern as the
reference impl at `/Users/iain/Documents/repos/ae/ae_task_executor`
(`claude_session.py` = session object with state machine + timeouts +
resource-monitoring; `monitored_claude_session.py` = output capture + error
detection + recovery; `terminal_pool.py` = warm pool + idle-eviction).

**Why this is safe / feasible:** we own the spawn (the cockpit server starts the
process), so we hold the handle — unlike the founder's interactive terminal TUI,
which we do **not** drive (pty-hijack is the explicitly-rejected path). The
cockpit owns its *own* warm session per change (same conversation, resumed from
the change's transcript on first spawn).

### Architecture: a `PersistentSessionManager` (new), keyed by changeId

- **On first message for a change:** spawn one persistent process in the change
  worktree (`buildArgv` + `--input-format stream-json`); on first spawn, resume
  from the transcript (`lastSessionRef`) for continuity. Hold
  `{ stdin, stdout, pid, state, lastActivity }` in a `Map<changeId, session>`.
- **Each send:** write a user-message JSON to stdin → route streamed stdout to
  the SSE `RelaySink`. No respawn, no per-message cold start.
- **Lifecycle:** health-check (process alive); **restart-on-death** + resume
  from transcript; **idle-eviction** after inactivity (memory: each warm process
  is real RAM — cap concurrent warm sessions + evict LRU); **write the PID to
  `session.json`** so `probeLiveness` + the Advanced view reflect it.
- **PID surfaced:** the Advanced view shows the exact owned process — "which
  process it's working with" stops being a mystery.

How it kills the root causes: continuity (one process holds the thread) → RC-1;
cold-load once → RC-2/RC-3; warm = instant, heartbeat only on the one-time spawn
→ RC-4; PID owned + shown → tracking. RC-5 stays one-in-flight *per process* but
messages are fast — a client-side **queue** covers it.

## Integration map (confirmed by reading the code)

**Reuse as-is:**
- `ports/SessionBridge.ts` (102–124) — the `SessionBridge` interface
  (`resolveSession`, `relay`, `SessionResolution`, `RelaySink`, `RelayOutcome`).
  The persistent manager implements the **same port** — the chat route is
  unchanged.
- `lib/streamJsonToEvents.ts` (38–89) — `parseStreamJsonLine`,
  `streamJsonToEvent`, `leadingStateFor`, `resumedFor`. Reused by the persistent
  reader.
- `adapters/StreamJsonSessionBridge.ts` `buildArgv` (201–231) — argv shape
  (already carries `--dangerously-skip-permissions`); add `--input-format
  stream-json`.
- `lib/sessionBinding.ts` `checkSessionBinding` (40–65) — fail-closed binding
  guard, unchanged (still runs pre-relay so a process can't attach to the wrong
  change).
- `lib/probeLiveness.ts` + `lib/resolveSession.ts` — liveness + transcript
  resolution; the manager updates `session.json` with the spawned PID.
- `tests/session-bridge.contract.test.ts` — `runSessionBridgeContract(name,
  factory)` 4-case suite; the new manager runs the **same contract** (inject a
  stubbed child + process map).

**Changes:**
- `index.ts` (63–96) — swap the `StreamJsonSessionBridge` construction for the
  `PersistentSessionManager` (same port; `spawnBridge` becomes "spawn or attach").
- `adapters/StreamJsonSessionBridge.ts` `consume()` (104–182) — the reader must
  delimit **per-message** boundaries (`result/success` ends a message) instead of
  process-exit; don't close the process on `complete`; multiplex one process's
  stdout across sequential `relay()` calls.
- `lib/inFlightLock.ts` — stays as the per-change write-safety lock (one message
  at a time per process); separate from process lifetime.
- **New:** the `PersistentSessionManager` (process map + lifecycle) — no such
  registry exists today (current architecture is fully stateless per message).

## Cheap mitigations (optional — ship first for a usable web chat *today*)

If we want relief before the full refactor lands, these are low-risk and
independently valuable (some overlap with the redesign already in flight on the
ADE change):
1. **RC-1:** make `live` resolution also `--resume` the transcript (continuity).
2. **RC-3:** raise the watchdog to ~150s and base "alive" on the process
   running, not just first-chunk.
3. **RC-4:** emit a "still starting… {N}s" heartbeat while waiting for the first
   token.
4. **RC-5:** client-side queue instead of blocking.

(Note: the ADE change also has pending web-chat UX fixes — in-thread message,
status footer with PID + alpha notice, queue. Decide whether those ride here or
stay on ADE.)

## Verification

- **Contract suite** green for the new manager (`runSessionBridgeContract`).
- **Unit:** message-boundary parsing (two messages over one process → two
  complete events); restart-on-death; idle-eviction; PID written to
  `session.json`.
- **Observed (the real done):** drive the web chat for a change — first message
  pays the warm-up once; **subsequent messages reply in ~1–3s** with no refresh;
  the Advanced view shows the one stable owned PID; killing that PID and sending
  again triggers a clean restart. (Per the testable-state gate: a user-facing
  outcome is done only when observed green, not merged.)

## Reference

- `/Users/iain/Documents/repos/ae/ae_task_executor/claude_session.py`,
  `monitored_claude_session.py`, `terminal_pool.py`, `terminal_launcher.py` —
  the long-lived-process management pattern.
- `claude --help` → `--input-format stream-json` (realtime streaming input).
