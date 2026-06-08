# Start something new — the cockpit journey

The experience a founder walks through to begin a new piece of work, from
"I want to do something" to "a new piece of work has started" — ending at the
hand-off into the change's workspace.

**Scope:** this journey covers only the **start flow** — the front door, the
intent screen, the light clarify step, the confirm-before-start gate, and the
"Starting…" / error states. It ends the moment the change is created and the
founder lands in their change's **existing workspace** (the coaching chat,
terminal, stages and files view the cockpit already has). That in-change
experience is **out of scope here and is not redesigned** — the founder is happy
with it as it is.

Open `MOCKUP.html` in a browser to see every state rendered with the cockpit's
real colours and fonts.

---

## The one decision: a single front door

There are several places a "start" could live — a top-bar button, the concierge
chat, onboarding, a dedicated screen. Four competing buttons would leave the
founder unsure which one is *the* way to start.

**The front door is one primary action: a "Start something new" button at the
top of the changes sidebar.** It is the only blue button in the whole workspace,
so it reads, instantly, as *the* way to begin. Everything else is an accelerant
to the **same** flow, never a parallel one:

- **⌘N / ⌘K → "Start something new"** — keyboard users and power users get there
  faster, but land on the identical intent screen.
- **The cold-start workspace** — when there's no work yet, the empty workspace
  itself shows the intent box, so a first-timer doesn't have to hunt for the
  button.
- **The concierge chat** (existing/future) — if the founder just starts typing
  what they want, it routes into this same describe → clarify → confirm arc.

One destination, several roads in. (Cross-cutting takeaway #1; Replit's single
"+ Create App", Todoist's always-visible "+ Add task".)

---

## The steps a founder walks through

### 1. The front door — "Start something new"
A blue pill button pinned to the top of the sidebar, above the list of changes.
Always visible, always the same place. Carries a quiet `⌘N` hint so the shortcut
is discoverable without shouting.

*Why:* one obvious primary action removes the "where do I even begin?" question.

### 2. The intent screen — "What do you want to do?"
Clicking it opens a focused screen with a big hero question and one large
free-text box: *"Describe it in your own words."* Not a form. Not a name field.
Just intent, in plain English, with a reassurance that Sulis figures out the
rest and that **nothing happens until they confirm.**

*Why:* intent-first, not form-first (takeaway #2). Founders think in outcomes
("let people reset their password"), not in project names or work types. We
classify behind the scenes.

*Cold start:* if it's their first time, the same screen adds **suggestion chips**
("Fix something that's broken", "Add a new feature", "I'm not sure yet") and two
soft welcome cards (a 60-second tour, a worked example). The empty box never
feels like a blank wall.

### 3. Clarify — one short, skippable step
Sulis reflects the intent back ("Got it — a self-service password reset") and
asks at most one or two light questions to scope it right, shown as a friendly
chat with a "Step 1 of 2" stepper so the founder can see it's short. **Skip is
always available** — clarification speeds things up, it never blocks the path.

*Why:* a little clarity up front means the right work gets started, but too many
questions before anything happens kills momentum. We deliberately cap this.

### 4. Confirm before start — the single gate
One summary card: the title Sulis chose, a plain-English line on what it'll do,
the kind of work it is, and the note that a fresh, separate workspace is created.
Then **one green "Start this work" button**, with the reassurance "Nothing
changes until you start."

*Why:* always end on one confirm (takeaway #3). The founder sees exactly what
they're committing to before anything is created — and it matches the cockpit's
existing confirm-before-start gate.

### 5. Starting… and the honest error
A brief progress moment while the workspace is created. If it can't start (a
name clash, the engine busy), the founder gets a plain-language message and a
single retry or rename — never a dead end or a raw error.

*Why:* the three states every surface must handle — the normal path, the empty
(cold start) path, and the error path — are all designed, not left to chance.

---

## After start — the hand-off (out of scope)

The journey ends at "Starting…". The moment the workspace is ready, the founder
**lands in their change's existing workspace** — the coaching chat, terminal,
stages and files view the cockpit already has, unchanged.

That in-change experience is deliberately **out of scope for this journey** and
is **not redesigned here.** The mockup marks the hand-off with a plain "existing
change experience — unchanged" placeholder, not a design.

---

## Which Mobbin references informed each part

| Part of the journey | Reference (from INSPIRATION.md) | What we took |
|---|---|---|
| The whole describe → clarify → confirm → start arc | **Base44 "Planning with AI"** | The hero question + big box, the clarifying Q&A, the summary-then-one-confirm gate. We trimmed the clarify to keep it short. |
| Cold-start chips + welcome cards | **Base44** (chips) · **Felt "Create a new project"** (welcome cards) | Seeds for the founder who faces an empty box. |
| One obvious primary action | **Replit "+ Create App"** · **Todoist "+ Add task"** | A single, always-visible primary button as the front door. |
| ⌘K / ⌘N as the accelerant | **Linear command palette** · **Todoist ⌘K (recents + nav)** | A faster route to the *same* flow, with recents below the start action. |
| Intent box collapses many entry points | **Google AI Studio** · **Jasper "what do you want to work on?"** | One input that absorbs the many possible "start" intents. |
| Light describe field, not a bare name | **Claude "Create a project"** | Intent carries meaning, not just a name (we explicitly avoided v0's name-only modal). |

Structure transferred from these references; every colour and font stays the
cockpit's own. The Mobbin screens shaped the *shape* of the flow, not its look.

> The in-change experience (coaching chat, terminal, stages, files view) is out
> of scope for this journey and is **not** designed here. INSPIRATION.md §D
> retains some references about post-start landings as a general reference board,
> but this journey does not propose any design for those existing surfaces.

---

## Grounded in the real tokens

The mockup uses the cockpit's actual design tokens (`tokens.css`, v4.2.0) — no
invented colours, spacing, or radii:

- **Front door & continue buttons:** `--primary` (#2563EB) pill (`--radius-button`).
- **The start gate:** `--positive` (#16A34A) green — "go".
- **Eyebrows, links, focus accents:** `--accent` (#2D7D90).
- **Errors:** `--destructive` (#DC2626).
- **Surfaces:** `--card` on `--background`; sidebar on `--muted`; 4px container radius.
- **Type:** Inter (body/UI) and JetBrains Mono (branch names / shortcuts) — the
  exact webfonts the live cockpit loads.

> **Note on fonts:** the type token `--font-display` references *Satoshi*, but
> the live cockpit does **not** load Satoshi today (only Inter + JetBrains Mono).
> The mockup therefore renders display text in Inter — what the founder will
> actually see. If Satoshi is wanted for headings, it needs adding to the font
> loader; that's a separate token/build decision to flag, not something to fake
> in the mockup.

---

## Accessibility (checked against the real tokens)

**Keyboard & focus**
- Every interactive element is reachable by Tab and shows a visible focus ring
  (`--ring`, 2px offset).
- `⌘N` opens the start flow; `⌘K` opens the palette; the intent box takes focus
  automatically when the screen opens.
- In the composer, ⏎ continues and Shift+⏎ adds a line — stated inline.
- Clarify options are real radio controls (arrow-key navigable); Skip is a
  first-class button, not a hidden link.

**Colour contrast (WCAG 2.1 AA, measured on the real tokens)**

| Pair | Ratio | Verdict |
|---|---|---|
| Body text on background (#171717 / #fafafa) | 17.18:1 | PASS |
| Text on card (#171717 / #fff) | 17.93:1 | PASS |
| Primary button label (#fff / #2563EB) | 5.17:1 | PASS |
| Accent eyebrow on card (#2D7D90 / #fff) | 4.72:1 | PASS |
| Error text on card (#DC2626 / #fff) | 4.83:1 | PASS |
| Muted text on background (#737373 / #fafafa) | 4.54:1 | PASS |

**Two things to verify at build (honest flags, not blockers):**

1. **The green "Start this work" button** — white on `--positive` is **3.30:1**.
   That passes AA only for *large* text. Keep the label at 16px+ or 14px bold so
   it qualifies, or darken the green slightly. Worth confirming on the real
   button.
2. **Muted text on the muted sidebar** (#737373 on #f5f5f5) is **4.35:1** — just
   under AA for small body text. We only use that pairing for large uppercase
   labels and placeholders (which is fine); muted text used as readable copy sits
   on `--background` instead (4.54:1, passes).

**Colour independence**
- Live/idle change dots are backed by a text label ("live" / "idle"), never
  colour alone.
- The start gate doesn't rely on green alone — it's labelled "Start this work"
  with a clear summary above it.
- Errors carry text and an icon-free plain message, not just a red border.

**Cognitive load**
- Never more than a handful of choices at any step; the clarify caps at one or
  two questions and is skippable.
- The journey is staged (describe → clarify → confirm) so the founder holds one
  idea at a time, not the whole thing at once.
- Every element earns its place — no decorative chrome; the one blue button and
  the one green button carry the two decisions that matter.
