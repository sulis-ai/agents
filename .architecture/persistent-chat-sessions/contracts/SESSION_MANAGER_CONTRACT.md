# Session Manager — interface contract

> **Change:** CH-01KTAD · persistent-chat-sessions
> **Status:** draft (interface locked; scope/phasing open)
> **Decision record:** [`../adrs/ADR-001-provider-neutral-foundation-session-manager.md`](../adrs/ADR-001-provider-neutral-foundation-session-manager.md)
> **Tier (CONTRACT_FIRST):** Lightweight internal seam — one capability,
> two transports (in-process library + local socket), two languages.

---

## Part 1 — For the founder (plain language)

### What this is

Today, every time you send a message in the cockpit chat, the system starts a
brand-new assistant from scratch, waits while it loads your whole project
(about a minute), gets one reply, and then throws it away. The next message
starts over. That's why it feels like a blackbox: a long silence, no memory of
what you just said, and a refresh needed to see the answer.

This contract describes a new shared piece of Sulis — a **session manager** —
that fixes that by keeping a warm assistant running for each piece of work.
The first message pays the one-time warm-up; every message after that is fast,
and the assistant remembers the conversation.

It's built once and used in two places: the cockpit's web chat, and the Sulis
command-line tool. Because it's shared, it's built to work with any assistant —
Claude today, others later — without rebuilding the core.

### What it gives you

- **No more blackbox.** The reply streams back as it's written. You see the
  assistant thinking and answering live, without refreshing.
- **It remembers.** One warm assistant per piece of work holds the whole
  conversation. The second message doesn't forget the first.
- **Fast after the first message.** The slow warm-up happens once, not every
  time.
- **You can leave and come back.** If you close the tab and reopen it, you see
  everything you missed — nothing is lost.
- **More than one viewer.** Two people (or two browser tabs) can watch the same
  conversation at once, each at their own place in it.
- **It recovers.** If the assistant crashes, the manager restarts it and picks
  the conversation back up.

### What happens when you send a message — a walkthrough

1. **You open the chat for a piece of work.** The manager checks: is there
   already a warm assistant for this work? If yes, it uses it. If not, it
   starts one — and if this work has talked to an assistant before, the new one
   wakes up with the full memory of that conversation.

2. **You type a message and hit send.** The manager hands your message to the
   warm assistant and immediately tells the chat *where in the conversation
   your message landed* — like a bookmark. It does not wait for the reply to
   send you that bookmark.

3. **The reply streams back.** Separately, the chat is *reading* the
   conversation from your bookmark onward, following along live. As the
   assistant writes, each piece of text appears in your chat the moment it's
   produced. When the assistant finishes, a "done" marker arrives with the
   usage for that turn.

4. **You close the tab mid-reply, then reopen it.** The chat remembers your
   last bookmark. It re-reads the conversation from there — so you see the rest
   of the reply you missed, then catch up to live. Nothing is dropped.

5. **You send a second message before the first reply finished.** The manager
   only lets one turn run at a time for a given piece of work, so your second
   message waits in line and runs as soon as the first reply is done. (Two
   *different* pieces of work run at the same time — the queue is per-work, not
   global.)

The key idea, in one sentence: **sending a message and reading the reply are
two separate things.** That separation is what makes live streaming, coming
back after a disconnect, multiple viewers, and full history all work through
one simple mechanism instead of four special cases.

### What you do NOT need to decide

You never choose "resume or start fresh" — the manager decides. You never see
process IDs, sockets, or offsets — those are the engine. The chat just works.

---

## Part 2 — For engineers (precise)

### 2.0 — Shape of the contract

Per `CONTRACT_FIRST_STANDARD.md`, this contract is a **transport-agnostic
schema layer** with two interchangeable **bindings**:

| Axis | This contract |
|---|---|
| **Schema** (operations + types + errors) | The six consumer operations (§2.2), the event vocabulary (§2.3), the adapter seam (§2.4), the log/cursor semantics (§2.5), concurrency (§2.6), resume-as-capability (§2.7). |
| **Binding** (transport) | (a) **in-process library** — the Python plugin CLI imports and calls directly; (b) **subprocess + NDJSON over a Unix-domain socket** — the Node cockpit (§2.8). |

The same schema serves both bindings. The library binding has no
`ProtocolError`; the socket binding maps transport faults onto it (§2.9).

### 2.1 — Core model

A `SessionManager` owns warm, long-lived agent **processes**, one per
**caller-supplied key**. Each session holds an ordered, offset-addressed,
append-only **event log**. The caller chooses the key namespace:

- the cockpit uses the **change id**;
- the Python plugin CLI uses **its own key** (caller-defined).

The manager treats the key as an opaque string. **Submitting input and reading
output are decoupled operations** (§2.2 `send` vs `read`).

### 2.2 — Consumer-facing operations (the six-method surface)

Signatures are given in Python (the in-process binding is authoritative; the
socket binding §2.8 mirrors them). Types in §2.3–§2.7.

```python
def open(key: str, spec: SessionSpec) -> Session:
    """
    Get-or-spawn the warm session for `key`. Idempotent: calling open() on a
    key with a live session returns the existing Session, starting nothing.

    On first spawn for a key, if spec.resume_ref is set AND the provider's
    capabilities.supports_resume is true, the new process resumes prior
    context from that ref (§2.7). Otherwise it starts fresh.

    Errors: Protocol (spawn failed / argv invalid); Expected (unknown provider,
    cwd does not exist); Internal (unexpected spawn crash).
    """

def send(key: str, command: str) -> int:
    """
    SUBMIT a command/turn for `key`. Returns the log OFFSET at which the
    submitted turn's first event will be appended (a bookmark). Returns
    immediately — does NOT wait for the turn to complete or for any reply
    event.

    One turn in flight per key (§2.6): if a turn is already running for `key`,
    this turn is QUEUED and the returned offset is its eventual landing offset.

    Errors: Expected (no open session for key; session terminated/disabled);
    Protocol (stdin pipe broken — triggers restart-on-death, §2.7); Internal.
    """

def read(key: str, since: int = 0, follow: bool = False) -> Iterator[Event]:
    """
    GET CONTENT for `key`: yield every event in the log with offset >= `since`,
    in order. This single method serves all four content use cases:

      - live turn tail:      since = <offset from send()>, follow = True
      - reconnect catch-up:  since = <last offset the viewer saw>, follow = True
      - multiple viewers:    each viewer calls read() with its own `since`
      - full history:        since = 0, follow = False

    With follow = False: yields the events present now, then stops (history).
    With follow = True:  yields existing events from `since`, then continues
                         yielding new events live until the caller stops
                         iterating or the session closes.

    `since` is an offset, not a count. Offsets are stable and monotonic (§2.5),
    so a reconnecting reader loses nothing.

    Errors: Expected (no open session for key; since > current max offset is
    treated as "wait for it" under follow=True, Expected error under
    follow=False); Internal.
    """

def health(key: str) -> Health:
    """
    Liveness + identity for one session, side-effect-free.
    Returns { alive, state, pid, provider }. (§2.3 Health)
    Errors: Expected (no session for key).
    """

def status() -> list[SessionStatus]:
    """
    Snapshot of ALL sessions the manager owns:
    [{ key, state, pid, provider, memory_bytes, last_activity, log_len }].
    Side-effect-free. (§2.3 SessionStatus)
    """

def close(key: str) -> None:
    """
    Terminate the session for `key` and release its process + log.
    Idempotent: closing an already-closed/unknown key is a no-op.
    Errors: Internal only (best-effort terminate; SIGTERM then SIGKILL).
    """
```

**Decoupling invariant (the load-bearing design property).** `send` returns an
offset and never blocks on the reply; `read` is the only way to obtain content.
A consumer that wants request/response convenience composes them
(`off = send(k, c); for ev in read(k, since=off, follow=True): ...`). The
manager never bundles them — bundling is what makes live-tail, catch-up,
multi-viewer, and history four special cases instead of one.

### 2.3 — Shared, provider-neutral event vocabulary (the log's record types)

Every event appended to a session log is one of four types. Each provider
adapter's `decode()` (§2.4) maps that provider's native stdout into these — the
manager and both consumers only ever see these four.

```python
@dataclass(frozen=True)
class Event:
    offset: int          # this event's position in the session log (§2.5)
    key: str             # the session key it belongs to
    turn: int            # which submitted turn produced it (monotonic per key)
    kind: Literal["chunk", "tool_use", "result", "error"]
    # ── payload, by kind ──────────────────────────────────────────────
    text: str | None         = None   # kind=chunk: assistant text fragment
    tool: ToolUse | None     = None   # kind=tool_use: name + input summary
    result: TurnResult | None = None  # kind=result: turn done + usage
    error: EventError | None = None   # kind=error: typed failure (§2.9)
```

| `kind` | Meaning | Payload |
|---|---|---|
| `chunk` | A fragment of assistant text, streamed. | `text` |
| `tool_use` | The agent invoked a tool. | `tool` (name, redacted input summary) |
| `result` | The current turn finished. **Turn-terminal** (§2.6). | `result` (usage: input/output tokens, duration, stop reason) |
| `error` | A typed failure within the turn or session. | `error` (category + code + message, §2.9) |

This vocabulary maps **onto the cockpit's existing `ChatStreamEvent`** with no
new founder-facing types (§2.8.3):

| Session-manager `Event.kind` | cockpit `ChatStreamEvent` |
|---|---|
| `chunk` | `{ type: "chunk", text }` |
| `result` | `{ type: "complete", resumed }` (+ leading/terminal `state`) |
| `error` | `{ type: "error", code, message }` |
| `tool_use` | (cockpit currently elides; available for a future tool-trace UI) |

### 2.4 — Provider adapter seam (the only agent-specific surface)

One adapter per agent CLI. The manager depends on this interface; it never
touches a vendor SDK directly. This is **EXPAND-Create** (an adapter for a seam
*we* own), not a wrap of the vendor CLI.

```python
class ProviderAdapter(Protocol):

    capabilities: Capabilities
    # Capabilities(supports_resume: bool, supports_tools: bool,
    #              supports_partial_streaming: bool)

    def spawn_argv(self, spec: SessionSpec) -> list[str]:
        """How to start this CLI in streaming mode, in spec.cwd.
        Claude: ['claude', '-p', '--input-format', 'stream-json',
                 '--output-format', 'stream-json',
                 '--include-partial-messages',
                 '--dangerously-skip-permissions', ...resume flags...]."""

    def encode(self, command: str) -> bytes:
        """Frame one submitted turn for this CLI's stdin.
        Claude: one NDJSON stream-json user-message line + newline."""

    def decode(self, line: bytes) -> Event | None:
        """Parse ONE line of this CLI's stdout into a shared Event, or None
        for lines that carry no founder-facing event (bookkeeping/init).
        Claude: stream_event(content_block_delta) → chunk;
                result/success → result; result/error|is_error → error."""

    def turn_complete(self, event: Event) -> bool:
        """This agent's 'turn done' signal — the manager uses it to release
        the one-in-flight slot (§2.6) and run the next queued send.
        Claude: event.kind == 'result' from a stream-json result/success."""
```

**Claude is adapter #1.** Codex and Gemini are future adapters that MUST slot
in with **zero change** to the manager or to either consumer — the seam is the
contract that guarantees that.

> **Note on reuse.** The cockpit already has the Claude stream-json → event
> mapping in `apps/cockpit/server/lib/streamJsonToEvents.ts`. The Python
> Claude adapter's `decode()` reimplements the *same mapping rules* on the
> Python side (the manager is Python; that TS file stays as the cockpit's
> client-side concern). The rules — not the code — are the shared asset; they
> are stated in §2.3's mapping table so both sides stay aligned.

### 2.5 — Log / cursor semantics (offsets, since, follow, history)

- The session log is **append-only**. Each appended `Event` gets a
  **monotonically increasing integer `offset`**, starting at 0, unique and
  stable for the life of the session. (Kafka-offset / `tail -f --since`
  convention, CP-01.)
- `send(key, command)` returns the offset **at which the submitted turn's first
  event will land** — a forward reference. (If the turn is queued behind
  another, this is still its eventual landing offset; readers following from it
  block until it materialises.)
- `read(key, since, follow)`:
  - **history** — `follow=False`: yields events `offset >= since` present now,
    then stops.
  - **live tail** — `since = <send offset>, follow=True`: yields the turn's
    events as they arrive.
  - **reconnect catch-up** — `since = <last offset seen>, follow=True`: yields
    everything after the last-seen offset, then live. **Nothing is lost**
    because the offset is the resumption point.
  - **multiple viewers** — each reader holds its own `since`; the log is shared,
    cursors are per-reader. Readers never interfere.
  - **full replay** — `since = 0`.
- **Retention:** the log is bounded per session (configurable cap; default is a
  decomposition concern, see Open Questions). A reader whose `since` predates
  the oldest retained offset receives an `Expected` error
  (`OFFSET_EVICTED`) so it can restart from the oldest available offset rather
  than silently skipping.

### 2.6 — Concurrency (one-in-flight per key)

- **At most one turn runs at a time per key.** A `send` while a turn is in
  flight is **queued**; queued turns run FIFO as the in-flight slot frees.
- A turn's slot is released when the adapter's `turn_complete(event)` returns
  true for an event in that turn (Claude: the `result/success`).
- **Different keys run in parallel** — the one-in-flight rule is per-key, not
  global. The cockpit's per-change write-safety lock (ADE ADR-004 neighbours)
  composes with this: it is a *per-change* lock and aligns with one-in-flight
  per change-keyed session.
- `read` is never blocked by `send` — any number of concurrent readers may
  follow a session while a turn runs.

### 2.7 — Resume-as-capability, and the internal state machine

**Resume is a provider capability, never an assumption.** On first spawn,
`open` resumes from `spec.resume_ref` **only if**
`adapter.capabilities.supports_resume` is true. For a provider that cannot
resume, `open` starts fresh and the returned `Session.resumed` is `false` — the
consumer is told honestly (mirrors the cockpit's FR-26 / `resumed` honesty;
never synthesise continuity a provider can't give).

**The manager owns the session state machine** (consumers never touch it),
adapted from the proven AE `SessionState` / `ClaudeState`:

```
INITIALIZING ──▶ READY ──▶ EXECUTING ──▶ READY        (normal turn cycle)
                   │           │
                   │           ├──▶ ERROR ──▶ (attempt_recovery) ──▶ READY
                   │           │                     │
                   │           │                     └──▶ TERMINATED_*
                   │           └──▶ TERMINATED_TIMEOUT  (turn exceeded budget)
                   │           └──▶ TERMINATED_RUNAWAY  (runaway tool-call guard)
                   └──▶ DEAD ──▶ (restart-on-death + resume) ──▶ INITIALIZING
                                                    │
                                                    └──▶ PERMANENTLY_DISABLED
                                                         (recovery exhausted)
```

Manager-owned lifecycle, all internal:

- **restart-on-death** — process exits unexpectedly → manager restarts it and,
  where capability allows, resumes from transcript; the log continues (the
  restart is not a new key).
- **idle-eviction** — a session idle past a configurable timeout is closed and
  its process released (AE `perform_maintenance` loop).
- **memory cap with LRU eviction** — total warm sessions are capped by a
  configurable memory limit; over the cap, the least-recently-used session is
  evicted first.
- **dead-process detection** — `health` reflects `process.poll()`-style
  liveness (AE `is_healthy`).
- **runaway / timeout guards** — a turn exceeding its budget →
  `TERMINATED_TIMEOUT`; runaway tool-call behaviour → `TERMINATED_RUNAWAY` (AE
  safety metrics), surfaced as an `error` event then a terminal state.

### 2.8 — Cross-process serving (the cockpit binding)

#### 2.8.1 — Transport

The Node cockpit consumes the Python manager over a **Unix-domain socket**
carrying **newline-delimited JSON (NDJSON)**, LSP-style. No TCP, no network
port. (CP-01: the established language-neutral local-IPC convention; lower
surface than a localhost TCP port.) The Python plugin CLI does **not** use the
socket — it imports the manager in-process.

#### 2.8.2 — Wire protocol

Each line is one JSON object. Requests carry an `id`; responses echo it. The
six operations map to request methods; `read(follow=True)` is a **streaming
response** — many `event` lines for one request `id`, terminated by an `end`
line.

```jsonc
// request:  open
{"id":"1","method":"open","params":{"key":"chg_01KTAD","spec":{"provider":"claude","cwd":"/…/worktree","resume_ref":"…"}}}
// response: open
{"id":"1","ok":true,"result":{"key":"chg_01KTAD","pid":48213,"provider":"claude","resumed":true,"state":"ready"}}

// request:  send
{"id":"2","method":"send","params":{"key":"chg_01KTAD","command":"…user message…"}}
// response: send  (the offset/bookmark — returned immediately)
{"id":"2","ok":true,"result":{"offset":42}}

// request:  read (follow live from the send offset)
{"id":"3","method":"read","params":{"key":"chg_01KTAD","since":42,"follow":true}}
// streamed responses for id=3:
{"id":"3","ok":true,"event":{"offset":42,"turn":7,"kind":"chunk","text":"Look"}}
{"id":"3","ok":true,"event":{"offset":43,"turn":7,"kind":"chunk","text":"ing…"}}
{"id":"3","ok":true,"event":{"offset":44,"turn":7,"kind":"result","result":{"input_tokens":1200,"output_tokens":85,"stop_reason":"end_turn"}}}
{"id":"3","ok":true,"end":true}          // stream terminator for this read

// error response (any method) — three-category, §2.9
{"id":"2","ok":false,"error":{"category":"expected","code":"NO_SESSION","message":"no open session for key"}}
```

Framing is newline-delimited; a partial line is buffered until its newline.
This is the same NDJSON discipline the cockpit already uses for stream-json.

#### 2.8.3 — How `SessionBridge.ts` maps onto this contract

The cockpit's existing port (ADE ADR-002) is **unchanged as an interface**. Its
production adapter changes from "spawn `claude` directly" to "a socket client
of the served manager." The mapping:

| `SessionBridge` (cockpit port) | Session-manager operation(s) |
|---|---|
| `resolveSession(changeId)` → `SessionResolution` | `health(changeId)` (+ the manager/consumer's transcript knowledge). `alive` → `{kind:"live"}`; not alive but a transcript exists → `{kind:"resumable"}`; none → `{kind:"fresh"}`. Side-effect-free, matches FR-N4. |
| `relay(changeId, prompt, sink)` → `RelayOutcome` | `open(changeId, spec)` (idempotent get-or-spawn; `spec.resume_ref` from the resolution) → `off = send(changeId, prompt)` → `for ev in read(changeId, since=off, follow=true): sink.emit(map(ev))`. |
| `RelaySink.emit(ChatStreamEvent)` | The socket client maps each `Event` per §2.3's table and emits onto the existing sink → SSE. Leading/terminal `state` events come from the resolution + the `result` event, exactly as `leadingStateFor`/`resumedFor` already compute them. |
| `RelayOutcome` | `result` event → `{kind:"completed", resumed}`; stream drop mid-turn → `{kind:"interrupted"}`; `open` Protocol error → `{kind:"unreachable", detail}`; binding-guard failure (ADE ADR-004, runs *before* the bridge) → `{kind:"mismatch", detail}`. |

Existing cockpit assets that **stay**:

- `lib/streamJsonToEvents.ts` mapping rules (now mirrored Python-side in the
  adapter; the TS stays for the client adapter's own mapping if it consumes raw
  events, or is bypassed since the manager already decodes).
- `lib/sessionBinding.ts` binding guard (ADE ADR-004) — runs at the route,
  before `relay`, unchanged.
- `lib/inFlightLock.ts` — the per-change write lock; composes with the
  manager's one-in-flight-per-key (both per-change).
- `tests/session-bridge.contract.test.ts` `runSessionBridgeContract(name,
  factory)` — the new socket-client adapter runs the **same contract suite**
  (its factory points at a manager fixture / recorded socket session); the
  `RecordedSessionBridge` fixture (MEA-09, real recorded stream, not a mock)
  still satisfies it.

### 2.9 — Errors (three categories, CONTRACT_FIRST CF-03)

Every operation declares failure modes mapped to the three transport-agnostic
categories. The library binding raises typed exceptions; the socket binding
returns `{"ok":false,"error":{category,code,message}}`; `error` *events* in the
log carry the same shape.

| Category | Meaning here | Example codes | Consumer recovery |
|---|---|---|---|
| **Protocol** | Transport/process failed before the op ran. | `SPAWN_FAILED`, `STDIN_BROKEN`, `SOCKET_CLOSED` | Retry-with-backoff (manager auto-restarts on death); else escalate. |
| **Expected** | The op ran and deterministically declined. | `NO_SESSION`, `UNKNOWN_PROVIDER`, `CWD_NOT_FOUND`, `OFFSET_EVICTED`, `SESSION_DISABLED` | Adjust inputs / restart from a valid offset / re-open; retrying unchanged repeats it. |
| **Internal** | Unexpected crash (a bug). | `DECODE_FAILED`, `LOG_CORRUPT` | Log + escalate; don't retry. |

These map cleanly to the cockpit's existing `ChatErrorCode` set and to the
`RelayOutcome` discriminants (§2.8.3).

### 2.10 — Stubs (CF-04: include error + empty cases)

Recorded NDJSON event sequences are the streaming stubs (CF-09). The fixture
set MUST include, at minimum:

1. **happy turn** — `open(resumed:false)` → `send`→ `chunk*` → `result`.
2. **resumed turn** — `open(resumed:true)` then a turn (proves §2.7 honesty).
3. **reconnect mid-turn** — `read(since=N, follow)` after a drop yields the
   tail then live (proves §2.5 nothing-lost).
4. **two viewers** — two `read`s with different `since` over one turn.
5. **queued send** — second `send` while one is in flight runs after the first
   `result` (proves §2.6).
6. **death + restart** — process dies mid-turn → restart-on-death → `error`
   event then continuation (proves §2.7).
7. **error cases** — `NO_SESSION`, `OFFSET_EVICTED`, `SPAWN_FAILED` responses
   (CF-04 error stubs, not happy-path only).

These feed both the Python manager's contract tests and the cockpit
socket-client's `runSessionBridgeContract` run.

---

## Part 3 — Open architecture questions (genuine forks — not silently decided)

These are real decisions deferred to decomposition / the founder, not gaps in
the interface above. The interface is stable regardless of how they resolve.

1. **Phasing of the two consumers.** Does the cockpit migration and the
   Python-CLI in-process consumer land in one slice or in sequence? And does
   the local socket server ship in the first slice, or does the cockpit first
   consume via a temporary in-process shim while the socket lands later? This
   is a `/sulis:plan-work` decomposition question; the contract holds either
   way. *(Scope/phasing explicitly open per the change brief.)*

2. **Log retention default.** §2.5 makes retention bounded and configurable
   and defines `OFFSET_EVICTED`, but the **default** cap (events per session /
   bytes) is a tuning decision with a founder-visible consequence (how far back
   "see what I missed" reaches). Recommend a generous default (full
   single-session history; sessions are short-lived) and surface only if the
   founder cares about long-running sessions. **Recommended: take the boring
   default (retain the whole live session), revisit only if memory pressure
   shows up.**

3. **Memory-cap default (max concurrent warm sessions).** §2.7 caps warm
   sessions by memory with LRU eviction; the **limit** depends on the host
   (founder laptop vs CI vs future cloud). Recommend deriving from available
   RAM with a conservative floor; this is an operational tuning value, not an
   interface change. *(No founder-facing consequence until eviction is
   observed — decided-by-default, revisit on signal.)*

4. **Socket location + lifecycle.** Path of the Unix-domain socket, who starts
   the manager process (cockpit-launched vs separately supervised), and
   cleanup of a stale socket on crash. Conventional answer: a well-known path
   under the project's runtime dir, manager auto-started by its first consumer,
   stale-socket reclaim on bind. **Recommended: take the convention; confirm
   the runtime-dir path against the cockpit's existing process model during
   decomposition.**

---

## Provenance & alignment

- **Decision:** ADR-001 (this change).
- **Extends:** ADE ADR-001 (SSE one-way reply), ADR-002 (`SessionBridge`
  resume-or-spawn port), ADR-004 (binding guard). Those remain the cockpit's
  port-level decisions; this contract sits beneath them.
- **Proven groundwork (design adapted, not lifted):**
  `ae/ae_task_executor/terminal_pool.py`, `claude_session.py`,
  `monitored_claude_session.py`.
- **Standards applied:** `CONTRACT_FIRST_STANDARD.md` (CF-01..CF-04, CF-08,
  CF-09 — schema-first, three-category errors, error+empty stubs, conventional
  binding, structured streaming events); `convention-preference-standard.md`
  (subprocess streams, Unix-domain socket, NDJSON, offset-addressed log —
  CP-01 established conventions over bespoke); MECE-3 Form MEA-01 (domain-owned
  ports; adapter seam is EXPAND-Create, not a vendor wrap).
