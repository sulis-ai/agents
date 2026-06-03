# Software Requirements Document — Sulis app: drive a change from the app

**Change:** CH-01KT50 · `create-autonomous-delivery-environment`
**Status:** draft
**Audience:** non-technical founder (plain English is the front door; the FR/NFR
blocks carry the precision a builder needs)
**Kind:** `frontend` + `backend` (the chat capability adds the app's first write
path; everything else is read-side)

---

## Summary (read this first)

Today the Sulis app is a **read-only window** onto your in-flight work. You can
look at every change, read the conversation, browse the files, and see the
contracts — but you cannot *do* anything from it. To actually drive a change you
still have to go to the terminal.

This change turns the app from a window into a **cockpit you can steer from**. Six
things get added:

1. **A board you land on** — every change you have on the go, shown as cards in
   columns that read left-to-right as the stages of work (find out what's there →
   write down what it should do → design it → build it → review it → ship it). One
   glance tells you what's where.
2. **Plain-English progress inside a change** — open any change and see which
   stage it's on and a short, readable "here's what's happening" note, instead of
   reading the raw conversation.
3. **The brain, in plain sight** — see the building blocks the agent has created
   for this change (the requirements, the workflows), grouped and readable.
4. **Rendered previews** — read a document or a web page the way it's meant to
   look, not as raw text. The raw is still one click away.
5. **Search and filter** — find a change by what's in it; narrow the board to one
   stage, or to "needs your attention".
6. **Two-way chat** — the big one. Type a message to a change from the app and the
   agent's reply streams back, live. This is what turns reviewing into *driving*.

The most safety-sensitive piece is the chat, because it is the first thing in the
app that **acts on** a running agent rather than just reading from it. A large part
of this document is about doing that safely: never corrupting a session, never
hijacking the wrong one, failing clearly when it can't, and keeping every other
surface exactly as read-only as it is today.

This is one thin, shippable slice of the larger Sulis app vision — not the whole
thing. It deliberately does **not** include live-product monitoring, automatic
status posts every few turns, deep question-and-answer over the brain, the
settings/admin area, or any cloud hosting. Those are named as non-goals below.

---

## Glossary

Full definitions live in `GLOSSARY.md`. The load-bearing terms: **change**
(a unit of work as a navigable thread), **board** (the landing Kanban),
**stage** (where a change sits in its lifecycle), **thread** (one change's
detail view), **session** (the running agent process behind a change),
**brain** (the entities + workflows created for a change), **liveness** (whether a
session is currently running), **the seam** (the single API boundary the app
reaches its data through).

---

## Actors

| Actor | Description | Goals |
|---|---|---|
| **Founder** | The single, non-technical user. Runs the app locally on their own machine. | See everything in flight at a glance; understand a change in plain English; steer a change by chatting to its agent. |
| **Sulis app server** | The local Node/Express process that serves the app and is the only thing that touches the data + the running sessions. | Read change/brain/worktree data through the seam; relay the founder's messages to the right session and stream replies back; protect read-only surfaces. |
| **Claude session (agent)** | A running `claude` process for a specific change, spawned by the terminal plugin. | Receive a prompt, do work, emit a streamed reply. |
| **Change store + brain** (data, not an agent) | The shared on-disk model the whole ladder reads/writes. | Source of truth for changes, stages, entities, workflows. |

The founder is the only human. There is no multi-user, no remote access — the app
binds to localhost only (inherited constraint, unchanged).

---

## Use cases

### UC-01 — Land on the board and read what's in flight

- **Actor:** Founder
- **Trigger:** Founder opens the app.
- **Preconditions:** App server is running locally.
- **Main flow:**
  1. App requests the list of changes from the server.
  2. Server returns every change with its stage and liveness.
  3. App lays the changes out as cards in columns, one column per stage.
  4. Each card shows the handle, the one-line intent, the current stage, and a
     liveness indicator (is its agent running right now).
- **Alternate flow (empty):** No changes in flight → the board shows an empty
  state that explains how to start a change.
- **Postcondition:** Founder can see, in one screen, every change and where it
  sits.
- **Governing requirements:** FR-01, FR-02, FR-03, FR-15.

### UC-02 — Open a change and read its progress in plain English

- **Actor:** Founder
- **Trigger:** Founder clicks a card (or a sidebar entry).
- **Main flow:**
  1. App opens the change's thread.
  2. The thread shows the stage track with the current stage marked.
  3. The thread shows a plain-English "what's happening" status, derived at
     read-time from the change's state and conversation.
- **Postcondition:** Founder understands the change's state without reading the
  raw transcript.
- **Governing requirements:** FR-04, FR-05.

### UC-03 — See the brain for a change

- **Actor:** Founder
- **Trigger:** Founder opens the brain view within a change's thread.
- **Main flow:**
  1. App requests the entities + workflows created for this change.
  2. Server returns them through the seam.
  3. App lists them grouped (e.g. requirements together, workflows together) with
     a readable detail view per item.
- **Alternate flow (empty):** No brain entities yet → a plain note saying so.
- **Postcondition:** Founder can see the building blocks the agent has created.
- **Governing requirements:** FR-06, FR-07.

### UC-04 — Read a rendered preview of a document or page

- **Actor:** Founder
- **Trigger:** Founder opens a `.md` / `.html` (or similar) file in a change.
- **Main flow:**
  1. App shows the file rendered the way it is meant to look.
  2. A toggle switches between the rendered view and the raw source.
- **Postcondition:** Founder reads the artifact as intended; raw is available.
- **Governing requirements:** FR-08, FR-09.

### UC-05 — Search and filter changes

- **Actor:** Founder
- **Trigger:** Founder types in the search box or picks a filter.
- **Main flow:**
  1. Founder enters search text and/or selects a stage filter and/or "needs
     attention".
  2. App narrows the board to the matching changes.
- **Postcondition:** Founder finds the change(s) they want.
- **Governing requirements:** FR-10, FR-11, FR-12.

### UC-06 — Send a message to a change's agent and watch the reply stream back

- **Actor:** Founder
- **Trigger:** Founder types a message in a change's chat and sends it.
- **Preconditions:** The change exists. (A *live* session is **not** a
  precondition — the app resumes or spawns one as needed. See the main flow.)
- **Main flow ("it just works"):**
  1. Founder types a prompt and sends it.
  2. App sends the prompt to the server, naming the change.
  3. Server resolves a session for the named change without asking the founder to
     choose:
     - If the change has a **live** session → use it (after the
       session-to-change match, step 4).
     - If the change has **no live session but a prior session exists** → the
       server **resumes** the change's most recent session, restarting it from its
       persisted conversation transcript so the agent wakes with full memory.
     - If the change has **never had a session** → the server **spawns a fresh**
       session **grounded in the change's saved context** (its CONTEXT.md / change
       manifest / stage / prior decisions) so the agent re-reads the change before
       acting, never starting blind.
  4. Server positively confirms the resolved session belongs to the named change
     (`SESSION_CHANGE_MISMATCH` guard), then relays the prompt to that session.
  5. The agent's reply streams back token-by-token; the app appends it live.
  6. When the reply completes, the message becomes part of the change's
     conversation.
- **Resume edge — a step that was mid-action when the prior session closed:** A
  resumed agent restores everything that was *said and done* (transcript + worktree
  files on disk + the brain entities it created). It does **not** magically continue
  an action that was interrupted mid-flight at close. The resumed agent **re-runs**
  the incomplete step from the restored state rather than pretending it completed.
  The app surfaces this honestly: the founder sees that the change was resumed, not
  that nothing happened. (FR-24, FR-25, FR-N5.)
- **Exception flows:**
  - Resume/spawn cannot establish a session at all (the underlying process fails to
    start) → app shows a clear failure and does not show the message as delivered
    (FR-19).
  - Session died mid-stream → app shows a clear failure, the partial reply is
    preserved, nothing is silently dropped (FR-19, FR-22).
  - Another message is already in flight for this change → app refuses the second
    send until the first completes (FR-20).
  - The resolved session does not match the named change → server refuses (FR-21,
    NFR-SEC-02).
- **Postcondition:** Exactly one session — the named change's own session, resumed
  or freshly spawned — received exactly the founder's message; no other change's
  session was touched; the reply is captured into the change's conversation.
- **Governing requirements:** FR-16..FR-26, NFR-SEC-01..06, NFR-REL-01..03.
- **Negative requirements:** see "Negative requirements" below.

---

## Functional requirements

> Each block uses the standard machine-emittable shape: an ID, a statement, and
> acceptance criteria a builder can write a test against.

### Board (landing)

**FR-01 — Board lists in-flight changes as cards in stage columns**
The app's landing view SHALL render every in-flight change as a card, arranged in
columns where each column is one lifecycle stage in order: `recon`, `specify`,
`design`, `implement`, `review`, `ship`.
- *Acceptance:* Given three changes at stages `specify`, `design`, `ship`, the
  board shows three cards, each in the column matching its stage, in left-to-right
  stage order.

**FR-02 — Each card shows handle, intent, stage, liveness**
Each card SHALL show the change handle, its one-line intent, its current stage,
and a liveness indicator reflecting whether its session is currently running.
- *Acceptance:* A card for a change whose session is running shows a "running"
  indicator; a card for a change with no running session shows a "not running" (or
  "unknown") indicator; both show handle, intent, and stage.

**FR-03 — Empty board guides starting a change**
When there are no in-flight changes, the board SHALL show an empty state that tells
the founder, in plain English, how to start a change.
- *Acceptance:* With zero changes, the board renders the empty-state guidance and
  no card grid.

**FR-15 — Shipped changes are not shown as in-flight on the board**
Changes in a terminal stage (`shipped`) SHALL NOT appear as in-flight cards in the
six lifecycle columns. (They remain reachable as audit history per the existing
app, unchanged.)
- *Acceptance:* A `shipped` change does not appear in any of the six stage columns.

### Per-change progress + status

**FR-04 — Thread shows the stage track with the current stage marked**
Inside a change's thread, the app SHALL show the six lifecycle stages with the
change's current stage clearly marked.
- *Acceptance:* For a change at `design`, the stage track marks `design` as current
  and shows the earlier stages as done and later stages as pending.

**FR-05 — Thread shows a plain-English read-time status**
Inside a change's thread, the app SHALL show a plain-English "what's happening"
status, derived at read-time from the change's state and conversation/journal.
- *Acceptance:* Opening a change's thread shows a human-readable status sentence or
  short paragraph; it is computed on read, not from a stored periodic status post
  (the periodic auto-publish beat is a non-goal — see Non-goals).

### Brain view

**FR-06 — Brain view lists a change's entities and workflows, grouped by kind**
Within a change's thread, the app SHALL list the entities and workflows the agent
has created for that change, **grouped by kind**, read-only.
- *Acceptance:* For a change with two requirements and one workflow, the brain view
  shows a requirements group with two items and a workflows group with one item.
- *Design-stage follow-up:* grouping-by-kind is the confirmed default for now; the
  grouping/sorting is to be refined in the design-stage whole-surface visual UX pass
  (recorded under Design-stage constraints).

**FR-07 — Brain items have a readable detail view**
Each brain item SHALL open a readable detail view showing its content.
- *Acceptance:* Clicking a listed entity shows its detail (its fields/content) in a
  readable form.

> Brain data is reached through the seam (the single API boundary), never the
> filesystem directly (NFR-ARCH-01). This view is read-only; deep question-and-
> answer over the brain is a non-goal.

### Rendered previews

**FR-08 — Renderable files show a rendered view**
For files whose type supports rendering (`.md`, `.html`, and similar), the app
SHALL show a rendered view of the file.
- *Acceptance:* Opening a `.md` file shows formatted output (headings, lists, etc.),
  not raw markdown source.

**FR-09 — Rendered/source toggle**
Any rendered preview SHALL offer a toggle to the raw source, and back.
- *Acceptance:* From a rendered `.md`, one action shows the raw text; the reverse
  action restores the rendered view.

> Where the existing design-system VIEWER / contract-preview renderers already fit
> (HTML, contract artifacts), the app SHALL reuse them rather than build a new
> renderer (EP-03; reuses the `design-system` skill VIEWER and the
> `wpx-render-contract` path already in the app).

### Search + filter

**FR-10 — Search changes by their content**
The app SHALL let the founder find changes by entering search text matched against a
change's **content** — its conversation and the entities/artifacts created for it —
in addition to the handle, intent, and stage. Search is over what's *in* a change,
not just its labels.
- *Acceptance:* Entering text that appears only in a change's conversation (not its
  handle or intent) still narrows the board to that change; likewise for text that
  appears in a brain entity/artifact created for the change.

**FR-11 — Filter by stage**
The app SHALL let the founder filter the board to one or more stages.
- *Acceptance:* Selecting the `design` filter shows only `design`-stage changes.

**FR-12 — Filter by "needs attention"**
The app SHALL let the founder filter the board to changes that **need attention**. A
change needs attention when it is **blocked**, **waiting on a founder decision**, or
its **agent stopped mid-reply**. A change that is simply idle but otherwise fine is
**not** flagged.
- *Acceptance:* Selecting "needs attention" shows a change that is blocked, a change
  waiting on a founder decision, and a change whose agent stopped mid-reply; it does
  **not** show a change that is idle-but-fine.

### Two-way chat (the new write capability)

**FR-16 — Founder can send a message to a change's agent from the app**
The app SHALL let the founder type a message within a change's thread and send it
to that change's session.
- *Acceptance:* The founder types a prompt, sends it, and the prompt is delivered
  to the session associated with that exact change.

**FR-17 — The agent's reply streams back into the thread live**
The agent's reply SHALL stream back to the app incrementally and be appended to the
conversation as it arrives.
- *Acceptance:* As the agent produces output, the app shows it progressively (not
  only after completion).

**FR-18 — A completed reply becomes part of the change's conversation**
When a streamed reply completes, it SHALL be presented as part of the change's
conversation history alongside prior messages.
- *Acceptance:* After completion, the new exchange appears in the same conversation
  view as the existing transcript, in order.

**FR-19 — Clear failure when the session is unreachable**
If the target session cannot be reached (no session, dead process, broken bridge),
the app SHALL show a clear, plain-English failure and SHALL NOT silently drop the
message.
- *Acceptance:* With no reachable session, sending a message produces a visible
  failure message naming what went wrong and what to do; no message is shown as
  "sent" when it was not delivered.

**FR-20 — One message in flight per change at a time**
While a reply is streaming for a change, the app SHALL prevent a second message
from being sent to that same change until the first completes or fails.
- *Acceptance:* With a stream in progress, the send control for that change is
  disabled/refused; sending is possible again once the stream ends.

**FR-21 — The send is bound to the named change's session, never another**
The server SHALL deliver a message only to the session belonging to the change
named in the request, and SHALL refuse if it cannot positively match them.
- *Acceptance:* A request naming change A is delivered only to A's session; if the
  server cannot confirm the session belongs to A, it refuses with a typed error and
  delivers nothing.

**FR-22 — A mid-stream break is surfaced and the partial reply preserved**
If a stream breaks partway, the app SHALL surface the break and preserve whatever
reply text arrived before the break.
- *Acceptance:* Killing the stream mid-reply leaves the partial text visible and
  shows a "the reply was interrupted" indication.

**FR-23 — Session lifecycle states are visible to the founder**
The chat SHALL reflect the session's state to the founder: reachable / running,
busy (reply in progress), resuming/starting, and could-not-start.
- *Acceptance:* The chat shows distinct, plain-English states for "ready to send",
  "agent is replying", "waking the change up" (resume/spawn in progress), and
  "couldn't start a session".

**FR-24 — No live session, prior session exists: resume from the saved transcript**
When the founder sends a message to a change that has **no live session but has had
one before**, the server SHALL resume the change's most recent session by restarting
it from its persisted conversation transcript, so the agent has the change's full
prior memory before the new message is delivered. The founder SHALL NOT be asked to
choose resume vs. spawn.
- *Acceptance:* Given a change with a prior, now-closed session and a non-empty
  transcript, sending a message resumes that session (the agent's reply demonstrably
  reflects prior context) and delivers the new message — with no resume/spawn prompt
  shown to the founder.

**FR-25 — Never had a session: spawn fresh, grounded in the change's saved context**
When the founder sends a message to a change that has **never had a session**, the
server SHALL spawn a fresh session that is grounded in the change's saved context
(CONTEXT.md / change manifest / stage / prior decisions) so the agent re-reads the
change before acting, and SHALL then deliver the message. The founder SHALL NOT be
asked to choose.
- *Acceptance:* Given a change with no session history but saved context, sending a
  message spawns a session that re-reads the change's context before its first
  action, and delivers the message — with no prompt shown to the founder.

**FR-26 — A step left incomplete at the prior session's close is handled gracefully on resume**
On resume, the system SHALL restore the change's recoverable state (transcript +
worktree files + brain entities) and SHALL NOT claim that an action interrupted
mid-flight at the prior close completed. A step that was incomplete at close SHALL be
re-run by the resumed agent from the restored state, and the founder SHALL be shown,
in plain English, that the change was resumed (not that it silently continued).
- *Acceptance:* Given a session that closed with a step part-done, resuming it shows
  the founder a "resumed this change" indication, and the resumed agent re-runs the
  incomplete step from the restored state rather than reporting it as already
  finished.

### Negative requirements (two-way chat)

These are the "MUST NOT / MUST refuse" requirements that came out of stress-testing
the chat. They are the load-bearing safety of this change.

**FR-N1 — Read-only surfaces stay read-only.** Adding chat MUST NOT make any other
surface writable. The board, thread, brain view, file/diff viewer, and contract
previews remain strictly read — they send nothing to and mutate nothing about a
session, the worktree, the change store, or the brain.
- *Acceptance:* The existing read-only guarantee gate
  (`apps/cockpit/scripts/check-read-only.sh`) is updated so the **only** sanctioned
  write path is the chat relay; every other route still fails the gate if it gains a
  mutation. (See NFR-ARCH-02.)

**FR-N2 — The app MUST NOT corrupt or hijack a session.** A message MUST be delivered
to exactly the named change's session — whether that session was already live,
resumed, or freshly spawned — MUST NOT interleave with another in-flight message to
the same session, and MUST NOT resume, spawn, or address a session belonging to a
different change. The resume/spawn act MUST act on **only** the targeted change's
session; it MUST NOT start, restart, or touch any other change's session. (Encodes
FR-20, FR-21, FR-24, FR-25 as prohibitions.)

**FR-N3 — The app MUST NOT silently fail.** Every send either visibly succeeds or
visibly fails; there is no state in which the founder believes a message was
delivered when it was not. This includes resume/spawn: if a session cannot be
resumed or spawned, the failure is visible and the message is not shown as delivered.
(Encodes FR-19.)

**FR-N4 — The app MUST NOT alter a session it only meant to read.** Liveness and
status remain side-effect-free probes (signal-0 existence check, no signals sent),
exactly as today. Reading the board, a thread, the brain, a preview, or a diff MUST
NOT resume or spawn a session — resume/spawn happens **only** on an explicit chat
send. (See the existing `probeLiveness` discipline, ADR-005.)

**FR-N5 — A resumed session MUST NOT fabricate completion of an interrupted step.**
On resume, the system MUST NOT present a step that was incomplete at the prior
session's close as having completed. The recoverable state restored is the
transcript + worktree files + brain entities; an interrupted action is re-run, not
silently continued or falsely reported as done. (Encodes FR-26.)

---

## Verification Plan

<!-- VERIFICATION_QUESTIONS source: plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md v1.0.0 -->

> Answers to the canonical 20-question set
> (`plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md` v1.0.0). The six
> required subsections (ADR-001) follow. All prior founder-owned open items
> (auto-spawn behaviour, "needs attention" rule, search scope, brain grouping) are
> now resolved; none remain open in this plan.

### What user-observable behaviour are we verifying?

A founder opens the app and sees a board of their in-flight changes as cards in
stage columns. They open a change and read a plain-English status and a marked
stage track. They see the change's brain entities grouped by kind, and they can read
a document rendered (with a raw toggle). They can search a change by its content
(conversation + artifacts), and filter the board (by stage, or to changes that need
attention — blocked, waiting on a decision, or stopped mid-reply). And — the headline
— they can type a message to **any** change from the app and it **just works**: if no
session is live, the app silently resumes the change's last session from its saved
transcript, or spawns a fresh one grounded in the change's saved context, then the
agent's reply streams back live — with every other surface staying read-only, and a
step that was interrupted at a prior close re-run honestly rather than faked.

### Verification environment(s)

- **Local dev + CI** for the unit/component/integration tests (server route tests
  via supertest; client component tests via Vitest; the read-only gate via
  `check-read-only.sh`). This mirrors the existing cockpit test setup.
- **Local (founder machine)** for the chat end-to-end, because the live stream-json
  bridge needs a real `claude` session, which is a local process. The earlier spike
  validated the bridge here.
- The change's **own dogfood path**: it is taken through `/sulis:specify` →
  `/sulis:draft-architecture` → implement → `/sulis:verify-acceptance --scenario`,
  so the scenario loop is itself an environment exercising this change.

### Bootstrap-from-zero case

- The read-side surfaces (board, thread, brain, previews, search) verify from a
  fresh clone using **fake/seeded change-store + transcript fixtures**, exactly as
  the existing cockpit tests already do (`FakeChangeStoreReader`, fixture
  transcripts). No external credentials.
- The chat end-to-end **cannot** fully bootstrap from zero in CI, because it needs a
  real running `claude` session and the stream-json bridge — and now also a real
  **resume** (restart from a persisted transcript) and a real **spawn** (grounded in
  saved context). → deferred verification need: a **recorded/replayable session bridge
  fixture** covering live, resume, and spawn (plus a mid-step transcript) so the relay
  + session-resolution logic can be tested without a live agent (see deferred needs).

### Per-integration verification strategy

| Integration | Boundary | Strategy | Classification |
|---|---|---|---|
| Change store + brain | In-process port (`ChangeStoreReader`, brain read) | Real via fakes/fixtures in tests; real store on the founder machine | **existing** |
| Claude session bridge (stream-json) | Local process / stdio bridge | Relay + lifecycle logic — including **resume-from-transcript** and **spawn-grounded-in-context** session resolution — tested against a **recorded bridge fixture**; full live path (real resume + real spawn) verified manually on the founder machine | **deferred** (fixture) |
| design-system VIEWER / contract renderer | In-process / subprocess | Reuse existing renderer + its existing tests | **existing** |
| Worktree recreate-on-demand | Subprocess (`RecreateRunner`) | Existing port + existing tests | **existing** |

- *Idempotency/replay (Q10):* the relay MUST treat a resend after a broken stream as
  a new message, not a silent duplicate; the one-in-flight rule (FR-20) is the
  guard.
- *Auth/authz (Q11):* localhost-only, single founder, no auth tokens crossing the
  seam; the authorization that matters is **session-to-change binding** (FR-21).
- *Failure mode if unavailable (Q12):* the session bridge being down ⇒ visible
  failure + preserved partial (FR-19, FR-22); read surfaces unaffected.
- *Observability (Q13):* the relay logs one structured line per send
  (change id, accepted/refused, completed/broken) without logging message bodies.

### Per-kind verification adapter

This change spans **two** adapters (Q18 → multiple):

- **`frontend`** (ADR-007 row): component-rendering tests for the board, stage
  track, brain view, previews, search, and chat UI; a11y check (axe-core) on the new
  surfaces; visual check against the design-system tokens (the design stage runs the
  whole-surface UX/visual pass — see Design-stage constraints).
- **`backend`** (ADR-007 row): behavioural API test for the chat relay against a
  running test server, asserting session-to-change binding (FR-21) across live,
  resumed, and spawned sessions; resume-from-transcript (FR-24); spawn-grounded
  (FR-25); incomplete-step-on-resume handling (FR-26 / FR-N5); resume/spawn-acts-on-
  -only-the-targeted-session (NFR-SEC-06); one-in-flight (FR-20); clear-failure
  (FR-19); and the read-only gate including the sanctioned resume/spawn act (FR-N1,
  NFR-ARCH-02). Concrete artifacts named at design time.

### Infrastructure needs surfaced (deferred)

- `recording-bridge-claude-session` — a recorded/replayable stream-json session so
  the chat relay + lifecycle can be verified in CI without a live agent. The fixture
  set MUST cover all three session-resolution paths: live, **resume-from-transcript**,
  and **spawn-grounded-in-context**, plus a transcript that ends mid-step (to verify
  FR-26 / FR-N5).
- `seed-brain-entities-fixture` — fixture brain entities for a change so the brain
  view (FR-06/07) can be verified from a fresh clone.

---

## Diagrams

- Board → thread navigation: `diagrams/board-navigation.md`
- Two-way chat send/stream flow: `diagrams/chat-flow.md`

---

## Out of scope (non-goals)

- Monitoring / observability of the live product (Platform tier).
- The agent auto-publishing a status checkpoint every few turns (read-time status
  is in; the periodic beat is later).
- Deep brain question-and-answer / interrogation (the brain view here is read-only
  list + detail only).
- The admin / defaults area.
- The cloud deployment modes. The **data seam** is designed-for (the app reaches
  data only through the single API boundary), but cloud hosting is not built; the
  near path is local web app → installable binary.

---

## Design-stage constraints (notes, not body requirements)

These are recorded for the design stage; they are not FR/NFR for this SRD body.

- **One coherent UX + visual design pass over the whole surface** — board, thread,
  chat, brain view, rendered previews, search — designed together, not per-piece.
  The app is currently "lumpy"; the design stage fixes that as one thing.
- **Both contracts rendered for founder review at design time** — the data contract
  (the API the app speaks) and the UI/visual contract are rendered and surfaced for
  the founder to eyeball **before build**, as a review gate (reusing the existing
  contract-preview path; plain-English-first per the dual-register pattern).
- **Brain view grouping/sorting refinement** — FR-06 ships grouped-by-kind as the
  confirmed default; the design-stage visual UX pass refines how brain entities are
  grouped, ordered, and surfaced as part of the one coherent surface design.

---

## Assumptions & decided-by-default

Engineering-internal defaults taken via Convention Preference (not founder-owned):

- **Chat transport across the seam:** Server-Sent Events (SSE) for the streamed
  reply — the established convention for one-way server→client token streaming over
  HTTP, simpler than WebSockets for this shape. (Builder may choose WebSockets if the
  bridge requires bidirectional framing; recorded for the design stage.)
- **Error envelope:** reuse the existing typed `{ error, code }` envelope and add
  chat-specific codes: `SESSION_BUSY` (one-in-flight), `SESSION_CHANGE_MISMATCH`
  (binding guard), and `SESSION_UNREACHABLE` (now meaning *could not resume or spawn a
  session*, since "no live session" is no longer itself a failure — it triggers
  resume/spawn).
- **Resume vs. spawn is the app's call, not the founder's:** the server picks resume
  (prior session exists) or spawn (none ever) automatically. "Resume" uses the
  built-in restart-from-transcript capability; "spawn" seeds the agent with the
  change's saved context. Mechanics (how the bridge resumes a transcript, how context
  is injected on spawn) are a design-stage concern.
- **Read-only gate extension:** the chat relay is added to
  `check-read-only.sh` as the single sanctioned write path; the gate keeps failing
  on any other mutation (FR-N1).
- **Code home:** extend `apps/cockpit/` (EP-03 — extend, don't rebuild); the chat
  write path is a new route + a new port (the session bridge) alongside the existing
  read ports.
