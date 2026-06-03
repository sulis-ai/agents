---
name: retro
description: "Run at the end of a session to capture what got in the way — friction, steers, missing context — and route each finding to where it'll actually get acted on."
related_skills:
  - related_to: capture-lessons   # change-grain sibling (this is session-grain)
  - related_to: resolve-lessons
  - related_to: feedback
---

# /sulis:retro — the session retrospective

## Conclusion (lead with the answer)

At the end of a session, surface what got in the way and **route every finding
to a durable home** — a task, a watchlist entry, brain-context, or a candidate
standard change. The spine is **surface → classify → route, not journal.** A
retro that ends in prose evaporates (the exact "ideas get lost" problem the
capture path exists to kill); one that ends in *acted-on dispositions*
compounds across sessions.

This is the **session-grain** funnel in the capture hierarchy: it feeds
`capture-lessons` (change-grain), the watchlist (pattern-grain), and the
idea-backlog (idea-grain). It is run by the founder/operator, in plain English.

## The four acts

Run in order. Acts 1–3 surface; act 4 self-attacks; then route everything.

### 1. Extract the steers FIRST (the highest-signal, most objective input)
> Standards: CRITICAL_THINKING_STANDARD.md (BI — balanced investigation; AT — adversarial posture)

Scan the session for **every moment the user corrected, steered, stopped, or
pushed back** on you. These aren't subjective ("how did it feel") — they're
things the user actually said, so they're objective signal. For each:
- what you'd defaulted to,
- what they redirected to,
- **why your default was off** (the load-bearing part).

A steer almost always means a default or a piece of judgment was wrong — that's
the calibration gold.

### 2. Framework friction (the diagnostic)
Where did the tooling or process **get in the way** — a bug, a papercut, a
dead-end, a false-green, anything that cost a re-do? For each, tag **one-off**
or **recurring** (recurring is the signal that matters).

### 3. Missing context (the brain-feed)
What did you **not know, have to discover, or get wrong for lack of context** —
that should live in the brain so the *next* session starts with it? This is the
context that changes future *decisions* (read by the agent), distinct from a
bug a human fixes.

### 4. The open probe (the blind-spot question)
> Standards: CRITICAL_THINKING_STANDARD.md (FR — falsifiability; AT-01 self-attack)

Answer honestly, even when it's uncomfortable:
- What should the user know that **they didn't ask**?
- What did they ask that they **shouldn't have had to**?
- What are you **least sure you got right** this session?

This is the generative act — it catches what the structured buckets missed.

## Route everything (the point)
> Standards: COACHING_STANDARD.md (structural-not-personal), TONE_STANDARD.md (no hyperbole), founder-facing-conventions.md (FE-06, no operator jargon)

Each finding gets a disposition and is **acted on**, not just listed:

| Finding | Route | Mechanism |
|---|---|---|
| Trivial, known fix | **fix now** | do it (CW-05) |
| Not-trivial bug / gap | **task** | `TaskCreate` |
| Recurring judgment failure | **watchlist** | a `label:watching` issue; **2nd observed strike → propose the structural fix** (the watchlist rule) |
| Actionable lesson for a human | **lesson** | `/sulis:capture-lessons` (issue + digest) |
| Missing *decision* context | **brain** | the idea-backlog (a `Lesson`-shaped entry) until the `Lesson` entity is minted — write it somewhere real, never nowhere |
| A wrong default | **proposed change** | name the candidate standard / agent-body change |

Output as the routed list — **Already-fixed / Tasked / Watchlisted / Lessons /
Brain-context / Proposed-change** — plus the open-probe answer. Triage, don't
yak-shave (one-off ≠ pattern) and don't hoard (every kept finding has a home).

## When to invoke

- At the **end of a working session** (the natural use).
- After a session that **felt friction-heavy** — lots of steering, re-dos, or
  dead-ends — while it's fresh.
- When the user asks to "capture learnings / what got in the way / a retro."

## When NOT to invoke

- **Mid-session** — the steers aren't complete yet; wait for the end.
- For a **change's** lessons specifically — that's `/sulis:capture-lessons`
  (change-grain, fires at ship). This is session-grain (spans changes).
- To file **product feedback** to the open-source repo — that's
  `/sulis:feedback`.
- As a **status report** — `/sulis:status` / `/sulis:dashboard` show in-flight
  work; retro is reflective, not a state dump.

## Gotchas

1. **Journaling instead of routing** (the #1 failure). A finding with no
   disposition is lost. Every kept finding routes or it didn't happen.
2. **Self-congratulation.** Keep "got right" short + factual; the value is in
   friction / steers / gaps. A glowing self-review is where retros go to die.
3. **Operator-jargon leak** (MUC-F1). The output is founder-facing — strip
   internal IDs / tool names from what the user reads (FE-06).
4. **Yak-shaving.** Don't fix everything surfaced; triage one-off vs pattern
   (the watchlist 2-strikes gate decides what earns a structural fix).
5. **Speculative findings.** Only real session signals — the steers (act 1)
   are objective because the user said them; don't invent friction to look
   thorough (NH / honest-uncertainty).
6. **Overwhelm** (MUC-F4). If there are many findings, lead with the routed
   *summary* (counts per disposition), not a wall of items.
7. **The brain-context slot writing nowhere.** Until the `Lesson` entity is
   minted, missing-context findings go to the idea-backlog — a real place,
   never a void. (Queued: the `Lesson` entity upgrade.)

## Vocabulary

- **Steer** — a moment the user corrected / stopped / redirected the agent; the
  retro's highest-signal input.
- **Routing** — assigning each finding a disposition + acting on it (the spine).
- **Brain-context** — a missing-context finding meant for the *agent* to read
  at decision-time (distinct from a lesson a *human* actions).
- **The open probe** — act 4's self-attacking question surfacing blind spots.
- **Session-grain** — the retro's scope (a whole session, spanning changes) —
  vs change-grain (`capture-lessons`) / pattern-grain (watchlist) / idea-grain
  (backlog).

## See also
- `/sulis:capture-lessons` — change-grain sibling (issues + digest at ship).
- The watchlist (`gh issue list --repo sulis-ai/agents --search "label:watching is:open"`) — pattern-grain; the retro feeds it.
- `../../references/founder-facing-conventions.md`, `standards/COACHING_STANDARD.md`, `standards/TONE_STANDARD.md` — the output discipline.
