# ADR-001 — A provider-neutral session/process manager as a Python Sulis foundation capability

- **Status:** accepted
- **Date:** 2026-06-05
- **Change:** CH-01KTAD · persistent-chat-sessions
- **Deciders:** SEA (formalising the locked model from the change Working Set)
- **Related:** extends `external:autonomous-delivery-environment/ADR-002`
  (the cockpit's `SessionBridge` resume-or-spawn port), `external:autonomous-delivery-environment/ADR-001`
  (SSE one-way reply stream), `external:autonomous-delivery-environment/ADR-004`
  (session-to-change binding guard). Those ADRs stand; this ADR puts a
  provider-neutral, multi-consumer manager *underneath* the cockpit's port.

## Context

This change began as "make the cockpit's web chat persistent." The cockpit's
chat bridge is **stateless**: it spawns a fresh `claude` process per message
and throws it away. That single choice produces the founder-visible
"blackbox" — every message is a context-less conversation (no `--resume`),
each pays the ~40–60s project cold-load, the 60s startup watchdog races that
cold-load and kills healthy spawns, and there is no heartbeat between the
leading state event and the first token. The deep cause is the absence of a
**warm, persistent session per change**.

Through several critical-thinking spirals with the founder, the problem was
re-aimed. Two facts changed the shape of the solution:

1. **There is a confirmed second consumer.** The Sulis plugin CLI is
   **long-running / agentic and written in Python**. It needs warm agent
   sessions for the same reasons the cockpit does. This is not a hypothetical
   — it is a real in-process consumer of the same capability.
2. **There will be more than one agent CLI.** Today the only agent CLI is
   `claude`. Codex and Gemini are anticipated. A solution wired to `claude`'s
   stdout shape specifically would have to be rebuilt for each.

So the unit of work is not "a persistent chat bridge for the cockpit." It is
a **generic, provider-neutral session/process manager** — a Sulis foundation
capability — with the cockpit as one consumer and the Python plugin CLI as
another, and a thin per-agent adapter as the only agent-specific surface.

### What "session manager" must own

A `SessionManager` owns warm, long-lived agent processes, keyed by a
**caller-supplied key** (the cockpit uses the change id; the CLI uses its
own). Each session is an ordered, **offset-addressed event log**. Submitting
input and reading output are **decoupled**: you `send` a turn and get back
the log offset it landed at; you `read` from any offset, optionally following
live. That one decoupling is what lets a single mechanism serve live tailing,
reconnect catch-up with nothing lost, multiple concurrent viewers each with
their own cursor, and full history — without a bespoke path for each.

The manager owns internally (consumers never touch): the session state
machine; resume-from-transcript where the provider supports it;
restart-on-death; idle eviction; a memory cap with least-recently-used
eviction; one-in-flight per key (extra sends queue; different keys run in
parallel); the stdin/stdout/stderr pumps; and appending decoded events to the
per-session log.

The **only** agent-specific surface is a small provider adapter:
`spawn_argv`, `encode`, `decode`, `turn_complete`, `capabilities`. Adding
Codex or Gemini is writing one adapter — zero change to the manager or to
either consumer.

### Proven groundwork

The pattern is not novel here. A proven Python implementation exists at
`ae/ae_task_executor`:

- `terminal_pool.py` — `PooledClaude{process, stdin_queue, stdout_queue,
  stderr_queue, state}`; `acquire`/`release`/`perform_maintenance`/
  `get_instance`/`get_pool_status`/`shutdown`; `ClaudeState`
  (STARTING/READY/BUSY/IDLE/ERROR/DEAD); `stdin_writer`/`stdout_reader`/
  `stderr_reader` I/O threads; idle-eviction + dead-process detection in a
  maintenance loop.
- `claude_session.py` — `SessionState`
  (INITIALIZING/READY/EXECUTING/ERROR/TERMINATED/TERMINATED_TIMEOUT/
  TERMINATED_RUNAWAY/PERMANENTLY_DISABLED); `is_healthy`/`is_terminated`/
  `attempt_recovery`/`shutdown`; runaway monitoring; safety metrics.
- `monitored_claude_session.py` — output capture, API error-pattern
  detection, `start_task`/`stop_task`/`get_session_monitoring_data`,
  recovery.

This change **adapts the design, not lifts the code blindly** — the AE code
keys on a task pool, has no event log, no provider seam, and no tests. We
re-shape the proven state machine, recovery, eviction, dead-process
detection, and the warm-process-plus-queues pattern into our keyed,
event-log-per-session, provider-neutral form, and add the tests the AE repo
never had. The two files the founder originally named (`cli_command_runner.py`
= blocking one-shot `subprocess.run`; `cli_progress_tracker.py` = a
gutted/deprecated shim) are **not** the groundwork and the design does not
derive from them.

## Decision

**Build the session/process manager as a provider-neutral Python module in
the Sulis foundation** (`plugins/sulis/scripts/` or an appropriate module
there), exposing six consumer-facing operations
(`open`/`send`/`read`/`health`/`status`/`close`), a shared provider-neutral
event vocabulary (`chunk` / `tool_use` / `result` / `error`), and a single
per-agent adapter seam (`spawn_argv`/`encode`/`decode`/`turn_complete`/
`capabilities`). Claude is adapter #1; Codex and Gemini slot in as future
adapters with zero change to the manager or to either consumer.

Each session is an **ordered, offset-addressed, append-only event log**.
`send` submits a turn and returns the offset; `read(since, follow)` is the
single content-retrieval path that serves live tail, reconnect catch-up,
multi-viewer, and history. **One turn in flight per key**; cross-key turns
run in parallel.

**The Python plugin CLI consumes the manager in-process** (native import —
it is Python). **The Node cockpit consumes it over a local Unix-domain
socket** using newline-delimited JSON (NDJSON), LSP-style — language-neutral,
no network port, no TCP. The cockpit's existing `SessionBridge` port
(`apps/cockpit/server/ports/SessionBridge.ts`, from ADE ADR-002) becomes a
thin **Node client adapter** that speaks the socket protocol to the served
manager and relays the decoded events onto SSE. The port's contract is
unchanged; its production implementation changes from "spawn `claude`
directly" to "call the served manager."

The precise interface — signatures, semantics, event vocabulary, adapter
seam, log/cursor semantics, concurrency, resume-as-capability, the socket
serving protocol, and how `SessionBridge.ts` maps onto it — is specified in
the companion contract:
[`../contracts/SESSION_MANAGER_CONTRACT.md`](../contracts/SESSION_MANAGER_CONTRACT.md).

### Why Python, in the foundation (the decisive rationale)

The home and language were genuinely open until the second consumer was
confirmed. The decisive fact: **the Sulis plugin CLI is long-running and
Python, and is a real in-process consumer of warm sessions.** A Python core
in the foundation lets that CLI consume the manager natively, in-process,
with no transport tax. The cross-language cost is then paid by exactly one
consumer — the Node cockpit — and it is paid over a boring local socket. We
pay a cross-language tax only where there is a genuine cross-language
consumer to justify it; the in-language consumer pays nothing.

### Why these conventions (Convention Preference, CP-01..CP-05)

Every transport and storage choice is the boring, established one, not a
bespoke invention:

- **Warm subprocess with stdin/stdout streams** — the proven AE pattern and
  the standard way to drive a long-lived child process. `claude`'s
  `--input-format stream-json --output-format stream-json` is realtime
  streaming over stdin/stdout (confirmed via `claude --help`).
- **Unix-domain socket, NDJSON, LSP-style** — the established language-neutral
  local IPC convention. No network port, no TCP, no port-allocation or
  firewall surface. The Language Server Protocol is the canonical precedent
  for "two processes in different languages talk locally over framed JSON."
- **Offset-addressed append-only log with `since` + `follow`** — the
  Kafka-offset / `tail -f --since` convention. A monotonically increasing
  integer cursor per session; readers carry their own cursor; nothing is lost
  on reconnect because the offset is the resumption point. This is the
  established convention for "decouple producing from consuming an ordered
  stream," and it is what makes one `read` method serve four use cases.
- **Three-category error model (CONTRACT_FIRST CF-03)** — Protocol /
  Expected / Internal, mapped onto the socket transport (and onto exceptions
  for the in-process consumer). Errors are part of the contract, not
  free-form strings discovered at runtime.

## Alternatives considered

1. **Python core serving only the Node cockpit (rejected).** A Python core
   that exists solely to serve a Node consumer is a cross-language tax with no
   offsetting benefit — every call crosses a process and a language boundary
   for no in-language consumer. This was the right rejection *until* the
   Python plugin CLI was confirmed as a real consumer. The confirmed second
   consumer is exactly what flips this from "tax with no benefit" to "the
   correct home."

2. **Port the design to TypeScript and keep it in the cockpit (rejected).**
   Correct *only* under a single-Node-consumer assumption. The long-running
   Python CLI breaks that assumption: a TS core in the cockpit would force the
   Python CLI to consume over a socket (paying the cross-language tax) *and*
   would couple the foundation capability to the cockpit's lifecycle and
   deployment. The capability is foundational, not cockpit-specific, so it
   does not live inside one consumer.

3. **Lift-and-shift the AE code as-is (rejected).** The AE code is a task
   *pool* (acquire/release N interchangeable workers), not a keyed, warm,
   per-key session registry. It has no event log, no provider seam, no
   decoupled send/read, and no tests. Lifting it would import the wrong shape.
   We adapt the proven *mechanisms* (state machine, recovery, eviction,
   dead-process detection, warm-process-plus-queues) into the keyed
   event-log-per-session provider-neutral form, and add tests. (Note also:
   the two files the founder first named are not the groundwork — see Context.)

4. **PTY-hijack of the founder's interactive terminal (rejected).** Driving a
   `claude` running in the founder's own tty means pty-scraping a session we
   don't own — the path the earlier attempt churned on (ADE ADR-002 rejects
   it too). The manager owns its **own** headless processes; it observes
   external liveness (signal-0) but never drives a session it didn't spawn.

5. **WebSocket / TCP duplex bridge between cockpit and manager (rejected).**
   A network port where a local file socket suffices. NDJSON over a
   Unix-domain socket is the lower-surface, more boring convention — no port
   allocation, no localhost-binding security questions, no TCP. (Consistent
   with ADE ADR-001's one-way reply: the manager's reply stream is one-way;
   `send` and `read` are separate channels, not a duplex socket.)

6. **One process per message, kept for the cockpit only (rejected — it is the
   status quo being removed).** This is the current stateless bridge and the
   direct cause of the four compounding faults (no continuity, repeated
   cold-load, watchdog race, no heartbeat). The whole change exists to
   replace it.

## Consequences

- **New foundation module** in Python under `plugins/sulis/` implementing the
  manager, the event log, the state machine, the lifecycle (restart-on-death,
  idle-eviction, LRU memory cap), and the Claude adapter — with tests (unit +
  contract) the AE repo lacked.
- **New local serving layer**: a Unix-domain socket server speaking NDJSON
  per the contract, so the Node cockpit can consume the in-process manager
  cross-language.
- **The cockpit's `SessionBridge` port is unchanged** as an interface; its
  production adapter becomes a socket client (`resolveSession` → `health` +
  resolution; `relay` → `send` then `read(follow)` mapped onto the existing
  `RelaySink`). The existing `runSessionBridgeContract` suite, the
  `RecordedSessionBridge` fixture (MEA-09, not a mock), the binding guard
  (ADE ADR-004), and the in-flight lock all still apply at the port seam.
- **Adding a new agent CLI is one adapter file** — `spawn_argv`/`encode`/
  `decode`/`turn_complete`/`capabilities` — with zero change to the manager or
  either consumer. This is the EXPAND-Create move (we author an adapter for a
  seam *we* own), not a SUBSTITUTE-Wrap of any vendor CLI.
- **Resume is a capability, not an assumption.** The manager resumes from
  transcript only where `capabilities.supports_resume` is true; for providers
  that cannot resume, `open` starts fresh and says so. The contract makes this
  explicit so consumers never assume continuity that a provider can't give.
- **Scope and phasing remain open** (deliberately not decided here): whether
  the cockpit migration and the Python-CLI consumer land together or in
  sequence, and whether the local socket server ships in the first slice or
  the cockpit first consumes in-process via a shim, are decomposition
  questions for `/sulis:plan-work`, not architecture decisions. See the
  contract's Open Questions.
