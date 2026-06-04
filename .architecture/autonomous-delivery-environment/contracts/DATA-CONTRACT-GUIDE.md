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

Of the requests below, **only three can _do_ anything** — and each one asks
you to confirm first. Everything else only _reads_. The three doers are:
sending a chat message, setting yourself up the first time (onboarding), and
starting a new piece of work from something you typed. Each of those three
**asks before it creates anything**. Every other request only reads. That is
the safety line for this whole change.

## The requests, one per thing you see

| What you see | What the app asks for | Can it change anything? |
|---|---|---|
| **The board** of your changes in stage columns | "Give me all my changes, with their stage and whether their agent is running." | No — read only |
| **A change's progress** (the plain-English "here's what's happening") | "For this change, work out a plain-English status right now." | No — read only |
| **The brain** (the things the agent made for a change) | "List the building blocks created for this change, grouped." | No — read only |
| **Reading a document** (rendered, with a raw toggle) | (uses the existing file + contract-preview requests — nothing new) | No — read only |
| **Search and filter** | "Find changes whose content matches this text; narrow to this stage; or to the ones needing attention." | No — read only |
| **Sending a chat message** | "Send this message to this change's agent and stream the reply back to me." | **Yes — asks nothing extra; it's a message** |
| **Switching which product you're looking at** | "Show me this product's work instead." | No — read only (it just changes what you see) |
| **Seeing your products** | "List my products and mark the one I'm looking at." | No — read only |
| **Asking the concierge a question** | "Find the change about the login page / where's the payments change up to? / what needs my attention?" | No — read only (it looks things up and tells you) |
| **Getting set up the first time (onboarding)** | "Look in this folder, figure out my product and where my code is, and — once I say yes — create my product and project." | **Yes — but only after you confirm** |
| **Starting work from something you typed** | "I want to fix the hanging login page — turn that into a new piece of work." | **Yes — but only after you confirm** |

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

## The front door that sets you up (the careful bits, again)

The very first time you open the app there's nothing there yet. So instead of
a form you can't fill in, a **conversation** does the setup for you. Here's
what it will and won't do:

- It **only looks where you point it.** You choose a folder; it reads inside
  that folder and nowhere else — not your whole disk, not your home folder.
- It **asks before it creates anything.** It shows you, in plain English, the
  product and project it's about to set up — and waits for your yes.
- **No code yet? It makes a repo for you.** By default that's a plain repo on
  your own machine — nothing published anywhere, nothing that needs a GitHub
  login. (This is the one new thing that's genuinely your call — see below.)
- **If anything fails, it leaves nothing behind.** If making the repo fails,
  you get a clear message and your setup is left exactly as it was — no
  half-finished product sitting around.
- It **remembers your setup.** Next time you open the app you can just say
  "make a change on Product X" and it starts — no setup again.

And the concierge (the question-answerer) **never does the work itself.** If
you ask it to *look into* something, it doesn't go poke around on its own — it
creates a proper piece of work to hold that investigation (after asking you),
so everything is tracked and nothing gets lost. The only things it ever
*does*, as opposed to *reads*, are setting you up and starting a piece of
work — and both of those ask you first.

## The question for you

Read the tables and the "needs attention" definition. The things that are
genuinely yours to confirm:

1. Is **"needs attention" = blocked / waiting-on-you / stopped-mid-reply**
   the right set, or do you also want "idle too long"?
2. Is **search-over-content** (it searches inside the conversation and the
   created items, not just titles) what you expect?
3. **When the app makes a new repo for you, where should it live?** The safe
   default is **a plain repo on your own machine** — nothing published, no
   GitHub login needed, and easy to undo. The alternative is creating it on
   **GitHub (or similar) under your account**, which puts your code online and
   needs your GitHub login. Is the on-your-machine default right, or would you
   rather it go straight to GitHub?

Everything else here is the boring, standard way to build it — no decision
needed from you.
