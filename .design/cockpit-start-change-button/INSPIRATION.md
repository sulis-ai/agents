# Inspiration board — "Start something new" journey (cockpit)

Curated from Mobbin (web) for the start-a-change entry point + journey.
Each entry: what to steal, what to avoid. Open the links on Mobbin for the
full screen sets.

## A. Describe-it → clarify → confirm → start (the gold pattern)

**Base44 — "Planning with AI"** · [flow](https://mobbin.com/flows/be92c8ba-95ad-49c8-876f-09ad12f259c3)
- Hero line: **"What will you build next?"** + a large free-text box
  ("Describe the app you want to create…") with a **Plan** affordance and a
  send arrow.
- **Suggestion chips** under the box ("Health & Wellness", "Dev Productivity",
  "CRM"…) to seed people who don't know where to start.
- Then a **clarifying Q&A** rendered as a chat: stepper "1/3", radio options +
  "Something else" free text, **Skip / Next**. An optional "add ideas,
  constraints, pivots" composer.
- Ends on a **summary card** ("Core Flows / Technical Requirements / Design
  Preferences") with a single **Start Building** button — the confirm gate.
- *Steal:* the describe → clarify → summary → one confirm arc; chips for cold
  start; the explicit "this will start the build" moment.
- *Avoid:* too many clarifying steps before anything happens.

**Notion — inline AI write/command** · [flow](https://mobbin.com/flows/8da206a6-57e1-4352-99f7-804cf8cba7c6)
- *Steal:* "Press space for AI, / for commands" — discoverable inline entry,
  streamed result with Try again / Stop.

## B. Lightweight create-from-top-bar (name + describe modal)

- **v0 — "Create a new project"** · [flow](https://mobbin.com/flows/6bcfbabd-7134-49a7-8b55-ce9ffeb810a2) — top-bar-triggered modal, single Name field + Create. Minimal friction.
- **Claude — "Create a project"** · [flow](https://mobbin.com/flows/68a600aa-4032-45ba-a462-5459cefc6500) — Name + "What are you trying to achieve?" describe field, with a "what is this?" helper.
- **ChatGPT — "Create a project"** · [flow](https://mobbin.com/flows/48f02d90-8549-4704-9b72-f707cfe24960) — tiny "Project name" modal, then a landing with "Add files / Add instructions".
- **Felt — "Create a new project"** · [flow](https://mobbin.com/flows/ed03afc1-abec-440e-9188-7c00c47e9f64) — full-page create (name + access) + a **Welcome get-started card row** (30-sec videos) on first entry.
- *Steal:* the modal is fine for "name + one line of intent"; Felt's welcome
  cards are a good empty-state for first-timers.
- *Avoid:* a bare name-only modal — our start carries *intent*, not just a name.

## C. Top-bar / command-palette entry points

- **Replit** · [screen](https://mobbin.com/screens/1817a08e-f7da-44f9-b1f4-8a903aefa5fa) — prominent **"+ Create App"** top-left above nav + a "Run a command" palette. Clear primary action.
- **Jasper** · [screen](https://mobbin.com/screens/f7c97ebf-4741-4e40-8d7f-f1802b28c216) — **"Welcome Alex, what do you want to work on?"** + ask box + three cards (Create a Project / Discover Apps / Create an App). Good "one front door, a few clear branches" model.
- **Google AI Studio** · [screen](https://mobbin.com/screens/d3212a1c-a0f1-49fb-835c-737c0117c3bd) — one input "Start a chat or vibe code an app" with a **slash menu** (/build /chat /key) — collapses many entry points into one box.
- **Linear** · [screen](https://mobbin.com/screens/8a6d227b-63e6-483c-925f-d256d0989a10) — the canonical ⌘K command palette ("Type a command or search").
- **Todoist** · [screen](https://mobbin.com/screens/4121eb20-aa88-4eef-9cc2-dfa7c4ccb4fa) — ⌘K palette with recents + navigation; **"+ Add task"** always-visible top-left.
- **Figma** · [screen](https://mobbin.com/screens/4347351c-56e3-48a4-9e2d-fa90ff48008d) — "What do you want to make?" + chips, minimal canvas.
- **Fibery** · [screen](https://mobbin.com/screens/d868ebec-3f34-4390-b8ae-73ed3d956de4) — ">>" / "/" inline command surfaces.
- *Steal:* one obvious primary action (Replit "+ Create App", Todoist "+ Add
  task"); the slash/⌘K palette as the power-user accelerant to the *same*
  destination.
- *Avoid:* multiple competing primary buttons — pick one front door, make the
  others accelerants to it.

## Cross-cutting takeaways

1. **One front door, clear accelerants.** A single obvious "start" action (the
   top-bar button), with the palette / slash-command as a faster route to the
   *same* flow — not a parallel one.
2. **Intent-first, not form-first.** Lead with "what do you want to do?" in
   plain language; classify behind the scenes; keep naming/structure light.
3. **Always end on one confirm.** Show what will happen, then a single
   start button. Matches the cockpit's existing confirm-before-start gate.
4. **Cold-start help.** Chips / examples / a welcome card for the first-timer
   who faces an empty box.

---

## D. The post-start landing (decided: coach in the cockpit chat, terminal opt-in)

**Founder decision:** after "Start this work," the founder lands in the
**cockpit's own chat** and is coached there by the change-bound Sulis agent.
The terminal is **not** auto-spawned — it becomes an opt-in surface revealed by
a **terminal icon**, or from inside the change. Chat is primary; terminal is the
power-user escape hatch.

### Coaching chat docked alongside the work
- **ClickUp (Brain)** · [screen](https://mobbin.com/screens/eee7da65-c3d6-49a3-8b32-0cf3d64e5730) — AI chat **docked on the right** beside the main workspace, "Tell AI what to do next" composer. Good model for chat-as-primary-coach next to the change.
- **WRITER** · [screen](https://mobbin.com/screens/7e69890a-f8b8-4fb6-905a-fdfb88960cf8) — "Hi Alex, how can I help you today?" session with a + menu of capabilities.
- **Sana AI** · [screen](https://mobbin.com/screens/bb8ca2ad-dfef-4929-a56a-52771f782ae3) — assistant streams a worked plan, then a composer to act on it.
- *Steal:* a calm, docked coach conversation that *is* the main surface for a change; clear "what next" composer; streamed replies.
- *Avoid:* making the chat a cramped sidebar — for a change, the coached conversation deserves the main stage.

### Terminal as an opt-in panel behind an icon
- **GitHub Codespaces** · [screen](https://mobbin.com/screens/baa262af-1957-4871-a3e5-9a296c08c034) — terminal is a **bottom panel tab** (Problems/Output/Terminal), hidden by default, toggled with ⌘J. The canonical "terminal exists but isn't in your face" pattern.
- **Udemy workspace** · [screen](https://mobbin.com/screens/c8cb5e22-6500-419d-aa91-9ca8f3b29b7d) — Terminal panel with explicit expand / close icons.
- **AWS CloudShell** · [screen](https://mobbin.com/screens/f2f7832e-9d56-4619-853f-6d8b1794f5d9) — console slides up from the bottom via an icon; closable.
- **PlanetScale Console** · [screen](https://mobbin.com/screens/a1fa1590-52b6-4554-b83c-03e998fe6537) — full-surface console reached from a left-nav "Console" item, scoped to a branch.
- *Steal:* a clear terminal **icon/affordance** that opens a dockable, closable panel; scope it to the change (Codespaces/PlanetScale). Default closed.
- *Avoid:* auto-spawning the terminal or making it compete with the chat.

### Takeaway for the landing
**Chat is the room; terminal is a drawer.** Landing = the change's coached chat
on the main stage. A single terminal icon (with a keyboard toggle like ⌘J)
opens the terminal as a closable panel for those who want the raw session.
Same change, same agent — two views of it, chat first.
