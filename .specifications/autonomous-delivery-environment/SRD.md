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

This change turns the app from a window into a **cockpit you can steer from**. Eight
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
7. **A chat front door that sets you up and starts work** — when you first open the
   app and there's nothing there yet, a conversation (backed by a behind-the-scenes
   agent on the *same* chat bridge) does the setup *for* you: it asks which product
   you're working on, asks where your code lives, and **handles the repo either way** —
   if you don't have one yet it **creates one** for you (asking first), and if you do
   it **finds and configures** it. It then saves your product and project for good, so
   next time you can just open the app and say "make a change on Product X" and it
   starts — **no setup again**. After that, you can just *say* what you want to work on
   in plain English and it starts the change for you (fetching the code first if it
   isn't on your machine). It always asks before it creates anything.
8. **One product at a time, with a switcher** — if you run more than one product, the
   board shows **one product's** work at a time, never a jumble of everything. A
   **product switcher** lets you flip between them; flipping re-points the board (and
   your search and filters) to whichever product you picked.

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

### UC-07 — Cold-start onboarding: build the graph from a conversation

This is the **adoption flow**: the very first thing a founder does when there is
nothing in the app yet. A "pick a Product, then a Project" form is useless against
an empty graph — there is nothing to pick. So instead of a form, the app opens a
**conversation** that *creates* the graph.

- **Actor:** Founder
- **Trigger:** Founder opens the app with **no Product or Project yet minted** (the
  board would otherwise be empty with nothing to start from), and starts the
  onboarding chat.
- **Preconditions:** App server running locally; the change store has no Product /
  Project for the founder's work yet.
- **Main flow ("the agent figures it out with you"):**
  1. The app opens a chat backed by a **headless discovery agent** — the same
     stream bridge as the two-way chat (FR-16..FR-26), just driven without a visible
     terminal.
  2. The agent asks **which Product** the founder is working on (or the founder
     states it).
  3. The agent then asks **where the repo(s) are**, and **branches** on the answer:
     - **No repo yet** → the agent offers to **create a new repo** for the founder.
       Creating a real git/GitHub repo is a **consequential, possibly-external** act,
       so it happens **only after the founder confirms** (the same confirm gate as
       minting, FR-N6). If the repo creation fails, the founder sees a clear,
       plain-English failure and **no Product/Project config is persisted** for that
       missing repo (FR-N10).
     - **Repos already exist** → the founder points the agent at the **area of their
       machine** the work lives in, and the agent **finds/configures** the repo(s)
       from that pointer — searching the chosen area only (FR-N7 / NFR-DISC-01),
       orchestrating the existing discovery skills (`discover-project`,
       `discover-context`, `codebase-mapping`).
  4. The agent asks plain-English clarifying questions as needed (*"Is this your
     product? What does it do? Which of these repos belong to it?"*) and proposes the
     **Tenant / Product / Project** it has discovered or will create, in plain English,
     and **asks the founder to confirm before anything is created**.
  5. On confirmation, the agent **mints** the entities through the spine emitters
     (the validated Tenant / Product / Project emitters), so the writes go through
     schema-checked paths, never freehand — and **completes and persists the
     Product + Project config**, including each `Project.source = {repo, path,
     primary_branch}` for the found-or-created repo (FR-N11).
  6. The board now has a Product and at least one Project — the founder is no longer
     looking at an empty graph — and the config is **durable**, so re-opening the app
     and saying "make a change on Product X" starts a change without re-running setup.
- **Alternate flow (nothing found, repos-exist branch):** The chosen area contains
  no recognisable repo / project → the agent says so plainly and asks the founder to
  point somewhere else (or offers to create a repo instead), rather than minting an
  empty or guessed entity.
- **Alternate flow (already exists):** The agent discovers a Project/Product that is
  **already minted** → it does **not** create a duplicate; it surfaces the existing
  one and continues (FR-31).
- **Exception flow (bridge):** The discovery session can't be established (bridge won't
  start) → clear, plain-English failure; nothing is minted (FR-19 discipline, reused).
- **Exception flow (repo creation):** The founder confirms a new repo but its creation
  fails → clear, plain-English failure; no repo, no Product/Project config persisted
  for it (FR-N10).
- **Postcondition:** The founder has confirmed, schema-valid Tenant / Product /
  Project entities in the graph, with each Project's `source` set to a found-or-created
  repo; the config is **persisted and durable** (next-session change-creation needs no
  re-setup); no entity or repo was created without the founder's confirmation; nothing
  outside the chosen search area was read.
- **Governing requirements:** FR-27, FR-28, FR-31, FR-35, FR-36, NFR-DISC-01..04,
  NFR-DISC-06.
- **Negative requirements:** FR-N6, FR-N7, FR-N10, FR-N11.

### UC-08 — Start a change from plain-English intent

Once a Product/Project exists, the founder shouldn't have to drop to the terminal to
begin a new piece of work. They say what they want in plain English; the app turns
that into a started change.

- **Actor:** Founder
- **Trigger:** Founder, in the chat, describes a new piece of work in plain English
  (e.g. *"fix the thing where the login page hangs"*).
- **Preconditions:** At least one Product and Project exist (via UC-07 or already
  present); the chosen Project's repo is known from its `source`.
- **Main flow:**
  1. The same headless agent reads the founder's intent and resolves it to a **change
     primitive + slug** using the existing classifier and the change-primitives
     vocabulary.
  2. The agent shows the founder, in plain English, **what it's about to start** (the
     kind of change and its name) and **asks the founder to confirm before creating
     it**.
  3. The app maps the chosen **Project's `source` (`repo`, `path`, `primary_branch`)**
     to the `--repo-root` the change machinery needs.
  4. **Local-first reachability:** if the Project's repo is **not present on the
     machine**, the agent **clones it from `Project.source.repo` first**; if the
     clone fails, the founder sees a clear failure and **no change is started**
     (FR-30).
  5. On confirmation (and a reachable repo), the agent runs `sulis-change start`
     against that repo with the resolved primitive/slug.
  6. The new change appears on the board at the **Recon** stage.
- **Alternate flow (intent ambiguous):** The classifier can't confidently pick a
  primitive → the agent asks one plain-English clarifying question rather than
  guessing.
- **Exception flow (repo unreachable / clone fails):** Clear failure; no change
  started; the founder is told what went wrong (FR-30).
- **Postcondition:** Exactly one new change is started against the chosen Project's
  repo and appears at Recon; nothing was started without the founder's confirmation.
- **Governing requirements:** FR-29, FR-30, NFR-DISC-04.
- **Negative requirements:** FR-N6.

### UC-09 — Concierge: find a change / get its status / ask about your world

The chat front door is a **concierge** — modelled on the `sulis:sulis` agent. Beyond
setting you up (UC-07) and starting work (UC-08), it answers plain-English questions
about the founder's world: *"which change was I doing the login fix in?"*, *"where's
the payments change up to?"*, *"what have I got in flight?"*. This is **read-only
help** — the concierge looks things up and tells you; it does not change anything.

- **Actor:** Founder
- **Trigger:** Founder asks the concierge a question about their existing changes,
  stages, or entities in plain English.
- **Preconditions:** App server running locally. (A populated graph is not required —
  if there's nothing yet, the concierge says so and offers onboarding, UC-07.)
- **Main flow:**
  1. The founder asks a question in the concierge chat (e.g. *"what needs my
     attention?"* or *"find the change about the hanging login page"*).
  2. The concierge reads the change store + brain **through the seam, read-only**
     (the same data the board and thread already show) to answer.
  3. The concierge replies in plain English — naming the change(s), their stage, and
     a short status — and, where useful, points the founder at the relevant card or
     thread.
- **Alternate flow (nothing matches):** No change matches the question → the concierge
  says so plainly rather than guessing, and offers to start one (UC-08).
- **Postcondition:** The founder has an answer drawn from their existing world;
  **nothing was created, changed, or started** — the graph and every session are
  exactly as they were before the question.
- **Governing requirements:** FR-33, FR-N8.
- **Negative requirements:** FR-N8 (coordinates only — no work done inline).

### UC-10 — An investigation becomes a change

The founder wants to *look into* something — explore an idea, poke at a question,
figure out whether something is worth doing. The concierge does **not** do that
exploring itself inline. Instead, an investigation is **first-class work**: the
concierge creates a change to hold it, so the exploring happens inside an audited,
self-contained change with its own lineage and worktree. If the investigation turns
into a build, it's already a change — nothing is lost in the hand-off.

- **Actor:** Founder
- **Trigger:** Founder asks the concierge to investigate / explore / look into
  something (e.g. *"can you look into why our sign-ups dropped last week?"*).
- **Preconditions:** A Product / Project exists (as for UC-08); if not, the concierge
  routes to onboarding first (UC-07).
- **Main flow:**
  1. The concierge recognises this as an **investigation** — real activity, not a
     read-only lookup.
  2. Rather than investigating inline, it resolves the intent to an **investigation
     change** (primitive + slug) and shows the founder, in plain English, the change
     it's about to create, **asking for confirmation first** (FR-N6).
  3. On confirmation, it runs `sulis-change start` so the investigation lands on the
     board as its own change (at Recon), exactly like UC-08.
  4. The actual exploring then happens **inside that change's session** (via the
     two-way chat, UC-06) — never inline in the concierge.
- **Alternate flow (turns into a build):** The investigation, now a change, can evolve
  straight into building — the same change carries forward its conversation, worktree,
  and brain; no separate hand-off and no lost context.
- **Postcondition:** Exactly one investigation change exists on the board; the
  concierge did **no** investigation work itself — all of it is contained in the
  change.
- **Governing requirements:** FR-34, FR-N9.
- **Negative requirements:** FR-N9 (all real activity, including investigation, is
  contained in a change).

### UC-11 — Switch the active Product; the board re-scopes

A founder can have **more than one Product**. The board never mixes them — it shows
one Product's in-flight changes at a time. A **product switcher** lets the founder
change which Product is active; switching re-scopes the board (and the rest of the
per-product views) to that Product.

- **Actor:** Founder
- **Trigger:** Founder opens the product switcher and picks a different Product.
- **Preconditions:** The founder's Tenant has **two or more Products** (with the
  single-Product case as a trivial sub-case — the switcher still shows the one
  Product as active).
- **Main flow:**
  1. The board is currently scoped to one **active Product** — it shows only that
     Product's in-flight changes (changes roll up Project → Product), never all
     Products mixed together.
  2. The founder opens the product switcher, which lists the Tenant's Products and
     marks the active one.
  3. The founder picks a different Product.
  4. The app re-scopes: the active Product becomes the chosen one, and the board now
     shows **that** Product's in-flight changes; the per-product views (search,
     filters, "needs attention") apply within the newly active Product.
- **Alternate flow (single Product):** The Tenant has exactly one Product → the
  switcher shows it as active; there is nothing else to switch to, and the board is
  scoped to that one Product.
- **Postcondition:** The board and the per-product views are scoped to exactly the
  chosen active Product; no other Product's changes are shown; nothing was created,
  changed, or started (switching is a read-side re-scope).
- **Governing requirements:** FR-37, FR-38, FR-01, FR-02, FR-03, FR-10, FR-11,
  FR-12, FR-15.
- **Negative requirements:** none beyond the standing read-only discipline (FR-N1)
  — switching is read-only.

---

## Functional requirements

> Each block uses the standard machine-emittable shape: an ID, a statement, and
> acceptance criteria a builder can write a test against.

### Board (landing)

> **The board is per-Product (FR-37).** A Tenant may have many Products; the board
> shows **one Product's** in-flight changes at a time — the **active Product** — never
> all Products mixed. The four board requirements below (FR-01, FR-02, FR-03, FR-15)
> are therefore read as **"for the active Product"**: each describes the board scoped
> to the currently active Product. This **supersedes the single-implicit-product
> board** the SRD originally described. The product switcher (FR-38) changes which
> Product is active.

**FR-01 — Board lists the active Product's in-flight changes as cards in stage columns**
The app's landing view SHALL render every in-flight change **belonging to the active
Product** (changes roll up Project → Product) as a card, arranged in columns where
each column is one lifecycle stage in order: `recon`, `specify`, `design`,
`implement`, `review`, `ship`. Changes belonging to other Products SHALL NOT appear.
- *Acceptance:* Given Product A with three changes at stages `specify`, `design`,
  `ship`, and Product B with two changes, when Product A is active the board shows A's
  three cards (each in the column matching its stage, in left-to-right stage order)
  and **none** of B's changes.

**FR-02 — Each card shows handle, intent, stage, liveness**
Each card SHALL show the change handle, its one-line intent, its current stage,
and a liveness indicator reflecting whether its session is currently running.
- *Acceptance:* A card for a change whose session is running shows a "running"
  indicator; a card for a change with no running session shows a "not running" (or
  "unknown") indicator; both show handle, intent, and stage.

**FR-03 — Empty board (for the active Product) guides starting a change**
When the **active Product** has no in-flight changes, the board SHALL show an empty
state that tells the founder, in plain English, how to start a change.
- *Acceptance:* With the active Product holding zero in-flight changes, the board
  renders the empty-state guidance and no card grid — even if other Products have
  changes.

**FR-15 — Shipped changes are not shown as in-flight on the board**
Changes in a terminal stage (`shipped`) SHALL NOT appear as in-flight cards in the
six lifecycle columns of the active Product's board. (They remain reachable as audit
history per the existing app, unchanged.)
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

### Chat-driven discovery + setup (cold-start onboarding and start-a-change)

> This whole capability **rides the headless-session bridge already specified**
> (FR-16..FR-26) and **orchestrates the existing discovery skills**
> (`discover-project`, `discover-context`, `codebase-mapping`) and the spine
> emitters (Tenant / Product / Project). It is **not** a new bespoke mechanism
> (EP-03 — reuse, don't reinvent).

**FR-27 — A conversational front door, backed by a headless discovery agent**
The app SHALL provide a chat that is backed by a **headless agent** (a `claude -p`
/ discovery agent) driven over the **same stream bridge** as the two-way chat
(FR-16..FR-26), used for onboarding and for starting changes from intent.
- *Acceptance:* The discovery chat sends prompts and streams replies through the
  same relay path as FR-16/FR-17 (no second, parallel bridge is introduced); a test
  asserts the discovery agent is driven via the existing stream-json bridge.

**FR-28 — Cold-start onboarding discovers and mints the entity graph from a conversation**
When the founder has **no Product / Project minted yet**, the discovery agent SHALL
search the founder's **chosen area** of the machine, ask plain-English clarifying
questions, and — orchestrating `discover-project`, `discover-context`, and
`codebase-mapping` plus the Tenant / Product / Project spine emitters — **discover
and mint** the Tenant / Product / Project entities, so the founder ends with a
populated graph rather than an empty board.
- *Acceptance:* Given an empty graph and a chosen folder containing a recognisable
  repo, the onboarding conversation results in minted Tenant / Product / Project
  entities for that repo; given a chosen folder with nothing recognisable, no entity
  is minted and the agent says so.

**FR-29 — Start a change from plain-English intent**
Once a Product / Project exists, the discovery agent SHALL resolve the founder's
plain-English intent to a **change primitive + slug** (using the existing classifier
and change-primitives vocabulary) and, against the chosen **Project's repo** (mapped
from `Project.source` → `--repo-root`), run `sulis-change start` so a new change is
created and appears on the board at **Recon**.
- *Acceptance:* Given an existing Project and a plain-English intent, the agent
  resolves a primitive + slug and a started change for that Project appears at the
  Recon stage on the board.

**FR-30 — Local-first: the Project's repo must be reachable, else clone first (or fail clearly)**
Before starting a change, the app SHALL ensure the chosen Project's repo is reachable
on the machine. If it is **absent**, the app SHALL **clone it from
`Project.source.repo`** first; if the clone fails, the app SHALL show a clear,
plain-English failure and SHALL NOT start the change.
- *Acceptance:* Given a Project whose repo is not present locally, starting a change
  first clones from `Project.source.repo` and then starts; given a clone that fails,
  the founder sees a visible failure and **no** change is started.

**FR-31 — Discovery is idempotent: no duplicate-entity minting**
When discovery encounters a Tenant / Product / Project that is **already minted**,
the app SHALL surface the existing entity and SHALL NOT create a duplicate.
- *Acceptance:* Running onboarding against an area whose Project is already minted
  results in **zero** new duplicate entities; the existing entity is reused/surfaced.

**FR-32 — Discovery entity writes go through the validated spine emitters**
All entity creation in onboarding SHALL go through the **spine emitters** (the
schema-validated Tenant / Product / Project emitters), never freehand file writes.
- *Acceptance:* Minted entities are produced by the spine emitters and pass their
  schema validation; a test asserts no onboarding path writes an entity file
  directly, bypassing the emitter.

**FR-35 — Onboarding finds-or-creates the Product's repo, branching on whether one exists**
During onboarding, after establishing which Product the founder is working on, the
app SHALL ask **where the repo(s) are** and branch on the answer:
- if the founder has **no repo**, the app SHALL — on the founder's confirmation
  (FR-N6) — **create a new repo** for them (a consequential, possibly-external act
  behind the confirm gate); if creation fails, it SHALL show a clear, plain-English
  failure and SHALL NOT persist a Product/Project config pointing at a non-existent
  repo (FR-N10);
- if the **repos exist**, the app SHALL find/configure them from the founder's
  pointer, searching **only the chosen area** (FR-N7 / NFR-DISC-01), reusing the
  existing discovery skills.
- *Acceptance:* Given a founder with no repo who confirms creation, a new repo is
  created and becomes the Project's `source.repo`; given a founder who points at an
  area with an existing repo, that repo is found and configured without creating a
  new one; given a confirmed creation that fails, the founder sees a visible failure
  and **no** Project config is persisted for that repo.

**FR-36 — Onboarding completes and persists a durable Product/Project config**
On confirmation, onboarding SHALL complete the **Product + Project config** —
including each `Project.source = {repo, path, primary_branch}` for the found-or-created
repo — and **persist it durably** through the validated spine emitters (FR-32), so
that the config survives the session. After onboarding, a subsequent app session
SHALL be able to start a change on that Product **without re-running setup**.
- *Acceptance:* After completing onboarding for Product X, **re-opening the app** (a
  fresh session) and saying *"make a change on Product X"* starts a change against
  X's persisted `Project.source` — with **no** repeat of the discover / ask / confirm
  setup; a test asserts the persisted Tenant/Product/Project (with `Project.source`
  populated) is read back on the next session and drives change-creation directly.

### Concierge: navigation + containment

> The chat front door is a **concierge** modelled on the `sulis:sulis` agent. It
> **coordinates only — it never does the work itself.** It rides the same headless
> bridge (FR-27) and reads through the same seam as every other read surface. Its
> only direct consequential acts are, on the founder's confirm, **minting the setup
> entities** (FR-28) and **creating a change** (FR-29). Everything else — including
> any investigation — is delegated *into* a change. The containment rule below
> (FR-N9) is the load-bearing principle of this capability.

**FR-33 — The concierge answers read-only questions about the founder's world**
Beyond onboarding (FR-28) and starting changes (FR-29), the concierge SHALL answer the
founder's plain-English questions about their existing world — finding changes,
reporting a change's stage and status, and answering questions over the change store +
brain — **read-only**, reaching the same data through the seam (NFR-ARCH-01) as the
board and thread.
- *Acceptance:* Asked *"find the change about the login page"* or *"where's the
  payments change up to?"*, the concierge returns the matching change(s) with stage and
  a plain-English status drawn from the existing store; a test asserts the navigation /
  status / Q&A path performs **zero** writes, mints nothing, starts nothing, and signals
  no session (it is a read-only path, like the board).

**FR-34 — An investigation triggers the creation of a change to contain it**
When the founder asks the concierge to **investigate / explore / look into** something
(real activity, not a read-only lookup), the concierge SHALL NOT do that work inline.
It SHALL resolve the request to an **investigation change** (primitive + slug, via the
existing classifier) and — on the founder's confirmation (FR-N6) — run `sulis-change
start` so the investigation lands on the board as its own change at Recon, with the
exploring then happening inside that change's session (UC-06), not in the concierge.
- *Acceptance:* Asked to *"look into"* something, the concierge proposes an
  investigation change and (on confirm) a new change for it appears at Recon; a test
  asserts the concierge itself performs no investigation work inline — the work path is
  the change's own session, not the concierge turn. A declined proposal starts nothing.

> *Rationale (why investigation is a change, not an inline concierge action):* making
> exploration first-class means every investigation is **audited, self-contained, and
> reusable**. It has its own lineage, worktree, and brain from the start, so if it
> evolves into a build there is no separate hand-off and no lost context. "The change
> is the unit of everything" — extended to investigation.

### Multi-product navigation (per-Product board + switcher)

> A Tenant has one or many Products. The board (and the rest of the per-product views)
> shows **one Product at a time** — the active Product — never all Products mixed.
> This **supersedes the single-implicit-product board**; FR-01/02/03/15 are read "for
> the active Product" (see the note at the head of the Board section).

**FR-37 — The board is scoped to one active Product**
The board SHALL show only the **active Product's** in-flight changes, where a change
belongs to a Product via its Project (Project → Product roll-up). It SHALL NOT show
changes from any other Product. Exactly one Product is active at a time.
- *Acceptance:* With Product A active and Product B also present, the board shows only
  A's in-flight changes; a test asserts that **no** change whose Project rolls up to B
  appears on the board while A is active.

**FR-38 — A product switcher re-scopes the board (and per-product views) to the chosen Product**
The app SHALL provide a **product switcher** that lists the Tenant's Products, marks
the active one, and lets the founder make a different Product active. Switching SHALL
re-scope the board **and** the per-product views (search FR-10, stage filter FR-11,
"needs attention" FR-12) to the newly active Product. Switching is **read-only** — it
changes scope, not data.
- *Acceptance:* Given Products A and B, selecting B in the switcher re-renders the
  board with B's in-flight changes (and A's gone), and a subsequent search/filter
  applies only within B; a test asserts the switch performs **zero** writes, mints
  nothing, and starts/signals no session.
- *Design-stage follow-up:* the switcher's exact placement and visual form are part of
  the whole-surface UX/visual pass (recorded under Design-stage constraints).

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

### Negative requirements (chat-driven discovery + setup)

The discovery agent **reads directories**, **writes entities** (mints Tenant /
Product / Project), and **starts changes** — all consequential. It sits in the same
"agent-driven, founder-confirms" model as the chat: the founder confirms before
anything consequential happens.

**FR-N6 — The discovery agent MUST NOT mint an entity or start a change without the
founder's confirmation.** Minting Tenant / Product / Project and running
`sulis-change start` are consequential acts; each MUST be confirmed by the founder
**before** it happens — the same "ask before consequential" gate as the chat relay.
A discovery turn that only reads and proposes is fine without confirmation; the
**act** of creating is not. (Encodes the confirm-gate behind FR-28, FR-29, FR-30.)
- *Acceptance:* A test asserts that no entity is minted and no change is started until
  an explicit founder confirmation; a declined proposal leaves the graph unchanged.

**FR-N7 — Directory search MUST be bounded to the founder's chosen area.** The
discovery agent MUST search **only** the area of the machine the founder chooses, and
MUST NOT roam the whole disk, the home directory wholesale, or anywhere outside the
chosen area.
- *Acceptance:* A test confirms discovery reads only under the chosen root and does
  not traverse to parent or sibling directories outside it. (See NFR-DISC-01.)

**FR-N10 — Creating a repo MUST be confirmed first, and a failed creation MUST NOT
leave a dangling config.** When the founder has no repo, the agent MUST NOT create one
without explicit founder confirmation (the same gate as minting, FR-N6). If a confirmed
repo creation **fails**, the app MUST surface a clear, plain-English failure and MUST
NOT persist a Product/Project config whose `source.repo` points at a repo that was
never created. (Encodes the repo-create branch of FR-35 as prohibitions.)
- *Acceptance:* A test asserts no repo is created without confirmation; a test asserts
  that a simulated repo-creation failure leaves **no** persisted Project whose `source`
  points at the failed repo (the graph is left as it was before the attempt).

**FR-N11 — Onboarding MUST NOT persist a partial or unconfirmed Product/Project config.**
The Product/Project config (including `Project.source`) MUST be persisted **only** after
the founder confirms and the repo is found-or-created and reachable. A declined or
abandoned onboarding MUST leave the graph unchanged; a config MUST NOT be half-written
(e.g. a Product without its Project's `source`).
- *Acceptance:* A declined onboarding leaves the graph unchanged; a test asserts that
  any persisted Product has a Project with a populated, reachable `source` (no
  half-written config is observable on the next session).

### Negative requirements (concierge containment)

The concierge is a **coordinator, not a worker**. These two prohibitions are the
load-bearing safety of the seventh capability: they keep real activity out of the
concierge turn and inside a change, where it is audited and self-contained.

**FR-N8 — The concierge MUST NOT do the work itself.** The concierge coordinates
only. Its navigation / status / Q&A help (FR-33) MUST be strictly read-only — it MUST
NOT edit code, write to a worktree, run a build, mutate the change store or brain, or
carry out investigation inline. Its **only** direct consequential acts are, on the
founder's confirmation, minting the setup entities (FR-28) and creating a change
(FR-29); every other action is delegated into a change. (This is the concierge form of
the read-only discipline FR-N1 / NFR-SEC-05, extended to the front door.)
- *Acceptance:* A test asserts the concierge's read/navigate/answer path performs no
  worktree write, no build/run, no code edit, and no store/brain mutation; the only
  write paths reachable from the concierge are the FR-28 mint and the FR-29 change
  start, each behind the FR-N6 confirm gate.

**FR-N9 — ALL real activity, including investigation, MUST be contained in a change.**
No real activity — exploring, investigating, building, or any consequential work —
MUST run inline in the concierge. An **investigation** MUST trigger the creation of a
change to contain it (FR-34) rather than running ad-hoc in the concierge turn, so that
all such activity is audited, self-contained, and carries its own lineage / worktree /
brain. The concierge's direct consequential surface is therefore exactly two acts
(mint setup entities; create a change); everything that does work happens inside a
change's own session.
- *Acceptance:* A test asserts that an investigation request results in a change being
  created (after confirmation) and **not** in inline investigation work within the
  concierge; a test asserts there is no concierge code path that performs build,
  edit, or exploration work outside a started change.

---

## Verification Plan

<!-- VERIFICATION_QUESTIONS source: plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md v1.0.0 -->

> Answers to the canonical 20-question set
> (`plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md` v1.0.0). The six
> required subsections (ADR-001) follow. Prior founder-owned items (auto-spawn
> behaviour, "needs attention" rule, chat-search scope, brain grouping) are resolved.
> The seventh capability adds **two genuinely founder-owned questions** that this plan
> does not pre-answer — they are listed in "Founder-owned gaps" at the end of this
> document and do not block the verification posture (each has a safe default
> recorded): (a) how broad the onboarding directory search may roam within the chosen
> area, and (b) whether onboarding mints a single Product or may discover several at
> once.
>
> Two **refinements** are folded into this plan: onboarding now also **finds-or-creates
> the Product's repo and persists a durable Product/Project config** (FR-35, FR-36,
> FR-N10, FR-N11, NFR-DISC-06), and the board is now **per-Product with a product
> switcher** (FR-37, FR-38, UC-11). Both are covered in the sections below; the repo
> find-or-create branch adds **one founder-owned question** (where to create the new
> repo — local-only vs. a hosted remote) with a safe default recorded.

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

And — the **chat front door** (the seventh capability): a founder who opens the app
with **nothing minted yet** is met by a conversation (backed by a behind-the-scenes
discovery agent on the *same* chat bridge) that searches a folder they choose, asks
"is this your product? which repos belong to it?", and — **only after they confirm** —
creates their Product and Project (through the validated emitters, never duplicating
an entity already there, never reading outside the chosen folder). Once that graph
exists, the founder can **say** what they want to work on in plain English and the
app starts the change for them — cloning the Project's repo first if it isn't on the
machine — and the new change shows up at Recon.

And the front door is a **concierge** (modelled on the `sulis:sulis` agent): the
founder can *ask* about their world — "find the change about the login page", "where's
the payments change up to?", "what needs my attention?" — and get a plain-English
answer drawn read-only from the change store + brain, with nothing created or changed.
The concierge **coordinates only — it never does the work itself**. If the founder
asks it to *investigate* or *look into* something, it does not explore inline; it
creates a **change** to contain that investigation (after confirming), so the
exploring happens inside an audited, self-contained change that can evolve straight
into a build. The concierge's only direct consequential acts are minting the setup
entities and creating a change; everything that does real work lives inside a change.

And onboarding now **does the repo setup for the founder**: it asks which Product
they're on, asks where the repo is, and **branches** — no repo? it offers to **create
one** (behind the confirm gate); repos exist? it **finds/configures** them from the
founder's pointer. It then **completes and persists** the Product/Project config (each
`Project.source = {repo, path, primary_branch}`), so the setup is durable: re-open the
app, say "make a change on Product X", and a change starts **without re-running setup**.

And the board is now **per-Product**: a founder with several Products sees **one
Product's** in-flight changes at a time (changes roll up Project → Product), never all
mixed; a **product switcher** changes which Product is active, re-scoping the board and
the per-product views (search, filters, needs-attention) to that Product. This
supersedes the single-implicit-product board.

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
- The **chat-driven discovery** path (FR-27..FR-32) has the same shape: it rides the
  same stream bridge, so it **cannot** fully bootstrap from zero in CI either. The
  search → ask → confirm → mint orchestration and the start-a-change classify → clone
  → start orchestration verify in CI against a **recorded discovery-session bridge
  fixture** plus a **fixture project directory** (a seeded folder with a recognisable
  repo) so search-scope (FR-N7), dedupe (FR-31), validated-emitter writes (FR-32), the
  confirm gate (FR-N6/NFR-DISC-04), and clone-then-start (FR-30) can be exercised
  without a live agent or network clone. The full live path (real discovery agent,
  real mint, real `git clone`, real `sulis-change start`) is verified manually on the
  founder machine. See deferred needs.
- The **repo find-or-create** branch (FR-35) verifies in CI two ways: the
  **repos-exist** branch reuses the fixture project directory above (find/configure a
  seeded repo, no creation); the **no-repo** branch is tested with `git init` into a
  **temp dir** as the local creation target (no network), asserting the confirm gate
  (FR-N10) and that a simulated creation failure persists **no** dangling config
  (FR-N10 / FR-N11). The live hosted-remote creation path (if the founder later chooses
  a hosted remote) is verified manually. See deferred needs.
- The **persisted-config durability** (FR-36 / NFR-DISC-06) verifies from a fresh
  clone with the existing change-store fixtures: mint a Product/Project in one
  test-session, then in a **second** session read it back (with `Project.source`
  populated) and drive change-creation directly — asserting **no** re-discovery and
  **no** new config store. No external credentials.
- The **per-Product board + switcher** (FR-37, FR-38, UC-11) verifies entirely from
  seeded fixtures: seed two Products (each with Projects + changes), assert the board
  shows only the active Product's changes (FR-37), assert switching re-scopes the board
  and the per-product views (FR-38), and assert the switch performs zero writes, mints,
  or session starts. No external credentials, no live agent.

### Per-integration verification strategy

| Integration | Boundary | Strategy | Classification |
|---|---|---|---|
| Change store + brain | In-process port (`ChangeStoreReader`, brain read) | Real via fakes/fixtures in tests; real store on the founder machine | **existing** |
| Claude session bridge (stream-json) | Local process / stdio bridge | Relay + lifecycle logic — including **resume-from-transcript** and **spawn-grounded-in-context** session resolution — tested against a **recorded bridge fixture**; full live path (real resume + real spawn) verified manually on the founder machine | **deferred** (fixture) |
| Headless discovery agent (same stream bridge, FR-27) | Local process / stdio bridge | Search→ask→confirm→mint and classify→clone→start orchestration tested against a **recorded discovery-session bridge fixture** + a **fixture project directory**; full live path verified manually | **deferred** (fixture) |
| Concierge navigation / status / Q&A (FR-33) | In-process read over the seam (same data as board/thread) | Read-only path tested with the existing `FakeChangeStoreReader` + brain fixtures, exactly as the board/thread tests do; assert zero writes, zero mints, zero session starts, zero signals from any concierge read path (FR-N8 / NFR-DISC-05) | **existing** |
| Discovery skills (`discover-project`, `discover-context`, `codebase-mapping`) | In-process / subprocess (existing skills) | Orchestrate the **existing** skills; reuse their existing tests; assert orchestration calls them rather than reimplementing | **existing** |
| Spine emitters (Tenant / Product / Project) | In-process (validated emitters) | Mint via the **existing** schema-validated emitters; assert minted entities pass emitter validation and no path bypasses them (FR-32) | **existing** |
| Project repo (local-first / `git clone`) | Subprocess (`git`) | Reachability check; clone-from-`Project.source.repo` on absence; clone-failure ⇒ visible failure + no change started (FR-30) — tested with a local fixture repo (no network) | **deferred** (fixture) |
| Repo find-or-create (onboarding, FR-35) | Subprocess (`git` / repo host) | Repos-exist branch: find/configure via the discovery skills + fixture project dir. No-repo branch: `git init` into a temp dir as the local creation target (no network), behind the confirm gate (FR-N10); failed-create ⇒ no dangling config (FR-N10 / FR-N11). Live hosted-remote create verified manually | **deferred** (fixture) |
| Persisted Product/Project config (FR-36) | In-process (existing change-store/graph via spine emitters) | Mint then read-back across two test-sessions with `Project.source` populated, driving change-creation with no re-discovery; no new config store (NFR-DISC-06 / NFR-DATA-01) | **existing** |
| Per-Product board scoping + product switcher (FR-37/38) | In-process read over the seam (same data as board) | Seed two Products; assert board shows only the active Product's changes and switching re-scopes board + per-product views; assert the switch performs zero writes/mints/session-starts (read-only re-scope) | **existing** |
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
  track, brain view, previews, search, and chat UI **including the chat front door /
  onboarding conversation UI** (now covering the **repo find-or-create** branch — the
  "do you have a repo?" question and its create-vs-find paths) and the **product
  switcher** (lists Products, marks the active one, re-scopes the board on selection,
  FR-37/38); a11y check (axe-core) on the new surfaces; visual check against the
  design-system tokens (the design stage runs the whole-surface UX/visual pass — see
  Design-stage constraints).
- **`backend`** (ADR-007 row): behavioural API test for the chat relay against a
  running test server, asserting session-to-change binding (FR-21) across live,
  resumed, and spawned sessions; resume-from-transcript (FR-24); spawn-grounded
  (FR-25); incomplete-step-on-resume handling (FR-26 / FR-N5); resume/spawn-acts-on-
  -only-the-targeted-session (NFR-SEC-06); one-in-flight (FR-20); clear-failure
  (FR-19); and the read-only gate including the sanctioned resume/spawn act (FR-N1,
  NFR-ARCH-02). **Plus the chat-driven discovery path:** the discovery agent rides the
  same bridge (FR-27); search bounded to the chosen area (FR-N7 / NFR-DISC-01); no
  duplicate minting (FR-31 / NFR-DISC-02); entity writes via the validated emitters
  (FR-32 / NFR-DISC-03); confirm-before-consequential gate for mint and start (FR-N6 /
  NFR-DISC-04); intent → primitive + slug classification and `sulis-change start` at
  Recon (FR-29); local-first reachability and clone-then-start, with clone-failure ⇒
  no change started (FR-30). **Plus the concierge containment behaviours:** the
  navigation / status / Q&A path is read-only and performs no writes, mints, session
  starts, or signals (FR-33 / FR-N8 / NFR-DISC-05); an investigation request creates a
  change rather than doing the work inline (FR-34 / FR-N9); and the read-only gate
  (`check-read-only.sh`) treats the concierge like every other surface, with the
  **only** sanctioned write paths reachable from it being the FR-28 mint and the FR-29
  change start, both behind the FR-N6 confirm gate (FR-N8, FR-N9, NFR-DISC-05).
  **Plus the onboarding repo find-or-create + persistence behaviours:** the
  find-or-create branch (FR-35) — repos-exist (find/configure, bounded to the chosen
  area) and no-repo (confirmed create, FR-N10) — with a failed create persisting no
  dangling config (FR-N10 / FR-N11); and the **durable config round-trip** (FR-36 /
  NFR-DISC-06) — mint in one session, read back `Project.source` in a fresh session,
  start a change with no re-setup, no new config store. **Plus the per-Product board
  behaviours:** the board is scoped to one active Product and shows no other Product's
  changes (FR-37), and the product switcher re-scopes the board and per-product views
  while performing zero writes/mints/session-starts (FR-38). Concrete artifacts named
  at design time.

### Infrastructure needs surfaced (deferred)

- `recording-bridge-claude-session` — a recorded/replayable stream-json session so
  the chat relay + lifecycle can be verified in CI without a live agent. The fixture
  set MUST cover all three session-resolution paths: live, **resume-from-transcript**,
  and **spawn-grounded-in-context**, plus a transcript that ends mid-step (to verify
  FR-26 / FR-N5).
- `seed-brain-entities-fixture` — fixture brain entities for a change so the brain
  view (FR-06/07) can be verified from a fresh clone.
- `recording-bridge-discovery-session` — a recorded/replayable discovery-session
  stream-json fixture (mirroring `recording-bridge-claude-session`) so the chat-driven
  discovery path (FR-27..FR-32) can be verified in CI without a live agent. It MUST
  cover the onboarding orchestration (search → ask → confirm → mint) and the
  start-a-change orchestration (classify → clone → start).
- `fixture-project-directory` — a seeded local folder containing a recognisable repo
  (and an "already-minted" variant) so search-scope (FR-N7), dedupe (FR-31), and the
  discovery skills' orchestration can be exercised from a fresh clone.
- `fixture-local-repo-for-clone` — a local git repo usable as a `Project.source.repo`
  clone target (and a deliberately-broken variant) so local-first clone-then-start and
  clone-failure behaviour (FR-30) verify without network access.
- `fixture-repo-create-target` — a writable temp dir as the **local** repo-creation
  target for the onboarding no-repo branch (`git init`, no network) plus a
  deliberately-failing variant, so the confirm-gated create (FR-35 / FR-N10) and the
  no-dangling-config-on-failure rule (FR-N10 / FR-N11) verify in CI. The live
  **hosted-remote** create path (chosen by the founder at design time) is verified
  manually on the founder machine.

---

## Diagrams

- Board → thread navigation: `diagrams/board-navigation.md`
- Two-way chat send/stream flow: `diagrams/chat-flow.md`
- Chat-driven discovery → mint → start-a-change flow: `diagrams/discovery-flow.md`

---

## Founder-owned gaps (open questions — safe default recorded)

These are calls only the founder can make. Each has a **safe default** so the spec is
complete and verification passes; confirm or change them at the design stage.

1. **How broad may the onboarding search roam within the chosen folder?** The search
   is bounded to the chosen area (FR-N7 / NFR-DISC-01) — that part is settled. Open:
   *within* that area, how deep / how wide? E.g. "just this folder and one level down"
   vs. "everything recursively under it".
   - *Safe default (recorded):* search **recursively under the chosen folder only**,
     skipping the usual noise (`node_modules`, `.git`, `vendor`, build output — the
     same skip-list `codebase-mapping` already uses). Confirm or narrow.

2. **Does onboarding mint a single Product, or may it discover several at once?** A
   chosen folder might contain one product or many.
   - *Safe default (recorded):* discover and confirm **one Product per onboarding
     conversation** (with one or more Projects under it). Discovering multiple Products
     in a single pass is deferred unless the founder wants it now.

3. **When onboarding creates a new repo (no-repo branch), where does it create it?**
   Either a **local-only** git repo on the founder's machine, or a repo on a **hosted
   remote** (e.g. GitHub) under the founder's account.
   - *Safe default (recorded):* create a **local-only** git repo (`git init`) in the
     founder's chosen area — no external account, no network, nothing published. If the
     founder later wants a hosted remote, that is an additional, separately-confirmed
     step at the design stage. (The local default keeps the consequential act fully
     reversible and avoids needing the founder's hosting credentials in this slice.)

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
- **Discovery rides the existing bridge (EP-03):** the chat front door (FR-27) reuses
  the same stream-json relay/port as the two-way chat — no second bridge. The headless
  discovery agent is `claude -p` driven over that same path.
- **Discovery orchestrates, doesn't reimplement:** onboarding calls the existing
  `discover-project`, `discover-context`, and `codebase-mapping` skills and the
  existing Tenant/Product/Project spine emitters. The classifier for intent →
  primitive is the existing `_specify_classifier` + change-primitives vocabulary.
- **`Project.source` → `--repo-root` mapping:** the app reads the Project entity's
  `source = {repo, path, primary_branch}` and maps it to the `--repo-root` that
  `sulis-change start` expects. Mechanics (exact field plumbing) are a design-stage
  concern.
- **Confirm gate reuses the chat's "ask before consequential" model:** mint and
  start go through the same confirm discipline as the chat relay (FR-N6 / NFR-DISC-04),
  not a new bespoke approval mechanism.
