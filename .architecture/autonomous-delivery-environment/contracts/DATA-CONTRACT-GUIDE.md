# What the app asks the server for — in plain English

> This is your review of the "data contract": the small set of requests the
> app makes to its own little server to get everything on screen. You don't
> need to read code — read this. The exact technical version is next to this
> file (`openapi.yaml`) for the builder; this page is for you to sign off.

## The one rule that matters

The app **only ever talks to the server** to get or do anything. It never
reaches into files on your disk by itself. That single doorway is what lets
the same app run on your laptop today and, much later, from the cloud —
with no rebuild. Everything below goes through that one doorway.

Of all the requests below, **only one can _do_ anything** — sending a chat
message. Every other request only _reads_. That is the safety line for this
whole change.

## The requests, one per thing you see

| What you see | What the app asks for | Can it change anything? |
|---|---|---|
| **The board** of your changes in stage columns | "Give me all my changes, with their stage and whether their agent is running." | No — read only |
| **A change's progress** (the plain-English "here's what's happening") | "For this change, work out a plain-English status right now." | No — read only |
| **The brain** (the things the agent made for a change) | "List the building blocks created for this change, grouped." | No — read only |
| **Reading a document** (rendered, with a raw toggle) | (uses the existing file + contract-preview requests — nothing new) | No — read only |
| **Search and filter** | "Find changes whose content matches this text; narrow to this stage; or to the ones needing attention." | No — read only |
| **Sending a chat message** | "Send this message to this change's agent and stream the reply back to me." | **Yes — this is the only one** |

## What "needs attention" means (so we agree on it)

When you filter to "needs attention", a change shows up only if it is one of:

- **blocked**, or
- **waiting on a decision from you**, or
- its **agent stopped in the middle of replying**.

A change that's just sitting idle but otherwise fine is **not** flagged.
(If you'd want idle-too-long flagged as well, that's a change to make now.)

## What happens when you send a message (the careful bit)

You type a message to a change and hit send. Behind the doorway, the server:

1. **Finds the right agent for that change** — and never asks you to pick:
   - if that change's agent is already running, it uses it;
   - if it ran before and stopped, it **wakes it up** from where it left
     off (it remembers the whole conversation);
   - if it never ran, it **starts a fresh one** that first reads up on the
     change so it isn't starting blind.
2. **Double-checks it's the right agent** before sending a single word — if
   it can't be sure the agent belongs to *this* change, it refuses and
   sends nothing.
3. **Streams the reply back live**, word by word, the way you'd expect.

Three things it will tell you plainly instead of failing silently:

- **"Busy"** — if a reply is already coming back for this change, it won't
  let you send a second one until the first finishes.
- **"Couldn't start"** — if it genuinely can't wake or start the agent,
  it says so, and your message is **not** marked as sent.
- **"Interrupted"** — if the reply gets cut off partway, it keeps the part
  that arrived and marks it interrupted, rather than pretending it finished.

And one honesty guarantee: if the agent was woken up after stopping mid-task,
it will **redo** the unfinished step rather than pretend it already did it —
and you'll see that the change was resumed.

## The question for you

Read the table and the "needs attention" definition. The only things that
are genuinely yours to confirm:

1. Is **"needs attention" = blocked / waiting-on-you / stopped-mid-reply**
   the right set, or do you also want "idle too long"?
2. Is **search-over-content** (it searches inside the conversation and the
   created items, not just titles) what you expect?

Everything else here is the boring, standard way to build it — no decision
needed from you.
