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
