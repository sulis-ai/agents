# Non-functional requirements — Sulis app: drive a change from the app

**Change:** CH-01KT50 · `create-autonomous-delivery-environment`

These are the constraints on *how well* the system behaves, all measurable. The
heaviest concentration is around the two-way chat, because it is the first thing in
the app that acts on a running session.

---

## Summary

The chat must never corrupt, hijack, or silently mislead about a session, and every
other surface must stay exactly as read-only as it is today. Performance targets are
modest and local (single founder, localhost). The architecture rule is the one that
matters most long-term: the app reaches its data only through the single API seam.

---

## Architecture & continuity

**NFR-ARCH-01 — Single data seam**
The app SHALL reach all change/brain/worktree data through the one API boundary
(the server), never the filesystem directly from the client.
- *Measure:* No client code reads the filesystem or the change store directly; every
  data read is an HTTP call to the server. Enforced by code review + the existing
  boundary check (`apps/cockpit/scripts/check-boundary.py`).

**NFR-ARCH-02 — Exactly one sanctioned write path**
The chat relay SHALL be the only write/act path in the app. The **resume or spawn**
of a session triggered by a chat send is part of that single sanctioned path (it is
the act that makes "it just works" possible) — it is allow-listed *because* the chat
relay triggers it, not as a separate write path. The read-only guarantee gate SHALL
pass with the chat relay (and its resume/spawn act) sanctioned and SHALL fail if any
other route gains a mutation, a filesystem write, a mutating git verb, or a process
start/signal.
- *Measure:* `apps/cockpit/scripts/check-read-only.sh` passes on the shipped code with
  the chat relay (including the resume/spawn it triggers) explicitly allow-listed and
  nothing else; any process-start outside that path fails the gate.

---

## Security & session safety (two-way chat)

**NFR-SEC-01 — Localhost only**
The server SHALL bind only to `127.0.0.1`. No remote access.
- *Measure:* The bind-address test confirms the server refuses non-loopback binds
  (existing `bind-address.test.ts` discipline, unchanged).

**NFR-SEC-02 — Session-to-change binding is positively verified**
Before relaying a message, the server SHALL positively confirm that the target
session belongs to the named change, and SHALL refuse delivery otherwise. This holds
for a session that was already live, **resumed**, or **freshly spawned** — the
`SESSION_CHANGE_MISMATCH` guard applies identically to all three.
- *Measure:* A test that points a change-A request at a change-B session results in
  `SESSION_CHANGE_MISMATCH` and zero bytes delivered; the same test passes for a
  resumed and a spawned session.

**NFR-SEC-03 — No message bodies in logs**
The relay SHALL log structured metadata (change id, accept/refuse, complete/break)
but SHALL NOT log the founder's message text or the agent's reply text.
- *Measure:* Log-line tests assert presence of metadata fields and absence of body
  content.

**NFR-SEC-04 — Liveness/status probes stay side-effect-free**
Liveness and status detection SHALL send no signals and write nothing (signal-0
existence probe only, per ADR-005).
- *Measure:* The existing `probeLiveness` tests still pass; no new signalling is
  introduced.

**NFR-SEC-05 — Read surfaces send nothing to a session and never start one**
Opening the board, a thread, the brain view, a preview, or a diff SHALL cause zero
writes to and zero signals at any session, and SHALL NOT resume or spawn any session.
Resume/spawn happens **only** on an explicit chat send.
- *Measure:* The read-only inventory test passes for every non-chat route; a test
  asserts that loading any read surface starts no `claude` process.

**NFR-SEC-06 — Resume/spawn acts only on the targeted change's session**
When relaying a chat message, the server SHALL resume or spawn **only** the session
bound to the targeted change. It SHALL NOT start, restart, or address any other
change's session, and the session it acts on SHALL pass the session-to-change binding
check (NFR-SEC-02) before any prompt is delivered.
- *Measure:* A test sending to change A while change B has a closed prior session
  confirms only A's session is resumed/spawned, B's session is untouched, and the
  binding check runs before delivery.

---

## Reliability (two-way chat)

**NFR-REL-01 — No silent message loss**
Every send SHALL resolve to a visible success or a visible failure; there is no
state where a message appears delivered but was not.
- *Measure:* Fault-injection tests (no session, dead session, broken bridge) each
  produce a visible failure; none show a false "sent".

**NFR-REL-02 — Partial replies are preserved on break**
A stream that breaks mid-reply SHALL preserve the text received so far and mark it
interrupted.
- *Measure:* Killing the bridge mid-stream leaves the partial text visible with an
  "interrupted" marker.

**NFR-REL-03 — One in-flight message per change**
The system SHALL allow at most one in-flight message per change at a time.
- *Measure:* A second send while a stream is in progress is refused with
  `SESSION_BUSY`; sending succeeds again after completion/failure.

**NFR-REL-04 — Resume restores recoverable state without fabricating completion**
A resumed session SHALL restore the change's recoverable state (persisted transcript
+ worktree files + brain entities) and SHALL NOT present a step that was incomplete at
the prior close as completed; an interrupted step is re-run from the restored state.
- *Measure:* A resume test from a transcript that ended mid-step shows the agent
  re-running the incomplete step (not reporting it done), and the founder sees a
  "resumed" indication rather than a silent continuation.

---

## Performance (local, single founder)

**NFR-PERF-01 — Board loads quickly**
The board SHALL render the change cards within 1 second of opening the app under a
normal local load (≤ 50 in-flight changes).
- *Measure:* Time-to-first-render of the card grid ≤ 1s at p95 with 50 seeded
  changes.

**NFR-PERF-02 — Streaming feels live**
The first reply chunk SHALL appear within 2 seconds of the agent beginning to
respond, and subsequent chunks SHALL append without perceptible batching (≤ 250 ms
between a chunk arriving at the server and appearing in the UI).
- *Measure:* Instrumented timing on the recorded-bridge fixture meets both bounds.

**NFR-PERF-03 — Search/filter is interactive**
Applying a search or filter SHALL update the board within 300 ms for ≤ 50 changes.
- *Measure:* Filter-to-render ≤ 300 ms at p95 with 50 seeded changes.

---

## Scalability

**NFR-SCALE-01 — Realistic local scale**
The app SHALL remain usable (board, search, filter within their performance bounds)
up to 200 in-flight changes — well beyond a single founder's realistic concurrency.
- *Measure:* The PERF bounds hold (relaxed by ≤ 2×) at 200 seeded changes.

---

## Availability

**NFR-AVAIL-01 — Local-process availability**
The app's availability is the availability of a local process the founder starts;
there is no uptime SLA. When the server is down, the app SHALL show a clear "the
Sulis app server isn't running" state rather than a blank or broken screen.
- *Measure:* With the server stopped, the client shows the server-down state.

---

## Data

**NFR-DATA-01 — The app stores no new state of its own**
The read surfaces SHALL introduce no new persistent store. Chat exchanges become
part of the existing change conversation/transcript through the existing data model;
the app does not create a parallel store.
- *Measure:* No new database/file store is added; the chat exchange is reflected in
  the change's existing conversation.

**NFR-DATA-02 — Retention follows the existing model**
Conversation/brain retention SHALL follow the existing change-store model; this
change adds no separate retention policy.
- *Measure:* No new retention configuration is introduced.
