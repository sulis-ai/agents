# Cockpit board refresh — ideas

Three things the founder asked about, each with the options I weighed, what I'd
pick, and why. Everything here is built on the board's *real* colours, fonts and
spacing (`apps/cockpit/client/src/tokens.css`) — nothing invented. Compare the
mockup (`MOCKUP.html`) against the current board (`board-current.png`).

A quick orientation first, because it shapes every recommendation: the board is
six lanes the work flows through left-to-right — Recon → Specify → Design →
Implement → Review → Ship. The lane a card sits in already tells you its stage.
So the guiding principle throughout is: **let the lane do its job, and only put
things on the card that the lane can't already tell you.**

---

## Concern 1 — Make the columns full height

**Today:** each lane is only as tall as its cards, so short lanes (Specify has
one card, Design has one) float as stubby boxes while busy lanes (Implement,
Recon) run long. The board looks ragged and there's dead space below the short
lanes.

**What good boards do** (from the inspiration board): the lane is a *container*
that fills the screen top to bottom. Its title stays pinned at the top, the
cards scroll *inside* the lane, and there's a quiet action pinned at the bottom.
Trello, Jira and GitHub Projects all work this way.

### Options

- **A. Full-height lanes, each scrolls on its own (recommended).**
  Every lane is the same height and fills the viewport. The lane header (dot +
  name + count) stays stuck to the top as you scroll its cards. The whole board
  no longer scrolls as one tall page; instead each lane scrolls independently.
  *Why:* it's the pattern the founder already recognises from every kanban tool,
  it kills the ragged dead space, and a busy lane never pushes the page down and
  drags its calm neighbours with it.
  *Informed by:* Trello, Jira board, GitHub Projects (all three in the
  inspiration board show sticky header + internal scroll).

- **B. Full-height lanes, but the whole board scrolls together.**
  Lanes fill the height but there's one shared vertical scrollbar. Simpler to
  build, but a long lane still forces you to scroll past empty space in the
  short lanes next to it — it only half-solves the ragged feeling.

- **C. Leave lanes content-sized, just cap and centre them.**
  A smaller change, but it doesn't give the founder the "full height" they
  asked for, and short lanes still look stubby.

**Recommendation: A.** It's the established convention, it directly answers
"full height", and it makes the board feel calm and deliberate rather than
ragged. The mockup shows this: try scrolling inside the Recon and Implement
lanes — the headers stay put.

### The pinned bottom action

Because each lane now has a clear bottom edge, there's a natural home for a quiet
per-lane action. **Important Sulis rule:** a change always *starts* at Recon —
you can't drop a new change straight into Review. So this is **not** a "+ add a
card" in every lane (that pattern lies about how Sulis works). See Concern 3 for
what goes there instead — a single global "Start something new", with at most a
subtle "Start here" hint under the Recon lane only.

### Accessibility

- Each lane is a labelled region (it already announces "Recon — 3 changes" to a
  screen reader); that's preserved.
- Internal scroll containers stay keyboard-reachable — you can tab to a lane and
  scroll it; focus never gets trapped.
- The sticky header keeps the lane name visible while scrolling, which helps
  anyone navigating by keyboard keep their place.

---

## Concern 2 — Replace the duplicative stage pill with three real signals

**Today:** every card wears a "RECON · 1/6" pill. The "RECON" part just repeats
the lane the card is sitting in — it's noise. The "· 1/6" part (how far along the
six-stage journey) is the one genuinely useful bit, because it's a progress
sense the eye doesn't get from lane position alone.

**The principle** (from the inspiration board): a card should carry *signals the
lane can't give you*. So we drop the stage **name**, keep the slim **`· N/6`
step dots** (the one non-redundant part of the old pill), and replace the rest
with **three signals**, each answering a different at-a-glance question:

1. **"Waiting on you" — does this change need me right now?** (the loudest)
2. **Change-health — is this on track or going sideways?** (the middle read)
3. **Activity — is something happening here right now?** (the quietest read)

### The top line: handle (left) · probe + relative time (right) — stripped to the essentials

The card's **top line carries two things on one row**: the change **handle**
(`CH-XXXXXX`) on the **left**, and a stripped-down liveness read — **just the
probe dot + the relative time** — on the **right**, opposite it.

- **Handle, top-left — small and muted.** The `CH-XXXXXX` handle is back on the
  card face (an earlier draft removed it entirely — that was an over-correction).
  It's kept deliberately small and quiet (mono, muted-foreground), just enough
  to identify a card at a glance without competing for attention. The full handle
  is also still on the card link's accessible name (`aria-label="Change CH-… :
  <intent>"`) for assistive tech.
- **Probe + time, top-right — pared right back.** The previous round showed a
  three-part read (state word + dot + "last active 6h ago"). The founder pared
  it down: **drop the state WORD** ("Working / Live / Idle" gone) **and drop the
  "last active" prefix**, leaving only the **probe dot + the bare relative
  time**:

  > `CH-01KSJA` ········· **● now**
  > `CH-01KK8G` ········· **● 12m**
  > `CH-01KP7C` ········· **● 6h**
  > `CH-01KD9N` ········· **● 1w**

  It stays top-right on the same row as the handle. The visible text is purely
  the relative time (now / 12m / 6h / 1w); the **state itself is carried by the
  probe** (see the accessibility note below — fill / motion / shape + a
  screen-reader label, never colour and never a word).

### The foot: full-width centered "Waiting on you" XOR change-health (the founder's rule)

**The foot carries exactly ONE triage read.** The two reads — "Waiting on you"
and the change-health state — are **mutually exclusive**, but they are **not
weighted the same**:

- **If the change is waiting on you** → the foot is a **full-width, horizontally
  centered** "Waiting on you — <why>" element that **spans the whole card foot**
  — loud and unmistakable. It keeps its prominent weight (the bold label, the
  1.5px solid warning border, the warning-triangle icon), now stretched edge to
  edge with the text centered. The **change-health state is hidden**.
- **If it is not waiting on you** → the foot shows the **change-health state**
  (On track / Worth a look / Off track + its reason). Health is the **quieter
  default**: it does *not* go full-width or centered — a left-aligned,
  content-width badge is fine, because health is the resting, secondary read.

**Never both.** The founder's reasoning: when a card needs you, "needs you" is
the *only* status that matters — so it earns the loud full-width treatment, and
the secondary health read moves to the card detail / hover rather than crowding
the board. The full-width centered waiting element makes "this one needs you"
impossible to miss when scanning a busy lane, while the quieter left-aligned
health badge keeps the resting cards calm.

There is **no top banner** and **no left-edge colour stripe**. Every card has the
same shape (**top line [handle · probe+time] → step dots → intent → slug →
foot**), so a founder scanning the board reads the handle and the probe+time in
the same place on every card, and reads a single triage verdict at each card's
foot. Whichever read is shown, its trailing *why* / reason truncates first so it
never wraps.

### Why the colour stripe is gone (and nothing is lost)

The old left-edge stripe was **colour-only** — a bar of warning colour with no
word and no shape. That's exactly the kind of cue that disappears for a
colour-blind founder or in greyscale, so it was never carrying real
accessibility weight; the icon + "Waiting on you" label beside it was already
doing the actual work. Removing the stripe therefore **loses no accessible
signal** — the carrier was always the label + icon, and that stays. (This is
stated explicitly in the Accessibility subsection below.)

### The visual hierarchy — top line read, one-line foot verdict

A founder scanning the board answers a few questions in one sweep. The refresh
splits them by **where on the card** they live, and the hierarchy is carried by
**weight, border and icon** — never by a colour stripe or by breaking card
consistency:

- **Top line — handle (left) + probe + relative time (right).** The handle is a
  small, muted identifier; on the right of the same line, the **probe dot + the
  bare relative time** answer *is anything running here, and how stale is it* —
  taken before the eye moves down. No state word: the probe's fill/motion/shape
  carries the state (with a screen-reader label), the visible text is just the
  time.
- **Foot, when the change needs you — full-width centered "Waiting on you —
  why."** The loud read. It **spans the whole card foot, text centered**, and
  stands out by **weight**, not colour: a heavier **1.5px solid warning border**,
  a **bold label**, and a **warning-triangle icon**. Even in pure greyscale it is
  unmistakably the heaviest thing on the card. It carries a short *why* ("a
  decision" / "a question" / "blocked"). When this is shown, the health state is
  **hidden** — "needs you" is the only verdict that matters.
- **Foot, otherwise — the change-health state.** A labelled badge (word + shape:
  a check / a dash / a warning triangle), thin 1px border. Shown **only when the
  change is not waiting on you** — a quieter "is anything drifting?" read.

So each card's foot is a **single verdict**: either "this needs you" or "here's
its health". The mockup shows a realistic mix — some cards waiting on you (health
hidden), the rest showing health (on track / worth a look / off track); some
working/now, one live, most idle across varied recencies — so the board reads as
a real triage surface at a glance. (Note `plan-work-listready-gate` in Review is
*waiting on you* yet happens to be on track: because it needs your sign-off, the
foot shows only "Waiting on you" and its health lives on the card detail — the
two reads are independent, and the rule keeps the board's foot uncluttered.)

### Signal 1 — "Waiting on you" (the needs-founder-input flag)

The most important new signal: a clear, prominent flag for when a change is
**blocked on the founder** — it needs their input or decision before it can move.
It ties directly to the board's existing **"Needs attention"** concept: the top
bar already has a "Needs attention" filter, and the server already computes a
per-change attention verdict (see the build note below). The card flag and the
filter share the same warning vocabulary on purpose, so the founder reads them
as one idea — "the filter shows me exactly the cards wearing this flag."

The chip also carries a short *why* ("a decision", "a question", "blocked"),
taken from the three reasons the server already distinguishes — so the founder
knows what kind of input is owed before they even open the card. (In a narrow
lane the *why* truncates first; the icon + "Waiting on you" label are never
dropped.)

### Signal 2 — Change-health state (the middle read)

**This replaces the earlier diff `+/−` idea entirely.** Lines added/removed
aren't a measure of success — a big diff isn't "more done" and a small one isn't
"behind". So instead of *how big is this change?* the middle signal answers the
question that actually helps a founder triage: **is this change on track, or
going sideways?** It's a per-change *health* read.

**Three levels, each a word + a shape (never colour alone):**

- **On track** — a **check** + "On track". The calm resting state: nothing to
  look at. (Tinted with the positive status background.)
- **Worth a look** — a **dash** + "Worth a look". A neutral nudge: not broken,
  but something's slightly off and you might want to glance. (Muted-neutral.)
- **Off track** — a **warning triangle** + "Off track". The change is drifting:
  failing tests, missing the artifacts it should have for its stage, or
  building past what was agreed. (Tinted with the destructive status
  background.)

**It's derived from quality checks against the change's stage, NOT activity
volume.** Three inputs roll up into the single verdict:

- **Rigor-for-stage** — does the change have the artifacts it *should* have for
  where it sits? A spec before design, a design or plan before implementing,
  tests alongside the code. Missing them is the classic "vibe-coding" drift —
  code appearing with nothing behind it — and pulls the health down.
- **Tests** — is the change's CI / test state green or red? Red tests are the
  clearest "off track" signal there is.
- **Scope drift** — is it building **beyond** what the spec or plan said? Work
  ballooning past the agreed boundary is drift even when the tests pass.

The verdict is a single rolled-up read so the founder gets one glance, not three
sub-meters. (Opening the change shows the detail behind it — which of the three
pulled it down.)

**Why a health state and not the diff:** the diff measured *size*; the founder's
sharper question is *direction*. A change can be large and perfectly on track,
or tiny and drifting (a one-line "fix" with no test, building something nobody
asked for). The health state names the thing the founder actually wants to
catch early — a change quietly going sideways — which a line count never could.

### The probe + relative time ("is it running, and how stale?")

The founder pared this read down to its essentials: on the right of the top line,
opposite the handle, sits **just the probe dot + the bare relative time** — no
state word, no "last active" prefix.

The probe has **three states, told apart by fill / motion / shape — never by a
word, never by colour alone**:

- **Working** — a session is live *and* actively moving: a **filled dot with a
  subtle pulse**. Motion is the distinguishing cue. Paired time: `now`.
- **Live** — a session is open but quiet: a **solid filled dot, steady** (no
  motion). Fill tells it apart from idle. Paired time: e.g. `12m`.
- **Idle** — nothing running: a **hollow / outline dot** (ring only, no fill) —
  the shape itself distinguishes it. Paired time: e.g. `6h` / `1w`.

The **relative time is the only visible text** — `now`, `12m`, `6h`, `1w` — so
the founder reads "how stale is this" at a glance, e.g. **● 6h**. The dropped
state word is recovered for assistive tech by a **screen-reader-only label** on
the probe (see accessibility note); sighted users read the state off the probe's
fill/motion/shape.

The pulse is the only motion on the card, so a working change reads as alive
without anything shouting. (Reduced-motion users get a static ring instead, and
the screen-reader label still names the state.)

### Why this set, vs. the earlier drafts

The first draft showed conversation length + a file count. A later draft tried a
diff `+/−` for size. The founder's final rework is sharper than both: a count of
lines or files measures *volume*, and volume isn't success. The three signals
that survive each answer a *decision* question a founder actually has when
scanning the board:

- **"Waiting on you"** — *do I need to act?* (the loudest — the one the old card
  was missing entirely).
- **Change-health** — *is this drifting?* (the middle read — catches a change
  going sideways early, which no size metric could).
- **Activity** — *is anything running?* (the quietest — a real "is it working"
  read, not a binary dot).

Together they let the founder triage the whole board in one sweep — which need
me, which are going sideways, which are alive — which is exactly the hierarchy
the three weights encode.

### Accessibility — the full pass (the founder asked for this explicitly)

This is the deliberate, point-by-point accessibility review of the card. It was
re-run after the foot-row rework, and the contrast numbers below were measured
against the **real** `tokens.css` values in **both** light and dark.

**1. Never colour alone — every signal is word + shape/icon.**
- **"Waiting on you"** — warning-triangle **icon** + the literal words **"Waiting
  on you"** + a *why*. Stands out by **border weight (1.5px) + bold label**, not
  colour. Strip all colour and it is still the heaviest, boldest element in the
  row.
- **Change-health** — **word + distinct shape**: "On track" / a **check**,
  "Worth a look" / a **dash**, "Off track" / a **warning triangle**. The three
  are told apart by icon shape + label with zero colour.
- **Probe + relative time** (top-right of the top line) — the state word was
  dropped, so the probe must carry the state **without colour and without a
  word**. It does so two ways: (a) by **fill / motion / shape** — a **pulsing**
  dot = actively working, a **solid filled** dot = live but quiet, a **hollow /
  outline** dot = idle / not running — distinguishable in greyscale and for a
  colour-blind founder; and (b) by a **screen-reader-only label** on the probe
  ("actively working" / "session live" / "idle, not running"), so assistive tech
  still announces the state. The only visible text is the relative time (now /
  12m / 6h / 1w), which is the recency read, not the state.
- **Handle present + on the accessible name** — the `CH-…` handle renders
  small/muted top-left, *and* the card link's **accessible name** carries the
  full handle (`aria-label="Change CH-… : <intent>"`), so assistive tech can
  announce and distinguish each card.

**2. Removing the stripe loses no accessibility.** The old left-edge stripe was
**colour-only** — no word, no shape — so it was invisible to a colour-blind
founder and in greyscale, i.e. it was never a conformant cue under WCAG 1.4.1
(Use of Colour) in the first place. The accessible carrier for "this needs me"
was always the **icon + "Waiting on you" label**, and that is fully retained in
the chip. Net accessibility change from dropping the stripe: **none** — we only
removed a redundant colour-only decoration.

**3. Screen-reader labels + predictable reading order.**
- Each signal exposes text: the probe exposes its state via an `.sr` label
  followed by the visible relative time, so a screen reader hears the full read
  ("idle, not running · 6h") even though the state word is hidden visually; the
  health badge appends a short reason in an off-screen `.sr` span ("Off track —
  tests failing"); the `· N/6` step dots are a labelled image ("Step 4 of 6").
  The probe dot itself is `aria-hidden`, so the reader hears the `.sr` words, not
  the decorative dot.
- When a card is **not** waiting on you, no waiting element exists at all — a
  screen reader hears **nothing** about waiting, which is correct: silence means
  "nothing is waiting on you". The flag is only ever rendered (and announced)
  when one genuinely exists.
- Reading order is now **identical on every card** (handle → probe state + time →
  step dots → intent → slug → the single foot read), because every card has the
  same DOM in the same place. A screen reader hears the handle, then the probe
  state + relative time, then the one foot verdict that applies — "Waiting on you
  — why" on a card that needs you, or the health state otherwise.

**4. AA contrast — verified light + dark against the real tokens.**
Every **text** label clears WCAG AA (4.5:1) in both themes — these are the
load-bearing carriers:

| Element (text) | Light | Dark (re-verified, new surfaces) |
|---|---:|---:|
| "Waiting on you" label (foreground on warning tint) | 17.3:1 ✓ | 6.7:1 ✓ |
| Waiting "why" text (foreground on warning tint) | 17.3:1 ✓ | 6.7:1 ✓ |
| Health "On track" label (on positive tint) | 7.5:1 ✓ | 9.0:1 ✓ |
| Health "Worth a look" label (on lane/muted) | 16.4:1 ✓ | 13.4:1 ✓ |
| Health "Off track" label (on destructive tint) | 16.4:1 ✓ | 9.3:1 ✓ |
| Relative-time text (text-secondary / muted-fg on card) | 7.5:1 ✓ | 5.5:1 ✓ |
| Intent / card title (foreground on card) | 16.1:1 ✓ | 11.6:1 ✓ |

Non-text (graphical) signals in dark, against the **3:1** WCAG 1.4.11 bar:
the waiting-triangle icon **4.8:1 ✓**, the waiting chip's 1.5px warning border
**3.9:1 ✓**, the On-track check **4.1:1 ✓** — all clear 3:1 on the new (lighter)
card surface. (The dark warning was sharpened and the waiting chip's tint/border
mix bumped specifically so the border still clears 3:1 against the lighter card;
see the token-changes subsection below.)

**The light `--warning` icon contrast flag — now FIXED at the token level.**
The previous pass flagged that the coloured **warning icon** (the waiting-on-you
/ off-track triangle) measured only **~2.2:1** on its light tint with the old
`--warning #F59E0B` — under the **3:1 non-text graphical-object bar (WCAG
1.4.11)**. The other two icons already cleared 3:1, and dark theme cleared all
three, so this was a *light-warning-only* gap. **Fix applied:** darken the light
`--warning` one step from `#F59E0B` (amber-500) to **`#B45309` (amber-700)**.
Re-measured against the real tokens, the warning icon now scores **4.84:1 on its
`--bg-warning` tint and 5.02:1 on the card** — clearing not just the 3:1
graphical bar but the 4.5:1 text bar — in light theme. The waiting chip's **1.5px
warning border** rides the same `--warning`, so it now clears 3:1 too (5.02:1 vs
the old amber's ~2:1). The positive check (3.2:1) and destructive triangle
(4.4:1) already cleared 3:1 and are unchanged. **Dark theme is untouched** — its
`--warning #f5b342` already cleared both bars (icon 8.8:1) — so this fix is
light-only and re-themes correctly.

This is a **design-system token change** (`--warning` in the light `:root`), not
a per-component patch, so every surface that uses the warning hue benefits. The
mockup carries the new value verbatim; if adopted it should land back in
`tokens.css` / the upstream `DESIGN_TOKENS.json` so the source of truth matches.
(Note: meaning never rode the icon's colour alone in the first place — the
triangle *shape* + the bold "Waiting on you" / "Off track" *label* always
carried the signal — so this fix strengthens a redundant cue rather than
rescuing a load-bearing one.)

### Dark-mode token changes (founder feedback: dark mode was too flat)

The founder pointed out that in dark mode the **page, the lane, and the card
were all nearly the same dark grey**, so cards didn't read as distinct, raised
surfaces — the board looked like one flat sheet. Worse, the card surface
(`#1e2127`) was actually **darker than the lane** (`--muted #20232a`), so cards
visually *sank into* the board instead of rising above it. That's a problem in
the **dark surface tokens themselves**, so the proper fix is to adjust those
tokens — not patch the mockup's card CSS. These are dark-`:root` changes only;
**light mode is completely untouched.**

The fix builds a clear three-step elevation — **page (darkest) → lane (a step
up) → card (a clear step up, the lightest surface)** — and brightens the card
border so the raised edge reads. The card also gets the existing
`--shadow-float` drop shadow in dark only (no new value — it reuses the token),
reinforcing "raised surface". Separately, the **dark `--warning`** is sharpened
so "Waiting on you" is unmistakably the loudest element.

**Surface elevation + border (the flatness fix):**

| Token | From | To | Why |
|---|---|---|---|
| `--background` (page/board) | `#16181d` | `#121419` | The darkest layer. Dropped one step so the lift up to the lane and card is unmistakable. |
| `--muted` (the **lane** surface) | `#20232a` | `#1b1e24` | The middle layer — now sits **between** page and card (it used to be the *lightest* of the three, which is what inverted the hierarchy). |
| `--card` (the **card** surface) | `#1e2127` | `#262a32` | The top layer — now clearly the **lightest** surface, so a card reads as raised above its lane. (Was previously darker than the lane.) |
| `--border` (card edge) | `#343842` | `#3a3f4a` | Brightened so the card's edge reads against the now-lighter card fill (1.36:1 vs the card — the edge is visible). Also drives `--input`. |
| `--input` | `#343842` | `#3a3f4a` | Kept equal to `--border` (it was before); follows the border bump. |
| `--popover` | `#23262e` | `#2b3038` | Lifted in step with `--card` so popovers stay a touch above cards. |
| `--secondary` | `#2a2e36` | `#2f343d` | Lifted to sit just above the new (lighter) card, preserving its "one step up from card" role. |
| `--shadow-float` | `0 6px 20px rgba(0,0,0,0.45)` | `0 6px 20px rgba(0,0,0,0.55)` | Deepened slightly so the new card drop-shadow reads as elevation against the darker page. (Light shadow unchanged.) |

Resulting luminance steps: **page → lane 1.10:1**, **lane → card 1.16:1**,
**page → card 1.28:1** — each step is visibly distinct while the whole board
stays calm and dark. Text stays well clear of AA on every surface (card title
11.6:1, relative-time 5.5:1, lane name 6.4:1 — all ✓).

**Sharper "Waiting on you" amber (secondary ask — the amber read muddy/pale):**

| Token | From | To | Why |
|---|---|---|---|
| `--warning` (dark only) | `#f5b342` | `#ffb627` | A more saturated, brighter amber-gold so the waiting flag is unmistakably the loudest thing on a dark board. Clears the 3:1 graphical bar as an icon (4.8:1 on its tint) and as text. |
| `--bg-warning` (dark waiting tint) | `color-mix(--warning 18%, --card)` | `color-mix(--warning 24%, --card)` | A warmer, more present fill (the old 18% read washed-out against the new lighter card). Label/why text on it stays at 6.7:1 ✓. |
| `--bg-warning-border` (dark) | `color-mix(--warning 45%, --card)` | `color-mix(--warning 60%, --card)` | The 1.5px waiting border. At 45% against the *lighter* card it only reached 2.8:1 — under the 3:1 graphical bar. 60% restores it to **3.9:1 ✓**, and makes the chip's edge crisper. |

These three warning changes are scoped to the **dark `:root` only** — the light
`--warning` (`#B45309`, the earlier graphical-contrast fix) and the light
`--bg-warning*` recipe are unchanged. The dark `--bg-positive*` / `--bg-destructive*`
tints keep the standard 16%/45% recipe (re-derived automatically against the new
lighter card; both health labels re-verified at 9.0:1 and 9.3:1 ✓).

One mockup-only CSS change rides alongside these tokens: the waiting chip's
**`.why` text switched from `--text-secondary` to `--foreground`**. With the
louder dark warning tint, `--text-secondary` (muted-foreground) would land at
3.2:1 — under AA — so the why now uses the full foreground and stays subordinate
to the bold label by **weight** instead. In light theme this only *raises*
contrast, so light is unaffected.

**Where these land when built:** all of the above are dark-`:root` values in
`apps/cockpit/client/src/tokens.css` (and upstream in `DESIGN_TOKENS.json`).
The mockup carries them verbatim in its dark token block so the founder can see
the improved dark board directly. No invented one-off hex sits in any card CSS —
every change is a token change, recorded here.

**5. Reduced motion.** The "Working" activity pulse has a
`prefers-reduced-motion: reduce` fallback to a **static ring** — the animation
stops and the "Working" label still names the state.

**6. Keyboard + focus.** Each card is a focusable link with a visible focus ring
(`outline: 2px solid var(--ring)`), and the "Start something new" button and the
Recon "Start here" both have the same visible `:focus-visible` ring. Everything
is keyboard reachable; nothing depends on hover.

All tints ride the **signed status-tint recipe** already in `tokens.css`
(`--bg-*` + `--bg-*-border` + a dark-neutral label) — no new colours invented.

### Honest build note — what the data feed supports today vs. needs adding

I checked the real wire types (`apps/cockpit/shared/api-types.ts`) and the
server (`needsAttention.ts`, `detectOpenBlocker.ts`, `computeStatus.ts`). Where
each of the three signals stands:

| Signal | State of the data today |
|---|---|
| **Change-health (On track / Worth a look / Off track)** | **Mixed — its inputs are at different stages of readiness, and the rolled-up verdict is new.** Of the three inputs: **tests** (CI / test state, green vs red) is the most available — it's a real status the change either has run or hasn't. **Rigor-for-stage** (does the change have a spec before design, a design/plan before implement, tests with the code) is **checkable today from the change's own artifacts** — we already know the stage and can see which artifacts exist; what's new is *codifying the rule* ("at this stage you should have X") and evaluating it. **Scope drift** (building beyond the spec/plan) is the most **heuristic / genuinely new** — there's no existing detector that compares what's being built against what was agreed; it needs new logic. And the **single rolled-up health verdict on the board feed** doesn't exist yet either: today there's no `Change.health` field — the verdict (and which input pulled it down) has to be computed server-side and added to the board list. |
| **Liveness "Working / Live / Idle" + recency** (the elevated top-of-card line) | **Partly exists.** The board feed's `Change.liveness` already gives `running` / `not-running` / `unknown` — that covers **Live** vs **Idle**. The new **"Working"** sub-state (live *and actively moving*) is **not** represented yet: `running` is currently binary. It needs a small "recently active" signal added (e.g. last-output timestamp, or a moved-in-last-N-seconds flag) to split "Working" from a quiet "Live". The **recency** half of the elevated line ("last active 6h ago") needs a **last-activity timestamp** on the feed — the same last-output timestamp that splits Working from Live can drive it, so the two needs share one field. ("now" is just recency under a small threshold while Working.) |
| **"Waiting on you"** | **The logic exists; not yet on the board feed.** The server already computes this: `needsAttention()` returns `{ flagged, reason: "blocked" \| "waiting-on-decision" \| "stopped-mid-reply" }`, and the "Needs attention" top-bar filter already routes through it server-side via search. But that verdict rides `ChangeStatus` (the *per-change* status read), **not** the board's `Change` list. Shipping the per-card flag means surfacing `needsAttention` (the `flagged` boolean + the `reason`, which feeds the banner's *why*) on the board feed for every card at once. **No new detection logic — just exposing the existing verdict on the list endpoint.** |

**Honest summary of what's free vs. new for change-health:**

- **Exists today:** the **tests** input (CI / test state); the **rigor-for-stage**
  input is *checkable* from the change's artifacts (we know the stage and which
  artifacts exist — what's new is encoding the per-stage expectation).
- **New / heuristic:** **scope-drift** detection (no existing comparison of
  built-vs-agreed); and the **single rolled-up health verdict** surfaced on the
  board feed (no `Change.health` field today — it has to be computed and added).

**Overlap to flag:** scope-drift and the rigor-for-stage rules overlap directly
with the in-flight **"change-stage OODA spiral"** work (`change-stage-ooda-spiral`,
sitting in Specify on this very board), which is about a stage-level feedback
loop and drift detection. The change-health state should **consume that work's
drift signal rather than build a second, parallel detector** — they're the same
underlying question ("is this change drifting from where it should be?") seen
from two surfaces (the board card vs. the stage loop). Worth sequencing so
health rides the OODA spiral's output.

So: of the three card signals, **"waiting on you"** is essentially free (lift an
existing verdict onto the list), **activity** needs one small new "recently
active" flag, and **change-health** is the most ambitious — one input is ready
(tests), one is checkable-but-needs-rules (rigor-for-stage), and one is genuinely
new (scope drift), all rolled into a new board-feed verdict. The mockup shows all
three at their recommended end state with realistic sample data. If change-health
ships in stages, the honest fallback is to start with **tests + rigor-for-stage**
(two levels: On track / Off track) and add **Worth a look** + scope-drift once the
OODA-spiral drift signal lands.

---

## Concern 3 — Add a visible way to start a change

**Today:** there's no button on the board to start a new change. The empty-board
state guides you, but once you have changes in flight there's no front door.

**The Sulis-specific rule that decides this:** a change always **starts at
Recon**. You never add one straight into "Review" or "Ship". That single fact
rules out the obvious kanban pattern (a "+" at the bottom of every lane), because
a per-lane "+" would imply you can start a change in any stage — which is false.

### Options

- **A. One global "Start something new" button in the top bar (recommended).**
  A single, always-visible primary button living in the persistent top bar
  (next to the product switcher / Board tab), so it's there on every screen, not
  just the board. This is also exactly where the **already-built-but-parked**
  "Start something new" button belongs — the design just gives it its home.
  *Why:* it matches how every change actually begins (at Recon), it's reachable
  everywhere, and it revives real work that's sitting on the shelf.
  *Informed by:* Jira "Create", GitHub "New", Trello "Create" — all keep one
  prominent global new-action in the top bar.

- **B. Global button + a subtle "Start here" under the Recon lane.**
  Option A, plus a quiet secondary affordance pinned at the bottom of the Recon
  lane only (never the other lanes). This leans on the new full-height lanes
  from Concern 1 — the pinned bottom slot finally has a use. It reinforces
  "changes begin at Recon" visually.
  *Why:* it's a nice touch and honest about the lifecycle, but it's optional —
  the global button is the load-bearing affordance.

- **C. Per-lane "+ add" in every column.**
  The standard kanban pattern — but rejected for Sulis, because it implies you
  can start a change in any stage, which contradicts the Recon-only rule.

**Recommendation: A as the primary, with B's "Start here" hint under Recon as an
optional secondary.** The global top-bar button is the real answer; the Recon
hint is a tasteful reinforcement now that the lanes are full height.

### Where it sits

In the persistent top bar, which today reads: *product switcher · Board tab ·
(open change tabs) · settings · theme toggle*. The "Start something new" button
slots in as a primary action near the left (just after the Board tab) so it
reads as "the main thing you do here", styled with the brand primary
(`--primary`) and the pill button radius the tokens already define. The mockup
shows it in place.

### Accessibility

- It's a real button with a clear label ("Start something new"), keyboard
  focusable, with a visible focus ring (`--ring`).
- As the primary action it uses the primary colour, but it's also the only
  filled button up there — so it stands out by shape and weight, not colour
  alone.
- The optional Recon "Start here" is a secondary, quieter style (outline, not
  filled) so the two never compete for "primary".

---

## Concern 4 — Responsive behaviour (the board has to work on a small screen)

**Today:** at small widths the board breaks. Confirmed at 390px (a typical
phone): the top bar overflows — "Start something new" wraps to two lines and the
settings + theme controls get pushed off the right edge; the stage/filter chip
row runs off-screen and gets cut; and the six-lane board shows only about one
lane, forcing awkward one-at-a-time horizontal scrolling with no sense of where
you are.

**The principle:** the board is the same board at every size — same cards, same
tokens, same dark elevation, same accessibility — it just *re-lays-out* as the
screen narrows. We pick three clear breakpoints and define exactly what the
board does at each. The card design never changes; only how the lanes are
arranged and how the chrome folds.

### The breakpoints

| Name | Width | Board layout |
|---|---|---|
| **Desktop** | ≥ 1100px | The current six full-height lanes, side by side. **Unchanged.** |
| **Tablet** | 600–1099px | Lanes stay side-by-side but the board **scrolls horizontally**, each lane held at a comfortable min-width (~260px) so none is squished. |
| **Mobile** | < 600px | **One lane, full-width, at a time.** The stage chips become the lane switcher; swipe/snap moves between lanes. |

The 1100px threshold is where six lanes at a comfortable width stop fitting
without squishing; below it we'd rather scroll than crush. The 600px threshold
is where even two comfortable lanes side-by-side stops being worth it on a phone,
so we switch to the strong one-lane pattern.

### Desktop (≥ 1100px) — unchanged

Six full-height lanes side by side, sticky headers, internal scroll — exactly
the layout from Concern 1. Nothing about the desktop experience changes; the
responsive rules below only *add* behaviour at narrower widths.

### Tablet (600–1099px) — lanes scroll sideways, nothing squished

- The board switches to a **horizontally-scrolling row** of lanes, each at a
  comfortable minimum width (~260px) so a lane is never crushed. You scroll the
  board left/right to reach later stages; lanes lightly snap into place.
- The **top bar condenses** so nothing wraps or clips: the product name text and
  the "Board" tab label fold away (the brand mark + the board icon stay), and
  **"Start something new" becomes a compact "+ New"** primary button — still the
  one filled action, still keyboard-reachable, just no longer able to wrap the
  bar. Settings + theme stay as icons.
- The **filter / stage chip row scrolls horizontally** instead of overflowing, so
  every chip — including **"Needs attention"** — stays reachable. The search
  field stops greedily taking all the width.

### Mobile (< 600px) — one lane at a time, the stage chips drive it

This is the strong pattern the founder asked for, and it **reuses the controls
that already exist** rather than inventing a new mobile widget:

- **One full-width lane fills the screen at a time.** The board is a
  horizontally-snapping track; each lane is exactly one screen wide, so you only
  ever see one stage's cards, full-width. **The card itself is unchanged — it
  just gets the full width of the screen.**
- **The existing stage chips become the lane switcher.** The same
  Recon / Specify / Design / Implement / Review / Ship chips the founder already
  knows now sit in a horizontally-scrolling rail above the board and act as
  **tabs**: tap a stage → that lane snaps into view and fills the width. The
  active stage's chip is the selected tab (it stands out by weight + fill + its
  stage dot, never colour alone), and **each chip shows that lane's count** (e.g.
  "Recon 4") so you know how much is in each stage before you switch.
- **Swipe still works.** You can swipe left/right between lanes directly; the
  selected chip follows whichever lane you land on, so the rail always reflects
  where you are.
- **"Needs attention" stays in the same rail** as a reachable filter toggle,
  wearing the same warning vocabulary as the card flag — so the one filter the
  founder most wants on a phone is never lost.
- The search field collapses to a single **icon tap-target** in the rail so it
  doesn't eat a phone's width, while staying reachable.
- The **top bar drops to pure essentials** — brand mark, the compact "+ New"
  primary action pushed to the right cluster, and the settings + theme icons —
  all on one row at a fixed height, so it can never wrap or clip at 390px.

### Why reuse the stage chips (not a new mobile control)

The founder already reads the six stage chips as "the stages of the board". On a
phone, "which stage am I looking at" *is* the only navigation question — so the
chips are the natural switcher. Reusing them means **one mental model across all
sizes** (Jakob's Law / consistency): the chips that filter/label stages on
desktop are the same chips that *pick* a stage on mobile. No new concept to
learn, and the count on each chip does double duty as a "how full is this stage"
read.

### Accessibility + touch (carried through every breakpoint)

- **Touch targets ≥ 44px** on mobile: every lane-switcher chip and the search
  icon are at least 44px tall, comfortably tappable.
- **The switcher chips are real tabs**, not styled divs: each is a `<button>`
  with `role="tab"` and `aria-selected`, inside a `role="tablist"` labelled
  "Pick a stage to view". A keyboard user can focus and activate them; a screen
  reader announces the selected stage. "Needs attention" is a proper toggle
  (`aria-pressed`).
- **Keyboard + focus ring** survive at every size — the chips, the compact
  "+ New", the cards all keep their visible `:focus-visible` ring.
- **Everything from the desktop card is intact** at mobile width: the
  handle · probe + time top line, the full-width "Waiting on you" XOR health
  foot, the word/shape signals + screen-reader labels, AA contrast on the real
  tokens, the reduced-motion fallback, and the dark page → lane → card
  elevation. Responsive **re-lays-out** the board; it changes **no** card
  internals and **invents no** new colours — all the same tokens.
- The full label "Start something new" is preserved on the button's
  **accessible name** even when the visible text condenses to "+ New", so
  assistive tech still announces the full action.

### Demonstrable in the mockup

All of this is baked into `MOCKUP.html` with **real CSS media queries**, so the
founder can just **resize the browser window** and watch the board adapt:
wide → six lanes; medium → lanes scroll sideways at a comfortable width;
phone-width → one lane at a time with the stage-chip switcher (tap a chip or
swipe to move between lanes; the active chip and counts update live). Light and
dark both stay correct at every width.

---

## Unknown + empty states (the honest ends the first draft missed)

The first pass only drew the **healthy, populated** board — every card had a
real liveness, a real recency, and a confident health verdict, and every lane
had cards in it. A real board doesn't always look like that. A brand-new change
has **no signal yet**; a session record can go **missing**; a lane or the whole
board can be **empty**; the feed can **fail to load**. If we render those as if
they were the healthy ends — a fresh change showing a green "On track", a
missing session showing a confident "Idle", a null timestamp showing "now" — the
board *lies*. This section adds the missing states, and the guiding rule for all
of them is the same: **when we don't know, the board says so — quietly,
honestly, and never with a falsely-positive (green) or falsely-confident cue.**

Every one of these reads is built the same accessible way as the rest of the
card: a **word + a shape**, a **screen-reader label**, **muted/neutral** colour
that's distinct from both the positive and the destructive states, and **never
colour alone**. All values are the real `tokens.css` — nothing invented — and
each was contrast-checked in **both** light and dark.

### 1. Health "not assessed yet" (FR-31)

**When:** a change with **no tests run and none of the artifacts its stage
expects** — e.g. a freshly-created Recon change. There is genuinely nothing to
judge health on yet.

**Treatment + wording:** a neutral badge reading **"Not assessed yet"** with a
**hollow outline circle** (an empty gauge — "nothing measured yet"), on the muted
surface with a **dashed** border. It is deliberately **NOT** the positive "On
track" (a green tick on a change that's done nothing is a lie) and **NOT** the
destructive "Off track" (it isn't failing — it simply hasn't started). It shares
the muted surface with "Worth a look" but is told apart by a **different word**
and a **different shape** (hollow circle vs. the dash), and its label uses the
quieter `--text-secondary` so it reads as the calmest, most provisional state on
the board. SR reason: *"no checks have run for this stage yet"*.

**Why it's honest:** it names the absence of a verdict instead of inventing one.
A founder scanning the board can tell a brand-new change apart from a genuinely
healthy one at a glance — which a fake "On track" would actively hide.

### 2. Liveness unknown (FR-41)

**When:** the session record is **missing or malformed** — we can't tell whether
anything is running.

**Treatment:** a **distinct "unknown" probe** — a **faint dashed ring with a
centred "?"** — clearly different from Idle's crisp solid outline dot. It must
**not** look like a confident Idle, because "we don't know" and "nothing is
running" are different facts. SR label: **"status unknown"**. The dashed edge +
the "?" + the lowered opacity carry the meaning in greyscale and for a
colour-blind founder; colour does no work here.

**Why it's honest:** Idle is a *confident* read ("a session exists and it's
quiet"). Unknown is the *absence* of a read. Giving them different shapes stops
a missing/broken session masquerading as a calm, healthy idle change.

### 3. No recency (FR-42)

**When:** `lastActivityAt` is **null** — there's no last-activity timestamp.

**Treatment:** **omit the time entirely.** The probe shows alone, with a muted
**em-dash** ("—") standing in for the time slot (the dash is `aria-hidden` so a
screen reader simply hears the probe's state with no time). We **never** print
"now" — "now" is a positive recency claim, and a null timestamp is the opposite
of a claim.

**Why it's honest:** "now" would tell the founder the change was just active when
in fact we have no idea. An em-dash reads as "no time recorded", which is the
truth. (The fresh Recon card shows this paired with the unknown probe.)

### 4. Empty board — first run (J-8)

**When:** **zero changes anywhere** — the first thing a brand-new user sees.

**Treatment:** the lane grid is replaced by a centred empty state that makes the
**"Start something new"** front door the **hero** — a single prominent filled
primary pill (the same affordance as the top bar, given centre stage), under a
one-line plain-English invite: *"Your board is empty. Every piece of work begins
as a change — start your first one and it will appear here."* Nothing else
competes for attention; there's exactly one thing to do.

**Why it's honest (and kind):** an empty board isn't an error — it's the
beginning. Treating it as the first-run moment (one clear call to action, warm
copy) turns "there's nothing here" into "here's how to start", which is what a
first-time founder needs.

### 5. Empty lane (a stage with zero changes in a populated board)

**When:** the board has changes, but **one stage is empty** (in the mockup,
Design).

**Treatment:** the lane is **never collapsed or hidden**. It keeps its full
height, its header (dot + name), and its **count badge showing 0**, and shows a
quiet **"Nothing here yet"** placeholder in a faint dashed outline. Muted only —
no status colour, because an empty stage is neither good nor bad.

**Why it's honest:** a missing lane would make the board's shape jump around as
work flows through, and would hide the fact that a stage is simply empty (vs.
broken). A stable, full-height lane with a visible "0" tells the founder exactly
what's true: this stage has no work right now.

### 6. Feed failed to load (the bonus state)

**When:** the changes feed **errors out**.

**Treatment:** a **calm** centred panel — a neutral alert icon on the destructive
tint (word + tint, never the red as a full-bleed alarm), **"Couldn't load your
changes"**, a one-line plain reassurance that it's usually temporary, and a
single outline **Retry** button. It uses `role="alert"` so assistive tech is
told, but it deliberately doesn't shout — a transient load failure isn't a
crisis.

**Why it's honest:** it distinguishes "we couldn't load" from "you have no
changes" — two very different facts that a naïve empty state would conflate. The
founder gets the truth (load failed) and the one action that fixes it (Retry),
without alarm.

### Accessibility note (all six, both themes)

- **Never colour alone.** Every state carries a **word + a shape**: "Not
  assessed yet" + hollow circle; the unknown probe's dashed "?" ring; the empty
  lane's "Nothing here yet" + dashed slot; the empty board's title + hero
  button; the feed error's title + Retry. Strip all colour and each is still
  legible.
- **The "no signal yet" states are muted, not coloured** — distinct from both
  the positive (green "On track") and destructive (red "Off track") ends, so
  none of them can be mistaken for a healthy or a failing read. A dashed edge is
  the shared visual language of "no signal yet" (unknown probe, unassessed
  health, empty lane, empty slot).
- **Screen-reader truth.** The unknown probe announces *"status unknown"*; the
  unassessed badge appends *"no checks have run for this stage yet"*; the null
  recency em-dash is `aria-hidden` (the reader hears the probe state with no
  time, never "now"); the feed error is a `role="alert"`.
- **AA contrast — verified light + dark against the real tokens.** Every text
  label clears AA (4.5:1) and every graphical cue clears the 3:1 bar (WCAG
  1.4.11), in **both** themes:

| Element | Light | Dark |
|---|---:|---:|
| "Not assessed yet" label (`--text-secondary` on muted) | 7.2:1 ✓ | 6.4:1 ✓ |
| "Not assessed yet" hollow-circle icon (graphical, 3:1 bar) | 4.4:1 ✓ | 6.4:1 ✓ |
| Unknown probe — dashed "?" ring (graphical, 3:1 bar, on card) | 4.7:1 ✓ | 5.5:1 ✓ |
| "Nothing here yet" placeholder (muted-fg on muted) | 4.4:1 ✓ | 6.4:1 ✓ |
| Empty-board title (foreground on bg) | 17.2:1 ✓ | 14.8:1 ✓ |
| Empty-board body copy (`--text-secondary` on bg) | 7.5:1 ✓ | 7.1:1 ✓ |
| "Start something new" hero (fg on primary) | 5.2:1 ✓ | 6.8:1 ✓ |
| Feed-error title / body (as above) | 17.2 / 7.5:1 ✓ | 14.8 / 7.1:1 ✓ |
| "Retry" button label (foreground on card) | 17.9:1 ✓ | 11.6:1 ✓ |

- **Keyboard + focus.** The hero "Start something new" and the "Retry" button
  are real buttons with the same visible `:focus-visible` ring (`--ring`) as the
  rest of the board; both are ≥38–44px tall.
- **Nothing already-settled regresses.** These are purely *additive* — new probe
  / health / lane / board variants. The healthy card, the full-height lanes, the
  dark elevation, the responsive breakpoints and the existing AA-verified reads
  are all untouched.

**Where these land when built:** all six are rendered with existing `tokens.css`
values — no new colours. The fresh-card states (FR-31/41/42) need three small
feed additions the build note already flagged (a `health: "unassessed"`
possibility, a `liveness: "unknown"` value — which the feed *already* carries —
and a nullable `lastActivityAt`); the empty-board, empty-lane and feed-error
states are pure client render branches off "how many changes / did the fetch
fail", needing no new server data.

---

## Alternate card states (the OTHER states a card can be in)

The content states above (stage, foot verdict, liveness, recency) describe what a
card *says*. These five are the other states a card can be *in* — selected,
interacting, loading, degraded, shipped. They're shown in their own labelled
**"Alternate card states"** frame beneath the live board in `MOCKUP.html` (the
live board already shows the content states). Like everything else on the board,
each is distinguishable by **shape / marker + a word**, never colour alone, and
each is correct in **both** light and dark on the real `tokens.css`. Nothing
already-settled changes — these are purely additive.

### 1. Selected / currently-open

**When:** the change is open in a tab (the active route) — the card the founder
is currently "in".

**Treatment:** marked the active card by **three** redundant cues so it never
leans on colour: (a) a **3px accent left-marker** — a solid `--primary` bar
inset on the card's left edge (a *shape* on the edge, drawn with an inset
box-shadow so the card's content doesn't shift versus a normal card); (b) the
card **border tints to `--primary`** with a **subtle raise** (the existing
`--shadow-float`); and (c) an **"Open" pill** on the top line naming the state in
a *word*. It carries `aria-current="true"` and its accessible name is suffixed
"— currently open".

**Coexists with the focus ring:** the focus ring is an `outline` (drawn *outside*
the border), while selected is border + an *inset* left-bar + the pill — so a
selected card that *also* has keyboard focus shows **both** at once with no
clash. (The selected demo card is shown alongside the focus demo so you can see
they're independent.)

**Accessibility:** shape (left-bar) + word ("Open") + `aria-current`, so it's the
active card in greyscale, for a colour-blind founder, and for a screen reader —
the primary tint is reinforcement only.

### 2. Interaction states — hover / keyboard-focus / pressed

**When:** pointer or keyboard interaction with a card.

**Treatment:**
- **Hover** — a **subtle surface lift**: the settled `.card:hover` already firms
  the border to `--input`; this *adds* a one-step background shift to `--muted`,
  so hover reads as a gentle "this is pointable". (Additive — the settled border
  rule is untouched.)
- **Keyboard focus** — the **visible ring** already present
  (`.card:focus-visible { outline: 2px solid var(--ring) }`). **Confirmed and
  unchanged**; the frame pins it statically (`.isFocus`) so it's visible without
  a real focus.
- **Pressed / active** — a **slight depress**: a 1px downward nudge + an inset
  shadow, so the card reads as pushed in (tactile, not a new colour).

The frame shows one hover card, one focused card, and one pressed card, each
labelled, using the static `.isHover / .isFocus / .isPressed` demo classes (the
real `:hover / :focus-visible / :active` rules drive the live board).

**Accessibility:** none of the three depends on hover to convey *information* —
they're affordance feedback, not signals. The focus ring is the load-bearing one
(keyboard reachability) and is unchanged. Hover/pressed are progressive polish on
top of the always-present focus ring; nothing is keyboard-unreachable.

### 3. Loading / skeleton

**When:** the feed is loading, before data arrives.

**Treatment:** a **calm placeholder skeleton card** — bars where the handle,
probe, two title lines, and the foot will be — **not a spinner**. A gentle
left-to-right **shimmer** sweeps across the bars to read as "loading". The bars
and the sweep are built from existing tokens only (`--muted` fill, a
`--border`→`--muted` gradient for the sweep) — no invented hue. The frame shows a
**short lane of three** skeleton cards (loading reads as a loading *lane*, not
one stray card), at real card width so the layout doesn't jump when data lands.

**Reduced motion:** under `prefers-reduced-motion: reduce` the **shimmer is
dropped entirely** and the calm muted placeholder bars remain — a static
skeleton, no movement.

**Accessibility:** the skeleton region carries `aria-busy="true"` and an
`.sr` **"Loading your changes…"** line, so a screen reader is told it's loading;
the placeholder bars themselves are `aria-hidden` (no meaningless bar
announcements) and the skeleton is **not focusable** (it isn't a real card yet).

### 4. Degraded / partial

**When:** a change's record is **malformed or partial** — the board must never
break over one bad record.

**Treatment:** render the card **minimally and honestly** — the **handle** plus
whatever fields *are* readable, and every unreadable field falls back to the
**same "no signal yet" language** used elsewhere on the board: the dashed **"?"
probe** (liveness unreadable), an **em-dash** (no recency), an empty/dashed step
track ("Stage not readable"), and the dashed **"Not assessed yet"** neutral
(health unreadable). A faint **dashed top edge** marks the whole card as
partially-read, and a quiet italic **"Some details couldn't be read"** line names
the partial state in words. The card **still links / opens**, so the founder can
go investigate — **never a crash, never a blank**.

**Consistency:** this deliberately reuses the **dashed-edge "no signal yet"
vocabulary** already established by the unknown probe and the unassessed-health
badge — a degraded record is just "no signal yet" applied to several fields at
once, so it speaks the same visual language.

**Accessibility:** every fallback is the existing word+shape+SR-label pattern
(the "?" probe announces "status unknown", the em-dash is `aria-hidden` so no
false "now", the health says "this field could not be read"); the card's
accessible name says "details partly unreadable… opens for a closer look". Muted
throughout — distinct from both the positive and destructive ends, so a partial
record can't be mistaken for healthy *or* failing.

### 5. Shipped / terminal

**When:** the change is **shipped** — done, terminal.

**Treatment:** the card reads as **archived** — quiet and out of the active
triage so the live board still dominates. The whole card is **muted** (the
`--muted` surface, the muted border, and a light `opacity` recede). The
**liveness probe is replaced by a static "Shipped" marker** — a check-in-circle +
the word "Shipped" — because nothing runs on a shipped change (no working / idle
to show). There is **no waiting / health foot** (neither read applies once it's
done); the foot instead carries the **ship recency** — "Shipped 3d ago". On
hover the card returns to full strength (it's still openable). Distinct-but-quiet.

**Accessibility:** the "Shipped" marker is a *shape* (check-in-circle) + a *word*,
not a colour; the card's accessible name says "shipped 3 days ago, archived". The
`opacity` is kept at **0.9** (not lower) on purpose so the foot recency text
(`--muted-foreground` on `--muted`, ~4.6:1 at full strength) stays **at/above
AA** once dimmed — the "receded" read comes from the muted surface + the static
marker, **not** from crushing text contrast. The 6/6 step track is filled and
labelled "Step 6 of 6 — complete".

### Accessibility note (all five, both themes)

- **Never colour alone — shape/marker + word on every state.** Selected = accent
  left-bar + "Open" pill + `aria-current`; hover/pressed = surface/depress
  feedback (not signals) over the always-present focus ring; skeleton = calm
  bars + `aria-busy` + an SR "Loading…" line; degraded = the dashed "no signal
  yet" marks + a "some details couldn't be read" line; shipped = the static
  "Shipped" check-marker + word. Strip all colour and each is still legible.
- **Selected coexists with focus** — outline (focus) vs border + inset bar
  (selected) never clash; a selected, focused card shows both.
- **Skeleton screen-reader truth** — the region is `aria-busy` and announces
  "Loading your changes…"; the bars are `aria-hidden` and not focusable.
- **Reduced motion** — the skeleton shimmer has a `prefers-reduced-motion`
  fallback to a **static** placeholder (no sweep), matching the card's existing
  reduced-motion discipline (the "Working" pulse already falls back to a static
  ring).
- **Degraded keeps the "dashed edge = no signal yet" language** consistent with
  the unknown probe and unassessed health — one shared vocabulary for "we
  couldn't read this".
- **AA holds in both themes.** All five ride existing `tokens.css` values; the
  only contrast-sensitive choice is the shipped card's dim, deliberately held at
  0.9 so its recency text stays ≥ AA. The selected `--primary` border/bar clears
  the 3:1 graphical bar in both themes (it's the same `--primary`/`--ring` the
  board already uses for the focus ring and the top-bar button), and the skeleton
  bars are non-informational so carry no contrast requirement.
- **Nothing already-settled regresses.** These are purely additive new card
  variants + one labelled demo frame; the healthy card, the unknown/empty states,
  the full-height lanes, the dark elevation, the responsive breakpoints and every
  existing AA-verified read are untouched. (The one settled rule touched —
  `.card:hover` — is *added to*, not changed: the border firm stays, a muted-bg
  lift is appended.)

**Where these land when built:** all five are pure client render states needing
no new server data — *selected* keys off the active route/open tab, *hover/
focus/pressed* are CSS, *skeleton* is the loading branch of the feed fetch,
*degraded* is the render fallback when a record fails to parse (the board catches
the bad record and renders the minimal honest card instead of throwing), and
*shipped* keys off the change's terminal stage (already on the feed). No invented
colours — every value is `tokens.css`.

---

## The three cross-cutting principles (carried from the inspiration board)

1. **Full-height lanes** with sticky headers and internal scroll — the board
   fills the screen and stops looking ragged.
2. **Cards earn their badges; a clean top line and a one-verdict foot** — drop
   the stage name (the lane already says it). The **top line** carries the small
   muted `CH-…` handle on the left and, on the right, the **probe dot + the bare
   relative time** — *is it running, and how stale?* (e.g. "● 6h"). No state
   word: the probe's fill/motion/shape + a screen-reader label carry the state
   (pulsing = working, solid = live, hollow = idle), never colour or a word. The
   **foot carries exactly one verdict**: if the change is **waiting on you** it
   shows a **full-width, centered "Waiting on you — why"** spanning the card and
   hides the health state (when a card needs you, that's all that matters; health
   moves to the card detail); otherwise it shows the **change-health state**
   (*is it going sideways?*) as a quieter, left-aligned badge. Never both. Keep
   the slim progress dots. No top banner, no colour stripe — hierarchy is carried
   by weight, border and icon, so the structure is identical on every card.
3. **One always-visible "Start something new"** in the top bar — because changes
   start at Recon, not a per-lane "+".

Across all three: colour is always *reinforcement*, never the only signal
(every stage also has its name + lane position; the change-health state carries
a word + a distinct shape — check / dash / warning; "waiting on you" carries an
icon + a bold label + a heavier border — **no colour stripe**; the probe carries
its state by **fill / motion / shape** — pulsing / solid / hollow — plus a
screen-reader label, not by colour or a word), and everything is
keyboard-reachable with a visible focus ring. See Concern 2's **Accessibility —
the full pass** for the explicit light + dark AA contrast table and the
**now-resolved** light `--warning` token fix (darkened `#F59E0B → #B45309` so
the warning icon and chip border clear the 3:1 graphical bar in light theme;
dark theme was already compliant).
