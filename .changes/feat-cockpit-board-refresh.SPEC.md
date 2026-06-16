---
founder_facing: true
---

# Spec — Refresh the cockpit board

**Change:** CH-084CAN · feat

> Grounds on the signed-off design at `.design/cockpit-board-refresh/`
> (`MOCKUP.html` + `IDEAS.md`). The mockup is the visual contract; this spec is
> the behavioural one. Where the two ever disagree, the mockup wins on look and
> this spec wins on behaviour.

## Intent

Refresh the cockpit board so it reads as a calm, deliberate triage surface at a
glance. The board is six lanes work flows through left-to-right (Recon → Specify
→ Design → Implement → Review → Ship); the refresh makes the lanes full-height,
redesigns the change cards around three at-a-glance signals, revives the parked
"Start something new" button, fixes dark mode so cards read as raised surfaces,
and makes the whole board work down to a phone — all on the board's *real*
design tokens, inventing no new colours.

## Scope

**1 — Full-height lanes.** Every lane fills the viewport at the same height; the
lane header (dot + name + count) sticks to the top; cards scroll *inside* each
lane independently; each lane has a clear bottom edge with a quiet pinned action
slot. Kills the ragged "stubby short lane / long busy lane" look. (Design
Concern 1, Option A.)

**2 — Redesigned change cards.** Every card has one identical shape:

- **Top line:** the `CH-XXXXXX` handle (small, muted, top-left) and, opposite it
  top-right, a pared-back liveness read — *just* the probe dot + the bare
  relative time (`● now` / `● 12m` / `● 6h` / `● 1w`). No state word on the face.
- **Step dots:** the slim `· N/6` journey-progress dots (the one non-redundant
  part of the old stage pill; the stage *name* is dropped — the lane already
  says it).
- **Intent, then slug.**
- **Foot — exactly one verdict, never both:**
  - **Waiting on you** (when the change needs founder input) → a full-width,
    horizontally-centered element spanning the card foot, with the bold label,
    1.5px solid warning border, warning-triangle icon, and a short *why*
    ("a decision" / "a question" / "blocked"). The health read is hidden.
  - **Change-health** (only when *not* waiting on you) → a quieter,
    left-aligned, content-width badge: word + shape (check / dash / triangle).

  The three card signals: **"Waiting on you"** (loudest, "do I need to act?"),
  **change-health** (middle, "is this drifting?"), **activity probe** (quietest,
  "is anything running?"). No top banner, no left-edge colour stripe — every
  signal is carried by word + shape/icon + weight, never colour alone.

- **Activity probe — three states by fill/motion/shape:** Working (filled dot +
  subtle pulse, `now`), Live (solid filled dot, steady), Idle (hollow/outline
  dot). The visible text is only the relative time; the state rides the probe
  plus a screen-reader-only label.

**3 — Change-health signal (scoped first cut).** A single rolled-up per-change
verdict on the board feed, derived from quality checks against the change's
stage. **This change ships the cheap first cut: two inputs → two levels.**

- **Inputs (this change):** **tests** (CI / test state, green vs red) and
  **rigor-for-stage** (does the change have the artifacts it should for its
  stage — a spec before design, a design/plan before implement, tests with the
  code).
- **Levels (this change):** **On track** (check) and **Off track** (warning
  triangle).
- Requires a new `Change.health` field computed server-side and exposed on the
  board list feed.

**4 — Revive "Start something new".** One global primary button in the
persistent top bar (just after the Board tab), present on every screen — this is
where the already-built-but-parked button gets its home. Optional quieter
"Start here" affordance pinned under the **Recon** lane only (outline style),
reinforcing "changes begin at Recon". (Design Concern 3, Option A primary + B
secondary.)

**5 — Dark-mode surface elevation + sharper waiting amber.** Dark-`:root` token
changes only (light theme untouched) that build a clear three-step elevation —
page (darkest) → lane (a step up) → card (lightest/raised) — fix the inverted
hierarchy where the card was darker than its lane, brighten the card border, add
the existing `--shadow-float` to cards in dark, and sharpen the dark `--warning`
amber + its waiting tint/border so "Waiting on you" is unmistakably the loudest
element. Specific token values are listed verbatim in `IDEAS.md` and carried in
`MOCKUP.html`; they land in `apps/cockpit/client/src/tokens.css` (and upstream
`DESIGN_TOKENS.json`). One light-theme token fix rides along: light `--warning`
darkens `#F59E0B` → `#B45309` so the warning icon clears the 3:1 graphical bar.

**6 — Responsive breakpoints.** The same board, same cards, same tokens,
re-laid-out at three widths:

- **Desktop ≥ 1100px** — six full-height lanes side by side. Unchanged.
- **Tablet 600–1099px** — lanes scroll horizontally, each held at ~260px min so
  none is squished; top bar condenses ("Start something new" → compact "+ New",
  labels fold to icons); filter/stage chip row scrolls horizontally.
- **Mobile < 600px** — one full-width lane at a time on a snapping track; the
  existing stage chips become the lane switcher (real tabs: `role="tab"` /
  `aria-selected` in a `role="tablist"`), each showing its lane's count;
  "Needs attention" stays in the rail as a toggle; search collapses to an icon;
  top bar drops to brand mark + "+ New" + settings/theme icons on one fixed row.

## Non-goals

- **The "Worth a look" health level and scope-drift detection are out.** The
  three-level health (adding the neutral "Worth a look") and the scope-drift
  input both depend on the in-flight **change-stage OODA-spiral** work, which
  owns drift detection. This change consumes *tests + rigor-for-stage* only and
  ships two levels. Health should later *ride the OODA spiral's drift signal*
  rather than build a second, parallel detector.
- **No new colours or one-off hex.** Every visual change is a design-token
  change recorded in `IDEAS.md`; nothing invented in per-component CSS.
- **No change to the card's internals across breakpoints.** Responsive
  re-lays-out the lanes and folds the chrome; the card design itself never
  changes — it only gets the available width.
- **No light-mode surface changes.** The elevation fix is dark-`:root` only
  (the single light `--warning` graphical-contrast fix aside).

## Acceptance

The board reads as a calm triage surface and the refresh is exercisable:

1. **Full-height lanes** — every lane fills the viewport at equal height; lane
   headers stay pinned while their cards scroll independently; short lanes no
   longer float as stubby boxes.
2. **Card shape** — every card shows handle + probe/time on the top line, `· N/6`
   step dots, intent, slug, and **exactly one** foot verdict. A card that needs
   input shows the full-width centered "Waiting on you — why" and hides health; a
   card that doesn't shows the left-aligned health badge. Never both.
3. **Activity probe** — Working reads as a pulsing dot (static ring under
   reduced-motion), Live as a steady filled dot, Idle as a hollow dot; the
   relative time is the only visible text; each probe carries a screen-reader
   label naming the state.
4. **Change-health** — the board feed carries a `Change.health` verdict computed
   from tests + rigor-for-stage; a change with red tests or missing
   stage-artifacts reads **Off track**, otherwise **On track**; opening the
   change can show which input drove it.
5. **"Start something new"** — a global primary button in the top bar starts a
   change (lands it at Recon) from any screen; the optional Recon "Start here"
   hint, if shipped, is a quieter outline affordance under the Recon lane only.
6. **Dark mode** — page → lane → card read as three distinct elevation steps
   (card is the lightest/raised surface, no longer sinking below its lane); the
   "Waiting on you" amber is the loudest element on a dark board; all text and
   graphical signals clear their WCAG bars (the contrast table in `IDEAS.md`).
7. **Responsive** — at 390px the top bar never wraps or clips, the chip row stays
   reachable, and the board shows one full-width lane with the stage chips acting
   as a working tab switcher; at tablet width lanes scroll sideways without being
   squished; desktop is unchanged.
8. **Accessibility holds at every size** — no signal is colour-only; touch
   targets ≥ 44px on mobile; keyboard reach + visible focus ring on cards, the
   start button, and the switcher chips; the card's accessible name carries the
   full handle + intent.

## Constraints

- **Built on the real tokens.** All colour/spacing/type changes are
  design-token changes in `apps/cockpit/client/src/tokens.css` (mirrored upstream
  in `DESIGN_TOKENS.json`), carried verbatim in `MOCKUP.html`. No invented hex in
  component CSS.
- **The mockup is the visual contract.** `MOCKUP.html` (with real CSS media
  queries for all three breakpoints) is the reference the built board must match.
- **Reuse existing server verdicts where they exist.** "Waiting on you" lifts the
  existing `needsAttention()` verdict (`flagged` + `reason`) onto the board list
  feed — no new detection logic, just exposing it per-card on the list endpoint.
- **New data the feed needs (honest build note in `IDEAS.md`):**
  - a **last-activity timestamp** + a "recently active" flag to split *Working*
    from a quiet *Live* and to drive the relative time;
  - a **`Change.health`** field (tests + rigor-for-stage rolled up) on the board
    list feed.
- **Sequence health behind the OODA spiral.** Don't build a second drift
  detector; this change's health stops at tests + rigor-for-stage and leaves a
  clean seam for the OODA-spiral drift signal to feed the third level later.
- **Keep the "Needs attention" vocabulary shared.** The card "Waiting on you"
  flag and the top-bar "Needs attention" filter share the same warning
  vocabulary on purpose — they're one idea seen two ways.

## Verification Plan

**How we'll know it works — the journeys a founder can run against the built
board:**

- **Triage sweep (the core journey).** Open the board with a realistic mix of
  changes. *Observable:* short and long lanes are equal full height with pinned
  headers; each card shows one foot verdict; cards needing input wear the
  full-width "Waiting on you", the rest wear a health badge; the probe + relative
  time read correctly per card. This is the primary user-facing scenario and its
  outcome (the board renders as a calm one-sweep triage surface matching the
  mockup) is observable.
- **Health is real, not cosmetic.** A change with red tests, and a change sitting
  in a stage without its required artifacts, both read **Off track**; a green,
  well-formed change reads **On track**. *Observable:* the `Change.health` field
  on the feed + the rendered badge agree with the actual test/artifact state.
- **Start something new.** Click the top-bar button from the board and from a
  non-board screen. *Observable:* a new change is created at the Recon stage and
  appears in the Recon lane.
- **Responsive walk.** Resize / load at 1200px, 800px, and 390px. *Observable:*
  desktop unchanged; tablet lanes scroll sideways un-squished with a condensed
  top bar; mobile shows one full-width lane with the stage chips switching lanes
  and the top bar never wrapping at 390px.
- **Accessibility pass.** Greyscale + keyboard-only + screen-reader walk of one
  card and the mobile switcher. *Observable:* every signal survives greyscale
  (word + shape); all interactive elements are keyboard-reachable with a visible
  focus ring; the screen reader announces probe state, foot verdict, and the
  full handle; contrast matches the verified table in `IDEAS.md`.
- **Visual-contract check.** The built board is diffed against `MOCKUP.html` in
  both light and dark — the elevation steps, the sharpened amber, and the card
  layout match.

The mockup carries all of this at its recommended end state with realistic
sample data, so each journey above has a concrete reference to verify against.
